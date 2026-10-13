"""The concierge's public URL is written by the deploy that learns it, not asked of a person.

PUBLIC_SERVER_URL is the endpoint's own Modal URL: Modal issues it at deploy. It used to be a
Bitwarden target on the `twilio` row, so the bridge rendered an ExternalSecret no person was
ever meant to fill (LAW 31) and it sat red, while the cutover wrote the URL into a vault entry
nothing carried to Modal. The endpoint reads it from the Modal secret `concierge-tunnel`
(mums-concierge ephemeral/webapp.py), so that is where the cutover writes it -- and only there.
"""

import pathlib

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
WORKFLOW = (ROOT / ".github/workflows/concierge-deploy.yml").read_text()


def _cutover_script():
    steps = yaml.safe_load(WORKFLOW)["jobs"]
    steps = [s for job in steps.values() for s in job.get("steps", [])]
    (step,) = [
        s for s in steps if s.get("name", "").startswith("cut the endpoint over")
    ]
    return step["run"]


def test_no_person_is_asked_for_the_url():
    rows = yaml.safe_load((ROOT / "platform/vendors/consoles.yaml").read_text())[
        "vendors"
    ]
    fields = [t.get("field") for row in rows.values() for t in row.get("targets") or []]
    assert "TWILIO_AUTH_TOKEN" in fields  # the walk reaches the rows at all
    assert "PUBLIC_SERVER_URL" not in fields
    assert "PUBLIC_WSS_URL" not in fields


def test_the_cutover_writes_the_secret_the_endpoint_reads():
    run = _cutover_script()
    assert "modal secret create concierge-tunnel PUBLIC_SERVER_URL=" in run
    assert "PUBLIC_WSS_URL=" in run
    # the warm container only sees a secret it started with
    assert "modal deploy code/ephemeral/webapp.py" in run


def test_the_cutover_does_not_write_a_second_home():
    assert "idp-vault-put" not in _cutover_script()


def test_the_first_deploy_is_not_refused_for_a_secret_only_the_cutover_can_fill():
    deploy = WORKFLOW[
        WORKFLOW.index("deploy the always-on endpoint") : WORKFLOW.index(
            "for s in human-twilio"
        )
    ]
    assert "modal secret create concierge-tunnel" in deploy
