"""The GitOps synchronization engine, graded where it runs.

Spec: docs/specs/2026-09-13-gitops-sync-engine.md

Every scenario here is offline and deterministic. The live read -- the cluster's
own Flux objects -- is `scheduler/estate_scheduler/gitops_sync.drift_payload`,
graded against recorded status rather than a cluster, because a test that needs
the estate up is a test that is skipped exactly when the estate is down.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


SPEC = importlib.util.spec_from_file_location(
    "gitops_sync",
    Path(__file__).resolve().parents[3]
    / "scheduler"
    / "estate_scheduler"
    / "gitops_sync.py",
)
assert SPEC and SPEC.loader, "the module under test must load by path"
sync = importlib.util.module_from_spec(SPEC)
sys.modules["gitops_sync"] = sync
SPEC.loader.exec_module(sync)


# --- a Kustomization Flux is not happy with ---------------------------------


def kustomization(
    name: str,
    *,
    namespace: str = "flux-system",
    ready: str = "False",
    reason: str = "ReconciliationFailed",
    message: str = "kustomize build failed",
) -> dict:
    return {
        "apiVersion": "kustomize.toolkit.fluxcd.io/v1",
        "kind": "Kustomization",
        "metadata": {"name": name, "namespace": namespace},
        "status": {
            "conditions": [
                {"type": "Ready", "status": ready, "reason": reason, "message": message}
            ]
        },
    }


def helmrelease(
    name: str,
    *,
    namespace: str = "observability",
    ready: str = "False",
    reason: str = "InstallFailed",
    message: str = "Helm install failed",
) -> dict:
    return {
        "apiVersion": "helm.toolkit.fluxcd.io/v2",
        "kind": "HelmRelease",
        "metadata": {"name": name, "namespace": namespace},
        "status": {
            "conditions": [
                {"type": "Ready", "status": ready, "reason": reason, "message": message}
            ]
        },
    }


def test_a_ready_object_is_not_a_drift() -> None:
    """The sensor must be silent about an estate that is fine.

    A watcher that reports healthy objects is a watcher nobody reads, which is
    LAW 28 and the reason the estate has fourteen unwatched dashboards.
    """
    objects = [
        kustomization("observability", ready="True", reason="ReconciliationSucceeded"),
        helmrelease("langfuse", ready="True", reason="InstallSucceeded"),
    ]
    assert sync.drifts_from(objects) == []


def test_a_kustomization_that_is_not_ready_is_a_drift_naming_its_reason() -> None:
    objects = [
        kustomization("temporal", message="timeout waiting for: HelmRelease/temporal")
    ]
    got = sync.drifts_from(objects)
    assert len(got) == 1
    assert got[0]["object"] == "flux-system/temporal"
    assert got[0]["kind"] == "Kustomization"
    assert "timeout waiting for" in got[0]["reason"]


def test_a_helmrelease_that_is_not_ready_is_a_drift() -> None:
    got = sync.drifts_from([helmrelease("langfuse")])
    assert len(got) == 1
    assert got[0]["object"] == "observability/langfuse"
    assert got[0]["kind"] == "HelmRelease"


def test_an_object_with_no_ready_condition_at_all_is_not_a_drift() -> None:
    """A brand new object has not reported yet, and that is not a defect.

    Reading 'no condition' as 'broken' is how a watcher pages on every apply.
    """
    fresh = {
        "kind": "Kustomization",
        "metadata": {"name": "new", "namespace": "flux-system"},
        "status": {},
    }
    assert sync.drifts_from([fresh]) == []


# --- one id for one drift ---------------------------------------------------


def test_the_same_drift_has_the_same_fingerprint_however_long_it_burns() -> None:
    """Nothing about when is in the id.

    This is `alert_fingerprint`'s rule, and it is what stops one broken object
    being reported every poll for a day.
    """
    a = sync.drifts_from([kustomization("temporal", message="timeout")])[0]
    b = sync.drifts_from([kustomization("temporal", message="timeout")])[0]
    assert sync.drift_fingerprint(a) == sync.drift_fingerprint(b)


def test_a_new_reason_is_a_new_drift() -> None:
    a = sync.drifts_from([kustomization("temporal", message="timeout")])[0]
    b = sync.drifts_from([kustomization("temporal", message="build failed")])[0]
    assert sync.drift_fingerprint(a) != sync.drift_fingerprint(b)


def test_two_objects_failing_identically_are_two_drifts() -> None:
    a = sync.drifts_from([kustomization("a", message="boom")])[0]
    b = sync.drifts_from([kustomization("b", message="boom")])[0]
    assert sync.drift_fingerprint(a) != sync.drift_fingerprint(b)


# --- attribution before repair ----------------------------------------------


def test_a_drift_is_attributed_to_the_pull_request_that_last_touched_its_file() -> None:
    drift = sync.drifts_from([helmrelease("langfuse")])[0]
    history = {
        "platform/observability/langfuse.yaml": {
            "sha": "a" * 40,
            "pull_request": 3284,
            "title": "the langfuse reservation is measured",
        }
    }
    got = sync.attribute([drift], history, owner=sync.helmrelease_owner)
    assert got[0]["pull_request"] == 3284
    assert got[0]["commit"] == "a" * 40
    assert got[0]["file"].endswith("langfuse.yaml")


def test_an_object_that_cannot_be_attributed_says_so_and_is_never_dropped() -> None:
    """The estate may not claim a cause its evidence does not carry.

    An unattributed drift still exists and is still reported -- dropping it
    because the estate could not find the file is a finding deleted for the
    convenience of the finder.
    """
    drift = sync.drifts_from([kustomization("mystery")])[0]
    got = sync.attribute([drift], {}, owner=lambda d: None)
    assert len(got) == 1
    assert got[0]["pull_request"] is None
    assert "flux-system/mystery" in got[0]["unattributed"]


def test_attribution_never_invents_a_pull_request_from_a_bare_commit() -> None:
    drift = sync.drifts_from([helmrelease("langfuse")])[0]
    history = {"platform/observability/langfuse.yaml": {"sha": "b" * 40}}
    got = sync.attribute([drift], history, owner=sync.helmrelease_owner)
    assert got[0]["commit"] == "b" * 40
    assert got[0]["pull_request"] is None


# --- what is posted ---------------------------------------------------------


def test_the_comment_names_the_object_the_reason_and_the_file() -> None:
    drift = sync.drifts_from(
        [helmrelease("langfuse", message="Helm install failed: 1000m exceeds quota")]
    )[0]
    drift.update(
        {
            "pull_request": 3284,
            "commit": "c" * 40,
            "file": "platform/observability/langfuse.yaml",
        }
    )
    body = sync.comment_body(3284, [drift])
    assert "observability/langfuse" in body
    assert "exceeds quota" in body
    assert "platform/observability/langfuse.yaml" in body


def test_the_comment_is_one_comment_for_one_pull_request() -> None:
    """A pull request that breaks three objects gets one comment, not three.

    A thread per object turns one cause into three notifications and buries the
    thing that would fix all of them.
    """
    a = sync.drifts_from([helmrelease("langfuse")])[0]
    b = sync.drifts_from([helmrelease("signoz")])[0]
    for d in (a, b):
        d.update({"pull_request": 3284, "commit": "d" * 40, "file": "f.yaml"})
    body = sync.comment_body(3284, [a, b])
    assert body.count("<!-- estate-drift -->") == 1
    assert body.count("observability/langfuse") == 1
    assert body.count("observability/signoz") == 1


def test_a_comment_never_claims_a_cause_it_cannot_name() -> None:
    drift = sync.drifts_from([kustomization("mystery")])[0]
    drift.update(
        {
            "pull_request": None,
            "commit": None,
            "file": None,
            "reason": "no file owns it",
        }
    )
    body = sync.comment_body(0, [drift])
    assert "3284" not in body
    assert "unknown" in body.lower()


# --- grouping, which is what decides how many comments are posted -----------


def test_drifts_group_by_pull_request_and_unattributed_ones_group_apart() -> None:
    a = sync.drifts_from([helmrelease("langfuse")])[0]
    a.update({"pull_request": 3284})
    b = sync.drifts_from([helmrelease("signoz")])[0]
    b.update({"pull_request": 3284})
    c = sync.drifts_from([kustomization("mystery")])[0]
    c.update({"pull_request": None})
    groups = sync.group_by_pull_request([a, b, c])
    assert sorted(groups) == [0, 3284]
    assert len(groups[3284]) == 2
    assert len(groups[0]) == 1


# --- a suspended row is a decision, not a defect -----------------------------


def test_a_suspended_object_is_not_a_drift_whatever_its_status_says() -> None:
    """Measured 2026-09-13: `temporal` carries `spec.suspend: true`.

    The founder suspended it on 2026-08-30 -- "what I spec'd was not what was
    built" (crew#284) -- so Flux stopped reconciling it. Its last recorded
    condition stayed `HealthCheckFailed / InProgress` and its old pods kept
    running, so a reader of the status alone sees a failure that is in fact a
    decision. Reporting it is how a watcher teaches people to ignore it.
    """
    obj = kustomization("temporal", message="timeout waiting for: HelmRelease/temporal")
    # Flux still holds the stale condition; the spec is what makes it suspended.
    obj["spec"] = {"suspend": True}
    assert sync.drifts_from([obj]) == []


def test_a_suspended_helmrelease_is_not_a_drift() -> None:
    obj = helmrelease("lago", message="Helm install failed")
    obj["spec"] = {"suspend": True}
    assert sync.drifts_from([obj]) == []


def test_suspend_false_is_still_graded() -> None:
    """`suspend: false` is the estate's switch back on, and it must be watched.

    The commerce rows carry `suspend: false` and Flux applies them, so a failure
    there is a real failure.
    """
    obj = helmrelease("lago", message="Helm install failed")
    obj["spec"] = {"suspend": False}
    assert len(sync.drifts_from([obj])) == 1
