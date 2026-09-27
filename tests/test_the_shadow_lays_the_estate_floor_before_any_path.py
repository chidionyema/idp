"""The shadow reconciles a platform path on the floor production has, not on a bare cluster.

Incident: 2026-09-27. Once the shadow could clone its head (idp#4488), every PR touching
platform/llm, temporal, epistemic-fabric, unified-memory-server or voice-router failed on
`no matches for kind "ExternalSecret"`, and event-bus's nats on `no PriorityClass platform-batch`.
Production installs both before any workload row (clusters/oke/secrets.yaml, priority-classes).
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import re
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def load_shadow():
    loader = importlib.machinery.SourceFileLoader(
        "idp_shadow", str(REPO / "bin" / "idp-shadow")
    )
    spec = importlib.util.spec_from_loader("idp_shadow", loader)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def test_the_floor_is_production_eso_crds_and_priority_classes(monkeypatch):
    shadow = load_shadow()
    applied = []

    def fake_run(argv, input=None, **kw):
        applied.append(json.loads(input))
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(shadow.subprocess, "run", fake_run)
    monkeypatch.setattr(shadow, "wait_ks", lambda name, deadline: (True, "", []))
    assert shadow.flux_floor(0) == []

    pinned = re.search(
        r"chart: external-secrets\s+version: *(\S+)",
        (REPO / "platform/secrets/external-secrets.yaml").read_text(),
    ).group(1)
    src = next(o for o in applied if o["kind"] == "GitRepository")
    assert src["spec"]["ref"] == {"tag": "v" + pinned}
    ks = {
        o["spec"]["path"]: o["spec"]["sourceRef"]["name"]
        for o in applied
        if o["kind"] == "Kustomization"
    }
    assert ks == {
        "./deploy/crds": src["metadata"]["name"],
        "./platform/priority-classes": "shadow",
    }
    assert (REPO / "platform/priority-classes/priorityclasses.yaml").exists()


def test_a_floor_that_does_not_converge_fails_the_run_before_any_path(monkeypatch):
    shadow = load_shadow()
    paths = []
    monkeypatch.setattr(shadow, "have", lambda tool: True)
    monkeypatch.setattr(shadow, "serve_tree", lambda: subprocess.Popen(["true"]))
    monkeypatch.setattr(shadow, "flux_source", lambda head: None)
    monkeypatch.setattr(shadow, "flux_floor", lambda deadline: ["no CRDs"])
    monkeypatch.setattr(
        shadow,
        "flux_kustomization",
        lambda name, path, source="shadow": paths.append(path),
    )
    rc, why = shadow.verify("a" * 40, ["platform/llm"])
    assert (rc, why, paths) == (1, ["no CRDs"], [])
