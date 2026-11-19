"""The proof reaches the pull request BEFORE the push that grades it.

2026-11-15. The Greenlane landed by force-pushing the rebased squash onto the lane branch,
and that push started fast-gate on the pull request the branch carries. The BDD-PROOF block
was written afterwards, in `_ensure_pr`, so the run grading the push read the previous
attempt's body -- or no block at all -- and refused it:

    FAIL  bddproof pull request #8099 carries no BDD-PROOF ... END-BDD-PROOF block
          (run 43703361365)

and #8124/#8110/#8115/#8117 hit the stale-head half of the same class. The body was repaired
after each push, which fixed the *next* attempt and never the run being graded, so a lane the
engine had proven green could not land at all.

This is the falsifier: it records the order of the two side effects and fails when the push
comes first.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from greenlane.github import GitHubBackend  # noqa: E402


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(cwd), *args], capture_output=True, text=True, check=True
    ).stdout.strip()


class OrderingBackend(GitHubBackend):
    """One real lane, one open PR whose body is stale, and a record of what happened when."""

    LAND_SETTLE_S = 0
    LAND_POLL_S = 0.01
    LAND_RETRY_S = 0.01

    def __init__(self) -> None:
        super().__init__("o/idp", ["test"])
        self.order: list[str] = []
        self.patched_body = ""

    def gh(self, path, method="GET", fields=None):
        if path.startswith("pulls?state=open&head="):
            return [{"number": 7, "body": self.patched_body or "the previous attempt"}]
        if path == "pulls/7" and method == "PATCH":
            self.patched_body = (fields or {}).get("body", "")
            self.order.append("proof")
            return {}
        if path == "pulls/7" and method == "GET":
            return {"head": {"sha": ""}}
        if path == "pulls/7/merge":
            return {"merged": True, "sha": (fields or {}).get("sha", "")}
        return {}

    def git(self, *args, **kwargs):
        if "push" in args:
            self.order.append("push")
        return super().git(*args, **kwargs)

    def checks(self, tip):
        return ("green", "")

    def adopted_prs(self):
        return []

    def _status(self, sha, fields):
        pass

    def _update_check_run(self, sha, status, conclusion, reason):
        pass

    def _approve(self, number, sha, tip):
        pass


def _repo(tmp_path, monkeypatch):
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
    return r


def _commit(r: Path, name: str, msg: str) -> str:
    (r / name).write_text(f"{name}\n")
    _git(r, "add", name)
    _git(r, "commit", "-q", "-m", msg)
    return _git(r, "rev-parse", "HEAD")


def test_the_proof_reaches_the_pull_request_before_the_push_that_grades_it(
    monkeypatch, tmp_path
):
    r = _repo(tmp_path, monkeypatch)
    head = _commit(r, "head.txt", "lane work")  # the head the batch tested
    _git(r, "push", "-q", "origin", f"{head}:refs/heads/lane/x")
    rebased = _commit(r, "sq.txt", "rebased squash")  # what land pushes over the lane
    tip = _git(r, "rev-parse", "HEAD")

    b = OrderingBackend()
    b.land([("lane/x", head, rebased)], tip)

    assert b.order[:2] == ["proof", "push"], (
        f"the proof must reach the pull request before the push that grades it: {b.order}"
    )
    assert f"head: {rebased}" in b.patched_body, (
        "the proof in the body must name the commit the push makes the head"
    )


# -- the adopted pull request (2026-11-19) -----------------------------------------------------
#
# 85 of the last 200 batch verdicts were one fingerprint, and the run behind it read
#   FAIL  bddproof pull request #8221: the proof names 3f3515e10b56..., but the head is 69e2bd2f4e8c
# An adopted pull request lives on the author's branch (`fix/zip-cve`), not on the lane
# (`lane/fix/zip-cve`), so the lookup by `head=<lane>` found nothing, the author's day-old block
# was never replaced, and every land of a lane proven green was refused by its own push.

STALE = "3f3515e10b56eaa26d7a4628898430fd6eaee8ac"


def _gate():
    import importlib.machinery
    import importlib.util

    loader = importlib.machinery.SourceFileLoader(
        "bdd_proof_gate", str(ROOT / "bin/idp-bdd-proof-gate")
    )
    spec = importlib.util.spec_from_loader("bdd_proof_gate", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


class AdoptedBackend(OrderingBackend):
    """The real shape: no PR on the lane branch, one adopted PR on the author's branch."""

    def __init__(self, body: str) -> None:
        super().__init__()
        self.body = body

    def gh(self, path, method="GET", fields=None):
        if path.startswith("pulls?state=open&head="):
            return []  # nothing is open on `lane/x`: the PR's head is the author's `x`
        if path == "pulls/8221" and method == "GET":
            return {"number": 8221, "body": self.body, "head": {"sha": ""}}
        if path == "pulls/8221" and method == "PATCH":
            self.body = (fields or {}).get("body", "")
            self.order.append("proof")
            return {}
        if path == "pulls/8221/merge":
            return {"merged": True, "sha": (fields or {}).get("sha", "")}
        return {}

    def adopted_prs(self):
        return [{"number": 8221, "branch": "x", "lane": "lane/x", "head": ""}]


