"""2026-08-29 12:4xZ: the pre-push hook ran two sovereign tests alone and both were red on the
Mac, after idp#786 had fixed the same red for the repository root. `sovereign/pytest.ini` makes
`sovereign/` its own pytest root, so the root conftest never loaded. Pin: collecting only a
sovereign path still yields the hook-free git config."""

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_a_sovereign_only_run_gets_the_hook_free_git_config() -> None:
    probe = ROOT / "sovereign" / "tests" / "test_incident_r29_spec_gate.py"
    env = {k: v for k, v in os.environ.items() if k != "GIT_CONFIG_GLOBAL"}
    out = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "-p",
            "no:xdist",
            "-o",
            "addopts=",
            str(probe),
        ],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert out.returncode == 0, out.stdout[-2000:] + out.stderr[-500:]
