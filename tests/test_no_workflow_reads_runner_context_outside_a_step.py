"""A workflow that reads `runner.*` outside a step is invalid, and an invalid workflow never runs.

2026-11-20: incident-loop.yml set `ESTATE_HOME: ${{ runner.temp }}/estate` in its job-level env.
GitHub rejects the whole file for that, so the 15-minute schedule fired 0 times after landing
(b6168) and every push recorded a failed "workflow file issue" run. The runner context exists only
inside steps; this reads every workflow and refuses it anywhere else in a job.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
JOB_KEYS = (
    "env",
    "runs-on",
    "timeout-minutes",
    "concurrency",
    "outputs",
    "if",
    "name",
    "container",
    "services",
    "strategy",
    "environment",
)
RUNNER = re.compile(r"\$\{\{[^}]*\brunner\.")


def offenders() -> list[str]:
    out = []
    for path in sorted((ROOT / ".github" / "workflows").glob("*.y*ml")):
        flow = yaml.safe_load(path.read_text()) or {}
        for name, job in (flow.get("jobs") or {}).items():
            for key in JOB_KEYS:
                if key in job and RUNNER.search(json.dumps(job[key])):
                    out.append(f"{path.name}: job {name} reads runner.* in {key}")
    return out


def test_no_job_reads_the_runner_context_outside_a_step():
    assert offenders() == []


def test_the_check_refuses_the_shape_that_broke_the_incident_loop(
    tmp_path, monkeypatch
):
    wf = tmp_path / ".github" / "workflows"
    wf.mkdir(parents=True)
    (wf / "bad.yml").write_text(
        "on: {workflow_dispatch: {}}\njobs:\n  t:\n    runs-on: ubuntu-24.04\n"
        "    env:\n      HOME_DIR: ${{ runner.temp }}/x\n    steps:\n      - run: true\n"
    )
    monkeypatch.setattr(__import__(__name__), "ROOT", tmp_path)
    assert offenders() == ["bad.yml: job t reads runner.* in env"]
