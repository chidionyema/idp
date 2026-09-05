"""On 2026-08-27 20:23Z idp had 9 running and 20 queued Actions runs; 12 were older runs of the same
workflow on the same ref (the flux/image-updates branch spawns four per push, every ten minutes), and a
one-line oke-check dispatch waited 19 minutes for a runner (crew#516). Every per-ref workflow declares a
concurrency group keyed on workflow, event and ref with cancel-in-progress, so a newer push supersedes
the older run instead of queueing behind it."""
import os
import re

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
WORKFLOWS = os.path.join(os.path.dirname(HERE), ".github", "workflows")
PER_REF = ("ci.yml", "build-multiarch.yml", "image-update-pr.yml")


def supersedes_on_the_same_ref(text):
    d = yaml.safe_load(text) or {}
    c = d.get("concurrency")
    if not isinstance(c, dict) or c.get("cancel-in-progress") is not True:
        return False
    g = str(c.get("group", ""))
    return "github.ref" in g and "github.workflow" in g and "github.event_name" in g


def test_every_per_ref_workflow_supersedes_its_older_run():
    for w in PER_REF:
        assert supersedes_on_the_same_ref(open(os.path.join(WORKFLOWS, w)).read()), w


def test_a_workflow_without_a_group_or_without_cancel_is_refused():
    assert not supersedes_on_the_same_ref("on: push\njobs: {}\n")
    assert not supersedes_on_the_same_ref("concurrency:\n  group: x-${{ github.ref }}\n  cancel-in-progress: false\njobs: {}\n")


def test_the_group_is_per_event_so_a_pull_request_run_never_cancels_the_push_run():
    assert not supersedes_on_the_same_ref(
        "concurrency:\n  group: ${{ github.workflow }}-${{ github.ref }}\n  cancel-in-progress: true\njobs: {}\n")
