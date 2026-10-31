"""The founder's void language raises an alarm; a clean report passes."""

import subprocess
import sys
from pathlib import Path

import pytest

EXE = str(Path(__file__).resolve().parents[1] / "bin" / "estate-fleet-monitor")


def check(text):
    return subprocess.run(
        [sys.executable, EXE, "check"],
        input=text,
        capture_output=True,
        text=True,
        timeout=30,
    )


@pytest.mark.parametrize(
    "bad",
    [
        "Delivery is not proven",
        "still open: 3",
        "Want me to continue?",
        "I can’t find it",
        "SHALL I proceed",
        "Next steps",
    ],
)
def test_void_language_alarms(bad):
    r = check(bad)
    assert r.returncode == 1 and "ALARM" in r.stdout


def test_clean_report_passes():
    r = check("claim #7503, proof cd06192b6 greenlane success, outcome landed in b4645")
    assert r.returncode == 0 and "ok" in r.stdout
