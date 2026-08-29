"""crew#63 A1: the Architect's verification ledger lives on the gateway PVC (HERMES_HOME=/data),
not on the Mac. The A1 done-when named a Mac path that the live Architect never writes, so the
row could never be proved. The architect-doctor playbook now reads the ledger in the pod."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PB = (ROOT / "bin" / "idp-oke-break-glass").read_text()


def _doctor() -> str:
    start = PB.index("pb_architect_doctor() {")
    return PB[start : PB.index("\n}\n", start)]


def test_architect_doctor_reads_the_ledger_on_the_pvc():
    body = _doctor()
    assert "show verification-events" in body
    assert "/data/verification_evidence.db" in body
    assert "verification_events" in body


def test_a_missing_db_is_named_not_swallowed():
    assert "db-missing" in _doctor()


def test_claim_gate_verdicts_are_counted_from_the_gateway_log():
    body = _doctor()
    assert "claim-gate-verdicts" in body and "UNVERIFIED" in body
