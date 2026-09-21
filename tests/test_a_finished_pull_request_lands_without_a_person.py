"""Ten pull requests waited on one person, and not one of them was red.

2026-09-08. Founder: "agents should be responsiblefor their own own, all this chasing is
fricion", and when asked whether it was a one-off, "its reocrring onstantly". Five of the ten
were green drafts whose sessions had ended; the rest were BEHIND main and wanted a button. The
only thing in this repository that landed a pull request was deploy-when-green.yml, and that one
looks at a single branch.

These grade bin/idp-pr-landable's verdict function, the same function
.github/workflows/merge-when-green.yml loads and runs, over pull requests built here.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import os
import re

import pytest
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
TOOL = os.path.join(ROOT, "bin", "idp-pr-landable")
BOT = os.path.join(ROOT, ".github", "workflows", "merge-when-green.yml")

#: bin/idp-pr-landable has no .py suffix, so importlib recognises no loader for it and
#: spec_from_file_location returns None. The loader is named explicitly; the assert stays for the
#: real failure mode, a renamed or deleted tool.
_spec = importlib.util.spec_from_file_location(
    "idp_pr_landable",
    TOOL,
    loader=importlib.machinery.SourceFileLoader("idp_pr_landable", TOOL),
)
assert _spec is not None and _spec.loader is not None, (
    "bin/idp-pr-landable is not where this test expects it"
)
landable = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(landable)


def check(name: str, conclusion: str = "SUCCESS") -> dict:
    return {"name": name, "status": "COMPLETED", "conclusion": conclusion}


def pull_request(**over) -> dict:
    pr = {
        "number": 1,
        "headRefName": "fix/something",
        "isDraft": False,
        "mergeStateStatus": "CLEAN",
        "labels": [],
        "statusCheckRollup": [check("ci")],
    }
    pr.update(over)
    return pr


REQUIRED = {"ci"}


def verdict(pr: dict) -> str:
    return landable.verdict(pr, REQUIRED)[0]


def test_a_green_clean_pull_request_lands():
    assert verdict(pull_request()) == "MERGE"


def test_a_green_draft_is_marked_ready_rather_than_left_to_rot():
    """The flag belongs to a session that ended. Five of these sat ten days in crew."""
    assert verdict(pull_request(isDraft=True)) == "READY"


@pytest.mark.parametrize(
    "over",
    [
        {"statusCheckRollup": [check("ci", "FAILURE")]},
        {"mergeStateStatus": "DIRTY"},
        {"labels": [{"name": "hold"}]},
        {"statusCheckRollup": []},
        {"statusCheckRollup": [{"name": "ci", "status": "IN_PROGRESS"}]},
    ],
    ids=["red", "conflicted", "held", "unproven", "still-running"],
)
def test_an_unfinished_draft_is_never_touched(over):
    """READY is reached only through MERGE, so nothing un-drafts work that is not finished."""
    assert verdict(pull_request(isDraft=True, **over)) == "SKIP"


def test_a_required_check_that_never_ran_is_not_a_pass():
    """crew#105: a check no workflow produces cannot appear, and 'not failing' read as green."""
    pr = pull_request(statusCheckRollup=[check("something-else")])
    assert verdict(pr) == "SKIP"


def test_behind_main_is_refreshed_rather_than_skipped():
    """Skipping this is how two stalled pull requests in crew became conflicts."""
    assert verdict(pull_request(mergeStateStatus="BEHIND")) == "UPDATE"


def test_the_bot_loads_the_verdict_from_the_tool_and_does_not_restate_it():
    """One copy of the rule. crew typed its required checks into a heredoc and went blind."""
    body = open(BOT).read()
    assert "bin/idp-pr-landable" in body
    assert "landable.verdict(" in body


def test_the_bot_leaves_the_deploy_branch_to_its_own_workflow():
    """deploy-when-green carries an extra gate (image-only diff); two bots on one branch race."""
    doc = yaml.safe_load(open(BOT))
    env = doc["jobs"]["land"]["steps"][-1]["env"]
    assert env["DEPLOY_BRANCH"] == "flux/image-updates"
    deploy = yaml.safe_load(
        open(os.path.join(ROOT, ".github/workflows/deploy-when-green.yml"))
    )
    assert "flux/image-updates" in json.dumps(deploy["jobs"])


