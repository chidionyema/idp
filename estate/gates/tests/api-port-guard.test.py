#!/usr/bin/env python3
"""Falsifier for estate/gates/api-port-guard and its shell layer.

Every refusal case is run against a DECOY: a compiled listener (estatedecoy.c) on a free
port that the test declares protected through ANTHROPIC_BASE_URL. A guard bug can only
kill the decoy, never a live estate service. The agent context is declared with
ESTATE_GUARD_AGENT_ROOT=<this pid>, so the same cases hold in CI, where no harness is an
ancestor. Exit 0 only when every case holds; residual gaps are printed by name, not hidden.

    python3 estate/gates/tests/api-port-guard.test.py
    python3 estate/gates/tests/api-port-guard.test.py --guard estate/gates/tests/fixtures/allow-all-guard
        (the law gate's falsifier: the same cases against a guard that refuses nothing must fail)
"""

import contextlib
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
GATES = os.path.dirname(HERE)
GUARD = os.path.join(GATES, "api-port-guard")
if "--guard" in sys.argv:
    GUARD = os.path.abspath(sys.argv[sys.argv.index("--guard") + 1])
    if not os.path.isfile(GUARD):
        sys.exit(
            f"--guard {GUARD}: no such file (exit 1 is a broken run, not a verdict)"
        )
SHELL_GUARD = os.path.join(GATES, "shell-guard.sh")
SHIMS = os.path.join(GATES, "shims")
results = []
OPTIMUS = (
    "--optimus" in sys.argv
)  # registered measure: the case lines go to stderr, one reading to stdout
_REAL_STDOUT = sys.stdout
if OPTIMUS:
    sys.stdout = sys.stderr


def check(label, ok, detail=""):
    results.append(ok)
    print(
        f"  {'PASS' if ok else 'FAIL'}  {label}"
        + (f"  [{detail}]" if detail and not ok else "")
    )


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def listening(port):
    try:
        socket.create_connection(("127.0.0.1", port), timeout=0.3).close()
        return True
    except OSError:
        return False


def alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


tmp = tempfile.mkdtemp(prefix="apg-")
decoy_bin = os.path.join(tmp, "estatedecoy")
# A copy of the binary THIS process runs, named estatedecoy, so pgrep -x and killall see that
# name. Not sys.executable: on macOS that is a launcher that re-execs as .../MacOS/Python, which
# would rename the decoy back. The copy finds libpython by leaf name through dyld's fallback
# path (sys.base_prefix holds it in a framework build; on Linux the variable is inert).
if os.path.exists("/proc/self/exe"):
    running = os.path.realpath("/proc/self/exe")
else:
    running = subprocess.run(
        ["ps", "-o", "comm=", "-p", str(os.getpid())], capture_output=True, text=True
    ).stdout.strip()
shutil.copy2(running, decoy_bin)
port = free_port()
decoy = subprocess.Popen(
    [decoy_bin, "-I", os.path.join(HERE, "estatedecoy.py"), str(port)],
    env=dict(os.environ, DYLD_FALLBACK_LIBRARY_PATH=sys.base_prefix),
    start_new_session=True,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
)
for _ in range(50):
    if listening(port):
        break
    time.sleep(0.05)
else:
    sys.exit("decoy never listened: the falsifier cannot run (exit 1, not a pass)")
D = decoy.pid


def _teardown():
    for p in (decoy, sleeper):
        with contextlib.suppress(OSError, NameError):  # already gone, or never started
            p.kill()
    shutil.rmtree(tmp, ignore_errors=True)


import atexit  # noqa: E402

atexit.register(_teardown)
sleeper = subprocess.Popen(["sleep", "60"], stdout=subprocess.DEVNULL)

ENV = dict(os.environ)
ENV["ANTHROPIC_BASE_URL"] = f"http://127.0.0.1:{port}"
ENV["ESTATE_GUARD_AGENT_ROOT"] = str(os.getpid())
ENV["ESTATE_GUARD"] = GUARD
ENV["PATH"] = SHIMS + os.pathsep + ENV.get("PATH", "")
ENV.pop("BASH_ENV", None)
ENV.pop("ENV", None)


