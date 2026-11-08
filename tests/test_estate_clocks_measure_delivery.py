"""Chronos measures delivered cadence, and the detector can fail.

These tests exist because the estate has already shipped a gate that could not
fail: the CLOCKS.md freshness check reported staleness only in theory, and the
pre-push gate passed ruff errors in nine seconds (AGENTS.md section 9, R1/R2).
So the assertions below are mostly about the gate's ability to REFUSE, and every
one of them runs without a network.
"""

from __future__ import annotations

import datetime as dt
import json
import subprocess
import sys
from pathlib import Path

import pytest

IDP = Path(__file__).resolve().parent.parent
CLOCKS = IDP / "bin" / "idp-estate-clocks"
PROOF = IDP / "bin" / "idp-estate-clocks-proof"
REGISTRY = IDP / "legions" / "estate-clocks.json"

NOW = "2026-11-08T12:00:00Z"
LATER = "2026-11-08T16:00:00Z"
TOL = 60


def scheduled(
    minutes_before_now: int = 20, now: str = NOW, conclusion: str = "success"
) -> dict:
    base = dt.datetime.fromisoformat(now.replace("Z", "+00:00"))
    at = base - dt.timedelta(minutes=minutes_before_now)
    return {
        "event": "schedule",
        "created": at.isoformat().replace("+00:00", "Z"),
        "conclusion": conclusion,
        "url": "https://example.invalid/run/1",
        "status": "completed",
    }


def other_event(event: str, minutes_before_now: int = 5, now: str = NOW) -> dict:
    run = scheduled(minutes_before_now, now)
    run["event"] = event
    return run


def write_runs(tmp_path: Path, runs: dict) -> Path:
    path = tmp_path / "runs.json"
    path.write_text(json.dumps(runs), encoding="utf-8")
    return path


def registry(tmp_path: Path, obligations: list[dict], name: str = "fixture") -> Path:
    doc = {
        "legion": 3,
        "name": name,
        "repo": "idp",
        "summary": "pytest fixture; never scheduled",
        "capabilities": ["delivered-cadence-measurement"],
        "modes": ["gh-runner"],
        "budget": {"max_usd_per_day": 0.01},
        "proof": {"command": "true", "max_seconds": 10},
        "slo": {"success_rate_min": 0.98, "p95_latency_s_max": 300},
        "health": {"max_heartbeat_age_minutes": 45},
        "obligations": obligations,
    }
    path = tmp_path / f"{name}.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


def obligation(oid: str = "ping", workflow: str = "ping.yml", **kw) -> dict:
    base = {
        "id": oid,
        "kind": "github-workflow",
        "workflow": workflow,
        "declares": "*/5 * * * *",
        "declares_human": "every 5 minutes",
        "owner": "estate",
        "evidence": "test fixture",
        "max_age_minutes": TOL,
        "catch_up": "next tick",
        "state": "active",
    }
    base.update(kw)
    return base


def run(
    registry_path: Path, now: str, runs_path: Path | None = None, *extra: str
) -> tuple[int, dict | str]:
    argv = [
        sys.executable,
        str(CLOCKS),
        "--registry",
        str(registry_path),
        "--now",
        now,
        *extra,
    ]
    if runs_path is not None:
        argv += ["--runs-json", str(runs_path)]
    proc = subprocess.run(argv, capture_output=True, text=True)
    payload: dict | str
    if proc.stdout.strip():
        try:
            payload = json.loads(proc.stdout)
        except json.JSONDecodeError:
            payload = proc.stdout
    else:
        payload = proc.stderr
    return proc.returncode, payload


def verdict_of(payload: dict, index: int = 0) -> str:
    return payload["obligations"][index]["verdict"]


# --------------------------------------------------------------------------
# the verdict vocabulary
# --------------------------------------------------------------------------


def test_a_clock_that_delivered_inside_its_tolerance_is_measured_ok(tmp_path):
    reg = registry(tmp_path, [obligation()])
    runs = write_runs(tmp_path, {"ping.yml": [scheduled(20)]})
    code, payload = run(reg, NOW, runs, "--json", "--gate")
    assert verdict_of(payload) == "MEASURED_OK"
    assert payload["obligations"][0]["age_minutes"] == pytest.approx(20.0)
    assert code == 0


def test_a_clock_past_its_tolerance_is_a_missed_cycle(tmp_path):
    reg = registry(tmp_path, [obligation()])
    runs = write_runs(tmp_path, {"ping.yml": [scheduled(20)]})
    code, payload = run(reg, LATER, runs, "--json", "--gate")
    assert verdict_of(payload) == "MISSED_CYCLE"
    assert code == 1


def test_the_verdict_changes_on_elapsed_time_alone_not_on_edited_evidence(tmp_path):
    reg = registry(tmp_path, [obligation()])
    runs = write_runs(tmp_path, {"ping.yml": [scheduled(20)]})
    fresh, _ = run(reg, NOW, runs, "--gate")
    late, _ = run(reg, LATER, runs, "--gate")
    assert (fresh, late) == (0, 1)


def test_a_clock_that_never_fired_is_a_finding_not_a_silence(tmp_path):
    reg = registry(tmp_path, [obligation()])
    runs = write_runs(tmp_path, {"ping.yml": []})
    code, payload = run(reg, NOW, runs, "--json", "--gate")
    assert verdict_of(payload) == "MISSED_CYCLE"
    assert "never fired" in payload["obligations"][0]["note"]
    assert code == 1