def _author_body() -> str:
    return (
        "Greenlane-Lane: lane/x\n\nLock moves zip 8.6.0 -> 9.7.0. Closes #8219.\n\n"
        f"BDD-PROOF\nhead: {STALE}\n$ python3 -m pytest -q\n10 passed in 0.59s\nEND-BDD-PROOF\n"
    )


def test_an_adopted_pull_request_gets_the_proof_before_the_push_that_grades_it(
    monkeypatch, tmp_path
):
    r = _repo(tmp_path, monkeypatch)
    head = _commit(r, "head.txt", "lane work")
    _git(r, "push", "-q", "origin", f"{head}:refs/heads/lane/x", f"{head}:refs/heads/x")
    rebased = _commit(r, "sq.txt", "rebased squash")
    tip = _git(r, "rev-parse", "HEAD")

    b = AdoptedBackend(_author_body())
    b.land([("lane/x", head, rebased)], tip)

    assert b.order[:2] == ["proof", "push"], b.order
    gate = _gate()
    code, why = gate.grade(b.body, rebased, "pull request #8221")
    assert code == gate.EXIT_PROVED, why
    assert STALE not in b.body, "a stale proof left beside the fresh one is two heads"
    assert b.body.startswith("Greenlane-Lane: lane/x\n"), (
        "the adoption line must stay first"
    )
    assert "Closes #8219" in b.body, "the author's words are kept"


def test_the_unfixed_lookup_is_the_refusal_measured_on_8221(monkeypatch, tmp_path):
    """Reverse the fix (no adopted fallback) and the measured refusal comes back exactly."""
    from greenlane.github import GitHubBackend as G

    r = _repo(tmp_path, monkeypatch)
    head = _commit(r, "head.txt", "lane work")
    _git(r, "push", "-q", "origin", f"{head}:refs/heads/lane/x", f"{head}:refs/heads/x")
    rebased = _commit(r, "sq.txt", "rebased squash")

    b = AdoptedBackend(_author_body())
    monkeypatch.setattr(
        G,
        "_lane_pr",
        lambda self, lane: (self.gh(f"pulls?state=open&head=o:{lane}") or [None])[0],
    )
    b._write_proof_body("lane/x", head, rebased, rebased)
    gate = _gate()
    code, why = gate.grade(b.body, rebased, "pull request #8221")
    assert code == gate.EXIT_REFUSED and f"the proof names {STALE}" in why


def test_the_proof_block_is_idempotent_on_retry(monkeypatch, tmp_path):
    """A retry rewrites the block to the new head; it never stacks a second one."""
    from greenlane.github import GitHubBackend as G

    once = G._adopted_proof_body(
        _author_body(), "x\nBDD-PROOF\nhead: aaaaaaa\nok\nEND-BDD-PROOF\n"
    )
    twice = G._adopted_proof_body(
        once, "x\nBDD-PROOF\nhead: bbbbbbb\nok\nEND-BDD-PROOF\n"
    )
    assert twice.count("END-BDD-PROOF") == 1 and "head: bbbbbbb" in twice
    assert "aaaaaaa" not in twice and twice.startswith("Greenlane-Lane: lane/x\n")
