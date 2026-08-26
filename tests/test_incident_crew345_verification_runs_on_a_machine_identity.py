"""Incident crew#345, 2026-08-26: live cluster verification stopped at least five times in one
night because the laptop's OCI browser session had expired. Measured: a browser session token is
a 60-minute JWT (exp - iat), refreshable to 24 h from the login; a `--no-browser` token-exchange
session has sess_exp == exp and cannot be refreshed at all. The rule (rung 4, incident test):
the platform's hourly health verification runs on the estate-ci machine identity from a runner,
the kube read happens inside the cluster on the node's instance principal (platform/state, idp#267), and no scheduled path
anywhere in this repository asks a person to log in."""
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WF = ROOT / ".github" / "workflows"
TOKEN_EXCHANGE = "gtrevorrow/oci-token-exchange-action"


def _docs(path: Path) -> list[dict]:
    return [d for d in yaml.safe_load_all(path.read_text()) if d]


def test_verify_drill_runs_hourly_on_the_exchanged_oidc_session_and_no_key() -> None:
    wf = yaml.safe_load((WF / "verify-drill.yml").read_text())
    crons = [s["cron"] for s in wf[True]["schedule"]]
    assert crons == ["23 * * * *"], crons
    assert wf["permissions"]["id-token"] == "write"
    steps = wf["jobs"]["verify-drill"]["steps"]
    assert any(TOKEN_EXCHANGE in s.get("uses", "") for s in steps), "no token exchange step"
    drill = next(s for s in steps if "bin/idp-verify-drill" in s.get("run", ""))
    assert drill["env"]["OCI_CLI_AUTH"] == "security_token"
    # identifiers only: no OCI API key, fingerprint, private key or password reaches the job
    text = (WF / "verify-drill.yml").read_text()
    assert not re.search(r"OCI_(API|PRIVATE)_KEY|FINGERPRINT|PASSWORD", text), "a static credential on the verification path"


def test_verify_drill_is_catalogued_with_its_own_cron_verbatim() -> None:
    drills = {d["name"]: d for d in yaml.safe_load((ROOT / "drills" / "catalogue.yaml").read_text())["drills"]}
    row = drills["verify-drill"]
    assert row["workflow"] == "verify-drill.yml"
    wf = yaml.safe_load((WF / row["workflow"]).read_text())
    assert row["schedule"] == wf[True]["schedule"][0]["cron"]
    assert row["max_age_hours"] <= 3, "an hourly drill older than three hours is a dead drill"


def test_the_drill_script_refuses_a_person_and_a_browser_login_as_the_subject() -> None:
    script = (ROOT / "bin" / "idp-verify-drill").read_text()
    assert 'EXPECT_USER="${ESTATE_CI_USER:-estate-ci}"' in script
    assert "oci iam user get --user-id" in script, "the subject is named through the API, not assumed"
    assert '[ "$ttype" != te ]' in script, "a browser login (ttype=login) must be a red identity row"
    assert "oci session authenticate" not in script
    assert not re.search(r"ocid1\.[a-z]+\.oc1\.[a-z0-9.-]*\.[a-z0-9]{20,}", script), "an OCID literal (LAW 46)"


def test_the_receipt_row_reuses_the_one_in_cluster_writer_and_its_reader() -> None:
    """One writer (platform/state, idp#267), one reader (bin/idp-cluster-state). A second CronJob
    or a second bucket reader for the same fact is the stitching the headline forbids."""
    script = (ROOT / "bin" / "idp-verify-drill").read_text()
    assert 'idp-cluster-state' in script and "oci os object" not in script
    assert not (ROOT / "platform" / "health").exists(), "a second health CronJob next to platform/state"
    rows = _docs(ROOT / "clusters" / "oke" / "platform.yaml")
    state = next(d for d in rows if d["kind"] == "Kustomization" and d["metadata"]["name"] == "cluster-state")
    assert state["spec"]["path"] == "./platform/state"
    wf = (WF / "verify-drill.yml").read_text()
    assert "platform/state/**" in wf and "bin/idp-cluster-state" in wf


def test_no_scheduled_workflow_asks_a_person_to_log_in() -> None:
    """Every scheduled workflow that touches OCI holds the exchanged session and nothing else."""
    for f in sorted(WF.glob("*.yml")):
        wf = yaml.safe_load(f.read_text())
        text = f.read_text()
        if "schedule" not in (wf.get(True) or {}) or "OCI_CLI_AUTH" not in text:
            continue
        assert TOKEN_EXCHANGE in text, f"{f.name} is scheduled, talks to OCI, and exchanges no OIDC token"
        # graded on what runs, not on comments: oke-check.yml names the command it replaces (idp#267)
        code = "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("#"))
        assert "oci session authenticate" not in code, f"{f.name} asks for a browser login"
