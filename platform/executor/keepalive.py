#!/usr/bin/env python3
"""
Estate Executor Keepalive — self-healing daemon watchdog.

Watches the executor socket and restarts the daemon if it becomes unhealthy.
Designed to survive:
  - daemon.py crashing on missing estate_executor.py
  - socket becoming orphaned (process dead, socket remains)
  - daemon hanging (accepting connections but not responding)

Usage:
  estate-executor-keepalive           # daemonize and watch
  estate-executor-keepalive --check    # print health and exit 0/1
  estate-executor-keepalive --kill     # stop the keepalive and daemon

Install as launchd or run manually. PID written to ~/.estate/keepalive.pid.
"""

from __future__ import annotations

import json
import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

HOME = Path.home()
ESTATE = HOME / ".estate"
# Locate daemon.py relative to this script's path.
# When installed to ~/.estate/bin/, this script is at ~/.estate/bin/keepalive.py.
# daemon.py lives at platform/executor/daemon.py in the repo.
# ../.. from ~/.estate/bin/ is ~/.estate/ so we go two more levels down to
# Documents/code/idp/platform/executor/.
_KEEPALIVE_DIR = Path(__file__).parent.resolve()
if (_KEEPALIVE_DIR / "daemon.py").exists():
    # Running from platform/executor/ during development
    DAEMON_PY = _KEEPALIVE_DIR / "daemon.py"
elif (HOME / ".estate" / "bin" / "daemon.py").exists():
    # Installed to ~/.estate/bin/
    DAEMON_PY = HOME / ".estate" / "bin" / "daemon.py"
else:
    # Installed to ~/.estate/bin/; find daemon.py via repo convention
    DAEMON_PY = (
        _KEEPALIVE_DIR
        / ".."
        / ".."
        / ".."
        / "Documents"
        / "code"
        / "idp"
        / "platform"
        / "executor"
        / "daemon.py"
    )
    if not DAEMON_PY.exists():
        # Last resort: absolute path used during development
        DAEMON_PY = (
            HOME / "Documents" / "code" / "idp" / "platform" / "executor" / "daemon.py"
        )
SOCKET_PATH = os.environ.get("IDP_EXECUTOR_SOCKET", str(ESTATE / "executor.sock"))
KEEPALIVE_PIDFILE = ESTATE / "keepalive.pid"
LOG = ESTATE / "logs" / "keepalive.log"
CHECK_INTERVAL = 15  # seconds between health checks
MAX_RESTARTS = 5  # max restarts per rolling window
RESTART_WINDOW = 300  # seconds (5 min rolling window)

LOG.parent.mkdir(parents=True, exist_ok=True)


def _log(msg: str) -> None:
    ts = time.strftime("%Y-%m-%dT%H:%M:%S")
    line = f"[{ts}] {msg}\n"
    with open(LOG, "a") as f:
        f.write(line)


def _daemon_pid() -> int | None:
    """Find PID of current daemon by checking which process has the socket open."""
    if not Path(SOCKET_PATH).exists():
        return None
    try:
        r = subprocess.run(
            ["lsof", SOCKET_PATH, "-F", "p"], capture_output=True, text=True, timeout=5
        )
        pids = [int(l[1:]) for l in r.stdout.splitlines() if l.startswith("p")]
        return pids[0] if pids else None
    except (subprocess.TimeoutExpired, ValueError, FileNotFoundError):
        return None


def _health_check() -> dict | None:
    """Ask the daemon for its health via --check. Returns parsed JSON or None."""
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.settimeout(3)
            sock.connect(SOCKET_PATH)
            sock.sendall(b'{"verb":"health"}\n')
            data = sock.recv(4096)
            return json.loads(data.decode())
    except Exception:
        return None


def _daemon_check() -> dict | None:
    """Run daemon.py --check directly (no socket needed)."""
    try:
        plugin_dir = DAEMON_PY.parent.parent / "mcp" / "plugins"
        env = {
            **os.environ,
            "EXECUTOR_SOCKET": SOCKET_PATH,
            "PYTHONPATH": str(plugin_dir),
        }
        r = subprocess.run(
            [sys.executable, str(DAEMON_PY), "--check"],
            capture_output=True,
            text=True,
            timeout=10,
            env=env,
        )
        if r.returncode == 0:
            return json.loads(r.stdout)
        return None
    except Exception:
        return None


def _healthy() -> bool:
    """True if daemon is alive and answering on socket."""
    return _health_check() is not None