def test_runs_triggered_by_a_human_do_not_count_as_delivery(tmp_path):
    reg = registry(tmp_path, [obligation()])
    runs = write_runs(
        tmp_path,
        {"ping.yml": [other_event("workflow_dispatch", 5), other_event("push", 10)]},
    )
    code, payload = run(reg, NOW, runs, "--json", "--gate")
    assert verdict_of(payload) == "MISSED_CYCLE", (
        "a dead cron must not hide behind a busy human"
    )
    assert code == 1


def test_a_workflow_missing_from_the_tree_is_not_here_and_fails_the_gate(tmp_path):
    reg = registry(tmp_path, [obligation(workflow="no-such-workflow-here.yml")])
    runs = write_runs(tmp_path, {})
    code, payload = run(reg, NOW, runs, "--json", "--gate")
    assert verdict_of(payload) == "NOT_HERE"
    assert code == 1, "reporting a finding and passing is the fail-open defect"


def test_a_retired_clock_is_not_graded_and_does_not_fail_the_gate(tmp_path):
    reg = registry(tmp_path, [obligation(state="retired", catch_up="none - retired")])
    runs = write_runs(tmp_path, {"ping.yml": []})
    code, payload = run(reg, NOW, runs, "--json", "--gate")
    assert verdict_of(payload) == "MEASURED_OK"
    assert "retired" in payload["obligations"][0]["note"]
    assert code == 0


def test_a_tolerance_that_is_missing_is_unknown_and_blind_never_ok(tmp_path):
    reg = registry(tmp_path, [obligation(max_age_minutes=None)])
    runs = write_runs(tmp_path, {"ping.yml": [scheduled(1)]})
    code, payload = run(reg, NOW, runs, "--json", "--gate")
    assert verdict_of(payload) == "UNKNOWN"
    assert code == 2, "UNKNOWN must never grade as healthy"


def test_an_unreadable_history_is_blind_and_exits_two(tmp_path):
    reg = registry(tmp_path, [obligation()])
    # No --runs-json and a repo that cannot resolve: the read fails.
    proc = subprocess.run(
        [
            sys.executable,
            str(CLOCKS),
            "--registry",
            str(reg),
            "--now",
            NOW,
            "--gate",
            "--repo",
            "chidionyema/chronos-pytest-repo-that-does-not-exist",
        ],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 2, (
        f"expected BLIND, got {proc.returncode}: {proc.stdout}{proc.stderr}"
    )


def test_a_scheduled_run_without_a_usable_timestamp_is_unknown(tmp_path):
    reg = registry(tmp_path, [obligation()])
    broken = [
        {
            "event": "schedule",
            "created": None,
            "conclusion": "success",
            "url": "",
            "status": "",
        }
    ]
    runs = write_runs(tmp_path, {"ping.yml": broken})
    code, payload = run(reg, NOW, runs, "--json", "--gate")
    assert verdict_of(payload) == "UNKNOWN"
    assert code == 2


def test_grading_one_obligation_leaves_the_others_out_of_the_report(tmp_path):
    reg = registry(
        tmp_path, [obligation("ping"), obligation("other", "branch-archive.yml")]
    )
    runs = write_runs(tmp_path, {"ping.yml": [scheduled(1)], "branch-archive.yml": []})
    code, payload = run(reg, NOW, runs, "--json", "--gate", "--obligation", "other")
    assert [o["id"] for o in payload["obligations"]] == ["other"]
    assert code == 1


def test_an_unknown_obligation_name_is_blind_rather_than_an_empty_pass(tmp_path):
    reg = registry(tmp_path, [obligation()])
    runs = write_runs(tmp_path, {"ping.yml": [scheduled(1)]})
    code, _ = run(reg, NOW, runs, "--gate", "--obligation", "does-not-exist")
    assert code == 2


def test_a_bad_now_value_is_blind(tmp_path):
    reg = registry(tmp_path, [obligation()])
    runs = write_runs(tmp_path, {"ping.yml": [scheduled(1)]})
    code, _ = run(reg, "yesterday", runs, "--gate")
    assert code == 2


# --------------------------------------------------------------------------
# the registry is the estate's own legion format, not a second schema
# --------------------------------------------------------------------------


def test_the_registry_validates_as_a_legion_manifest():
    sys.path.insert(0, str(IDP))
    from legion.manifest import load_manifest, validate

    manifest = load_manifest(REGISTRY)
    assert validate(manifest) == [], (
        "the Chronos registry must pass the estate's one manifest validator"
    )
    assert manifest["name"] == "estate-clocks"


def test_every_obligation_states_its_tolerance_and_its_evidence():
    manifest = json.loads(REGISTRY.read_text(encoding="utf-8"))
    for ob in manifest["obligations"]:
        assert ob.get("workflow"), f"{ob.get('id')}: no workflow to measure"
        tol = ob.get("max_age_minutes")
        assert isinstance(tol, (int, float)) and tol > 0, (
            f"{ob['id']}: needs a positive tolerance"
        )
        assert ob.get("evidence"), (
            f"{ob['id']}: a verdict with no stated evidence is not actionable"
        )
        assert ob.get("state") in {"active", "retired"}, f"{ob['id']}: unknown state"


# --------------------------------------------------------------------------
# the falsifier itself
# --------------------------------------------------------------------------


def test_the_proof_command_passes_and_covers_the_refusal_cases():
    assert PROOF.exists(), "the detector ships with its falsifier"
    proc = subprocess.run([sys.executable, str(PROOF)], capture_output=True, text=True)
    assert proc.returncode == 0, f"chronos proof failed:\n{proc.stdout}\n{proc.stderr}"
    assert "PASS" in proc.stdout
    # The proof must exercise refusal, not just acceptance.
    assert "BLIND" in proc.stdout
    assert "MISSED_CYCLE" in proc.stdout
