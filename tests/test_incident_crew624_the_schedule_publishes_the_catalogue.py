"""2026-08-29 (crew#624, "WHY IS HUBBLE NOT THERE"): after idp#792 put the cluster in the
catalogue, the portal still did not show it. Two faults on the publish road, both green on paper:
(1) catalog-render.yml's schedule ran in --dry-run, so nothing published unless a person
dispatched mode=commit; (2) idp#776 handed the render step a GitHub App token as GH_TOKEN and
bin/idp-catalog-push pushed the artifact with `gh auth token`, which now answered 403 on every
blob (runs 33253658000, 33254290214). This file pins both.
"""

from pathlib import Path

import yaml

IDP = Path(__file__).resolve().parents[1]
WF = IDP / ".github" / "workflows" / "catalog-render.yml"
PUSH = IDP / "bin" / "idp-catalog-push"


def _render_step() -> dict:
    wf = yaml.safe_load(WF.read_text())
    steps = wf["jobs"]["render"]["steps"]
    (step,) = [s for s in steps if s.get("name") == "render"]
    return step


def test_the_schedule_publishes_not_dry_runs():
    wf = yaml.safe_load(WF.read_text())
    assert "schedule" in wf.get(True, wf.get("on", {})), "no schedule"
    assert _render_step()["env"]["MODE"].startswith("${{ inputs.mode || 'commit' }}")


def test_the_registry_credential_is_the_actions_token_not_the_app_token():
    env = _render_step()["env"]
    assert env["GHCR_TOKEN_FILE"].startswith("${{ runner.temp }}/ghcr.token"), env
    assert "GITHUB_TOKEN" not in yaml.safe_dump(env), (
        "the arming step must not see the bot token (idp#769)"
    )
    assert "steps.app.outputs.token" in env["GH_TOKEN"], (
        "auto-merge still needs the App token (idp#769)"
    )
    wf = yaml.safe_load(WF.read_text())
    assert wf["permissions"]["packages"] == "write"
    steps = wf["jobs"]["render"]["steps"]
    names = [s.get("name") for s in steps]
    cred = [s for s in steps if (s.get("name") or "").startswith("registry credential")]
    assert cred and names.index(cred[0]["name"]) < names.index("render"), names
    assert "secrets.GITHUB_TOKEN" in yaml.safe_dump(cred[0]["env"])
    assert "ghcr.token" in cred[0]["run"]
