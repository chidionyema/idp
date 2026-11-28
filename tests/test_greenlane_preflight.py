"""The Greenlane holds a lane at intake for what main's own deterministic gates refuse.

Root cause, measured 2026-11-28 on lane/meridian-flow-door-v2 (idp#8686): a lane pushed through the
GitHub API skips every local gate, so the fast-gate first met it on a batch candidate, where its
`door_s: 600` failed the budget rung for the whole batch. The lure here is that exact change.
A gate that cannot judge admits the lane (CI stays the guarantee); only a named FAIL holds it.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from greenlane.github import GitHubBackend

EXECUTOR = "mcp/plugins/estate_executor.py"
INTENT = "platform/estate/intents/flow-decide.yaml"


def _git(repo: Path, *args: str) -> str:
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@example.test",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@example.test",
    }
    done = subprocess.run(
        ["git", *args], cwd=repo, env=env, capture_output=True, text=True, check=True
    )
    return done.stdout.strip()


def _write(repo: Path, rel: str, body: str) -> None:
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body)


@pytest.fixture()
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    # hermetic: a developer's global hooks, signing or templates must not reach the fixture
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    _git(tmp_path, "init", "-q", "-b", "main")
    _write(tmp_path, EXECUTOR, "CEILING_SEC = 100\n")
    _write(tmp_path, INTENT, "name: flow-decide\nclass: read\ndoor_s: 100\nsteps: []\n")
    _write(tmp_path, "bin/note", "base\n")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "base")
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _lane(repo: Path, message: str, files: dict[str, str]) -> tuple[str, str]:
    base = _git(repo, "rev-parse", "HEAD")
    _git(repo, "checkout", "-q", "-b", "lane/x")
    for rel, body in files.items():
        _write(repo, rel, body)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", message)
    return base, _git(repo, "rev-parse", "HEAD")


def _backend() -> GitHubBackend:
    backend = GitHubBackend.__new__(GitHubBackend)
    backend.repo = "chidionyema/idp"
    return backend


LURE = "name: flow-decide\nclass: read\ndoor_s: 600\nsteps: []\n"


def test_the_door_lanes_own_lure_is_held_at_intake(repo: Path) -> None:
    base, head = _lane(repo, "fix: flow door", {INTENT: LURE})
    why = _backend().lane_preflight(base, head)
    assert why.startswith("preflight: ")
    assert "budget:" in why and "declares 600s" in why and "flow-decide.yaml" in why


def test_the_corrected_door_is_admitted(repo: Path) -> None:
    base, head = _lane(repo, "fix: flow door", {"bin/note": "changed\n"})
    assert _backend().lane_preflight(base, head) == ""


def test_a_new_python_file_without_a_reason_is_held(repo: Path) -> None:
    base, head = _lane(repo, "feat: a thing", {"bin/newtool.py": "print(1)\n"})
    why = _backend().lane_preflight(base, head)
    assert why.startswith("preflight: language:") and "bin/newtool.py" in why


def test_a_new_python_file_with_its_reason_is_admitted(repo: Path) -> None:
    base, head = _lane(
        repo,
        "feat: a thing\n\nLanguage-Exception: bin/newtool.py -- the gate it mirrors is Python",
        {"bin/newtool.py": "print(1)\n"},
    )
    assert _backend().lane_preflight(base, head) == ""


def test_a_gate_that_cannot_judge_admits_the_lane(
    repo: Path, tmp_path_factory: pytest.TempPathFactory
) -> None:
    base, head = _lane(repo, "fix: x", {"bin/note": "changed\n"})
    crash = tmp_path_factory.mktemp("gates") / "timeout-budget"
    crash.write_text("import sys\nsys.exit(2)\n")
    backend = _backend()
    backend.BUDGET_GATE = crash  # rc 2, no FAIL line: cannot judge
    assert backend.lane_preflight(base, head) == ""
    backend.BUDGET_GATE = repo / "does-not-exist"
    assert backend.lane_preflight(base, head) == ""


def test_unclaimed_reports_the_preflight_when_the_claim_is_live(
    repo: Path, tmp_path_factory: pytest.TempPathFactory
) -> None:
    base, bad = _lane(repo, "fix: x", {INTENT: LURE})
    live = tmp_path_factory.mktemp("claim") / "claim-gate"
    live.write_text("import sys\nsys.exit(0)\n")
    backend = _backend()
    backend.CLAIM_GATE = live
    assert "declares 600s" in backend.unclaimed(bad, base)
    # the same lane with the door corrected is admitted
    _write(repo, INTENT, "name: flow-decide\nclass: read\ndoor_s: 100\nsteps: []\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "door_s 100")
    assert backend.unclaimed(_git(repo, "rev-parse", "HEAD"), base) == ""


def test_extract_refuses_a_path_that_leaves_the_sandbox(tmp_path: Path) -> None:
    import io
    import tarfile

    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tf:
        info = tarfile.TarInfo("../escape.txt")
        info.size = 1
        tf.addfile(info, io.BytesIO(b"x"))
    inner = tmp_path / "inner"
    inner.mkdir()
    GitHubBackend._extract(buf.getvalue(), str(inner))
    assert not (tmp_path / "escape.txt").exists()
