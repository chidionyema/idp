"""Reject the job-level env context defect that prevented incident-loop from starting."""

import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
RUNNER = re.compile(r"\$\{\{[^}]*\brunner\s*(?:\.|\[)")


def offenders(root: Path) -> list[str]:
    result = []
    for path in sorted((root / ".github" / "workflows").glob("*.y*ml")):
        flow = yaml.safe_load(path.read_text()) or {}
        for name, job in (flow.get("jobs") or {}).items():
            if RUNNER.search(json.dumps(job.get("env", {}))):
                result.append(f"{path.name}: {name}: job env")
    return result


def test_no_workflow_reads_runner_in_job_env():
    assert offenders(ROOT) == []


def test_rejects_bad_context_but_allows_step_and_outputs(tmp_path):
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    (workflows / "bad.yml").write_text(
        """jobs:
  tick:
    env:
      ESTATE_HOME: ${{ runner.temp }}/estate
    steps:
      - run: echo ok
"""
    )
    (workflows / "good.yml").write_text(
        """jobs:
  tick:
    outputs:
      home: ${{ runner.temp }}
    steps:
      - env:
          HOME_PATH: ${{ runner.temp }}
        run: echo ok
"""
    )
    assert offenders(tmp_path) == ["bad.yml: tick: job env"]


def test_incident_loop_sets_home_before_ledger_steps():
    flow = yaml.safe_load((ROOT / ".github/workflows/incident-loop.yml").read_text())
    tick = flow["jobs"]["tick"]
    assert "ESTATE_HOME" not in tick.get("env", {})
    steps = tick["steps"]
    initializer = next(i for i, step in enumerate(steps) if
                       step.get("name") == "Name the ledger home")
    assert steps[initializer]["run"] == (
        'echo "ESTATE_HOME=$RUNNER_TEMP/estate" >> "$GITHUB_ENV"'
    )
    assert initializer < next(i for i, step in enumerate(steps) if
                              step.get("name") == "Restore the ledger from refs/incidents/state")
