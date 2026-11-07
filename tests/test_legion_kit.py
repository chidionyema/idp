"""Legion kit pins: manifest validation, chained proof evidence, scoreboard math.

The kit is the Legion automation floor: discovery (manifest), proof (chained
evidence), ranking (scorecard). Zero tokens, zero network — deterministic first.
"""

from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from legion.manifest import ManifestError, load_manifest, validate  # noqa: E402
from legion.proof import run_proof, verify_chain  # noqa: E402
from legion.scorecard import (  # noqa: E402
    DEFAULT_WEIGHTS,
    ScorecardError,
    build_scoreboard,
    score_legion,
)


def _manifest(tmp_path: Path, **over) -> Path:
    base = {
        "legion": 3,
        "name": "army",
        "repo": "agent-foundry",
        "summary": "goal -> DAG",
        "capabilities": ["dag-execution"],
        "modes": ["in-process", "nats-worker"],
        "budget": {"max_usd_per_day": 5},
        "proof": {"command": "true", "max_seconds": 60},
        "slo": {"success_rate_min": 0.98, "p95_latency_s_max": 300},
        "health": {"max_heartbeat_age_minutes": 30},
    }
    base.update(over)
    p = tmp_path / "legion.json"
    p.write_text(json.dumps(base))
    return p


# --------------------------------------------------------------------------- #
# Manifest validation
# --------------------------------------------------------------------------- #
def test_a_good_manifest_validates(tmp_path) -> None:
    assert validate(load_manifest(_manifest(tmp_path))) == []


def test_every_required_field_is_enforced(tmp_path) -> None:
    bad = json.loads(_manifest(tmp_path).read_text())
    del bad["capabilities"]
    errors = validate(bad)
    assert any("capabilities" in e for e in errors)


def test_unknown_mode_is_named(tmp_path) -> None:
    errors = validate(load_manifest(_manifest(tmp_path, modes=["in-process", "telepathy"])))
    assert any("telepathy" in e for e in errors)


def test_proof_timeout_over_ceiling_is_refused(tmp_path) -> None:
    errors = validate(
        load_manifest(_manifest(tmp_path, proof={"command": "true", "max_seconds": 9999}))
    )
    assert any("ceiling" in e for e in errors)


def test_validation_reports_every_problem_not_just_the_first(tmp_path) -> None:
    errors = validate({"legion": -1, "modes": ["bogus"], "slo": {}})
    assert len(errors) >= 5


def test_non_mapping_manifest_is_a_manifest_error(tmp_path) -> None:
    p = tmp_path / "legion.json"
    p.write_text("[1, 2]")
    with pytest.raises(ManifestError):
        load_manifest(p)


