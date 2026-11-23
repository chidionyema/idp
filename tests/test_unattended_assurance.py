"""Offline negatives and positive controls for the bounded assurance observer."""

import importlib.machinery
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

TOOL = Path(__file__).resolve().parents[1] / "bin" / "idp-unattended-assurance"
loader = importlib.machinery.SourceFileLoader("assurance_watch", str(TOOL))
spec = importlib.util.spec_from_loader(loader.name, loader)
mod = importlib.util.module_from_spec(spec)
loader.exec_module(mod)
NOW = "2026-11-22T12:00:00+00:00"
SHA_A = "a" * 40
SHA_B = "b" * 40


def event(number, sha, state="completed", outcome="failure", name="ci"):
    return {
        "id": number,
        "workflow_id": 20,
        "name": name,
        "head_branch": "main",
        "head_sha": sha,
        "status": state,
        "conclusion": outcome,
        "html_url": f"https://github.com/chidionyema/idp/actions/runs/{number}",
    }


def registry():
    return {
        "functions": [
            {"id": "router", "severity": "critical"},
            {"id": "db", "severity": "important", "failure_modes": ["disk-full"]},
        ]
    }


def test_two_independent_failed_shas_are_only_suspected_recurrence():
    r = mod.analyse(
        [event(1, SHA_A), event(2, SHA_B)], registry(), "chidionyema/idp", NOW
    )
    assert r["suspected_recurrences"][0]["distinct_failed_shas"] == 2
    assert (
        r["suspected_recurrences"][0]["epistemic_state"]
        == "RECURRING_FAILURE_OUTCOME_NOT_CAUSAL_CLASS"
    )
    assert r["independent_operational_effect"] == "UNKNOWN"
    assert r["coverage"]["critical_function_denominator"] == 2
    assert r["next_falsifiable_target"] == "router"


def test_retries_on_same_sha_do_not_claim_independent_recurrence():
    r = mod.analyse(
        [event(1, SHA_A), event(2, SHA_A)], registry(), "chidionyema/idp", NOW
    )
    assert r["suspected_recurrences"] == []


def test_cancelled_successful_and_ongoing_do_not_count_as_failures():
    cases = [
        event(1, SHA_A, outcome="success"),
        event(2, SHA_B, outcome="cancelled"),
        event(3, SHA_A, state="in_progress", outcome=None),
    ]
    r = mod.analyse(cases, registry(), "chidionyema/idp", NOW)
    assert r["coverage"]["failed_runs"] == 0
    assert r["coverage"]["nonterminal_runs"] == 1


def test_empty_sample_is_blind():
    with pytest.raises(ValueError, match="no usable"):
        mod.analyse([], registry(), "chidionyema/idp", NOW)


def test_unavailable_function_registry_is_blind():
    with pytest.raises(ValueError, match="registry"):
        mod.analyse([event(1, SHA_A)], {}, "chidionyema/idp", NOW)


def test_malformed_function_is_not_silently_skipped():
    with pytest.raises(ValueError, match="malformed"):
        mod.analyse([event(1, SHA_A)], {"functions": [{}]}, "chidionyema/idp", NOW)


def test_over_budget_sample_refuses_unbounded_scan():
    with pytest.raises(ValueError, match="bounded"):
        mod.analyse(
            [event(i, SHA_A) for i in range(101)], registry(), "chidionyema/idp", NOW
        )


def test_offline_cli_is_deterministic_and_explicit_about_effect(tmp_path):
    (tmp_path / "registry.json").write_text(json.dumps(registry()))
    (tmp_path / "runs.json").write_text(
        json.dumps([event(1, SHA_A), event(2, SHA_B)])
    )
    cmd = [
        sys.executable,
        str(TOOL),
        "--registry",
        str(tmp_path / "registry.json"),
        "--runs-json",
        str(tmp_path / "runs.json"),
        "--now",
        NOW,
        "--json",
    ]
    a = subprocess.run(cmd, capture_output=True, text=True)
    b = subprocess.run(cmd, capture_output=True, text=True)
    assert a.returncode == b.returncode == 0
    assert a.stdout == b.stdout
    assert json.loads(a.stdout)["paid_inference_calls"] == 0


def test_offline_blind_exit_is_two(tmp_path):
    (tmp_path / "registry.json").write_text(json.dumps(registry()))
    (tmp_path / "runs.json").write_text("[]")
    p = subprocess.run(
        [
            sys.executable,
            str(TOOL),
            "--registry",
            str(tmp_path / "registry.json"),
            "--runs-json",
            str(tmp_path / "runs.json"),
            "--json",
        ],
        capture_output=True,
        text=True,
    )
    assert p.returncode == 2
    assert json.loads(p.stdout)["state"] == "BLIND"
