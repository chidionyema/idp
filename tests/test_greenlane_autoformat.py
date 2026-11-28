"""Greenlane fixes a format-only lane instead of leaving it red (shift left).

Real git, real pinned Ruff for the formatter; a fake GitHub only where the network starts.
"""

# Pytest assertions are test checks, never runtime input validation.
# ruff: noqa: S101
from __future__ import annotations

import subprocess
from pathlib import Path
from types import SimpleNamespace

from greenlane.engine import Engine, Lane, State, RED
from greenlane.ferrari import FORMAT_REFUSAL, TRUSTED_RUFF_VERSION, format_fixes
from greenlane.github import GitHubBackend

UGLY = "x = {  'a':1,\n'b' :2 }\n"
CLEAN = 'x = {"a": 1, "b": 2}\n'


def _repo(tmp_path: Path, files: dict[str, str]) -> tuple[str, str]:
    def git(*args):
        return subprocess.run(
            ["git", *args], cwd=tmp_path, capture_output=True, text=True, check=True
        ).stdout.strip()

    git("init", "-q")
    git("config", "user.name", "t")
    git("config", "user.email", "t@example.invalid")
    (tmp_path / "README.md").write_text("base\n")
    git("add", ".")
    git("commit", "-qm", "base")
    base = git("rev-parse", "HEAD")
    for name, text in files.items():
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_text(text)
    git("add", ".")
    git("commit", "-qm", "work")
    return base, git("rev-parse", "HEAD")


def _ruff() -> str:
    for cand in (
        str(Path.home() / ".local/bin/ruff"),
        "ruff",
    ):
        r = subprocess.run([cand, "--version"], capture_output=True, text=True)
        if r.returncode == 0 and r.stdout.strip() == f"ruff {TRUSTED_RUFF_VERSION}":
            return cand
    raise AssertionError("pinned ruff not installed; these tests never skip it")


def test_unformatted_python_comes_back_formatted(tmp_path):
    base, head = _repo(tmp_path, {"a.py": UGLY, "b.py": CLEAN})
    fixes = format_fixes(base, head, checkout=tmp_path, ruff_binary=_ruff())
    assert fixes == {"a.py": CLEAN}


def test_already_formatted_lane_has_nothing_to_fix(tmp_path):
    base, head = _repo(tmp_path, {"a.py": CLEAN})
    assert format_fixes(base, head, checkout=tmp_path, ruff_binary=_ruff()) == {}


def test_without_the_pinned_ruff_nothing_is_fixed(tmp_path):
    base, head = _repo(tmp_path, {"a.py": UGLY})
    assert format_fixes(base, head, checkout=tmp_path, ruff_binary=False) == {}

    def wrong_version(argv, **kw):
        if argv[:2] == ["fake-ruff", "--version"]:
            return SimpleNamespace(returncode=0, stdout="ruff 0.0.1\n", stderr="")
        return subprocess.run(argv, **kw)

    assert (
        format_fixes(
            base, head, runner=wrong_version, checkout=tmp_path, ruff_binary="fake-ruff"
        )
        == {}
    )


def test_unsafe_path_is_never_touched(tmp_path):
    base, head = _repo(tmp_path, {"a.py": UGLY})

    def evil(argv, **kw):
        if argv[:2] == ["git", "diff"]:
            return SimpleNamespace(returncode=0, stdout="../escape.py\0", stderr="")
        return subprocess.run(argv, **kw)

    assert (
        format_fixes(base, head, runner=evil, checkout=tmp_path, ruff_binary=_ruff())
        == {}
    )


class _Gh:
    """A fake GitHub: records what Greenlane would push; never talks to the network."""

    def __init__(self):
        self.calls = []

    def __call__(self, path, method="GET", fields=None):
        self.calls.append((path, method, fields))
        if path == "git/blobs":
            return {"sha": "b" * 40}
        if path == "git/trees":
            return {"sha": "t" * 40}
        if path == "git/commits":
            return {"sha": "c" * 40}
        return {}


def _backend(tmp_path, message, files):
    base, head = _repo(tmp_path, files)
    backend = object.__new__(GitHubBackend)
    gh = _Gh()

    def git(*args, check=True):
        if args[0] == "log":
            return message
        return subprocess.run(
            ["git", *args], cwd=tmp_path, capture_output=True, text=True, check=check
        ).stdout.strip()

    backend.git, backend.gh = git, gh
    return backend, gh, base, head


