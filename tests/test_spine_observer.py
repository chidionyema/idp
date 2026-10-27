"""The spine's decisions: a verdict becomes an outcome, an outcome becomes a receipt."""

from __future__ import annotations

from spine.observer import (
    COMPLETE,
    GAP,
    WAIT,
    aevum_body,
    build_receipt,
    decide,
    timeout_receipt,
)

EVENT = {
    "eventId": "msg-1",
    "subject": "flux.event.kustomization.reconciled.v1",
    "kind": "Kustomization",
    "namespace": "flux-system",
    "name": "efda",
    "reason": "ReconciliationSucceeded",
    "severity": "info",
}


def test_a_verified_reconciliation_is_complete():
    verdict = {"verdict": "verified", "ready": True, "revision": "main@sha1:abc"}
    assert decide(verdict) == COMPLETE


def test_a_failed_reconciliation_is_waited_on_not_declared_good():
    verdict = {"verdict": "failed", "ready": False, "reason": "HealthCheckFailed"}
    assert decide(verdict) == WAIT


def test_a_stale_reconciliation_is_waited_on():
    assert decide({"verdict": "stale", "ready": False}) == WAIT


def test_a_missing_object_is_a_gap_not_a_pass():
    assert decide({"verdict": "missing", "ready": False}) == GAP


def test_an_unknown_verdict_is_a_gap():
    assert decide({"verdict": "something-new", "ready": False}) == GAP
    assert decide({}) == GAP


def test_the_receipt_says_what_was_checked_and_what_was_found():
    verdict = {"verdict": "verified", "ready": True, "revision": "main@sha1:abc"}
    body = build_receipt(EVENT, verdict, COMPLETE)
    assert body["eventId"] == "msg-1"
    assert body["verdict"] == "verified"
    assert body["outcome"] == COMPLETE
    assert body["revision"] == "main@sha1:abc"
    assert body["digest"]


def test_a_receipt_that_was_not_written_says_so():
    body = build_receipt(
        EVENT, {"verdict": "verified", "ready": True}, COMPLETE, ingested=False
    )
    assert body["ingested"] is False


def test_a_timeout_is_routed_to_a_human():
    body = timeout_receipt(
        {"kind": "Kustomization", "namespace": "flux-system", "name": "efda"}, 3600
    )
    assert body["outcome"] == GAP
    assert body["detail"]["routedTo"] == "human_review"
    assert body["detail"]["waitedSeconds"] == 3600
    assert body["digest"]


def test_the_aevum_body_has_the_shape_the_api_wants():
    body = build_receipt(EVENT, {"verdict": "verified", "ready": True}, COMPLETE)
    payload = aevum_body(body)
    assert set(payload) == {"data", "provenance", "purpose", "subject_id"}
    assert payload["data"]["digest"] == body["digest"]
    assert payload["provenance"]["source"] == "spine"
    assert payload["subject_id"] == body["subject"]
