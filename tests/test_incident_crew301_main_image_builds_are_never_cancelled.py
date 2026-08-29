"""On 2026-08-29 08:19Z the merge of idp#750 cancelled the backstage image build of idp#747 (run
33242788019, both build jobs 'cancelled' at 08:19:05Z), because build-multiarch.yml cancelled the
in-progress run of the same workflow, event and ref. The next push to main built only what changed
since its own parent, so no backstage image was ever built for #747, #751, #758 or #760: ghcr's newest
backstage tag stayed main-2246 (built 07:34Z) and login-drill run 33245839791 read the vendor manifest
from the cluster while main carried the branded one (crew#301, crew#459). A push to main gets a group
per sha and is never cancelled; pull-request runs still supersede their older run (crew#516)."""
import os

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
WF = os.path.join(os.path.dirname(HERE), ".github", "workflows", "build-multiarch.yml")


def concurrency(text):
    return (yaml.safe_load(text) or {}).get("concurrency") or {}


def main_pushes_are_never_cancelled(text):
    c = concurrency(text)
    cancel = str(c.get("cancel-in-progress", ""))
    group = str(c.get("group", ""))
    if cancel.strip() in ("True", "true"):
        return False
    if "github.event_name == 'pull_request'" not in cancel:
        return False
    return "github.event_name == 'push' && github.sha" in group and "github.workflow" in group


def test_incident_run_33242788019_a_push_to_main_is_never_cancelled_by_the_next_merge():
    assert main_pushes_are_never_cancelled(open(WF).read())


def test_the_old_shape_that_cancelled_the_backstage_build_is_refused():
    old = ("concurrency:\n  group: ${{ github.workflow }}-${{ github.event_name }}-${{ github.ref }}\n"
           "  cancel-in-progress: true\njobs: {}\n")
    assert not main_pushes_are_never_cancelled(old)


def test_a_workflow_that_never_cancels_anything_is_refused_too():
    never = ("concurrency:\n  group: ${{ github.workflow }}-${{ github.sha }}\n"
             "  cancel-in-progress: false\njobs: {}\n")
    assert not main_pushes_are_never_cancelled(never)


def test_pull_request_pushes_still_supersede_their_older_run():
    c = concurrency(open(WF).read())
    assert "github.event_name == 'pull_request'" in str(c["cancel-in-progress"])
    assert "github.ref" in str(c["group"])
