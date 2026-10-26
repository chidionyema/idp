"""The spine's contracts: the event, the subject, the receipt.

The subject test is the important one: the founder's build kit proposed a subject that the
estate's own grammar rejects, and this is the test that says so in code rather than in a
review nobody reads.
"""

from __future__ import annotations

import json
import os
import re

import pytest

from spine.contracts import (
    DOMAIN,
    SIGNAL_NAME,
    EventError,
    FluxEvent,
    SubjectError,
    digest_of,
    receipt,
    subject_for,
    validate_subject,
)

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GO_SUBJECT = os.path.join(REPO, "platform", "messaging", "subject", "subject.go")


def flux_event(**overrides):
    body = {
        "involvedObject": {
            "kind": "Kustomization",
            "name": "efda",
            "namespace": "flux-system",
            "apiVersion": "kustomize.toolkit.fluxcd.io/v1",
            "uid": "6f1c1f0a-0000-4000-8000-000000000001",
            "resourceVersion": "12345",
        },
        "severity": "info",
        "timestamp": "2026-10-26T12:00:00Z",
        "message": "Applied revision: main@sha1:abc",
        "reason": "ReconciliationSucceeded",
        "reportingController": "kustomize-controller",
    }
    body.update(overrides)
    return body


def test_an_event_parses_into_the_facts_the_spine_needs():
    event = FluxEvent.from_payload(json.dumps(flux_event()), event_id="msg-1")
    assert event.kind == "Kustomization"
    assert event.name == "efda"
    assert event.namespace == "flux-system"
    assert event.reason == "ReconciliationSucceeded"
    assert event.event_id == "msg-1"
    assert event.failed is False


def test_an_event_without_a_reason_is_not_routable():
    body = flux_event()
    body.pop("reason")
    with pytest.raises(EventError):
        FluxEvent.from_payload(json.dumps(body))


def test_a_body_that_is_not_json_is_not_routable():
    with pytest.raises(EventError):
        FluxEvent.from_payload("this is not json")


def test_the_subject_is_a_d1_subject():
    event = FluxEvent.from_payload(json.dumps(flux_event()))
    assert event.subject == "flux.event.kustomization.reconciled.v1"
    assert validate_subject(event.subject) == event.subject


def test_the_build_kits_subject_is_not_a_d1_subject():
    # The kit proposed `evt.flux.kustomization.reconciled`. Four tokens, the kind is not
    # one D1 admits, and there is no version. The estate's grammar says so, and the spine
    # publishes the subject the estate speaks.
    with pytest.raises(SubjectError):
        validate_subject("evt.flux.kustomization.reconciled")
    assert subject_for("Kustomization") == "flux.event.kustomization.reconciled.v1"


def test_a_subject_must_carry_a_version():
    with pytest.raises(SubjectError):
        validate_subject("flux.event.kustomization.reconciled")


def test_an_environment_is_never_part_of_a_subject():
    with pytest.raises(SubjectError):
        validate_subject("prod.event.kustomization.reconciled.v1")


def test_the_workflow_id_names_the_object():
    event = FluxEvent.from_payload(json.dumps(flux_event()))
    assert event.workflow_id == "spine-verify-kustomization-flux-system-efda"
    assert event.signal_name == SIGNAL_NAME


def test_a_failed_reconciliation_is_marked_as_one():
    body = flux_event(severity="error", reason="ReconciliationFailed")
    assert FluxEvent.from_payload(json.dumps(body)).failed is True


def test_the_receipt_carries_a_digest_of_its_own_body():
    event = FluxEvent.from_payload(json.dumps(flux_event()), event_id="msg-1")
    body = receipt(event, "verified", detail={"revision": "main@sha1:abc"})
    assert body["digest"]
    stripped = dict(body)
    stripped.pop("digest")
    assert body["digest"] == digest_of(stripped)
    # The same facts, the same digest: a receipt is checkable by whoever holds it.
    assert (
        receipt(event, "verified", detail={"revision": "main@sha1:abc"})["digest"]
        == body["digest"]
    )


def test_the_python_subject_rules_still_match_the_go_package():
    """The spine mirrors the estate's grammar; the mirror must not drift.

    platform/messaging/subject/subject.go is the source of truth. If its kinds, its
    version pattern or its forbidden words change, this test fails and the mirror is
    updated with it -- rather than the two quietly disagreeing about what a subject is.
    """
    with open(GO_SUBJECT, "r", encoding="utf-8") as handle:
        go = handle.read()
    go_kinds = re.search(r"kinds\s*=\s*map\[string\]bool\{([^}]*)\}", go)
    assert go_kinds, "the Go package no longer declares its kinds"
    for kind in re.findall(r'"(\w+)"\s*:\s*true', go_kinds.group(1)):
        assert kind in ("event", "command", "dlq"), "the Go kinds changed: %s" % kind
    go_version = re.search(r"version\s*=\s*regexp\.MustCompile\(`([^`]+)`\)", go)
    assert go_version, "the Go package no longer declares its version pattern"
    assert go_version.group(1) == r"^v[1-9][0-9]*$"
    go_forbidden = re.search(r"forbidden\s*=\s*map\[string\]bool\{([^}]*)\}", go)
    assert go_forbidden, "the Go package no longer declares its forbidden words"
    for word in re.findall(r'"(\w+)"\s*:\s*true', go_forbidden.group(1)):
        with pytest.raises(SubjectError):
            validate_subject("%s.event.kustomization.reconciled.v1" % word)


def test_the_domain_is_the_estates():
    assert DOMAIN == "flux"
