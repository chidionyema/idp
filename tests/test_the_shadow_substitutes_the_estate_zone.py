"""The shadow substitutes ${ESTATE_ZONE} the way production's Flux rows do.

Incident: 2026-09-27, idp#4582. shadow-verify failed platform/llm on
`HTTPRoute "litellm" is invalid: spec.hostnames[0]: Invalid value: "llm.${ESTATE_ZONE}"`.
Production substitutes every hostname in Flux postBuild from the estate-config ConfigMap
(clusters/oke/estate-config.yaml). The shadow had neither the ConfigMap nor the postBuild, so any
path that publishes a hostname was refused for a gap in the shadow, not in the change.
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


class _Daemon:
    def terminate(self):
        pass

    def wait(self, timeout=None):
        return 0


def test_every_path_under_test_substitutes_from_the_estate_config_it_lays(
    monkeypatch,
):
    shadow = load_shadow()
    applied, files = [], []

    def fake_run(argv, input=None, **kw):
        if input is not None:
            applied.append(json.loads(input))
        elif "-f" in argv:
            files.append(argv[argv.index("-f") + 1])
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(shadow.subprocess, "run", fake_run)
    monkeypatch.setattr(shadow, "have", lambda tool: True)
    monkeypatch.setattr(shadow, "serve_tree", lambda: _Daemon())
    monkeypatch.setattr(shadow, "flux_source", lambda head: None)
    monkeypatch.setattr(shadow, "flux_floor", lambda deadline: [])
    monkeypatch.setattr(shadow, "stand_in_vault", lambda stop: None)
    monkeypatch.setattr(shadow, "wait_ks", lambda name, deadline: (False, "x", []))

    shadow.verify("abc123", ["platform/llm"])

    assert files == [str(REPO / "clusters" / "oke" / "estate-config.yaml")]
    (ks,) = [o for o in applied if o["kind"] == "Kustomization"]
    assert ks["spec"]["path"] == "platform/llm"
    assert ks["spec"]["postBuild"] == {
        "substituteFrom": [{"kind": "ConfigMap", "name": "estate-config"}]
    }


def test_the_config_it_lays_defines_every_variable_the_llm_route_names():
    text = (REPO / "clusters" / "oke" / "estate-config.yaml").read_text()
    assert re.search(r"^\s*name: estate-config\s*$", text, re.M)
    assert re.search(r"^\s*namespace: flux-system\s*$", text, re.M)
    keys = set(re.findall(r"^  ([A-Z][A-Z0-9_]*):", text, re.M))
    used = set(
        re.findall(
            r"\$\{([A-Z][A-Z0-9_]*)\}",
            (REPO / "platform" / "llm" / "httproute.yaml").read_text(),
        )
    )
    assert used and used <= keys
