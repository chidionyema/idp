"""idp#699. Diagnose prints storage classes, unbound claims and Kyverno policy-report fail
counts; before this a pod stuck on a missing StorageClass and a rule failing in Audit were
both invisible from the playbook. This test pins the three rows."""
from pathlib import Path

PLAYBOOK = Path(__file__).resolve().parents[1] / "bin" / "idp-oke-break-glass"
ROWS = ("storage-classes", "claims-not-bound", "policy-report-fails")


def test_diagnose_prints_storage_and_policy_report_rows():
    text = PLAYBOOK.read_text()
    missing = [row for row in ROWS if f"show {row} " not in text]
    assert not missing, f"diagnose no longer prints {missing}"