# --------------------------------------------------------------------------- #
# Proof runner + chain
# --------------------------------------------------------------------------- #
def test_proof_records_success_with_chain(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("LEGION_STATE_DIR", str(tmp_path / "state"))
    rec = run_proof(_manifest(tmp_path))
    assert rec["ok"] is True and rec["exit"] == 0
    assert verify_chain(tmp_path / "state" / "legion-proof.jsonl") == []


def test_proof_records_failure_without_raising(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("LEGION_STATE_DIR", str(tmp_path / "state"))
    rec = run_proof(_manifest(tmp_path, proof={"command": "false", "max_seconds": 60}))
    assert rec["ok"] is False and rec["exit"] == 1


def test_proof_timeout_is_recorded_as_timeout(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("LEGION_STATE_DIR", str(tmp_path / "state"))
    rec = run_proof(
        _manifest(tmp_path, proof={"command": f"{sys.executable} -c \"import time;time.sleep(9)\"", "max_seconds": 1})
    )
    assert rec["timed_out"] is True and rec["ok"] is False and rec["exit"] == 124


def test_chain_detects_tampering(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("LEGION_STATE_DIR", str(tmp_path / "state"))
    run_proof(_manifest(tmp_path))
    run_proof(_manifest(tmp_path))
    chain = tmp_path / "state" / "legion-proof.jsonl"
    lines = chain.read_text().splitlines()
    rec = json.loads(lines[0])
    rec["exit"] = 1  # tamper
    lines[0] = json.dumps(rec)
    chain.write_text("\n".join(lines) + "\n")
    problems = verify_chain(chain)
    assert problems and any("hash mismatch" in p or "prev link broken" in p for p in problems)


def test_two_proofs_chain_together(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("LEGION_STATE_DIR", str(tmp_path / "state"))
    r1 = run_proof(_manifest(tmp_path))
    r2 = run_proof(_manifest(tmp_path))
    assert r2["prev"] == r1["hash"] != r2["hash"]


# --------------------------------------------------------------------------- #
# Scorecard
# --------------------------------------------------------------------------- #
def _metrics(**over) -> dict:
    base = {
        "legion": "army",
        "success_rate": 1.0,
        "cost_efficiency": 1.0,
        "latency_score": 1.0,
        "audit_integrity": 1.0,
        "uptime": 1.0,
        "proof_age_hours": 1,
    }
    base.update(over)
    return base


def test_perfect_legion_scores_one() -> None:
    assert score_legion(_metrics())["composite"] == 1.0


def test_weights_are_applied() -> None:
    s = score_legion(_metrics(success_rate=0.5))
    # 0.5 * 0.30 weight + 0.7 from the other perfect components
    assert abs(s["composite"] - 0.85) < 1e-4


def test_stale_proof_halves_the_score() -> None:
    fresh = score_legion(_metrics(proof_age_hours=2))
    stale = score_legion(_metrics(proof_age_hours=48))
    assert stale["composite"] == round(fresh["composite"] * 0.5, 4)
    assert stale["proof_stale"] is True


def test_missing_proof_age_means_stale() -> None:
    m = _metrics()
    del m["proof_age_hours"]
    assert score_legion(m)["proof_stale"] is True


def test_below_threshold_is_shadow() -> None:
    s = score_legion(_metrics(success_rate=0.1, cost_efficiency=0.1, latency_score=0.1))
    assert s["status"] == "shadow"


def test_component_out_of_range_is_refused() -> None:
    with pytest.raises(ScorecardError):
        score_legion(_metrics(uptime=1.5))


def test_weights_must_sum_to_one() -> None:
    with pytest.raises(ScorecardError):
        score_legion(_metrics(), {**DEFAULT_WEIGHTS, "uptime": 0.5})


def test_scoreboard_ranks_descending(tmp_path) -> None:
    (tmp_path / "army.json").write_text(json.dumps(_metrics()))
    (tmp_path / "bridge.json").write_text(
        json.dumps(_metrics(legion="bridge", success_rate=0.5))
    )
    board = build_scoreboard(tmp_path)
    assert [l["legion"] for l in board["legions"]] == ["army", "bridge"]
    assert board["legions"][0]["rank"] == 1


# --------------------------------------------------------------------------- #
# CLI surface
# --------------------------------------------------------------------------- #
def _cli(args, cwd):
    env = dict(os.environ, PYTHONPATH=str(REPO))
    return subprocess.run(
        [sys.executable, "-m", "legion", *args],
        capture_output=True, text=True, cwd=cwd, env=env,
    )


def test_cli_validate_good_and_bad(tmp_path) -> None:
    good = _manifest(tmp_path)
    assert _cli(["validate", str(good)], tmp_path).returncode == 0
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"legion": 1}))
    r = _cli(["validate", str(bad)], tmp_path)
    assert r.returncode == 1 and "INVALID" in r.stderr


def test_cli_proof_and_verify(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("LEGION_STATE_DIR", str(tmp_path / "state"))
    m = _manifest(tmp_path)
    assert _cli(["proof", str(m)], tmp_path).returncode == 0
    r = _cli(["proof", "--verify", str(tmp_path / "state" / "legion-proof.jsonl")], tmp_path)
    assert r.returncode == 0 and "CHAIN-OK" in r.stdout



def test_real_homes_legion_command_resolves_from_manifest_dir() -> None:
    """Proof commands run in their manifest's folder, not repository root."""
    path = REPO / "legions" / "estate-homes.json"
    manifest = load_manifest(path)
    command = shlex.split(manifest["proof"]["command"])
    assert command[-1] == "--gate"
    # --help validates executable path without touching a live service.
    command[-1] = "--help"
    result = subprocess.run(
        command, cwd=path.parent, capture_output=True, text=True, timeout=10
    )
    assert result.returncode == 0, result.stderr
    assert "usage:" in result.stdout.lower()
