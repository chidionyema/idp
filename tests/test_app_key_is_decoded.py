"""No workflow hands the base64 App key to create-github-app-token as if it were the PEM.

SEED_GITHUB_APP_PEM_B64 is base64 of the PEM (bin/idp-github-app). feature-request-enable.yml
passed it straight to `private-key:`, which fails on the first run; nothing caught it because the
workflow had never run (crew#975 CP28). This reads every workflow, and runs the decode step.
"""

from __future__ import annotations

import base64
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = sorted((ROOT / ".github/workflows").glob("*.yml"))


def _steps(path: Path):
    for job in (yaml.safe_load(path.read_text()).get("jobs") or {}).values():
        yield from job.get("steps") or []


@pytest.mark.parametrize("path", WORKFLOWS, ids=lambda p: p.name)
def test_no_base64_secret_is_passed_as_a_private_key(path):
    for s in _steps(path):
        key = str((s.get("with") or {}).get("private-key", ""))
        assert "_B64" not in key, (
            f"{path.name}: private-key is the base64 secret, not the PEM"
        )


def test_the_decode_step_hands_on_the_pem_itself(tmp_path):
    wf = ROOT / ".github/workflows/feature-request-enable.yml"
    (step,) = [s for s in _steps(wf) if s.get("id") == "pem"]
    pem = "-----BEGIN RSA PRIVATE KEY-----\nMIIEfake\nline2\n-----END RSA PRIVATE KEY-----"
    out = tmp_path / "out"
    p = subprocess.run(
        ["bash", "-e", "-c", step["run"]],
        env={
            "PATH": "/usr/bin:/bin",
            "PEM_B64": base64.b64encode(pem.encode()).decode(),
            "GITHUB_OUTPUT": str(out),
        },
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert p.returncode == 0, p.stderr
    body = out.read_text().split("key<<PEM_EOF\n", 1)[1].split("\nPEM_EOF", 1)[0]
    assert body == pem
    assert "::add-mask::MIIEfake" in p.stdout
