"""New Zone B releases are bound to Greenlane main and fail closed before mutation."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/router-edge-release.yml"
SOURCE = ROOT / "platform/router-edge/scripts/release.mjs"
NEGATIVE = ROOT / "platform/router-edge/tests/release.falsifier.mjs"


def test_trusted_main_only_deployment_and_receipt():
    flow = yaml.safe_load(WORKFLOW.read_text())
    assert flow["permissions"] == {"contents": "read", "id-token": "write"}
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
    assert "delete childEnv.CLOUDFLARE_API_TOKEN;" in source
    assert "delete childEnv.CLOUDFLARE_ACCOUNT_ID;" in source


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



def _vault_binding_step():
    flow = yaml.safe_load(WORKFLOW.read_text())
    steps = flow["jobs"]["release"]["steps"]
    matched = [
        step
        for step in steps
        if "bin/idp-cloud secret get cloudflare-workers-token" in step.get("run", "")
    ]
    assert len(matched) == 1
    binding = matched[0]
    exchange = [
        step for step in steps if "oci-token-exchange-action@" in step.get("uses", "")
    ]
    assert len(exchange) == 1
    assert steps.index(exchange[0]) < steps.index(binding)
    assert binding["env"]["OCI_CLI_AUTH"] == "security_token"
    release = next(
        step for step in steps if "node scripts/release.mjs" in step.get("run", "")
    )
    assert "CLOUDFLARE_API_TOKEN" not in release["env"]
    assert "SEED_CLOUDFLARE_ROOT_TOKEN" not in WORKFLOW.read_text()
    assert "::add-mask::" in binding["run"]
    return binding["run"]


@pytest.mark.parametrize(
    "token,expected",
    [
        (None, False),
        ("not-a-valid-token", False),
        ("a" * 40, True),
    ],
)
def test_oidc_vault_release_binding_fails_closed_and_injects_only_valid_token(
    token, expected
):
    script = _vault_binding_step()
    with tempfile.TemporaryDirectory() as root:
        secret_dir = Path(root) / "secrets"
        secret_dir.mkdir()
        if token is not None:
            (secret_dir / "cloudflare-workers-token").write_text(token)
        output = Path(root) / "github_env"
        output.touch()
        env = {
            **os.environ,
            "IDP_CLOUD_BACKEND": "file",
            "IDP_CLOUD_FILE_ROOT": root,
            "GITHUB_ENV": str(output),
        }
        run = subprocess.run(
            ["bash", "-c", script],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            check=False,
            timeout=12,
        )
        assert (run.returncode == 0) == expected
        contents = output.read_text()
        if expected:
            assert contents == f"CLOUDFLARE_API_TOKEN={token}\n"
            assert f"::add-mask::{token}" in run.stdout
        else:
            assert not contents, "failed custody must not export a credential"
            assert token is None or token not in run.stdout + run.stderr
