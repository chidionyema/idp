import datetime as dt
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("proof", Path(__file__).resolve().parents[1] / "bin" / "estate_operational_proof.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
NOW = dt.datetime(2026, 11, 6, 23, 0, tzinfo=dt.timezone.utc)
SHA = "a" * 40


def evidence():
    receipt = {"status": "success", "sha": SHA, "url": "https://github.com/example/proof",
               "observed_at": NOW.isoformat()}
    return {"mission_id": "issue-7771", "source_sha": SHA, "promoted_sha": SHA,
            "deployed_sha": SHA, **{name: dict(receipt) for name in
            ("greenlane", "independent_review", "deployment", "functional_probe", "founder_surface")}}


def test_complete_evidence():
    assert module.evaluate(evidence(), NOW)["state"] == "OPERATING"


def test_dispatch_is_not_deployment():
    item = evidence()
    item.pop("deployment")
    assert module.evaluate(item, NOW)["state"] != "OPERATING"


def test_wrong_revision_refused():
    item = evidence()
    item["deployed_sha"] = "b" * 40
    assert "revision_mismatch" in module.evaluate(item, NOW)["reasons"]


def test_stale_founder_surface_refused():
    item = evidence()
    item["founder_surface"]["observed_at"] = (NOW - dt.timedelta(minutes=11)).isoformat()
    assert "stale_or_future:founder_surface" in module.evaluate(item, NOW)["reasons"]


def test_unsigned_or_missing_review_refused():
    item = evidence()
    item["independent_review"]["status"] = "pending"
    assert module.evaluate(item, NOW)["state"] != "OPERATING"


def test_future_receipt_refused():
    item = evidence()
    item["functional_probe"]["observed_at"] = (NOW + dt.timedelta(seconds=1)).isoformat()
    assert module.evaluate(item, NOW)["state"] != "OPERATING"
