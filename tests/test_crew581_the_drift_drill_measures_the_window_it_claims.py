"""crew#581 CP6: the drift drill's arithmetic, and the row that keeps it scheduled.

The drill itself needs a live cluster, so what is graded here is everything that can be wrong
without one: the duration parsing that decides how long the drill waits, the target discovery that
decides what it mutates, and the agreement between the catalogue row and the workflow's own cron.
A drill whose ceiling is computed wrong either passes without waiting or hangs the job, and neither
failure is visible from the receipt it prints.
"""

import importlib.machinery
import importlib.util
import pathlib

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
DRILL_PATH = ROOT / "bin" / "idp-drift-drill"
WORKFLOW = ROOT / ".github" / "workflows" / "drift-drill.yml"
CATALOGUE = ROOT / "drills" / "catalogue.yaml"

_loader = importlib.machinery.SourceFileLoader("idp_drift_drill", str(DRILL_PATH))
_spec = importlib.util.spec_from_loader("idp_drift_drill", _loader)
drill = importlib.util.module_from_spec(_spec)
_loader.exec_module(drill)


def _row():
    rows = yaml.safe_load(CATALOGUE.read_text())["drills"]
    matching = [r for r in rows if r["workflow"] == WORKFLOW.name]
    assert len(matching) == 1, f"expected one catalogue row for {WORKFLOW.name}, got {len(matching)}"
    return matching[0]


@pytest.mark.parametrize(
    "raw,seconds",
    [
        ("10m", 600),      # what 36 of this tree's Kustomizations declare
        ("10m0s", 600),    # and what the 37th declares, spelled differently
        ("1h", 3600),
        ("1h30m", 5400),
        ("45s", 45),
        ("0s", 0),
    ],
)
def test_a_flux_duration_becomes_the_seconds_the_drill_will_wait(raw, seconds):
    assert drill.interval_seconds(raw) == seconds


def test_the_ceiling_is_the_slowest_reconcile_not_the_first_one_seen():
    # The drill must wait out the worst case. Taking the first, or the fastest, would let it
    # declare a revert failed while the slowest Kustomization had not yet run once.
    items = [{"spec": {"interval": "10m"}}, {"spec": {"interval": "1h"}}, {"spec": {"interval": "5m"}}]
    assert drill.longest_interval(items) == 3600
    assert drill.longest_interval([]) == 0


def test_a_target_must_be_a_configmap_flux_applied_that_holds_data():
    applied = {
        "metadata": {"name": "cm", "namespace": "ns", "labels": {drill.FLUX_NAME_LABEL: "k"}},
        "data": {"b": "2", "a": "1"},
    }
    # sorted() so the same key is chosen on every run; a drill that picks a different field each
    # time produces numbers that cannot be compared across runs
    assert drill.pick_from([applied]) == ("ns", "cm", "a", "1")


@pytest.mark.parametrize(
    "candidate",
    [
        # not applied by Flux: mutating it would measure nothing and never revert
        {"metadata": {"name": "cm", "namespace": "ns", "labels": {}}, "data": {"a": "1"}},
        # applied by Flux but declares no data: there is no field Flux owns to hand-edit
        {"metadata": {"name": "cm", "namespace": "ns", "labels": {drill.FLUX_NAME_LABEL: "k"}}, "data": {}},
    ],
)
def test_a_resource_the_drill_cannot_learn_anything_from_is_refused(candidate):
    assert drill.pick_from([candidate]) is None


def test_the_catalogue_row_declares_the_cron_the_workflow_actually_runs():
    # The catalogue's own contract: `schedule` is copied verbatim from the workflow, so a drill
    # that is quietly unscheduled shows up as a diff rather than as a row that keeps saying ok.
    workflow = yaml.safe_load(WORKFLOW.read_text())
    triggers = workflow[True] if True in workflow else workflow["on"]
    assert _row()["schedule"] == triggers["schedule"][0]["cron"]


def test_the_row_is_not_marked_pending_because_the_job_ships_with_it():
    assert "pending" not in _row(), "the workflow is in this same commit; a pending row would never FAIL"


def _deployment(labelled=True, containers=("api",)):
    return {
        "metadata": {
            "name": "d", "namespace": "ns",
            "labels": {drill.FLUX_NAME_LABEL: "k"} if labelled else {},
        },
        "spec": {"template": {"spec": {"containers": [{"name": c} for c in containers]}}},
    }


def test_the_sidecar_case_targets_a_deployment_flux_actually_applied():
    # The undeclared-container measurement is the one the architecture is really claiming to
    # prevent, so it must run against a Deployment Flux owns. Injecting into one Flux never
    # applied would show a container surviving for a reason that has nothing to do with GitOps.
    assert drill.pick_deployment([_deployment()]) == ("ns", "d", ["api"])
    assert drill.pick_deployment([_deployment(labelled=False)]) is None
    assert drill.pick_deployment([_deployment(containers=())]) is None
    assert drill.pick_deployment([]) is None


def test_the_injected_container_name_cannot_collide_with_a_real_one():
    # The drill decides "was it pruned" by name. A name a chart might also use would make a
    # surviving sidecar look pruned, which is the one direction this drill must never fail in.
    assert drill.SIDECAR not in {"api", "app", "web", "sidecar", "istio-proxy", "linkerd-proxy"}
    assert drill.SIDECAR.startswith("drift-drill-")
