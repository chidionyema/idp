"""The five diagnostic-artifact JSON Schemas.

One schema per component kind, sharing one envelope. The schemas are
generated from one builder so the five cannot drift apart, and the generated
files are committed (``efda/schemas/*.json``) because consumers -- the sink,
the reasoning layer, anything written against the contract -- need a file,
not a function.

``python -m efda.schemas --write`` regenerates them.
"""

from __future__ import annotations

import json
import os
import sys

from . import SCHEMA_VERSION
from .contract import CAPTURE_METHODS, COMPONENT_KINDS, PAYLOAD_KINDS

SCHEMA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schemas")

DIGEST_PATTERN = "^sha256:[0-9a-f]{64}$"


def _envelope(kind: str, kind_required) -> dict:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": f"https://efda.estate/schemas/diagnostic-artifact-{kind}.json",
        "title": f"EFDA DiagnosticArtifact ({kind})",
        "type": "object",
        "required": [
            "schema_version",
            "identity",
            "failure_boundary",
            "raw_evidence",
            "self_assessment",
            "integrity",
        ],
        "additionalProperties": False,
        "properties": {
            "schema_version": {"const": SCHEMA_VERSION},
            "identity": {
                "type": "object",
                "required": [
                    "component_id",
                    "component_class",
                    "component_kind",
                    "runner_id",
                ],
                "additionalProperties": True,
                "properties": {
                    "component_id": {"type": "string", "minLength": 1},
                    "component_class": {"type": "string", "minLength": 1},
                    "component_kind": {"type": "string", "enum": list(COMPONENT_KINDS)},
                    "component_version": {"type": "string"},
                    "runner_id": {"type": "string", "minLength": 1},
                    "parent_task_id": {"type": "string"},
                    "tenant_id": {"type": "string"},
                    "cluster": {"type": "string"},
                    "namespace": {"type": "string"},
                },
            },
            "failure_boundary": {
                "type": "object",
                "required": [
                    "attempted_operation",
                    "invariant_broken",
                    "triggering_step",
                    "failure_class",
                    "failure_class_registry_version",
                ],
                "additionalProperties": False,
                "properties": {
                    "attempted_operation": {"type": "string", "minLength": 1},
                    "invariant_broken": {"type": "string", "minLength": 1},
                    "triggering_step": {"type": "string", "minLength": 1},
                    # Not an enum: a novel failure class is introduced by a
                    # registry version, not by a schema bump.
                    "failure_class": {"type": "string", "minLength": 1},
                    "failure_class_registry_version": {
                        "type": "string",
                        "minLength": 1,
                    },
                },
            },
            "raw_evidence": {
                "type": "object",
                "required": ["capture_method", "payloads"],
                "additionalProperties": False,
                "properties": {
                    "capture_method": {"type": "string", "enum": list(CAPTURE_METHODS)},
                    "payloads": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["kind"],
                            "additionalProperties": False,
                            "properties": {
                                "kind": {"type": "string", "enum": list(PAYLOAD_KINDS)},
                                "digest": {"type": "string", "pattern": DIGEST_PATTERN},
                                "inline": {"type": "string"},
                                "uri": {"type": "string"},
                            },
                        },
                    },
                },
            },
            "self_assessment": {
                "type": "object",
                "required": ["hypotheses"],
                "additionalProperties": False,
                "properties": {
                    "hypotheses": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["rank", "cause", "confidence"],
                            "additionalProperties": True,
                            "properties": {
                                "rank": {"type": "integer", "minimum": 1},
                                "cause": {"type": "string"},
                                "confidence": {
                                    "type": "number",
                                    "minimum": 0.0,
                                    "maximum": 1.0,
                                },
                                "evidence_refs": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                                "source": {"type": "string"},
                            },
                        },
                    },
                    "next_read": {"type": "string"},
                },
            },
            "integrity": {
                "type": "object",
                "required": ["content_digest", "writer_identity", "written_at"],
                "additionalProperties": False,
                "properties": {
                    "content_digest": {"type": "string", "pattern": DIGEST_PATTERN},
                    "writer_identity": {"type": "string", "minLength": 1},
                    "written_at": {"type": "string", "minLength": 1},
                },
            },
            # Where a gap was routed when the evidence was missing. It is
            # inside the digest, so "somebody saw it" is a fact a reader can
            # check rather than a promise.
            "routing": {
                "type": "object",
                "additionalProperties": True,
                "properties": {
                    "routed_to": {"type": "string", "minLength": 1},
                    "reason": {"type": "string"},
                    "at": {"type": "string"},
                },
            },
        },
        "x-efda-kind": kind,
        "x-efda-kind-required": kind_required,
    }


KINDS = {
    "workload": ["component_version"],
    "controller": ["component_version", "parent_task_id"],
    "agent": ["runner_id"],
    "script": ["runner_id"],
    "external_dependency": ["component_version"],
}


def build_all() -> dict:
    schemas = {}
    for kind, kind_required in KINDS.items():
        schema = _envelope(kind, kind_required)
        # The kind's extra requirements are identity fields, so they belong to
        # the identity's own required list -- not to the envelope's.
        identity = schema["properties"]["identity"]
        identity["required"] = sorted(set(identity["required"]) | set(kind_required))
        schemas[f"diagnostic-artifact-{kind}.json"] = schema
    return schemas


def write(directory=SCHEMA_DIR):
    os.makedirs(directory, exist_ok=True)
    written = []
    for name, schema in build_all().items():
        path = os.path.join(directory, name)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(schema, handle, indent=2, sort_keys=True)
            handle.write("\n")
        written.append(path)
    return written


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "--write":
        for path in write():
            print(path)
        return 0
    print(json.dumps(sorted(build_all().keys()), indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
