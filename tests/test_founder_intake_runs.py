"""The founder's instruction store must be runnable: it sat at mode 644 and failed 'Permission denied'."""

import os
import subprocess
from pathlib import Path

BIN = Path(__file__).resolve().parents[1] / "bin" / "estate-founder-intake"


def test_intake_is_executable_and_classifies():
    assert os.access(BIN, os.X_OK), "bin/estate-founder-intake is not executable"
    r = subprocess.run(
        [
            str(BIN),
            "--json",
            "--no-publish",
            "--text",
            "Never repeat yourself. Close the loop.",
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert r.returncode == 0, r.stderr
    assert '"fingerprint"' in r.stdout and '"sentences"' in r.stdout
