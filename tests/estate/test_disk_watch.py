"""bin/idp-disk-watch's memory brake: measured memory pressure stops ollama, and only ollama.

The founder, 2026-09-10: "no i killed ollama because machine is slow" -- 8GB of RAM and no GPU,
and a resident 7B model took the machine to load 95 with the swap thrashing. ollama's autostart
was removed on 2026-10-24, so the brake is recurrence insurance: the 5-minute tick measures
memory and stops the one process that causes the grind, and says so in the log.

The test never touches the real machine: vm_stat and sysctl are shimmed on PATH, the brake's
target is a uniquely named copy of sleep, and the disk floors are set so the tick takes no
cleanup branch at all.
"""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

WATCH = Path(__file__).resolve().parents[2] / "bin/idp-disk-watch"
# macOS matches the process name, and a process name is at most 16 characters: a longer one is
# truncated and `pgrep -x` would never match it. So the brake target is named "ollama" -- the
# name the founder's ollama actually has -- and the test's stand-in wears that name.
PROC_NAME = "ollama"


def _shims(tmp_path: Path, free_pages: int, swap_used: float) -> Path:
    bindir = tmp_path / "bin"
    bindir.mkdir()
    (bindir / "vm_stat").write_text(
        "#!/bin/sh\n"
        "cat <<'EOF'\n"
        "Mach Virtual Memory Statistics: (page size of 4096 bytes)\n"
        f"Pages free:                                {free_pages}.\n"
        "Pages active:                              200.\n"
        "Pages speculative:                           0.\n"
        "EOF\n"
    )
    (bindir / "sysctl").write_text(
        "#!/bin/sh\n"
        "cat <<'EOF'\n"
        f"total = 5120.00M  used = {swap_used:.2f}M  free = 525.25M  (encrypted)\n"
        "EOF\n"
    )
    for f in (bindir / "vm_stat", bindir / "sysctl"):
        f.chmod(0o755)
    return bindir


def _stand_in(bindir: Path) -> subprocess.Popen:
    """A live process that macOS calls "ollama", without being one.

    A copied binary is SIGKILLed on this laptop, so the stand-in is the real /bin/sleep wearing
    the name: `exec -a <path>/ollama` sets argv[0], and both pgrep -x and pkill -x match the last
    component of it -- exactly how they match the founder's ollama server.
    """
    return subprocess.Popen(
        ["bash", "-c", f"exec -a {bindir / PROC_NAME} /bin/sleep 300"]
    )


def _run(tmp_path: Path, bindir: Path) -> subprocess.CompletedProcess:
    home = tmp_path / "home"
    (home / ".estate").mkdir(parents=True, exist_ok=True)
    env = {
        **os.environ,
        "HOME": str(home),
        "PATH": f"{bindir}:{os.environ['PATH']}",
        # no disk branch: the tick must not clean, must not notify, must only brake
        "ACT_GB": "0",
        "CRIT_GB": "0",
        "MIN_FREE_GB": "0",
        "DISK_WATCH_BRAKE_PROCS": PROC_NAME,
    }
    return subprocess.run(
        ["bash", str(WATCH)], env=env, capture_output=True, text=True, timeout=60
    )


def _log(tmp_path: Path) -> str:
    return (tmp_path / "home" / ".estate" / "disk-watch.log").read_text()


def test_pressure_stops_the_brake_target_and_says_so(tmp_path):
    bindir = _shims(tmp_path, free_pages=100, swap_used=4594.75)
    _stand_in(bindir)
    time.sleep(0.5)
    assert subprocess.run(["/usr/bin/pgrep", "-x", PROC_NAME]).returncode == 0

    r = _run(tmp_path, bindir)
    assert r.returncode == 0, r.stdout + r.stderr
    time.sleep(0.5)
    assert subprocess.run(["/usr/bin/pgrep", "-x", PROC_NAME]).returncode != 0, (
        "the brake target must be stopped under memory pressure"
    )
    log = _log(tmp_path)
    assert f"memory brake: stopped {PROC_NAME}" in log, log
    assert "memory pressure: free=0M RAM, swap=89%" in log, log


def test_a_healthy_machine_is_left_alone(tmp_path):
    bindir = _shims(tmp_path, free_pages=500000, swap_used=100.0)
    proc = _stand_in(bindir)
    time.sleep(0.5)

    r = _run(tmp_path, bindir)
    assert r.returncode == 0, r.stdout + r.stderr
    time.sleep(0.5)
    assert subprocess.run(["/usr/bin/pgrep", "-x", PROC_NAME]).returncode == 0, (
        "nothing may be stopped when memory is healthy"
    )
    assert "memory brake" not in _log(tmp_path), _log(tmp_path)
    proc.terminate()
