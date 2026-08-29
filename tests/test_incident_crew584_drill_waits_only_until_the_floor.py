"""crew#584 CP-A (LAW 45): the portability drill waits only until the floor is met.

Incident 2026-08-29: both drill jobs ran `kubectl wait kustomization --all -A --timeout=600s`,
which always burned the full 600 s because OCI-only layers never come Ready off OCI. Measured
11 min on 9 of the last 10 runs. bin/idp-drill-wait polls the grader and exits at the floor.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WF = os.path.join(ROOT, ".github", "workflows", "portability-drill.yml")
WAIT = os.path.join(ROOT, "bin", "idp-drill-wait")


def test_no_job_sleeps_the_full_600s_on_kubectl_wait():
    text = open(WF, encoding="utf-8").read()
    assert not re.search(r"kubectl wait kustomization --all", text), "the fixed 600 s wait is back"
    assert text.count("run: bin/idp-drill-wait") == 2, "both hydrate and k3s must use the floor wait"


def test_wait_script_polls_the_grader_and_exits_at_the_floor():
    text = open(WAIT, encoding="utf-8").read()
    assert "bin/idp-portability-drill" in text
    assert 'DRILL_WAIT_MAX:-600' in text
    assert os.access(WAIT, os.X_OK)
    subprocess.run(["bash", "-n", WAIT], check=True)


def test_wait_script_returns_the_moment_the_floor_is_met(tmp_path):
    """A fake kubectl that reports two Ready layers (floor 2) must end the wait on the first poll."""
    fake = tmp_path / "kubectl"
    fake.write_text(
        "#!/usr/bin/env bash\n"
        'printf \'{"items":[%s,%s]}\' '
        "'{\"metadata\":{\"namespace\":\"a\",\"name\":\"x\"},\"status\":{\"conditions\":[{\"type\":\"Ready\",\"status\":\"True\"}]}}' "
        "'{\"metadata\":{\"namespace\":\"a\",\"name\":\"y\"},\"status\":{\"conditions\":[{\"type\":\"Ready\",\"status\":\"True\"}]}}'\n"
    )
    fake.chmod(0o755)
    env = dict(os.environ, PATH=f"{tmp_path}:{os.environ['PATH']}", DRILL_WAIT_STEP="1", DRILL_WAIT_MAX="5")
    out = subprocess.run([WAIT], env=env, capture_output=True, text=True, timeout=30)
    assert out.returncode == 0, out.stderr
    assert re.search(r"floor met after [0-2] s", out.stdout), out.stdout


def test_wait_script_gives_up_at_the_ceiling_without_failing_the_job(tmp_path):
    fake = tmp_path / "kubectl"
    fake.write_text("#!/usr/bin/env bash\nprintf '{\"items\":[]}'\n")
    fake.chmod(0o755)
    env = dict(os.environ, PATH=f"{tmp_path}:{os.environ['PATH']}", DRILL_WAIT_STEP="1", DRILL_WAIT_MAX="2")
    out = subprocess.run([WAIT], env=env, capture_output=True, text=True, timeout=30)
    assert out.returncode == 0
    assert "floor not met after 2 s" in out.stdout, out.stdout


if __name__ == "__main__":
    sys.exit(subprocess.call([sys.executable, "-m", "pytest", "-q", __file__]))
