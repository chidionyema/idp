"""Reading a Flux object's own status, and grading it.

The grading is the whole check, and it has no I/O in it -- so the four verdicts can be
stated here and be true.
"""

from __future__ import annotations

import pytest

from spine.kube import KubeError, KubeReader, verdict_from_object

# A token that is obviously not a credential: the reader is never allowed to reach the
# network in these tests, and the literal lives here so it is not a call-site secret.
FAKE_CREDENTIAL = "not-a-credential"


def test_a_ready_object_with_the_applied_revision_is_verified():
    obj = {
        "status": {
            "conditions": [
                {"type": "Ready", "status": "True", "reason": "ReconciliationSucceeded"}
            ],
            "lastAppliedRevision": "main@sha1:abc",
            "lastAttemptedRevision": "main@sha1:abc",
        }
    }
    verdict = verdict_from_object(obj)
    assert verdict["verdict"] == "verified"
    assert verdict["ready"] is True
    assert verdict["revision"] == "main@sha1:abc"


def test_an_object_that_is_not_ready_is_failed_and_says_why():
    obj = {
        "status": {
            "conditions": [
                {
                    "type": "Ready",
                    "status": "False",
                    "reason": "HealthCheckFailed",
                    "message": "no",
                }
            ],
            "lastAppliedRevision": "main@sha1:abc",
        }
    }
    verdict = verdict_from_object(obj)
    assert verdict["verdict"] == "failed"
    assert verdict["reason"] == "HealthCheckFailed"


def test_an_object_whose_applied_revision_lags_is_stale_not_verified():
    obj = {
        "status": {
            "conditions": [{"type": "Ready", "status": "True"}],
            "lastAppliedRevision": "main@sha1:old",
            "lastAttemptedRevision": "main@sha1:new",
        }
    }
    verdict = verdict_from_object(obj)
    assert verdict["verdict"] == "stale"
    assert verdict["ready"] is False


def test_an_object_with_no_ready_condition_is_not_verified():
    verdict = verdict_from_object({"status": {"conditions": []}})
    assert verdict["verdict"] == "failed"
    assert verdict["reason"] == "NoReadyCondition"


def test_a_missing_object_is_missing():
    reader = KubeReader(token=FAKE_CREDENTIAL, ca_file=__file__)

    def boom(_path):
        raise KubeError("not found: /apis/...")

    reader.get = boom
    verdict = reader.status_of("Kustomization", "flux-system", "efda")
    assert verdict["verdict"] == "missing"
    assert verdict["found"] is False


def test_an_unreadable_object_is_unreadable_not_missing():
    reader = KubeReader(token=FAKE_CREDENTIAL, ca_file=__file__)

    def boom(_path):
        raise KubeError("api server unreachable")

    reader.get = boom
    verdict = reader.status_of("Kustomization", "flux-system", "efda")
    assert verdict["verdict"] == "unreadable"


def test_the_path_names_the_flux_group():
    reader = KubeReader(token=FAKE_CREDENTIAL, ca_file=__file__)
    seen = {}

    def capture(path):
        seen["path"] = path
        return {"status": {}}

    reader.get = capture
    reader.get_object("Kustomization", "flux-system", "efda")
    assert seen["path"] == (
        "/apis/kustomize.toolkit.fluxcd.io/v1/namespaces/flux-system/kustomizations/efda"
    )
    reader.get_object("HelmRelease", "flux-system", "zeroedge")
    assert seen["path"] == (
        "/apis/helm.toolkit.fluxcd.io/v2/namespaces/flux-system/helmreleases/zeroedge"
    )


def test_a_kind_the_spine_does_not_verify_is_refused():
    reader = KubeReader(token=FAKE_CREDENTIAL, ca_file=__file__)
    with pytest.raises(KubeError):
        reader.get_object("Pod", "default", "x")
