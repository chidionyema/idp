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


def test_the_drill_script_refuses_a_person_and_a_browser_login_as_the_subject() -> None:
    script = (ROOT / "bin" / "idp-verify-drill").read_text()
    assert 'EXPECT_USER="${ESTATE_CI_USER:-estate-ci}"' in script
    assert "oci iam user get --user-id" in script, "the subject is named through the API, not assumed"
    assert '[ "$ttype" != te ]' in script, "a browser login (ttype=login) must be a red identity row"
    assert "oci session authenticate" not in script
    assert not re.search(r"ocid1\.[a-z]+\.oc1\.[a-z0-9.-]*\.[a-z0-9]{20,}", script), "an OCID literal (LAW 46)"


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