def argv_rc(*argv):
    return subprocess.run(
        [sys.executable, GUARD, "--argv", *argv],
        env=ENV,
        capture_output=True,
        text=True,
    ).returncode


def hook_rc(cmd):
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": cmd}})
    return subprocess.run(
        [sys.executable, GUARD], input=payload, env=ENV, capture_output=True, text=True
    ).returncode


print("judge (--argv, nothing is executed)")
check(
    "kill -9 <listener on protected port> refused", argv_rc("kill", "-9", str(D)) == 2
)
check("kill <listener> (default signal) refused", argv_rc("kill", str(D)) == 2)
check(
    "kill -TERM -- -<listener's process group> refused",
    argv_rc("kill", "-TERM", "--", f"-{D}") == 2,
)
check("kill -0 <listener> allowed (liveness probe)", argv_rc("kill", "-0", str(D)) == 0)
check("kill -s 0 <listener> allowed", argv_rc("kill", "-s", "0", str(D)) == 0)
check("kill -l allowed", argv_rc("kill", "-l") == 0)
check("kill -9 <unrelated child> allowed", argv_rc("kill", "-9", str(sleeper.pid)) == 0)
check(
    "kill -9 <the agent root itself> refused",
    argv_rc("kill", "-9", str(os.getpid())) == 2,
)
check(
    "pkill -f estatedecoy refused (pattern resolved by pgrep)",
    argv_rc("pkill", "-f", "estatedecoy") == 2,
)
check(
    "pkill -9 -f estatedecoy refused (signal stripped)",
    argv_rc("pkill", "-9", "-f", "estatedecoy") == 2,
)
check(
    "pkill -f no-such-process-zz9 allowed",
    argv_rc("pkill", "-f", "no-such-process-zz9") == 0,
)
check("killall estatedecoy refused", argv_rc("killall", "estatedecoy") == 2)
check(
    "launchctl bootout gui/UID/com.estate.pennyd refused (declared label)",
    argv_rc("launchctl", "bootout", f"gui/{os.getuid()}/com.estate.pennyd") == 2,
)
check(
    "launchctl kickstart -k com.estate.pennyd allowed (the restart door)",
    argv_rc("launchctl", "kickstart", "-k", f"gui/{os.getuid()}/com.estate.pennyd")
    == 0,
)
check(
    "launchctl print allowed", argv_rc("launchctl", "print", f"gui/{os.getuid()}") == 0
)

print("hook (stdin JSON, command text)")
check(
    "rg reading 'pkill -f estatedecoy' allowed (a read is not a kill)",
    hook_rc('rg -n "pkill -f estatedecoy" /dev/null') == 0,
)
check("echo kill <listener> allowed", hook_rc(f"echo kill {D}") == 0)
check("kill -9 <listener> refused", hook_rc(f"kill -9 {D}") == 2)
check("cd /tmp && kill -9 <listener> refused", hook_rc(f"cd /tmp && kill -9 {D}") == 2)
check(
    "bash -c 'kill -9 <listener>' refused (recursed)",
    hook_rc(f"bash -c 'kill -9 {D}'") == 2,
)
check(
    "sh -c 'kill <listener>' refused at the hook (shell layer cannot see it)",
    hook_rc(f"sh -c 'kill {D}'") == 2,
)
check(
    "launchctl bootout com.estate.pennyd refused",
    hook_rc("launchctl bootout com.estate.pennyd") == 2,
)
check(
    "kill $(cat pidfile) deferred to the shell layer",
    hook_rc("kill $(cat /nonexistent)") == 0,
)
check(
    "malformed JSON allowed (fail open)",
    subprocess.run(
        [sys.executable, GUARD],
        input="{not json",
        env=ENV,
        capture_output=True,
        text=True,
    ).returncode
    == 0,
)

