"""idp#7354: the otto-parity tick must CONCLUDE, never be cancelled.

Measured before this file existed: the workflow's job timeout was 15 minutes and the playbook
needs longer than that against a dark cluster, so GitHub cancelled the job and the tick's
conclusion was `cancelled` -- it measured nothing. Runs #40715893797 through #40792186310 all
concluded `cancelled`.

These tests pin the three things that make the tick conclude:

  1. the job's timeout is LONGER than the wall clock the playbook is given, so the inner
     `timeout` fires first and the run ends with a conclusion and a log
  2. the playbook asks the cluster once, and when the cluster does not answer it says BLIND and
     exits non-zero -- it does not hang, and it does not claim the rows proved anything
  3. the kubectl request timeout is the caller's to set, and the workflow sets it

Nothing here needs the estate: the kubectl on PATH is a stub that fails like a dark cluster.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
WORKFLOW = REPO / ".github" / "workflows" / "otto-parity.yml"
PLAYBOOK = REPO / "bin" / "idp-oke-break-glass"

try:  # pyyaml is a CI dependency (ci.yml installs it); the fallback keeps this file runnable
    import yaml  # type: ignore
except ImportError:  # pragma: no cover - only when pyyaml is missing
    yaml = None  # type: ignore


def _workflow() -> dict:
    if yaml is None:
        raise AssertionError("pyyaml is required to read the workflow")
    return yaml.safe_load(WORKFLOW.read_text())


def _stub_kubectl(tmp_path: Path, rc: int = 1) -> Path:
    """A kubectl that behaves like a cluster that is not there."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    stub = bin_dir / "kubectl"
    stub.write_text(
        "#!/bin/sh\n"
        # the stub records how it was called, so the request timeout can be asserted
        'printf "%s\\n" "$*" >> "$STUB_KUBECTL_LOG"\n'
        "echo 'The connection to the server localhost:8080 was refused - did you specify the right host or port?' >&2\n"
        f"exit {rc}\n"
    )
    stub.chmod(0o755)
    return bin_dir


def test_the_job_timeout_outlives_the_wall_clock_the_playbook_is_given():
    workflow = _workflow()
    job = workflow["jobs"]["parity"]
    env = job["env"]
    wall_clock = int(str(env["PARITY_WALL_CLOCK_S"]))
    job_timeout_s = int(job["timeout-minutes"]) * 60
    # the inner `timeout` kills the playbook and lets the step fail with a conclusion; the
    # job timeout must be longer than that kill, or GitHub cancels and the tick says nothing
    assert job_timeout_s > wall_clock + 30, (
        f"job timeout {job_timeout_s}s must outlive the playbook wall clock {wall_clock}s "
        "plus the kill grace, or the tick is cancelled instead of concluded"
    )
    # and the playbook's own budget is shorter than the wall clock, so it normally concludes
    # by itself before the backstop fires
    assert int(str(env["PARITY_BUDGET_S"])) < wall_clock


def test_the_playbook_concludes_blind_against_a_cluster_that_does_not_answer(tmp_path):
    bin_dir = _stub_kubectl(tmp_path)
    env = dict(os.environ)
    env["PATH"] = f"{bin_dir}{os.pathsep}{env.get('PATH', '')}"
    env["KUBECTL_REQUEST_TIMEOUT"] = "20s"
    env["PARITY_BUDGET_S"] = "600"
    log = tmp_path / "kubectl.log"
    env["STUB_KUBECTL_LOG"] = str(log)

    proc = subprocess.run(
        [str(PLAYBOOK), "otto-parity"],
        capture_output=True,
        text=True,
        env=env,
        timeout=90,
    )
    out = proc.stdout + proc.stderr
    assert "cluster-unreachable" in out, out
    assert "BLIND" in out, out
    # BLIND is never green: the tick is red, and it says it measured nothing
    assert proc.returncode == 1, (proc.returncode, out)
    # and the request timeout the workflow sets is the one kubectl was called with
    assert log.exists() and log.read_text().strip(), "the playbook never called kubectl"
    assert "--request-timeout=20s" in log.read_text(), log.read_text()


def test_the_playbook_is_still_a_playbook_the_dispatch_table_advertises():
    # the estate's own self-test already proves every advertised playbook has a pb_ function
    # ("--list advertises X with no pb_ function"); this only proves the name is still there.
    listing = subprocess.run(
        [str(PLAYBOOK), "--list"], capture_output=True, text=True, timeout=60
    )
    assert listing.returncode == 0, listing
    assert "otto-parity" in listing.stdout.split()


if __name__ == "__main__":  # pragma: no cover
    sys.exit(subprocess.call([sys.executable, "-m", "pytest", __file__]))
