"""crew#85, 2026-08-27: 39 schedule.yml jobs were also loaded launchd agents and ran from both.
Rule: the overlap between schedule.yml and loaded launchd labels is empty. Pure set rule both
ways, plus the live check on a Mac that has launchctl (skipped in CI). Rung 4."""
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "bin/idp-launchd-retire"


def test_overlap_is_the_intersection_and_nothing_else():
    ns = {}
    exec(compile(TOOL.read_text(), str(TOOL), "exec"), {"__name__": "lib", "__file__": str(TOOL)}, ns)
    assert ns["overlap"]({"a", "b"}, {"b", "c"}) == ["b"]
    assert ns["overlap"]({"a"}, {"c"}) == []


@pytest.mark.skipif(shutil.which("launchctl") is None, reason="no launchd here (CI)")
def test_no_schedule_yml_job_is_still_a_loaded_launchd_agent():
    r = subprocess.run([sys.executable, str(TOOL)], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout
