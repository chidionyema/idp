"""The merge queue exists in git and every required check reports inside a queued run.

Founder order 2026-09-02: green pull requests merge themselves; the founder handles
exceptions only. The failure mode this guards is silent and total: a required check
that never reports in the queue's own event leaves every queued entry hanging until
its timeout, which reads as "the queue is broken" while every individual piece is
green. So the control walks the chain end to end: the queue ruleset record, the
zero-review release ruleset, the workflow trigger, and the two checks that need a
pull-request number the queue event does not carry.
"""

import json
import pathlib

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
QUEUE = json.loads((ROOT / "platform/github/ruleset.idp.merge-queue.json").read_text())
RELEASES = json.loads(
    (ROOT / "platform/github/ruleset.idp.founder-only-releases.json").read_text()
)
REQUIRED = json.loads(
    (ROOT / "platform/github/ruleset.idp.required-checks.json").read_text()
)
CI = yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text())
CI_TEXT = (ROOT / ".github/workflows/ci.yml").read_text()
GATE_TEXT = (ROOT / ".github/workflows/operating-model-gate.yml").read_text()


def _rule(ruleset, kind):
    rows = [r for r in ruleset["rules"] if r["type"] == kind]
    assert len(rows) == 1, (
        f"{ruleset['name']} carries {len(rows)} {kind} rules, wants exactly 1"
    )
    return rows[0]


def test_the_queue_ruleset_squash_merges_the_default_branch():
    assert QUEUE["enforcement"] == "active"
    assert QUEUE["conditions"]["ref_name"]["include"] == ["~DEFAULT_BRANCH"]
    p = _rule(QUEUE, "merge_queue")["parameters"]
    assert p["merge_method"] == "SQUASH", "trunk-only: the queue lands squash commits"
    assert p["min_entries_to_merge_wait_minutes"] == 0, (
        "a lone green entry lands at once"
    )


def test_the_release_ruleset_asks_no_human_for_a_review():
    p = _rule(RELEASES, "pull_request")["parameters"]
    assert p["required_approving_review_count"] == 0
    assert p["require_last_push_approval"] is False
    assert p["require_extra_approval_for_unattributed_changes"] is False
