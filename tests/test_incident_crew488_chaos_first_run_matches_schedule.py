"""crew#483 residual: the chaos drill graded FAIL for five days because a Schedule's first tick is
the next cron match, never the day it is applied. A one-shot Workflow runs the same experiment on
apply. Rung 4: the Workflow's spec must equal the Schedule's spec.workflow, so the receipt the
first run leaves proves the same thing the weekly one does. Both ways: the live pair is equal, and
a mutated copy is caught.
"""
from __future__ import annotations

import copy
import pathlib

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1] / "platform" / "chaos"


def _pair():
    schedule = yaml.safe_load((ROOT / "backstage-pod-kill.yaml").read_text())
    workflow = yaml.safe_load((ROOT / "backstage-pod-kill-first-run.yaml").read_text())
    return schedule, workflow


def _same(schedule, workflow) -> bool:
    return (
        workflow["kind"] == "Workflow"
        and workflow["metadata"]["namespace"] == schedule["metadata"]["namespace"]
        and workflow["spec"] == schedule["spec"]["workflow"]
    )


def test_first_run_equals_schedule_both_ways():
    schedule, workflow = _pair()
    assert _same(schedule, workflow)
    drifted = copy.deepcopy(workflow)
    drifted["spec"]["templates"][0]["deadline"] = "1s"
    assert not _same(schedule, drifted)
    kust = yaml.safe_load((ROOT / "kustomization.yaml").read_text())
    assert "backstage-pod-kill-first-run.yaml" in kust["resources"]
