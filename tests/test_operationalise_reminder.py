"""Yield capture must be prompted before merge ceremony gets a chance to hide it."""

from __future__ import annotations

import importlib.machinery
import importlib.util
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "bin/operationalise-reminder"


def _load():
    loader = importlib.machinery.SourceFileLoader(
        "operationalise_reminder", str(SCRIPT)
    )
    spec = importlib.util.spec_from_loader(loader.name, loader)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def test_a_low_risk_change_is_a_candidate_for_immediate_operationalisation():
    mod = _load()
    verdict = mod.assess(["bin/instruction", "tests/test_instruction_tracker.py"])
    assert verdict["risk"] == "low"
    assert "operationalise now" in verdict["next"]


def test_governance_router_and_deployment_paths_require_a_risk_assessment():
    mod = _load()
    for path in (
        "platform/estate/governance/laws.yaml",
        "platform/llm/pennyd/src/main.rs",
        "deploy/app.yaml",
    ):
        verdict = mod.assess([path])
        assert verdict["risk"] == "high", path
        assert "rollback" in verdict["next"].lower()


def test_each_required_stage_prints_the_same_operationalisation_obligation():
    for stage in ("commit", "pre-push", "push"):
        result = subprocess.run(
            ["python3", str(SCRIPT), "--stage", stage],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr
        assert "OPERATIONALISE NOW" in result.stdout
        assert "capture yield" in result.stdout


def test_an_unknown_stage_is_refused():
    result = subprocess.run(
        ["python3", str(SCRIPT), "--stage", "someday"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2


def test_commit_prepush_and_lane_submit_all_call_the_reminder():
    checks = (
        (ROOT / ".githooks/commit-msg", "--stage commit"),
        (ROOT / ".githooks/pre-push", "--stage pre-push"),
        (
            ROOT / "platform/estate/intents/lane-submit.yaml",
            "--stage push",
        ),
    )
    for path, expected in checks:
        assert "operationalise-reminder" in path.read_text(), path
        assert expected in path.read_text(), path
