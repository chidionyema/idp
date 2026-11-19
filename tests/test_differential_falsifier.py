"""The differential falsifier has to refuse, or it is decoration.

Each test writes a receipt in a throwaway git repo and runs the real script as a subprocess --
the same invocation the wall and CI use.
"""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
GATE = REPO_ROOT / "bin" / "idp-differential-falsifier"


def git(cwd, *args):
    return subprocess.check_output(["git", *args], cwd=cwd, text=True).strip()


@pytest.fixture()
def repo(tmp_path):
    r = tmp_path / "r"
    r.mkdir()
    git(r, "init", "-b", "main")
    git(r, "config", "user.email", "t@t")
    git(r, "config", "user.name", "t")
    (r / ".ci").mkdir()
    (r / "platform" / "llm").mkdir(parents=True)
    (r / "platform" / "llm" / "x.py").write_text("x = 1\n")
    git(r, "add", ".")
    git(r, "-c", "core.hooksPath=/dev/null", "commit", "-m", "base")
    git(r, "branch", "origin-main")
    (r / "platform" / "llm" / "x.py").write_text("x = 2\n")
    git(r, "add", ".")
    git(r, "-c", "core.hooksPath=/dev/null", "commit", "-m", "change")
    return r


def run(repo, receipt):
    (repo / ".ci" / "proof-receipt.json").write_text(json.dumps(receipt))
    return subprocess.run(
        [sys.executable, str(GATE), "origin-main"],
        cwd=repo,
        capture_output=True,
        text=True,
    )


GOOD = {
    "tested_subsystems": ["platform/llm"],
    "falsifiers": [{"test_name": "t", "base_exit_code": 1, "head_exit_code": 0}],
    "mutations_killed": [{"guard": "g", "killed": True}],
}


def test_a_good_receipt_passes(repo):
    p = run(repo, GOOD)
    assert p.returncode == 0, p.stderr


def test_an_unbound_path_is_refused(repo):
    bad = dict(GOOD, tested_subsystems=["somewhere/else"])
    p = run(repo, bad)
    assert p.returncode != 0 and "PATH_UNBOUND" in p.stderr


def test_a_test_that_passes_on_base_is_refused(repo):
    bad = dict(
        GOOD, falsifiers=[{"test_name": "t", "base_exit_code": 0, "head_exit_code": 0}]
    )
    p = run(repo, bad)
    assert p.returncode != 0 and "NON_FALSIFYING_TEST" in p.stderr


def test_no_mutation_proof_is_refused(repo):
    bad = dict(GOOD, mutations_killed=[])
    p = run(repo, bad)
    assert p.returncode != 0 and "NO_MUTATION_PROOF" in p.stderr


def test_a_surviving_mutant_is_refused(repo):
    bad = dict(GOOD, mutations_killed=[{"guard": "g", "killed": False}])
    p = run(repo, bad)
    assert p.returncode != 0 and "SURVIVING_MUTANT" in p.stderr