def test_backend_pushes_a_fast_forward_fixup_that_keeps_the_claim(
    tmp_path, monkeypatch
):
    msg = "work\n\nClaim: chidionyema/idp#1\nAgent: claude-code\n"
    backend, gh, base, head = _backend(tmp_path, msg, {"a.py": UGLY})
    monkeypatch.setattr(
        "greenlane.github.format_fixes", lambda b, h: {"a.py": CLEAN}, raising=True
    )
    assert backend.format_fix("lane/x", head, base) == "c" * 40
    paths = [c[0] for c in gh.calls]
    assert paths == ["git/blobs", "git/trees", "git/commits", "git/refs/heads/lane/x"]
    commit = gh.calls[2][2]
    assert commit["parents"] == [head]
    assert "Claim: chidionyema/idp#1" in commit["message"]
    assert "Agent: claude-code" in commit["message"]
    assert f"Greenlane-Autoformat: {head[:12]}" in commit["message"]
    assert gh.calls[3][1:] == ("PATCH", {"sha": "c" * 40, "force": False})
    assert gh.calls[1][2]["tree"][0]["mode"] == "100644"


def test_backend_never_fixes_its_own_fixup_twice(tmp_path, monkeypatch):
    msg = "Greenlane: apply\n\nGreenlane-Autoformat: abcdef123456\n"
    backend, gh, base, head = _backend(tmp_path, msg, {"a.py": UGLY})
    monkeypatch.setattr(
        "greenlane.github.format_fixes", lambda b, h: {"a.py": CLEAN}, raising=True
    )
    assert backend.format_fix("lane/x", head, base) == ""
    assert gh.calls == []


def test_backend_pushes_nothing_when_a_push_fails(tmp_path, monkeypatch):
    backend, gh, base, head = _backend(tmp_path, "work\n", {"a.py": UGLY})
    monkeypatch.setattr(
        "greenlane.github.format_fixes", lambda b, h: {"a.py": CLEAN}, raising=True
    )

    def boom(path, method="GET", fields=None):
        raise RuntimeError("non-fast-forward")

    backend.gh = boom
    assert backend.format_fix("lane/x", head, base) == ""


class _EngineBackend:
    def __init__(self, fixer):
        self.base = "a" * 40
        self.reports = []
        self.pushed = []
        if fixer is not None:
            self.format_fix = fixer

    def main(self):
        return self.base

    def now(self):
        return 1.0

    def rebase(self, head, onto, lane=""):
        return head

    def preflight(self, base, candidate):
        return False, FORMAT_REFUSAL + ": a.py"

    def push_candidate(self, batch_id, tip):
        self.pushed.append(tip)

    def report(self, lane, head, status, reason):
        self.reports.append((lane, head, status, reason))

    def unclaimed(self, head, base):
        return ""

    def lanes(self):
        return {}


def _run_engine(fixer):
    backend = _EngineBackend(fixer)
    state = State(lanes={"lane/x": Lane("lane/x", "h1", seq=1)})
    Engine(backend, state, batch_size=1)._start_batch()
    return backend, state.lanes["lane/x"]


def test_engine_repairs_a_format_only_refusal_and_reports_the_new_head():
    seen = []

    def fixer(lane, head, base):
        seen.append((lane, head, base))
        return "f" * 40

    backend, lane = _run_engine(fixer)
    assert seen == [("lane/x", "h1", "a" * 40)]
    assert lane.status == RED and "pushed ffffffffffff" in lane.reason
    assert backend.pushed == []  # still no CI spent on the unformatted head


def test_engine_without_a_fixer_still_refuses_exactly_as_before():
    backend, lane = _run_engine(None)
    assert lane.status == RED and lane.reason == FORMAT_REFUSAL + ": a.py"


def test_engine_does_not_try_to_fix_a_non_format_refusal():
    called = []
    backend = _EngineBackend(lambda *a: called.append(a) or "f" * 40)
    backend.preflight = lambda base, cand: (False, "pre-CI language-gate: x")
    state = State(lanes={"lane/x": Lane("lane/x", "h1", seq=1)})
    Engine(backend, state, batch_size=1)._start_batch()
    assert called == []