def test_the_bot_caps_how_much_one_tick_can_land():
    doc = yaml.safe_load(open(BOT))
    env = doc["jobs"]["land"]["steps"][-1]["env"]
    assert int(env["MAX_PER_RUN"]) >= 1


def test_every_verdict_the_tool_can_return_is_handled_by_the_bot():
    """A verdict the shell has no case for is a pull request that silently does nothing."""
    returned = set(re.findall(r'return "([A-Z]+)"', open(TOOL).read()))
    handled = set(re.findall(r"^\s{14}([A-Z]+)\)", open(BOT).read(), re.M))
    assert returned - handled - {"SKIP"} == set(), (
        f"{returned - handled} has no case in the bot"
    )


def test_admitted_remediation_with_a_green_shadow_proof_lands():
    """A PR the lane admits (type:auto-remediation) may auto-merge when a real shadow-verify check
    on that head is green (W3.3): the proof is the shadow run, not the label."""
    pr = pull_request(
        labels=[{"name": "type:auto-remediation"}],
        statusCheckRollup=[
            check("ci"),
            check("shadow-verify", "SUCCESS"),
        ],
    )
    assert verdict(pr) == "MERGE"


def test_remediation_without_a_green_shadow_proof_never_lands():
    """A label is not a proof. A PR claiming risk-few (type:auto-remediation) but with no green
    shadow-verify/convergence check must not auto-merge (W3.3): fail closed, never ride the plain
    green path into the cluster."""
    for broken in (
        # a PR with no shadow-verify check at all
        {"statusCheckRollup": [check("ci")]},
        # a PR whose shadow-verify failed
        {"statusCheckRollup": [check("ci"), check("shadow-verify", "FAILURE")]},
    ):
        bl = dict(labels=[{"name": "type:auto-remediation"}], **broken)
        assert verdict(pull_request(**bl)) == "SKIP", f"should SKIP: {bl}"


def test_row_three_wires_the_admitted_mutation_scope_check():
    """ADR 0025: the Greenlane grows by adding a row whose scope binary is called, proved both
    ways. Row 3 (an admitted reversible mutation) must CALL bin/idp-admitted-mutation-diff --
    a row that names the rule but never runs the binary lands anything."""
    body = open(os.path.join(ROOT, ".github/workflows/deploy-when-green.yml")).read()
    assert "bin/idp-admitted-mutation-diff" in body, (
        "Row 3 does not call the scope check, so a mutation PR would be treated as landable"
    )
    assert "mutation/" in body, "Row 3 does not scope itself to mutation/* branches"
    # The scope check must be a PRECONDITION of landing, like Row 1's image-only check: it is
    # called and, only on success, try_land is reached. A row that lands first and proves later
    # is not a guard.
    assert re.search(
        r"if bin/idp-admitted-mutation-diff --pr \"\$p\"; then\s*\n\s*try_land \"\$p\"",
        body,
    ), "Row 3 does not gate try_land on the scope check passing"


def test_the_admitted_mutation_scope_check_refuses_a_double_inverse_free_branch(
    monkeypatch,
):
    """The scope binary itself is exercised from disk: a non-mutation branch is refused.

    This is the rung the ADR asks a new row to carry -- a fixture it must refuse and one it must
    pass -- read here so the row cannot be added without a working binary behind it.
    """
    import subprocess
    import sys as _sys

    binary = os.path.join(ROOT, "bin", "idp-admitted-mutation-diff")
    good = subprocess.run(
        [
            _sys.executable,
            binary,
            "--fixture-dir",
            "tests/fixtures/admitted-mutation/good",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert good.returncode == 0, good.stdout + good.stderr
    bad = subprocess.run(
        [
            _sys.executable,
            binary,
            "--fixture-dir",
            "tests/fixtures/admitted-mutation/bad",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert bad.returncode == 1, bad.stdout + bad.stderr
