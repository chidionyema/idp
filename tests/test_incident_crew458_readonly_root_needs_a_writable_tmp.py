"""crew#458 row 3, 2026-08-27 20:30Z: estate-mcp crash-looped five times on the cluster with
`FileNotFoundError: No usable temporary directory found in ['/tmp', '/var/tmp', '/usr/tmp', '/']`.
The container ran with `readOnlyRootFilesystem: true` and mounted only the read-only data volume,
so Python's tempfile had nowhere to write. healthchecks.yaml and backstage catalogue.yaml carry a
`tmp` emptyDir for exactly this reason; this test makes the rule cover every container under
platform/, not one manifest at a time (LAW 45: the mistake ends as a guard over every instance).

Rule: a container that sets readOnlyRootFilesystem: true and runs a Python, Node or shell workload
mounts a writable volume at /tmp (or names one through TMPDIR). Init containers that only copy
files (flux-cli pull) are outside the rule: they do not open a temp file.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
PLATFORM = ROOT / "platform"

# Images that never touch a temp dir: a copy-only init container. Everything else is in the rule.
COPY_ONLY_IMAGE_PREFIXES = ("ghcr.io/fluxcd/flux-cli",)


def _containers():
    for path in sorted(PLATFORM.rglob("*.yaml")):
        try:
            docs = list(yaml.safe_load_all(path.read_text()))
        except yaml.YAMLError:
            continue
        for doc in docs:
            if not isinstance(doc, dict) or doc.get("kind") not in {"Deployment", "StatefulSet", "DaemonSet", "CronJob", "Job"}:
                continue
            spec = doc.get("spec", {})
            if doc["kind"] == "CronJob":
                spec = spec.get("jobTemplate", {}).get("spec", {})
            pod = spec.get("template", {}).get("spec", {})
            volumes = {v.get("name"): v for v in pod.get("volumes", []) or []}
            for c in (pod.get("containers", []) or []) + (pod.get("initContainers", []) or []):
                yield path.relative_to(ROOT), doc.get("metadata", {}).get("name"), c, volumes


def _writable_tmp(c, volumes) -> bool:
    env = {e.get("name"): e.get("value") for e in c.get("env", []) or []}
    tmpdir = env.get("TMPDIR", "/tmp")
    for m in c.get("volumeMounts", []) or []:
        if m.get("mountPath") == tmpdir and not m.get("readOnly", False):
            return True
    return False


def _in_rule(c) -> bool:
    if not (c.get("securityContext") or {}).get("readOnlyRootFilesystem"):
        return False
    return not str(c.get("image", "")).startswith(COPY_ONLY_IMAGE_PREFIXES)


CASES = [(str(p), n, c, v) for p, n, c, v in _containers() if _in_rule(c)]


@pytest.mark.parametrize("path,workload,container,volumes", CASES, ids=[f"{p}::{n}/{c['name']}" for p, n, c, _ in CASES])
def test_readonly_root_container_mounts_a_writable_tmp(path, workload, container, volumes):
    assert _writable_tmp(container, volumes), (
        f"{path} {workload}/{container['name']}: readOnlyRootFilesystem without a writable /tmp "
        "(or TMPDIR on a mounted volume) -- estate-mcp crash-looped on this on 2026-08-27 (crew#458)"
    )


def test_the_rule_sees_estate_mcp():
    assert any(n == "estate-mcp" and c["name"] == "estate-mcp" for _, n, c, _ in CASES), "estate-mcp fell out of the sweep"


def test_the_rule_refuses_the_incident_shape():
    c = {"name": "x", "image": "ghcr.io/o/app", "securityContext": {"readOnlyRootFilesystem": True},
         "volumeMounts": [{"name": "data", "mountPath": "/data", "readOnly": True}]}
    assert _in_rule(c) and not _writable_tmp(c, {})
    c["volumeMounts"].append({"name": "tmp", "mountPath": "/tmp"})
    assert _writable_tmp(c, {})
