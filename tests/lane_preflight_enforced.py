"""Optimus measure: greenlane.lane_preflight_before_floor.

Prints `optimus.greenlane.lane_preflight_before_floor=1` when the pre-push judgement runs the
pre-CI rules a lane is refused for: bin/lane-preflight refuses a new Python file that carries no
Language-Exception trailer (naming it), refuses a lane that does not merge onto origin/main, and
passes a clean lane; and .githooks/pre-push calls it BEFORE its disk-floor exit, so a machine
short of disk is judged like any other. Prints 0 on code where any of those is false, or where
the judgement cannot be run.

Stdlib only (the Greenlane judge has no pytest). Real git, a real bare origin and the real
bin/language-gate in a tmp repo; nothing here stubs a verdict. The ruff-format rule needs the
pinned formatter, which the judge may not carry, so it is proved by
tests/test_lane_preflight.py and not read here.
"""

from __future__ import annotations

import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
ENV = {
    **os.environ,
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_AUTHOR_NAME": "m",
    "GIT_AUTHOR_EMAIL": "m@example.test",
    "GIT_COMMITTER_NAME": "m",
    "GIT_COMMITTER_EMAIL": "m@example.test",
}


def _git(cwd, *args) -> str:
    done = subprocess.run(
        ["git", *args], cwd=cwd, env=ENV, capture_output=True, text=True, check=True
    )
    return done.stdout.strip()


def _preflight(work, ref):
    return subprocess.run(
        ["bash", str(ROOT / "bin" / "lane-preflight"), ref],
        cwd=work,
        env=ENV,
        capture_output=True,
        text=True,
        timeout=40,
    )


def _lane(work, files, message="work"):
    _git(work, "checkout", "-q", "-B", "lane/m", "origin/main")
    for rel, text in files.items():
        target = pathlib.Path(work, rel)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)
    _git(work, "add", "-A")
    _git(work, "commit", "-q", "-m", message + "\n\nClaim: o/r#1\nAgent: m")
    return _git(work, "rev-parse", "HEAD")


def _hook_runs_preflight_before_the_floor() -> bool:
    hook = (ROOT / ".githooks" / "pre-push").read_text()
    call = hook.find("if ! _preflight_guard; then")
    floor = hook.find("_free_mb=$(/bin/df -m")
    return 0 <= call < floor and "bin/lane-preflight" in hook


def measure() -> int:
    if not _hook_runs_preflight_before_the_floor():
        return 0
    base = pathlib.Path(tempfile.mkdtemp(prefix="lane-preflight-measure."))
    try:
        origin, work = base / "origin.git", base / "work"
        subprocess.run(
            ["git", "init", "-q", "--bare", "-b", "main", str(origin)],
            env=ENV,
            check=True,
        )
        subprocess.run(
            ["git", "clone", "-q", str(origin), str(work)], env=ENV, check=True
        )
        _git(work, "checkout", "-q", "-b", "main")
        (work / "bin").mkdir()
        shutil.copy(ROOT / "bin" / "language-gate", work / "bin" / "language-gate")
        (work / "greenlane").mkdir()
        (work / "greenlane" / "ferrari.py").write_text(
            'TRUSTED_RUFF_VERSION = "0.0.0"\n'
        )
        (work / "shared.txt").write_text("one\ntwo\nthree\n")
        _git(work, "add", "-A")
        _git(work, "commit", "-q", "-m", "seed")
        _git(work, "push", "-q", "origin", "main")

        clean = _lane(work, {"docs/note.md": "hello\n"})
        if _preflight(work, clean).returncode != 0:
            return 0

        bare_python = _lane(work, {"bin/tool.py": "x = 1\n"})
        refused = _preflight(work, bare_python)
        if (
            refused.returncode != 1
            or "bin/tool.py" not in refused.stdout + refused.stderr
        ):
            return 0

        lane = _lane(work, {"shared.txt": "one\nLANE\nthree\n"})
        _git(work, "checkout", "-q", "main")
        pathlib.Path(work, "shared.txt").write_text("one\nMAIN\nthree\n")
        _git(work, "commit", "-q", "-am", "main moves")
        _git(work, "push", "-q", "origin", "main")
        conflict = _preflight(work, lane)
        said = conflict.stdout + conflict.stderr
        if conflict.returncode != 1 or "does not merge onto origin/main" not in said:
            return 0
        return 1
    except (OSError, subprocess.SubprocessError):
        return 0
    finally:
        shutil.rmtree(base, ignore_errors=True)


if __name__ == "__main__":
    print(f"optimus.greenlane.lane_preflight_before_floor={measure()}")
    sys.exit(0)