def _start_daemon() -> int:
    """Start daemon, return PID or -1 on failure."""
    # Ensure socket dir exists
    Path(SOCKET_PATH).parent.mkdir(parents=True, exist_ok=True)

    # Remove stale socket if no process has it open
    if Path(SOCKET_PATH).exists() and _daemon_pid() is None:
        Path(SOCKET_PATH).unlink()
        _log(f"Removed stale socket: {SOCKET_PATH}")

    env = {**os.environ, "EXECUTOR_SOCKET": SOCKET_PATH}
    # Set PYTHONPATH so daemon can find estate_executor
    plugin_dir = DAEMON_PY.parent.parent / "mcp" / "plugins"
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{plugin_dir}:" + existing

    try:
        with open(ESTATE / "logs" / "daemon.log", "a") as logf:
            proc = subprocess.Popen(
                [sys.executable, str(DAEMON_PY)],
                cwd=str(HOME / "Documents" / "code" / "idp"),
                env=env,
                stdout=logf,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
        _log(f"Started daemon PID {proc.pid}")
        time.sleep(3)  # wait for socket to appear

        if _healthy():
            return proc.pid
        else:
            _log("Daemon started but socket not healthy")
            return proc.pid  # still return pid, keepalive will retry
    except Exception as e:
        _log(f"Failed to start daemon: {e}")
        return -1


def _stop_daemon() -> None:
    """Kill the daemon if running."""
    pid = _daemon_pid()
    if pid:
        try:
            os.kill(pid, signal.SIGTERM)
            _log(f"Terminated daemon PID {pid}")
            time.sleep(2)
            # Force kill if still alive
            try:
                os.kill(pid, 0)
                os.kill(pid, signal.SIGKILL)
                _log(f"Force-killed daemon PID {pid}")
            except ProcessLookupError:
                pass
        except ProcessLookupError:
            _log(f"Daemon PID {pid} already gone")
        except PermissionError:
            _log(f"Cannot kill PID {pid} — permission denied")

    # Clean up socket
    if Path(SOCKET_PATH).exists() and _daemon_pid() is None:
        Path(SOCKET_PATH).unlink()


def _watch() -> None:
    """Main keepalive loop. Runs as a daemon."""
    restart_times: list[float] = []
    running = True

    def sigterm_handler(signum, frame):
        nonlocal running
        _log("Received SIGTERM, shutting down keepalive")
        running = False

    signal.signal(signal.SIGTERM, sigterm_handler)

    # Write PID
    with open(KEEPALIVE_PIDFILE, "w") as f:
        f.write(str(os.getpid()))

    _log("Keepalive starting")
    _start_daemon()

    while running:
        time.sleep(CHECK_INTERVAL)

        if not running:
            break

        check = _daemon_check()
        if check is None:
            _log("daemon --check failed — daemon is unhealthy")
        elif not check.get("answering", False):
            _log("daemon socket not answering")
        else:
            continue  # healthy

        # Unhealthy — rolling restart rate limit
        now = time.time()
        restart_times = [t for t in restart_times if now - t < RESTART_WINDOW]
        if len(restart_times) >= MAX_RESTARTS:
            _log(
                f"RESTART LOOP DETECTED: {MAX_RESTARTS} restarts in {RESTART_WINDOW}s. "
                "Stopping keepalive to prevent crash loop."
            )
            _stop_daemon()
            running = False
            break

        _log("Restarting daemon...")
        _stop_daemon()
        restart_times.append(now)
        _start_daemon()

    KEEPALIVE_PIDFILE.unlink(missing_ok=True)
    _log("Keepalive stopped")


def cmd_check() -> int:
    """Check daemon health, print result, exit 0 if healthy else 1."""
    check = _daemon_check()
    if check:
        print(json.dumps(check, indent=2))
        return 0 if check.get("answering") else 1
    else:
        # Fallback: try socket directly
        health = _health_check()
        if health:
            print(
                json.dumps(
                    {"socket": SOCKET_PATH, "answering": True, "method": "socket"}
                )
            )
            return 0
        print(json.dumps({"socket": SOCKET_PATH, "answering": False}), file=sys.stderr)
        return 1


def cmd_kill() -> int:
    """Stop the keepalive daemon."""
    if KEEPALIVE_PIDFILE.exists():
        try:
            pid = int(KEEPALIVE_PIDFILE.read_text().strip())
            os.kill(pid, signal.SIGTERM)
            _log(f"Sent SIGTERM to keepalive PID {pid}")
            return 0
        except (ProcessLookupError, ValueError):
            KEEPALIVE_PIDFILE.unlink()
    _stop_daemon()
    return 0


def main() -> int:
    if len(sys.argv) > 1:
        if sys.argv[1] == "--check":
            return cmd_check()
        elif sys.argv[1] == "--kill":
            return cmd_kill()
        elif sys.argv[1] == "--help":
            print(__doc__)
            return 0

    # Daemonize
    _log("Forking keepalive")
    pid = os.fork()
    if pid != 0:
        # Parent exits
        sys.stdout.write(f"keepalive PID {pid}\n")
        sys.exit(0)

    # Child: become session leader
    os.setsid()
    # Close stdin, redirect stdout/stderr to log
    sys.stdin.close()
    os.close(1)
    os.close(2)
    open(LOG, "a").close()  # truncate-safe
    fd = os.open(LOG, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
    os.dup2(fd, 1)
    os.dup2(fd, 2)
    if fd > 2:
        os.close(fd)

    _watch()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
