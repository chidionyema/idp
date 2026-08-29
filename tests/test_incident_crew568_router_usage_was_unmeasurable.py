"""crew#568: the founder asked who uses the model router and nobody could answer from a command.

Files say who is configured to call llm.<zone>; only the router's own ledger says who did (LAW 50,
LAW 28). This test holds the read-only `router-spend` playbook in place: listed, dispatchable from
the oke-check workflow, reading LiteLLM_SpendLogs, and never printing a key value.
"""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BG = ROOT / "bin" / "idp-oke-break-glass"
WF = ROOT / ".github" / "workflows" / "oke-check.yml"


def test_router_spend_is_a_listed_playbook():
    out = subprocess.run(["bash", str(BG), "--list"], capture_output=True, text=True, check=True).stdout
    assert "router-spend" in out.split()


def test_router_spend_is_dispatchable_from_the_workflow():
    assert "router-spend" in WF.read_text()


def test_router_spend_reads_the_ledger_and_prints_no_key_value():
    body = BG.read_text().split("pb_router_spend() {", 1)[1].split("\n}\n", 1)[0]
    assert "LiteLLM_SpendLogs" in body and "LiteLLM_VerificationToken" in body
    assert "show_redacted" in body
    assert "select token" not in body and ", token" not in body
    for verb in ("insert", "update", "delete", "drop", "alter"):
        assert verb not in body.lower(), verb
