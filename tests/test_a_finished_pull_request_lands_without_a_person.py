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
