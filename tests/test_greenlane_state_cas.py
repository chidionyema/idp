"""The state ref is written by ticks that do not serialize with each other.

A lane push run and a main dispatch run sit in different concurrency groups and overlap in
time. Both load the state, both act, and -- before 2026-10-17 -- both saved with a blind
force push: last writer won, the loser's batch vanished from the state while its queue
branch sat green forever, and lanes were re-marked CONFLICT by a tick running on a
pre-batch snapshot. Measured that day: b2953 and b2954 were both stranded this way within
one hour, and `landed_total` froze at 446->447 while ten lanes waited.

The save is a compare-and-swap now: it leases on the remote sha the load observed and
refuses to overwrite a state it never saw.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from greenlane.github import GitHubBackend  # noqa: E402


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(cwd), *args], capture_output=True, text=True, check=True
    ).stdout.strip()


class Quiet(GitHubBackend):
    """No GitHub: nothing this test exercises needs the API."""

    def __init__(self):
        super().__init__("o/idp", ["test"])

    def gh(self, path, method="GET", fields=None):
        return [] if method == "GET" else None


@pytest.fixture
def repo(tmp_path, monkeypatch):
    r = tmp_path / "r"
    r.mkdir()
    _git(r, "init", "-q", "-b", "main")
    _git(r, "config", "user.email", "t@t")
    _git(r, "config", "user.name", "t")
    _git(r, "config", "commit.gpgsign", "false")
    (r / "a.txt").write_text("one\n")
    _git(r, "add", "a.txt")
    _git(r, "commit", "-q", "-m", "root")
    bare = tmp_path / "o.git"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(bare)], check=True)
    _git(r, "remote", "add", "origin", str(bare))
    _git(r, "push", "-q", "origin", "main")
    monkeypatch.chdir(r)
    return bare


def _remote_state_sha(bare: Path) -> str:
    out = subprocess.run(
        ["git", "ls-remote", str(bare), "refs/greenlane/state"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    return out.split()[0] if out else ""


def test_a_save_after_a_concurrent_save_is_refused(repo):
    """The b2953/b2954 shape, in miniature: two ticks load the same state, one saves, and the
    other must not silently overwrite it."""
    a, b = Quiet(), Quiet()
    a.fetch()
    a.load_state_text()
    b.fetch()
    b.load_state_text()

    b.save_state_text('{"lanes": {}, "landed": 1}')  # the concurrent tick wins the race

    with pytest.raises(RuntimeError, match="stale info"):
        a.save_state_text('{"lanes": {}, "landed": 2}')  # a's lease is stale now

    # the remote still carries b's state, not a's
    sha = _remote_state_sha(repo)
    subprocess.run(
        ["git", "fetch", "-q", str(repo), "refs/greenlane/state"], check=True
    )
    text = _git(repo.parent / "r", "show", f"{sha}:state.json")
    assert '"landed": 1' in text


def test_a_save_with_no_interleaving_succeeds(repo):
    a = Quiet()
    a.fetch()
    assert a.load_state_text() == ""  # first tick: no state ref yet
    a.save_state_text('{"lanes": {}, "landed": 1}')
    sha = _remote_state_sha(repo)
    assert sha  # the ref now exists

    a.fetch()
    a.load_state_text()  # fresh lease on the sha it just wrote
    a.save_state_text('{"lanes": {}, "landed": 2}')
    assert _remote_state_sha(repo) != sha


def test_a_first_tick_save_refuses_when_the_ref_appeared_under_it(repo):
    """An empty lease means the ref must not exist: a first tick that raced a first save
    loses loudly instead of clobbering."""
    a = Quiet()
    a.fetch()
    assert a.load_state_text() == ""

    Quiet().save_state_text('{"lanes": {}, "landed": 1}')  # the ref appears mid-tick

    with pytest.raises(RuntimeError, match="stale info"):
        a.save_state_text('{"lanes": {}, "landed": 2}')
    assert _remote_state_sha(repo)  # and the winner's state is still there
