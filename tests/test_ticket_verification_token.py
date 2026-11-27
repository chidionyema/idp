"""Execute the real workflow shell against a noisy token producer, without credentials."""

import json
import os
from pathlib import Path
import subprocess

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
TOKEN = "ghs_fixture_only_123"


def execute(tmp_path, token=TOKEN, diagnostic="OIDC allowed", mint_exit=0):
    flow = yaml.safe_load(
        (ROOT / ".github/workflows/ticket-verification.yml").read_text()
    )
    step = next(s for s in flow["jobs"]["verify"]["steps"] if s.get("id") == "verify")
    script = (
        step["run"]
        .replace("${{ github.event_name }}", "schedule")
        .replace("${{ inputs.apply }}", "true")
    )
    bindir = tmp_path / "bin"
    bindir.mkdir()
    mint = bindir / "idp-github-app"
    mint.write_text(
        '#!/bin/sh\nprintf "%s" "$FIXTURE_TOKEN"\nprintf "%s\\n" "$FIXTURE_DIAGNOSTIC" >&2\nexit "$FIXTURE_MINT_EXIT"\n'
    )
    mint.chmod(0o755)
    verifier = bindir / "idp-ticket-verify"
    verifier.write_text(
        '#!/bin/sh\nprintf "%s" "$GH_TOKEN" > captured-token\necho VERIFIED\n'
    )
    verifier.chmod(0o755)
    env = dict(
        os.environ,
        FIXTURE_TOKEN=token,
        FIXTURE_DIAGNOSTIC=diagnostic,
        FIXTURE_MINT_EXIT=str(mint_exit),
        GITHUB_OUTPUT=str(tmp_path / "output"),
        GITHUB_STEP_SUMMARY=str(tmp_path / "summary"),
    )
    result = subprocess.run(
        ["bash", "-e", "-c", script],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    return result, tmp_path / "captured-token", tmp_path / "output"


def test_diagnostics_cannot_become_authorization_header(tmp_path):
    result, captured, output = execute(tmp_path)
    assert result.returncode == 0, result.stderr
    assert captured.read_text() == TOKEN
    assert output.read_text() == f"tok={TOKEN}\n"


@pytest.mark.parametrize(
    "token", ["", "not-a-token", TOKEN + "\n" + TOKEN, TOKEN + "\r", " " + TOKEN]
)
def test_malformed_token_never_reaches_verifier_or_output(tmp_path, token):
    result, captured, output = execute(tmp_path, token=token, diagnostic="")
    assert result.returncode == 2
    assert not captured.exists()
    assert not output.exists() or not output.read_text()
    assert token.strip() not in result.stdout or not token.strip()


def test_failed_mint_does_not_echo_partial_credential(tmp_path):
    result, captured, output = execute(
        tmp_path, token=TOKEN, diagnostic="mint failed", mint_exit=1
    )
    assert result.returncode == 2
    assert not captured.exists()
    assert TOKEN not in result.stdout + result.stderr
    assert not output.exists() or not output.read_text()
