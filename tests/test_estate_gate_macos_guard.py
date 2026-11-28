#!/usr/bin/env python3
"""bin/estate-gate refuses to run its pytest/node/venv work on macOS unless ALLOW_LOCAL_TESTS=1.

Runs the real script with a fake `uname` first on PATH. Cases: Darwin is refused (rc=1, message, and
no venv or lock work started); Darwin with the override passes the guard (it then stops at the missing
lock file, rc=2, which proves the guard let it through); Linux passes the guard. Falsifier: the pre-fix
script on Darwin is not refused by the guard.
"""

import os, pathlib, subprocess, sys, tempfile

REPO = pathlib.Path(__file__).resolve().parent.parent
GATE = REPO / "bin" / "estate-gate"


def run(script, system, env_extra=None):
    with tempfile.TemporaryDirectory() as d:
        d = pathlib.Path(d)
        fake = d / "bin"
        fake.mkdir()
        u = fake / "uname"
        u.write_text(
            '#!/bin/sh\n[ "$1" = "-s" ] && echo %s || echo %s\n' % (system, system)
        )
        u.chmod(0o755)
        work = d / "work"
        work.mkdir()
        env = {"PATH": f"{fake}:{os.environ['PATH']}", "HOME": str(d)}
        env.update(env_extra or {})
        return subprocess.run(
            ["bash", str(script)],
            cwd=work,
            env=env,
            capture_output=True,
            text=True,
            timeout=15,
        )


def pre_fix_script(tmp):
    text = GATE.read_text()
    start = text.index("# 0. macOS")
    end = text.index("fi\n", start) + 3
    p = pathlib.Path(tmp) / "estate-gate-prefix"
    p.write_text(text[:start] + text[end:])
    return p


def check():
    out = {}
    r = run(GATE, "Darwin")
    out["darwin_refused"] = r.returncode == 1 and "Blocked on macOS" in r.stderr
    r = run(GATE, "Darwin", {"ALLOW_LOCAL_TESTS": "1"})
    out["darwin_override_passes_guard"] = (
        r.returncode == 2 and "Blocked on macOS" not in r.stderr
    )
    r = run(GATE, "Linux")
    out["linux_passes_guard"] = r.returncode == 2 and "Blocked on macOS" not in r.stderr
    with tempfile.TemporaryDirectory() as t:
        r = run(pre_fix_script(t), "Darwin")
        out["falsifier_prefix_not_refused"] = "Blocked on macOS" not in r.stderr
    return out


def test_guard():
    res = check()
    assert all(res.values()), res


if __name__ == "__main__":
    res = check()
    print(res)
    if "--optimus" in sys.argv:
        print(
            "optimus.estate_gate.unguarded_macos_run=%d"
            % (0 if all(res.values()) else 1)
        )
    sys.exit(0 if all(res.values()) else 1)
