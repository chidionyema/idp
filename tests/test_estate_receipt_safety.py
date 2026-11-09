"""Falsifiers for the historical receipt boundary (idp#7849).

A verification function may inspect a historical observation. It MUST NOT
perform the observed command again, especially commands with side effects.
The observation hash proves local consistency, not actor authentication.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MOD = ROOT / "platform" / "estate" / "governance" / "receipt.py"
SPEC = importlib.util.spec_from_file_location("historical_receipt", MOD)
assert SPEC and SPEC.loader
receipt = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(receipt)


def test_historical_verify_does_not_repeat_side_effect(tmp_path, monkeypatch):
    cmd = [
        sys.executable,
        "-c",
        "from pathlib import Path; p=Path('counter'); "
        "p.write_text(p.read_text()+'x' if p.exists() else 'x')",
    ]
    historical = receipt.run_receipt(cmd, cwd=str(tmp_path))
    assert (tmp_path / "counter").read_text() == "x"

    def forbidden(*args, **kwargs):
        raise AssertionError("verification attempted to replay the historical command")

    monkeypatch.setattr(receipt, "run_receipt", forbidden)
    for _ in range(2):
        verdict = receipt.verify(historical)
        assert verdict == {
            "ok": True,
            "level": "local-consistency",
            "authenticated": False,
            "replayed": False,
            "reason": "locally consistent, not independently authenticated",
        }
    assert (tmp_path / "counter").read_text() == "x"


def test_failure_still_produces_a_checkable_local_observation(tmp_path):
    historical = receipt.run_receipt([sys.executable, "-c", "raise SystemExit(17)"], cwd=str(tmp_path))
    assert historical["exit"] == 17
    assert receipt.verify(historical)["ok"] is True
    assert receipt.verify(historical)["authenticated"] is False


def test_alteration_legacy_and_poisoned_shape_fail_closed(tmp_path):
    historical = receipt.run_receipt([sys.executable, "-c", "print('receipt observation')"], cwd=str(tmp_path))
    for field, value in (
        ("exit", 0 if historical["exit"] != 0 else 1),
        ("line", "fabricated success"),
        ("sha256", "a" * 64),
        ("command", ["rm", "-rf", "/"]),
    ):
        poison = dict(historical, **{field: value})
        assert receipt.verify(poison)["ok"] is False, field
        assert receipt.verify(poison)["replayed"] is False
    no_integrity = dict(historical)
    no_integrity.pop("observation_sha256")
    assert receipt.verify(no_integrity)["ok"] is False
    assert receipt.verify({"command": ["echo", "hello"]})["ok"] is False
    assert receipt.verify([])["ok"] is False
    invalid_exit = dict(historical, exit=True)
    assert receipt.verify(invalid_exit)["ok"] is False


def test_round_trip_stays_local_and_unattested(tmp_path):
    historical = receipt.run_receipt([sys.executable, "-c", "print('ok')"], cwd=str(tmp_path))
    saved = tmp_path / "receipt.json"
    receipt.save(historical, str(saved))
    loaded = json.loads(saved.read_text())
    verdict = receipt.verify(loaded)
    assert verdict["ok"] is True
    assert verdict["authenticated"] is False
    assert verdict["level"] == "local-consistency"
