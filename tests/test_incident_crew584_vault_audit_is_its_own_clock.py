"""Incident crew#584, 2026-08-29: the vault audit (bin/idp-vault-reads, a 90-minute OCI audit query)
sat inside oke-check --check and took 427 s of every platform pull request (run 33237964214). The
founder's ruling: monitoring never blocks a pull request. The audit now runs from
.github/workflows/vault-reads.yml on its own schedule; red opens a P1, green closes it."""
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]
WF = ROOT / ".github" / "workflows" / "vault-reads.yml"
TITLE = "P1: external-secrets is not reading the vault"


def _wf():
    return yaml.safe_load(WF.read_text())


def test_the_audit_runs_on_a_schedule_and_never_on_a_pull_request():
    on = _wf()[True] if True in _wf() else _wf()["on"]
    assert "schedule" in on and "workflow_dispatch" in on
    assert "pull_request" not in on and "push" not in on


def test_red_opens_the_p1_and_green_closes_it():
    steps = _wf()["jobs"]["audit"]["steps"]
    by_name = {s.get("name", ""): s for s in steps}
    red = by_name["a red or blind audit opens or updates the P1"]
    green = by_name["a green audit closes the open P1, with the run as the receipt"]
    assert red["if"].startswith("failure()") and TITLE in red["run"] and "gh issue create" in red["run"]
    assert green["if"] == "success()" and TITLE in green["run"] and "gh issue close" in green["run"]
    assert "bin/idp-vault-reads" in by_name["bin/idp-vault-reads"]["run"]
    assert _wf()["permissions"]["issues"] == "write"


def test_the_audit_is_no_longer_a_row_of_oke_check():
    src = (ROOT / "bin" / "idp-oke-rebuild").read_text()
    assert "step vault-reads" not in src
