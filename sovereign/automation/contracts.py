"""Pure context compiler. No network, Temporal client or side effects.

An automation is described by executable Python, not by a maintained catalogue.
The compiled plan is a value: never mutate it after starting a Temporal history.
"""

from __future__ import annotations

import hashlib
import importlib
import inspect
import pkgutil
import json
import re
from typing import Any

from jsonschema import Draft202012Validator

from sovereign.automation import definitions


def _automations() -> tuple[type, ...]:
    """Discover executable workflow definitions from the Python package.

    The sole registration rule is the implementation protocol, not a
    hand-maintained list of intent names or manifests.
    """
    result = []
    for module_info in pkgutil.iter_modules(
        definitions.__path__, definitions.__name__ + "."
    ):
        mod = importlib.import_module(module_info.name)
        for _, cls in inspect.getmembers(mod, inspect.isclass):
            if cls.__module__ == mod.__name__ and all(
                hasattr(cls, field)
                for field in (
                    "ID",
                    "VERSION",
                    "manifest",
                    "compile_steps",
                    "authorized",
                )
            ):
                result.append(cls)
    if len({c.ID for c in result}) != len(result):
        raise ValueError("duplicate automation implementation ID")
    return tuple(sorted(result, key=lambda c: c.ID))


_HEX40 = re.compile(r"^[0-9a-f]{40}$")
_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")


def canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode()


def sha256(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def catalogue() -> list[dict[str, Any]]:
    """Generated from code-defined types; only registered executable classes are exposed."""
    return [cls.manifest() for cls in _automations()]


def find(outcome: str) -> list[dict[str, Any]]:
    tokens = set(re.findall(r"[a-z0-9]+", outcome.lower()))
    matches = []
    for manifest in catalogue():
        terms = " ".join(
            [manifest["id"], manifest["summary"], *manifest["search_terms"]]
        ).lower()
        if tokens and tokens & set(re.findall(r"[a-z0-9]+", terms)):
            matches.append(manifest)
    return matches


def compile_request(request: dict[str, Any], release: dict[str, str]) -> dict[str, Any]:
    """Strictly validate identity, version, inputs and an immutable release fingerprint.

    source_sha = git commit; artifact_digest = immutable worker image digest;
    config_digest = digest of active deployment configuration (not its secrets).
    Unknown identity or release is never guessed.
    """
    allowed = {"id", "version", "request_id", "surface", "actor", "inputs"}
    if set(request) != allowed:
        raise ValueError(f"request keys must be exactly {sorted(allowed)}")
    if not isinstance(request["request_id"], str) or not re.fullmatch(
        r"[A-Za-z0-9._:-]{8,128}", request["request_id"]
    ):
        raise ValueError("request_id must be a stable 8-128 character idempotency key")
    if not isinstance(request["actor"], str) or not re.fullmatch(
        r"[A-Za-z0-9._:@/-]{2,128}", request["actor"]
    ):
        raise ValueError("actor must be a verified identity, not an unbounded string")
    if not isinstance(request["surface"], str):
        raise ValueError("surface must be a string")
    chosen = next((c for c in _automations() if c.ID == request["id"]), None)
    if chosen is None or request["version"] != chosen.VERSION:
        raise ValueError("unknown/incompatible automation version: read-only")
    manifest = chosen.manifest()
    if request["surface"] not in manifest["surfaces"]:
        raise ValueError("surface not supported")
    if set(release) != {"source_sha", "artifact_digest", "config_digest"}:
        raise ValueError("release provenance incomplete")
    if not _HEX40.fullmatch(release["source_sha"]) or any(
        not _DIGEST.fullmatch(release[k]) for k in ("artifact_digest", "config_digest")
    ):
        raise ValueError("invalid release identity; refuse execution")
    errors = list(
        Draft202012Validator(manifest["input_schema"]).iter_errors(request["inputs"])
    )
    if errors:
        raise ValueError(
            "invalid automation inputs: " + "; ".join(sorted(e.message for e in errors))
        )
    if not chosen.authorized(request["actor"], request["inputs"]):
        raise PermissionError("actor lacks authority for this automation")
    steps = chosen.compile_steps(request["inputs"])
    _validate_dag(steps, manifest["max_concurrency"])
    content = {
        "contract": {"id": chosen.ID, "version": chosen.VERSION},
        "request": dict(request),
        "release": dict(release),
        "steps": steps,
        "max_concurrency": manifest["max_concurrency"],
        "receipt_schema_version": 1,
    }
    digest = sha256(content)
    workflow_id = (
        "estate-auto:"
        + chosen.ID.replace(".", "-")
        + ":"
        + sha256(
            {
                "request_id": request["request_id"],
                "actor": request["actor"],
                "version": chosen.VERSION,
            }
        )[:32]
    )
    return {**content, "plan_hash": digest, "workflow_id": workflow_id}


def _validate_dag(steps: list[dict[str, Any]], ceiling: int) -> None:
    if not steps or not 1 <= ceiling <= 16:
        raise ValueError("empty DAG or invalid concurrency ceiling")
    nodes = {s["id"]: s for s in steps}
    if len(nodes) != len(steps):
        raise ValueError("duplicate DAG node")
    if any(
        s["timeout_s"] < 1
        or s["timeout_s"] > 600
        or s["max_attempts"] < 1
        or s["max_attempts"] > 5
        for s in steps
    ):
        raise ValueError("unsafe activity timeout / retry")
    for s in steps:
        if (
            s["id"] in s["deps"]
            or len(s["deps"]) != len(set(s["deps"]))
            or any(d not in nodes for d in s["deps"])
        ):
            raise ValueError("invalid dependency")
    pending = set(nodes)
    while pending:
        ready = {n for n in pending if not set(nodes[n]["deps"]) & pending}
        if not ready:
            raise ValueError("DAG cycle")
        pending -= ready


def verify_plan(plan: dict[str, Any]) -> None:
    """Must be checked again at the execution boundary, not just by the UI."""
    raw = {k: v for k, v in plan.items() if k not in ("plan_hash", "workflow_id")}
    if sha256(raw) != plan.get("plan_hash"):
        raise ValueError("plan was mutated after compilation")
    _validate_dag(plan["steps"], plan["max_concurrency"])
