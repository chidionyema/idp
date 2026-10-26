"""Interface 1 -- the Diagnostic Artifact contract.

One envelope, five component kinds, one content digest. The rules that make
it evidence rather than prose:

  * ``failure_class`` is not an enum in the schema. It names an entry in the
    versioned FailureClassRegistry, so a novel failure mode
    (``provider_quota_exhaustion``) needs no schema bump.
  * ``raw_evidence`` is content-addressed. A payload carries a digest or a URI,
    not an inline blob, so an artifact stays small enough to pass admission.
  * ``self_assessment`` is mandatory even when empty: an empty assessment is
    itself diagnostic information.
  * ``integrity.content_digest`` is the sha256 of the artifact with the digest
    field itself removed, so a reader can recompute it and a writer cannot
    change a payload after the fact without breaking the digest.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone

from . import SCHEMA_VERSION

COMPONENT_KINDS = (
    "workload",
    "controller",
    "agent",
    "script",
    "external_dependency",
)

CAPTURE_METHODS = (
    "in_process",
    "supervisor_wrapper",
    "sidecar_ebpf",
    "log_tail",
    "admission_rejection",
    "checkpoint_resume",
)

PAYLOAD_KINDS = (
    "kubernetes_events",
    "pod_state",
    "log_tail",
    "trace",
    "network",
    "process_tree",
    "checkpoint",
)

DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


def now_iso() -> str:
    """The timestamp every artifact carries, in UTC, second-resolution."""
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def canonical_bytes(obj) -> bytes:
    """The one byte sequence a digest is computed over."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")


def digest_of(obj) -> str:
    """``sha256:<hex>`` over the canonical bytes of ``obj``."""
    return "sha256:" + hashlib.sha256(canonical_bytes(obj)).hexdigest()


class FailureClassRegistry:
    """The versioned list of failure classes an artifact may name.

    A ConfigMap (``efda-system/failure-class-registry``) holds it. A class
    that is not in the registry is not a failure the estate can reason about,
    so the sink refuses the artifact rather than storing an orphan vocabulary.
    """

    def __init__(self, version: str, classes):
        self.version = version
        self.classes = list(classes)

    @classmethod
    def from_dict(cls, data: dict) -> "FailureClassRegistry":
        classes = data.get("classes") or []
        ids = []
        for entry in classes:
            if isinstance(entry, dict):
                if entry.get("id"):
                    ids.append(str(entry["id"]))
            elif entry:
                ids.append(str(entry))
        return cls(str(data.get("version", "v0")), ids)

    def contains(self, failure_class: str) -> bool:
        return failure_class in self.classes

    def to_dict(self) -> dict:
        return {"version": self.version, "classes": [{"id": c} for c in self.classes]}


def artifact_address(identity: dict) -> str:
    """The deterministic address of an artifact.

    ``{cluster}/{namespace}/{component_class}/{runner_id}/artifact.json``

    Consumers never search for an artifact; they are handed this reference.
    """
    cluster = identity.get("cluster") or "unknown-cluster"
    namespace = identity.get("namespace") or "default"
    component_class = identity.get("component_class") or "unclassified"
    runner_id = identity.get("runner_id") or "unknown-runner"
    return f"{cluster}/{namespace}/{component_class}/{runner_id}/artifact.json"


def build_artifact(
    *,
    component_id: str,
    component_class: str,
    component_kind: str,
    runner_id: str,
    failure_class: str,
    attempted_operation: str,
    invariant_broken: str,
    triggering_step: str,
    capture_method: str,
    payloads=(),
    hypotheses=(),
    writer_identity: str = "spiffe://estate/efda",
    failure_class_registry_version: str = "v1",
    component_version: str = "",
    parent_task_id: str = "",
    tenant_id: str = "",
    cluster: str = "",
    namespace: str = "",
    routing=None,
) -> dict:
    """Build a schema-shaped artifact and stamp its content digest.

    The digest is computed over the artifact with ``integrity.content_digest``
    empty, then written in. A reader recomputes it the same way.
    """
    if component_kind not in COMPONENT_KINDS:
        raise ValueError(f"unknown component_kind: {component_kind}")
    if capture_method not in CAPTURE_METHODS:
        raise ValueError(f"unknown capture_method: {capture_method}")

    identity = {
        "component_id": component_id,
        "component_class": component_class,
        "component_kind": component_kind,
        "component_version": component_version,
        "runner_id": runner_id,
        "parent_task_id": parent_task_id,
        "tenant_id": tenant_id,
        "cluster": cluster,
        "namespace": namespace,
    }
    artifact = {
        "schema_version": SCHEMA_VERSION,
        "identity": identity,
        "failure_boundary": {
            "attempted_operation": attempted_operation,
            "invariant_broken": invariant_broken,
            "triggering_step": triggering_step,
            "failure_class": failure_class,
            "failure_class_registry_version": failure_class_registry_version,
        },
        "raw_evidence": {
            "capture_method": capture_method,
            "payloads": [dict(p) for p in payloads],
        },
        "self_assessment": {
            "hypotheses": [dict(h) for h in hypotheses],
        },
        "integrity": {
            "content_digest": "",
            "writer_identity": writer_identity,
            "written_at": now_iso(),
        },
    }
    if routing:
        # Where the gap was routed when the evidence was missing. It is part
        # of the artifact, so the digest covers it: a reader can see that the
        # task was handed to a human rather than silently dropped.
        artifact["routing"] = dict(routing)
    artifact["integrity"]["content_digest"] = recompute_digest(artifact)
    return artifact


