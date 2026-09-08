"""The three ways an automation stopped running without a single check going red.

2026-09-08. crew's merge bot had refused every pull request for ten days because it required a
check whose workflow the founder had deleted; idp's `founder-word.yml` had failed at startup on
every run since 2026-09-04 because it calls a reusable workflow that a Weave GitOps commit
deleted as collateral; and idp's `deploy-when-green.yml` -- the only thing here that lands a
pull request without a person -- had been `disabled_manually` in GitHub's settings since
2026-08-31. Three mechanisms off, eight to ten days, and every light in the estate green.

Founder, 2026-09-08: "agents should be responsiblefor their own own, all this chasing is
fricion".

These grade bin/idp-mechanism-gate by running it over trees built here, not by reading it.
"""

from __future__ import annotations

import os
import subprocess
import sys
import textwrap

import pytest
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
GATE = os.path.join(ROOT, "bin", "idp-mechanism-gate")
WORKFLOWS = os.path.join(ROOT, ".github", "workflows")


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, GATE, *args],
        capture_output=True,
        text=True,
        cwd=ROOT,
        timeout=120,
    )


def tree(tmp_path, files: dict[str, str]) -> str:
    for rel, body in files.items():
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(textwrap.dedent(body))
    return str(tmp_path)


CALLEE = """\
    name: callee
    on: {workflow_call: null}
    jobs:
      work:
        runs-on: ubuntu-latest
        steps: [{run: echo ok}]
"""


def test_a_call_to_a_workflow_that_is_not_in_the_tree_is_refused(tmp_path):
    root = tree(
        tmp_path,
        {
            ".github/workflows/caller.yml": "name: caller\non: [push]\njobs:\n  gate:\n    uses: ./.github/workflows/gone.yml\n",
        },
    )
    out = run(root)
    assert out.returncode == 1, out.stdout
    assert "gone.yml" in out.stdout


def test_a_call_that_resolves_passes(tmp_path):
    root = tree(
        tmp_path,
        {
            ".github/workflows/callee.yml": CALLEE,
            ".github/workflows/caller.yml": "name: caller\non: [push]\njobs:\n  gate:\n    uses: ./.github/workflows/callee.yml\n",
        },
    )
    assert run(root).returncode == 0


def test_the_shipped_fixtures_grade_both_ways():
    assert run(os.path.join(ROOT, "tests/fixtures/mechanism/bad")).returncode == 1
    assert run(os.path.join(ROOT, "tests/fixtures/mechanism/good")).returncode == 0


def test_the_founder_word_gate_is_in_the_tree_again():
    """founder-word.yml calls it, so its absence is what made the APPROVE word do nothing."""
    called = os.path.join(WORKFLOWS, "operating-model-gate.yml")
    assert os.path.isfile(called), (
        "founder-word.yml calls a reusable workflow that is gone again"
    )


def test_this_repositorys_own_workflows_all_resolve():
    out = run(ROOT)
    assert out.returncode == 0, out.stdout


def test_every_workflow_named_in_disabled_yaml_is_a_file_that_exists():
    """An excuse for a workflow that no longer exists is an excuse that hides the next one."""
    doc = yaml.safe_load(open(os.path.join(WORKFLOWS, "disabled.yaml"))) or {}
    for path, why in (doc.get("disabled") or {}).items():
        assert os.path.isfile(os.path.join(ROOT, path)), (
            f"{path} is excused but not in the tree"
        )
        assert len(str(why).split()) >= 15, (
            f"{path} is excused by too few words to be a reason"
        )


@pytest.mark.parametrize("state,expected", [("active", 0), ("disabled_manually", 1)])
def test_the_settings_half_refuses_a_workflow_that_github_is_not_running(
    tmp_path, state, expected
):
    """The switch lives in GitHub, so the gate is handed a fake `gh` that answers for it."""
    root = tree(
        tmp_path,
        {
            ".github/workflows/callee.yml": CALLEE,
            "bin/gh": f"#!/bin/sh\nprintf '%s\\t%s\\n' '{state}' '.github/workflows/callee.yml'\n",
        },
    )
    subprocess.run(["git", "init", "-q", root], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            root,
            "remote",
            "add",
            "origin",
            "https://github.com/chidionyema/idp.git",
        ],
        check=True,
    )
    os.chmod(os.path.join(root, "bin", "gh"), 0o700)
    env = dict(
        os.environ, PATH=os.path.join(root, "bin") + os.pathsep + os.environ["PATH"]
    )
    out = subprocess.run(
        [sys.executable, GATE, "--live", root],
        capture_output=True,
        text=True,
        env=env,
        timeout=120,
    )
    assert out.returncode == expected, out.stdout


def test_a_gh_that_cannot_answer_is_blind_and_not_a_pass(tmp_path):
    """Fail-closed: an unreadable settings half returns 2, never 0."""
    root = tree(
        tmp_path,
        {
            ".github/workflows/callee.yml": CALLEE,
            "bin/gh": "#!/bin/sh\necho 'HTTP 401' >&2\nexit 1\n",
        },
    )
    subprocess.run(["git", "init", "-q", root], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            root,
            "remote",
            "add",
            "origin",
            "https://github.com/chidionyema/idp.git",
        ],
        check=True,
    )
    os.chmod(os.path.join(root, "bin", "gh"), 0o700)
    env = dict(
        os.environ, PATH=os.path.join(root, "bin") + os.pathsep + os.environ["PATH"]
    )
    out = subprocess.run(
        [sys.executable, GATE, "--live", root],
        capture_output=True,
        text=True,
        env=env,
        timeout=120,
    )
    assert out.returncode == 2, out.stdout
