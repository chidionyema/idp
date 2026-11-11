"""IDP #7777: exact-object fetch races must not halt independent Greenlane work."""
import subprocess
import pytest
from greenlane.engine import Engine, Lane, PENDING, State, TESTING, UnavailableLaneObject
from greenlane.github import GitHubBackend

def git(cwd, *args, check=True):
    r = subprocess.run(["git", "-C", str(cwd), *args], text=True, capture_output=True)
    if check and r.returncode:
        raise AssertionError(f"{args!r}: {r.stderr}")
    return r.stdout.strip()

@pytest.fixture
def late(tmp_path, monkeypatch):
    remote, seed, runner = [tmp_path / n for n in ("remote.git", "seed", "runner")]
    remote.mkdir(); seed.mkdir()
    git(remote, "init", "--bare", "-q")
    git(seed, "init", "-q", "-b", "main")
    git(seed, "config", "user.name", "test")
    git(seed, "config", "user.email", "test@example.org")
    (seed / "base.txt").write_text("trusted\n")
    git(seed, "add", "."); git(seed, "commit", "-qm", "root")
    git(seed, "remote", "add", "origin", str(remote))
    git(seed, "push", "-q", "origin", "main")
    git(remote, "symbolic-ref", "HEAD", "refs/heads/main")
    subprocess.run(["git", "clone", "-q", str(remote), str(runner)], check=True)
    git(seed, "checkout", "-q", "-b", "lane/late")
    (seed / "late.txt").write_text("work\n")
    git(seed, "add", "."); git(seed, "commit", "-qm", "late work")
    head = git(seed, "rev-parse", "HEAD")
    git(seed, "push", "-q", "origin", "lane/late")
    main = git(runner, "rev-parse", "HEAD")
    assert git(runner, "rev-parse", "-q", "--verify", f"{head}^{{commit}}", check=False) == ""
    monkeypatch.chdir(runner)
    return remote, seed, runner, main, head

def test_race_recovers_exact_commit_without_changing_head(late):
    _, _, runner, main, head = late
    b = GitHubBackend("chidionyema/idp", [])
    assert b._merge_base_exact(main, head, "lane/late") == main
    assert git(runner, "rev-parse", "--verify", f"{head}^{{commit}}") == head

def test_moved_remote_ref_is_deferred_not_substituted(late):
    _, seed, _, main, head = late
    (seed / "late.txt").write_text("moved\n")
    git(seed, "add", "."); git(seed, "commit", "-qm", "moved head")
    git(seed, "push", "-q", "origin", "lane/late")
    with pytest.raises(UnavailableLaneObject, match="moved or deleted"):
        GitHubBackend("chidionyema/idp", [])._merge_base_exact(main, head, "lane/late")

def test_deleted_ref_is_deferred(late):
    _, seed, _, main, head = late
    git(seed, "push", "-q", "origin", "--delete", "lane/late")
    with pytest.raises(UnavailableLaneObject, match="moved or deleted"):
        GitHubBackend("chidionyema/idp", [])._merge_base_exact(main, head, "lane/late")

def test_fetch_failure_is_bounded_to_two_exact_attempts(late, monkeypatch):
    _, _, _, main, head = late
    b = GitHubBackend("chidionyema/idp", [])
    real = b.git; attempts = []
    def fail(*args, check=True):
        if args and args[0] == "fetch":
            attempts.append(args)
            raise RuntimeError("transport lost")
        return real(*args, check=check)
    monkeypatch.setattr(b, "git", fail)
    with pytest.raises(UnavailableLaneObject, match="two fetch attempts"):
        b._merge_base_exact(main, head, "lane/late")
    assert attempts == [("fetch", "-q", "--no-tags", "origin", head)] * 2

def test_unavailable_lane_does_not_starve_unrelated_candidate():
    class Backend:
        def __init__(self): self.pushed = []; self.reported = []
        def main(self): return "a" * 40
        def rebase(self, head, onto, lane=""):
            if lane == "lane/missing": raise UnavailableLaneObject("exact oid unavailable")
            return "c" * 40
        def report(self, name, head, status, reason): self.reported.append((name, status))
        def push_candidate(self, bid, tip): self.pushed.append((bid, tip))
        def now(self): return 1.0
    b = Backend()
    s = State(lanes={
        "lane/missing": Lane("lane/missing", "b"*40, status=PENDING, seq=1),
        "lane/good": Lane("lane/good", "d"*40, status=PENDING, seq=2),
    })
    Engine(b, s)._start_batch()
    assert s.lanes["lane/missing"].status == PENDING
    assert "waiting for exact" in s.lanes["lane/missing"].reason
    assert s.lanes["lane/good"].status == TESTING
    assert [row[0] for row in s.batch.members] == ["lane/good"]
    assert len(b.pushed) == 1