def recompute_digest(artifact: dict) -> str:
    """The digest of an artifact, ignoring the digest field itself."""
    stripped = dict(artifact)
    integrity = dict(stripped.get("integrity") or {})
    integrity.pop("content_digest", None)
    stripped["integrity"] = integrity
    return digest_of(stripped)


def validate_artifact(artifact: dict, registry=None) -> list:
    """Return the list of contract violations. Empty means valid.

    Deliberately explicit rather than schema-driven: the sink must be able to
    say *why* it refused, and a refusal with a reason is what routes the gap
    to a human.
    """
    errors = []
    if not isinstance(artifact, dict):
        return ["artifact is not an object"]

    if artifact.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION}")

    identity = artifact.get("identity")
    if not isinstance(identity, dict):
        errors.append("identity is missing")
        identity = {}
    for field in ("component_id", "component_class", "component_kind", "runner_id"):
        if not identity.get(field):
            errors.append(f"identity.{field} is required")
    if (
        identity.get("component_kind")
        and identity["component_kind"] not in COMPONENT_KINDS
    ):
        errors.append(
            f"identity.component_kind {identity['component_kind']!r} is not a component kind"
        )

    boundary = artifact.get("failure_boundary")
    if not isinstance(boundary, dict):
        errors.append("failure_boundary is missing")
        boundary = {}
    for field in (
        "attempted_operation",
        "invariant_broken",
        "triggering_step",
        "failure_class",
    ):
        if not boundary.get(field):
            errors.append(f"failure_boundary.{field} is required")
    if registry is not None and boundary.get("failure_class"):
        if not registry.contains(boundary["failure_class"]):
            errors.append(
                f"failure_class {boundary['failure_class']!r} is not in FailureClassRegistry "
                f"{registry.version}"
            )

    evidence = artifact.get("raw_evidence")
    if not isinstance(evidence, dict):
        errors.append("raw_evidence is missing")
        evidence = {}
    method = evidence.get("capture_method")
    if method not in CAPTURE_METHODS:
        errors.append(f"raw_evidence.capture_method {method!r} is not a capture method")
    payloads = evidence.get("payloads")
    if not isinstance(payloads, list):
        errors.append("raw_evidence.payloads must be a list")
    else:
        for index, payload in enumerate(payloads):
            if not isinstance(payload, dict):
                errors.append(f"raw_evidence.payloads[{index}] is not an object")
                continue
            if not payload.get("kind"):
                errors.append(f"raw_evidence.payloads[{index}].kind is required")
            if payload.get("digest") and not DIGEST_RE.match(str(payload["digest"])):
                errors.append(
                    f"raw_evidence.payloads[{index}].digest is not a sha256 digest"
                )
            if (
                not payload.get("digest")
                and not payload.get("uri")
                and not payload.get("inline")
            ):
                errors.append(
                    f"raw_evidence.payloads[{index}] carries no digest, uri or inline payload"
                )

    assessment = artifact.get("self_assessment")
    if not isinstance(assessment, dict) or "hypotheses" not in assessment:
        errors.append(
            "self_assessment.hypotheses is required (an empty list is a valid assessment)"
        )

    integrity = artifact.get("integrity")
    if not isinstance(integrity, dict):
        errors.append("integrity is missing")
        integrity = {}
    digest = integrity.get("content_digest")
    if not digest or not DIGEST_RE.match(str(digest)):
        errors.append("integrity.content_digest is not a sha256 digest")
    elif digest != recompute_digest(artifact):
        errors.append("integrity.content_digest does not match the artifact contents")
    if not integrity.get("writer_identity"):
        errors.append("integrity.writer_identity is required")
    if not integrity.get("written_at"):
        errors.append("integrity.written_at is required")

    return errors
