"""A door must find its own tools, not depend on the caller's PATH.

Measured 2026-11-11: the executor runs with a PATH that omits `~/.local/bin`, where `gh` lives on
this machine. Two doors failed differently on the same missing lookup, and the quieter one was the
worse one:

  * `bin/claim-open` called a bare `gh`, so every claim attempt died with
        FileNotFoundError: [Errno 2] No such file or directory: 'gh'
    -- loud, and each agent hand-wrapped it (absolute path here, `export PATH` there), which is the
    environment-fighting defect class rather than a fix.

  * `platform/estate/memory/focus.py` called `shutil.which("gh")` and returned `None` when it was
    not found. The write-guard read that as "there are no claims" and refused EVERY edit in the
    estate, for a reason it could not show. An empty result indistinguishable from a real absence:
    the guard failed closed into a total stop, silently.

These tests grade the resolution, which is the whole defect. They do not post a claim: that needs a
network and a live issue, and a gate that depends on GitHub is not a gate.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CLAIM_OPEN = REPO / "bin" / "claim-open"
FOCUS = REPO / "platform" / "estate" / "memory" / "focus.py"

# The narrowest PATH a process can plausibly be given: the system binaries, and nothing a user
# installed. This is what the executor's environment looked like when the defect was measured.
BARE_PATH = "/usr/bin:/bin"


def _probe(program: str, source: Path) -> str:
    """Load `source` as a module on a forced PATH and print its gh resolution."""
    script = (
        "import importlib.machinery, types, sys\n"
        f"m = types.ModuleType('probe')\n"
        f"m.__file__ = {str(source)!r}\n"
        f"importlib.machinery.SourceFileLoader('probe', {str(source)!r}).exec_module(m)\n"
        f"print(getattr(m, {program!r}, ''))\n"
    )
    out = subprocess.run(  # noqa: S603 - fixed argv, no shell string
        ["/usr/bin/python3", "-c", script],
        capture_output=True,
        text=True,
        env={**os.environ, "PATH": BARE_PATH},
        timeout=60,
    )
    assert out.returncode == 0, f"loading {source.name} failed: {out.stderr[-800:]}"
    return out.stdout.strip()


def test_the_bare_path_really_cannot_see_gh() -> None:
    """The falsifier: prove a bare `gh` is unresolvable here, so the fix is load-bearing.

    Without this, the other tests could pass for the wrong reason -- because the machine happened
    to put gh somewhere the bare PATH can see, not because the resolver did the work.
    """
    probe = subprocess.run(  # noqa: S603 - fixed argv, no shell string
        ["/usr/bin/python3", "-c", "import shutil;print(shutil.which('gh') or '')"],
        capture_output=True,
        text=True,
        env={**os.environ, "PATH": BARE_PATH},
        timeout=60,
    )
    assert probe.returncode == 0
    assert probe.stdout.strip() == "", (
        "gh is now discoverable on the bare PATH, so this test can no longer prove the fix is "
        "load-bearing; re-derive the defect against the machine's current environment"
    )


def test_claim_open_invokes_an_absolute_gh() -> None:
    """The caller must not invoke a bare name, because a bare name is what broke."""
    src = CLAIM_OPEN.read_text()
    assert 'run(["gh", *a])' not in src, (
        "claim-open is back to invoking a bare 'gh'; on the executor's PATH that raises "
        "FileNotFoundError and every session hand-wraps it again"
    )
    gh = _probe("GH", CLAIM_OPEN)
    assert os.path.isabs(gh), f"claim-open resolved GH to a bare name {gh!r}"
    assert os.path.isfile(gh) and os.access(gh, os.X_OK), (
        f"GH is not executable: {gh!r}"
    )


def test_focus_resolves_gh_where_shutil_which_would_fail() -> None:
    """focus.py must find gh even though `shutil.which` cannot, or the guard goes dark."""
    src = FOCUS.read_text()
    assert 'gh = shutil.which("gh")' not in src, (
        "focus.py is back to a bare shutil.which('gh'); on the executor's PATH that returns None "
        "and the write-guard reads it as 'no claims' and refuses every edit in the estate"
    )
    assert "resolve_tool(" in src, (
        "focus.py has no resolver; it cannot find gh off the PATH"
    )

    script = (
        "import importlib.machinery, types\n"
        f"m = types.ModuleType('probe')\n"
        f"m.__file__ = {str(FOCUS)!r}\n"
        f"importlib.machinery.SourceFileLoader('probe', {str(FOCUS)!r}).exec_module(m)\n"
        "print(m.resolve_tool('gh'))\n"
    )
    out = subprocess.run(  # noqa: S603 - fixed argv, no shell string
        ["/usr/bin/python3", "-c", script],
        capture_output=True,
        text=True,
        env={**os.environ, "PATH": BARE_PATH},
        timeout=60,
    )
    assert out.returncode == 0, f"loading focus.py failed: {out.stderr[-800:]}"
    gh = out.stdout.strip()
    assert os.path.isabs(gh), (
        f"focus.py resolved gh to {gh!r}, which is unusable as argv[0]"
    )
    assert os.path.isfile(gh) and os.access(gh, os.X_OK), (
        f"resolved gh is not executable: {gh!r}"
    )
