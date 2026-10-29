"""The engine regenerates the capability witness on the candidate, so a lane is never red on the
offline-gate's registry rung for a snapshot only a pull request used to refresh (measured
2026-10-29: 14 of the last 18 red ci-success verdicts). Real git, a stand-in tool, no GitHub."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from greenlane.github import WITNESS, WITNESS_TOOL, GitHubBackend  # noqa: E402

# A stand-in for bin/capability-index with the same CLI: the snapshot is the sorted list of the
# tree's .py files, so it is derived from the tree and drifts when a lane adds one.
TOOL = """#!/usr/bin/env python3
import argparse, pathlib
ap = argparse.ArgumentParser()
ap.add_argument("--idp"); ap.add_argument("--home"); ap.add_argument("--no-refresh", action="store_true")
ap.add_argument("cmd"); ap.add_argument("--write", action="store_true"); ap.add_argument("--out")
a = ap.parse_args()
names = sorted(p.name for p in pathlib.Path(a.idp).glob("*.py"))
pathlib.Path(a.out).write_text("\\n".join(names) + "\\n")
"""


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(cwd), *args], capture_output=True, text=True, check=True
    ).stdout.strip()


@pytest.fixture
def repo(tmp_path, monkeypatch):
    r = tmp_path / "r"
    (r / "bin").mkdir(parents=True)
    (r / "catalog").mkdir()
    _git(r, "init", "-q", "-b", "main")
    _git(r, "config", "user.email", "t@t")
    _git(r, "config", "user.name", "t")
    _git(r, "config", "commit.gpgsign", "false")
    (r / WITNESS_TOOL).write_text(TOOL)
    (r / "one.py").write_text("1\n")
    (r / WITNESS).write_text("one.py\n")
    _git(r, "add", "-A")
    _git(r, "commit", "-q", "-m", "root")
    monkeypatch.chdir(r)
    return r


def _backend():
    return GitHubBackend("o/idp", ["test"])


def test_candidate_carries_a_witness_matching_the_tree(repo):
    base = _git(repo, "rev-parse", "HEAD")
    _git(repo, "checkout", "-q", "-b", "lane/x")
    (repo / "two.py").write_text("2\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "add two")
    head = _git(repo, "rev-parse", "HEAD")
    new = _backend().rebase(head, base, "lane/x")
    assert new
    # the lane never touched the witness; the candidate's is nonetheless current
    assert _git(repo, "show", f"{new}:{WITNESS}") == "one.py\ntwo.py"


def test_two_lanes_that_each_touched_the_witness_do_not_conflict(repo):
    base = _git(repo, "rev-parse", "HEAD")
    _git(repo, "checkout", "-q", "-b", "lane/a")
    (repo / "a.py").write_text("a\n")
    (repo / WITNESS).write_text("a.py\none.py\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "a")
    _git(repo, "checkout", "-q", "main")
    (repo / "b.py").write_text("b\n")
    (repo / WITNESS).write_text("b.py\none.py\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "b lands first")
    onto = _git(repo, "rev-parse", "HEAD")
    head = _git(repo, "rev-parse", "lane/a")
    new = _backend().rebase(head, onto, "lane/a")
    assert new, "a hand-regenerated witness on both sides must not conflict"
    assert _git(repo, "show", f"{new}:{WITNESS}") == "a.py\nb.py\none.py"


def test_a_lane_that_edits_the_tool_keeps_its_own_witness(repo):
    base = _git(repo, "rev-parse", "HEAD")
    _git(repo, "checkout", "-q", "-b", "lane/tool")
    (repo / WITNESS_TOOL).write_text(TOOL + "# changed\n")
    (repo / WITNESS).write_text("reviewed-by-a-human\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "change the tool")
    head = _git(repo, "rev-parse", "HEAD")
    new = _backend().rebase(head, base, "lane/tool")
    assert new
    assert _git(repo, "show", f"{new}:{WITNESS}") == "reviewed-by-a-human"


def test_flux_lanes_are_left_alone(repo):
    base = _git(repo, "rev-parse", "HEAD")
    _git(repo, "checkout", "-q", "-b", "flux/image-updates")
    (repo / "img.py").write_text("x\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "image")
    head = _git(repo, "rev-parse", "HEAD")
    new = _backend().rebase(head, base, "flux/image-updates")
    assert new
    assert _git(repo, "show", f"{new}:{WITNESS}") == "one.py"


def test_a_broken_tool_never_kills_the_tick(repo):
    base = _git(repo, "rev-parse", "HEAD")
    _git(repo, "checkout", "-q", "-b", "lane/y")
    (repo / WITNESS_TOOL).write_text("raise SystemExit(7)\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "x")
    _git(repo, "checkout", "-q", "main")
    (repo / WITNESS_TOOL).write_text("raise SystemExit(7)\n")
    _git(repo, "commit", "-q", "-am", "main tool broken too")
    onto = _git(repo, "rev-parse", "HEAD")
    (repo / "z.py").write_text("z\n")
    _git(repo, "checkout", "-q", "-b", "lane/z", base)
    (repo / "z.py").write_text("z\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "z")
    head = _git(repo, "rev-parse", "HEAD")
    assert _backend().rebase(head, onto, "lane/z")  # candidate is still built
