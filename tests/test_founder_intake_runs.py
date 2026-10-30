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


def test_repeat_hit_is_reported_not_crashed(tmp_path):
    """Regression: the CLI read 'similarity'/'text' while find_repeat returns 'score'/'earlier'; any real hit crashed."""
    env = {**os.environ, "ESTATE_HOME": str(tmp_path), "HOME": str(tmp_path)}
    text = "Never repeat yourself and close the loop on every instruction."
    subprocess.run(
        [str(BIN), "--no-publish", "--text", text],
        env=env,
        capture_output=True,
        timeout=60,
    )
    r = subprocess.run(
        [str(BIN), "--repeat", text],
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert "Traceback" not in r.stderr, r.stderr
    assert r.returncode == 2 and r.stdout.startswith("REPEAT")
