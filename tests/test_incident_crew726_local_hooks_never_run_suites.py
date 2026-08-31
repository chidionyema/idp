"""crew#726 D1 / R58 fast-gates (founder 2026-08-31, verbatim record in the founder docs at
2026-08-31T0225Z): a laptop never runs a test suite in a git hook. On 2026-08-30/31 four
sessions each ran the pre-push suite (13-52 minutes) at once; load hit 530 and pushes were
refused on subprocess.TimeoutExpired reds with zero real failures - the gate graded the
machine's load, not the branch. This pins the selector's three roads: outside CI the run is
skipped right after the selection prints; in CI the suite runs unchanged; TESTS_FOR_RUN=1
keeps the hand-debug road. The runner is stubbed through IDP_PY so the proof costs
milliseconds, never a suite.
"""

import os
import stat
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "bin" / "idp-tests-for"


def _run(tmp_path, **env_over):
    marker = tmp_path / "py-ran"
    stub = tmp_path / "stub-python"
    stub.write_text(f"#!/bin/sh\necho ran >> {marker}\nexit 0\n")
    stub.chmod(stub.stat().st_mode | stat.S_IEXEC)
    env = {k: v for k, v in os.environ.items() if k not in ("CI", "TESTS_FOR_RUN")}
    env["IDP_PY"] = str(stub)
    env.update(env_over)
    p = subprocess.run(
        [str(TOOL), "--for", "bin/idp-tests-for"],
        capture_output=True,
        text=True,
        env=env,
        timeout=120,
        cwd=ROOT,
    )
    return p, marker.exists()


def test_local_push_skips_the_suite_and_defers_to_ci(tmp_path):
    p, ran = _run(tmp_path)
    assert p.returncode == 0, p.stdout + p.stderr
    assert "local run skipped (R58 fast-gates)" in p.stdout
    assert "test file(s) read the changed files" in p.stdout, (
        "the selection record must still print"
    )
    assert not ran, "the suite ran on the laptop path (R58)"


def test_ci_runs_the_suite_unchanged(tmp_path):
    p, ran = _run(tmp_path, CI="true")
    assert "local run skipped" not in p.stdout
    assert ran, "the CI path never reached the test runner: " + p.stdout + p.stderr


def test_hand_debug_road_still_runs_locally(tmp_path):
    p, ran = _run(tmp_path, TESTS_FOR_RUN="1")
    assert "local run skipped" not in p.stdout
    assert ran, "TESTS_FOR_RUN=1 must keep the old local run: " + p.stdout + p.stderr