print("shell layer (commands really run; the decoy must survive)")
pidfile = os.path.join(tmp, "pid")
open(pidfile, "w").write(str(D))
shells = {
    "zsh": ["zsh", "-f", "-c", f". {SHELL_GUARD}; kill -9 {D}"],
    "bash (BASH_ENV)": ["bash", "--norc", "--noprofile", "-c", f"kill -9 {D}"],
    "bash $(...) expansion": [
        "bash",
        "--norc",
        "--noprofile",
        "-c",
        f"kill -9 $(cat {pidfile})",
    ],
    "sh -> PATH shim pkill": ["sh", "-c", "pkill -f estatedecoy"],
    "execvp killall (shim)": ["killall", "estatedecoy"],
    "execvp kill (shim)": ["kill", "-9", str(D)],
}
for name, argv in shells.items():
    if not shutil.which(argv[0]):
        print(f"  SKIP  {name}: {argv[0]} not installed")
        continue
    env = dict(ENV, BASH_ENV=SHELL_GUARD) if name.startswith("bash") else ENV
    rc = subprocess.run(argv, env=env, capture_output=True, text=True).returncode
    time.sleep(0.1)
    check(
        f"{name}: refused and the listener is alive",
        rc != 0 and alive(D) and listening(port),
        f"rc={rc} alive={alive(D)}",
    )

# zsh where it exists (macOS), else bash: CI's ubuntu runner ships no zsh, and both source the layer
SH = (
    ["zsh", "-f", "-c"]
    if shutil.which("zsh")
    else ["bash", "--norc", "--noprofile", "-c"]
)
rc = subprocess.run(
    SH + [f". {SHELL_GUARD}; kill -TERM {sleeper.pid}"], env=ENV
).returncode
sleeper.wait(timeout=3)
check(
    f"{SH[0]}: kill of an unrelated child really runs",
    rc == 0 and sleeper.returncode is not None,
)

broken = os.path.join(tmp, "broken-guard")
open(broken, "w").write("this is not python(\n")
s2 = subprocess.Popen(["sleep", "60"], stdout=subprocess.DEVNULL)
rc = subprocess.run(
    SH + [f". {SHELL_GUARD}; kill -TERM {s2.pid}"], env=dict(ENV, ESTATE_GUARD=broken)
).returncode
s2.wait(timeout=3)
check(
    "a broken guard fails open: the kill still runs",
    rc == 0 and s2.returncode is not None,
)

print("not an agent (orphaned to launchd, no agent root): never judged")
r, w = os.pipe()
if os.fork() == 0:
    if os.fork() == 0:
        os.close(r)
        for _ in range(
            100
        ):  # wait until the middle process has exited and we are orphaned
            if os.getppid() == 1:
                break
            time.sleep(0.02)
        env = dict(ENV)
        env.pop("ESTATE_GUARD_AGENT_ROOT")
        rc = subprocess.run(
            [sys.executable, GUARD, "--argv", "kill", "-9", str(D)], env=env
        ).returncode
        os.write(w, f"{os.getppid()} {rc}".encode())
        os._exit(0)
    os._exit(0)
os.close(w)
os.wait()
ppid, rc = os.read(r, 64).decode().split()
if ppid != "1":
    print(f"  SKIP  orphan case: grandchild was reparented to {ppid}, not launchd/init")
else:
    check("non-agent caller may signal the listener (exit 0)", rc == "0", f"rc={rc}")

print("residual gaps (named, not hidden)")
print(
    "  GAP   `sh -c 'kill N'` run outside any hook: POSIX sh reads no BASH_ENV and kill is a builtin"
)
print(
    "  GAP   absolute /bin/kill, os.kill() and libc kill(2): no shell layer exists to intercept them"
)

passed = sum(results)
print(f"\napi-port-guard falsifier: {passed}/{len(results)} passed")
if OPTIMUS:
    print(
        f"optimus.guard.self_kill_cases_failing={len(results) - passed}",
        file=_REAL_STDOUT,
    )
    sys.exit(0)
sys.exit(0 if passed == len(results) else 1)
