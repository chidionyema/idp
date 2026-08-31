"""crew#584 PR B: the "Enable platform feature" Backstage template requests a tier from
platform/features/features.yaml (crew#584 PR A, feat/crew584-feature-register) by opening a
reviewed pull request -- there is no runner in the scaffolder to flip a Flux Kustomization's
`suspend:` field directly, so the template does not invent one.

REGISTER_FEATURES below is frozen from the register as read on 2026-08-29 so this test does
not depend on PR A landing first (it has not, as of this pull request: platform/features/ is
still untracked on feat/crew584-feature-register). The moment features.yaml exists in this
checkout, test_feature_enum_matches_the_live_register_file_when_it_exists stops skipping and
cross-checks the frozen list against the real file, so drift between the two pull requests
cannot go unnoticed.
"""
import pathlib

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
TPL = ROOT / "backstage" / "templates" / "enable-platform-feature"
CI = ROOT / ".github" / "workflows" / "ci.yml"

REGISTER_FEATURES = [
    "traces",
    "logs-metrics-store",
    "alerting-healing",
    "workflows",
    "agent-memory",
    "model-routing",
    "agent-gateway",
    "hermes-agent",
    "founder-screen",
    "health-checks",
    "autoscaling",
    "chaos-drills",
    "science",
    "staging",
    "config-reload",
    "dev-loop",
    "commerce",
    "customer-identity",
]

# Every tier name used anywhere in the register, across all 18 features.
REGISTER_TIERS = {"enterprise", "lean", "on", "off", "namespace"}


def _spec():
    return yaml.safe_load((TPL / "template.yaml").read_text())


def _feature_props():
    return _spec()["spec"]["parameters"][0]["properties"]


def test_the_template_is_a_backstage_template():
    spec = _spec()
    assert spec["kind"] == "Template"
    assert spec["metadata"]["name"] == "enable-platform-feature"
    required = spec["spec"]["parameters"][0]["required"]
    for r in ("feature", "tier", "reason"):
        assert r in required


def test_feature_enum_matches_the_register():
    assert _feature_props()["feature"]["enum"] == REGISTER_FEATURES


def test_feature_enum_matches_the_live_register_file_when_it_exists():
    register_path = ROOT / "platform" / "features" / "features.yaml"
    if not register_path.exists():
        pytest.skip(
            "platform/features/features.yaml lands with crew#584 PR A "
            "(feat/crew584-feature-register), not on this branch yet"
        )
    register = yaml.safe_load(register_path.read_text())
    names = [f["name"] for f in register["features"]]
    assert REGISTER_FEATURES == names, "the frozen list in this test has drifted from the register"
    assert _feature_props()["feature"]["enum"] == names


def test_tier_enum_covers_every_tier_name_in_the_register():
    assert set(_feature_props()["tier"]["enum"]) == REGISTER_TIERS


def test_the_pr_body_carries_the_optimised_line_and_the_required_fields():
    body = (TPL / "template.yaml").read_text()
    assert "Optimised: template -> 1 PR, 0 hand edits" in body
    assert "Feature: ${{ parameters.feature }}" in body
    assert "Tier: ${{ parameters.tier }}" in body
    assert "Reason: ${{ parameters.reason }}" in body


def test_the_pr_body_admits_what_the_scaffolder_cannot_do_instead_of_inventing_it():
    body = (TPL / "template.yaml").read_text()
    assert "bin/idp-features enable" in body
    assert "no runner" in body or "does not invent" in body


def test_the_template_opens_a_pull_request_rather_than_running_enable_directly():
    spec = _spec()
    actions = [s["action"] for s in spec["spec"]["steps"]]
    assert "publish:github:pull-request" in actions
    assert "publish:github" not in [a for a in actions if a != "publish:github:pull-request"]


def test_the_template_is_registered_in_the_catalogue_and_shipped_in_the_image():
    for cfg, target in (
        ("app-config.yaml", "../../templates/enable-platform-feature/template.yaml"),
        ("app-config.container.yaml", "/app/templates/enable-platform-feature/template.yaml"),
    ):
        text = (ROOT / "backstage" / cfg).read_text()
        assert target in text, f"{cfg} does not register the template"
    assert "COPY --chown=node:node templates ./templates" in (ROOT / "backstage" / "Dockerfile").read_text()


def test_the_ci_workflow_prices_the_requested_row():
    ci = CI.read_text()
    assert "idp-features plan" in ci
    assert "platform/features/requests.yaml" in ci
    assert "GITHUB_STEP_SUMMARY" in ci
    # No-op, not a hard failure, until crew#584 PR A lands bin/idp-features.
    assert "bin/idp-features" in ci
