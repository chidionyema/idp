"""platform/github/ruleset.idp.required-checks.json drifted from the live ruleset on
chidionyema/idp for an unknown period: the file said idp-required-checks and required
offline-gate/security-scan/shadow-verify/portal-app, while the live ruleset (24071703) was
named required-checks-main and actually required fast-gate/fast-gate, bdd, guarded-paths,
test, executes-gate, feature-request-plan. bin/idp-pr-landable and bin/repo-rulesets both
read this file as ground truth, so a silent drift here is a silent drift in what every PR
verdict and every ruleset apply believes main requires. This pins the reconciled spec so a
future edit that reintroduces the stale list, or renames the ruleset away from what's live,
fails loudly instead of drifting again unnoticed.
"""

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPEC = os.path.join(ROOT, "platform", "github", "ruleset.idp.required-checks.json")

EXPECTED_CONTEXTS = {
    "fast-gate / fast-gate",
    "bdd",
    "guarded-paths",
    "test",
    "executes-gate",
    "feature-request-plan",
}


def _load():
    with open(SPEC, encoding="utf-8") as f:
        return json.load(f)


def test_ruleset_name_matches_the_live_ruleset_on_github():
    assert _load()["name"] == "required-checks-main"


def test_required_status_checks_match_what_is_actually_enforced():
    doc = _load()
    rule = next(r for r in doc["rules"] if r["type"] == "required_status_checks")
    contexts = {c["context"] for c in rule["parameters"]["required_status_checks"]}
    assert contexts == EXPECTED_CONTEXTS


def test_pull_request_rule_requires_no_human_approval():
    doc = _load()
    rule = next(r for r in doc["rules"] if r["type"] == "pull_request")
    assert rule["parameters"]["required_approving_review_count"] == 0
