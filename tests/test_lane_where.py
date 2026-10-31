"""bin/lane-where must not call a lane landed because a subject line matches.

Measured 2026-10-31: `bin/lane-where lane/catalog-completeness-gate` answered LANDED for a lane
whose head (fe255574) was not in main and never landed -- that work landed later, in a different
lane, under a different commit. The reason was the old fallback: when the head is not an ancestor
of main, the door looked for a commit on main with the SAME SUBJECT and, finding one (an unrelated
`chore(registry): regenerate the capability witness` commit, 09b9550af), answered LANDED.

A false "landed" is the expensive answer. It tells an agent its work is in main, so the agent
stops working on something that is not there, and reports work that never landed. So the fallback
is content now, not words:

  * the greenlane's own status on the head ("landed in bNNNN"), when the engine says so;
  * git's own patch-id equivalence (`git cherry origin/main <head>`);
  * the lane's own content, path by path, against main.

These tests run the real door against a real git repository, because the defect is in what the
door concludes from git's own words, and only a real repository can say that.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LANE_WHERE = ROOT / "bin" / "lane-where"
SUBJECT = "chore(registry): regenerate the capability witness"


def _git(repo: Path, *args: str) -> str:
    env = dict(
        os.environ,
        GIT_AUTHOR_NAME="lane",
        GIT_AUTHOR_EMAIL="lane@example.com",
        GIT_COMMITTER_NAME="lane",
        GIT_COMMITTER_EMAIL="lane@example.com",
    )
    proc = subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, env=env, check=True
    )
    return proc.stdout


def _commit(work: Path, content: str, message: str) -> str:
    (work / "file.txt").write_text(content)
    _git(work, "add", "file.txt")
    _git(work, "commit", "-q", "-m", message)
    return _git(work, "rev-parse", "HEAD").strip()


@pytest.fixture()
def work(tmp_path: Path) -> Path:
    """A bare origin and a working clone that holds the door under test."""
    origin = tmp_path / "origin.git"
    _git(tmp_path, "init", "--bare", "-q", str(origin))
    clone = tmp_path / "work"
    _git(tmp_path, "clone", "-q", str(origin), str(clone))
    (clone / "bin").mkdir(exist_ok=True)
    # `shutil.copy` carries the mode with the bytes, so the door under test is executable without
    # a chmod (and the pre-push gate's ruff selection refuses a permissive mask).
    shutil.copy(LANE_WHERE, clone / "bin" / "lane-where")
    _git(clone, "config", "user.email", "lane@example.com")
    _git(clone, "config", "user.name", "lane")
    _git(clone, "checkout", "-q", "-b", "main")
    return clone


def _where(work: Path, branch: str, *extra: str) -> tuple[int, str]:
    proc = subprocess.run(
        [
            "python3",
            str(work / "bin" / "lane-where"),
            branch,
            "--repo",
            "none/none",
            *extra,
        ],
        cwd=work,
        capture_output=True,
        text=True,
        timeout=120,
    )
    return proc.returncode, proc.stdout + proc.stderr


def _receipt(work: Path, branch: str) -> dict:
    """The door's own receipt, which says WHY it reached a verdict."""
    code, out = _where(work, branch, "--json")
    assert code in (0, 3, 4), f"the door could not judge the lane at all\n{out}"
    return json.loads(out)


def test_a_lane_whose_subject_matches_a_landed_commit_is_not_landed(work: Path):
    """The measured false positive: main carries a commit with the lane's subject; the lane's
    own work is not in main. The door must not read the subject as a landing."""
    _commit(work, "one", SUBJECT)
    _git(work, "push", "-q", "origin", "main")

    _git(work, "checkout", "-q", "-b", "lane/same-subject")
    _commit(work, "two", SUBJECT)
    _git(work, "push", "-q", "origin", "lane/same-subject")

    code, out = _where(work, "lane/same-subject")

    assert code == 3, (
        f"the door answered exit {code} for a lane whose work is not in main; a subject match is "
        f"not a landing (measured 2026-10-31: fe255574 answered LANDED against an unrelated "
        f"09b9550af with the same subject)\n{out}"
    )
    assert "LANDED" not in out, f"the door called an unlanded lane landed\n{out}"
    receipt = _receipt(work, "lane/same-subject")
    assert receipt["landed"] is False, (
        f"the receipt calls an unlanded lane landed\n{receipt}"
    )
    assert not receipt.get("landed_by"), (
        f"the receipt names a landing reason for a lane that is not landed\n{receipt}"
    )
    assert receipt.get("subject_seen_at"), (
        "the subject match is not recorded at all; it is useful as a hint and must never be a "
        f"verdict\n{receipt}"
    )


def test_a_squash_landed_lane_is_landed(work: Path):
    """The reason the fallback existed (measured 2026-10-24: a change that had landed minutes
    earlier as #7039 was answered "NOT in main"). The greenlane lands by squash, so the lane's
    head is never an ancestor of main; its CONTENT is in main, and that must still read LANDED."""
    _commit(work, "one", SUBJECT)
    _git(work, "push", "-q", "origin", "main")

    _git(work, "checkout", "-q", "-b", "lane/squashed")
    _commit(work, "two", "feat: the lane's own work")
    _git(work, "push", "-q", "origin", "lane/squashed")

    # main receives the same content under a different commit -- the shape of a squash landing.
    _git(work, "checkout", "-q", "main")
    _commit(work, "two", "feat: the lane's own work, landed by the engine")
    _git(work, "push", "-q", "origin", "main")

    code, out = _where(work, "lane/squashed")

    assert code == 0, f"the door did not recognise a squash-landed lane\n{out}"
    assert "LANDED" in out, (
        f"the door did not say LANDED for a squash-landed lane\n{out}"
    )
    receipt = _receipt(work, "lane/squashed")
    assert receipt["landed"] is True, (
        f"the receipt does not call a squash-landed lane landed\n{receipt}"
    )
    assert str(receipt.get("landed_by")).startswith(("patch-id", "content")), (
        f"the door landed the lane without saying by what proof\n{receipt}"
    )


def test_a_lane_head_that_is_in_main_is_landed_by_ancestry(work: Path):
    """The ordinary case, which no fallback may break."""
    _commit(work, "one", "feat: the first thing")
    _git(work, "push", "-q", "origin", "main")

    _git(work, "checkout", "-q", "-b", "lane/plain")
    _commit(work, "two", "feat: the second thing")
    _git(work, "push", "-q", "origin", "lane/plain")

    _git(work, "checkout", "-q", "main")
    _git(work, "merge", "-q", "--ff-only", "lane/plain")
    _git(work, "push", "-q", "origin", "main")

    code, out = _where(work, "lane/plain")

    assert code == 0, f"the door did not recognise a lane that is in main\n{out}"
    receipt = _receipt(work, "lane/plain")
    assert receipt.get("landed_by") == "ancestry", (
        f"the door did not land the lane by ancestry\n{receipt}"
    )
