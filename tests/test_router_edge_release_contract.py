"""New Zone B releases are bound to Greenlane main and fail closed before mutation."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/router-edge-release.yml"
SOURCE = ROOT / "platform/router-edge/scripts/release.mjs"
NEGATIVE = ROOT / "platform/router-edge/tests/release.falsifier.mjs"


def test_trusted_main_only_deployment_and_receipt():
    flow = yaml.safe_load(WORKFLOW.read_text())
    assert flow["permissions"] == {"contents": "read"}
    assert flow["concurrency"]["cancel-in-progress"] is False
    assert flow["jobs"]["release"]["if"] == "github.ref == 'refs/heads/main'"
    steps = flow["jobs"]["release"]["steps"]
    assert any("npm test" in step.get("run", "") for step in steps)
    assert any(
        "node --test tests/release.falsifier.mjs" in step.get("run", "")
        for step in steps
    )
    assert any("node scripts/release.mjs" in step.get("run", "") for step in steps)
    assert any(step.get("if") == "always()" for step in steps)
    assert "npm ci" not in WORKFLOW.read_text()


def test_no_unverified_initial_deploy_or_silent_gate_removal():
    source = SOURCE.read_text()
    for needle in (
        "requireMainSha(",
        "activeRollbackId(",
        "immutableTag(",
        '"versions", "upload"',
        '"versions", "deploy"',
        '"rollback",',
        "--strict",
        "--keep-vars",
        "EXPECTED_COMMIT_SHA: sha",
        "rollback_verified = true",
    ):
        assert needle in source, needle
    assert 'run(wrangler, ["deploy"' not in source
    assert 'run("npm", ["test"])' not in source
    assert 'run("node", ["--test"' not in source
    assert "RELEASE_PREFLIGHT_FILE" in source


def test_three_negative_release_tests_execute_without_credentials():
    node = shutil.which("node")
    if node is None:
        pytest.skip("node absent in local environment")
    result = subprocess.run(
        [node, "--test", str(NEGATIVE)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "# tests 3" in result.stdout
