"""The shadow has no vault, so it stands in for one: every ExternalSecret gets its Secret.

Incident: 2026-09-27. With the ESO CRDs on the shadow floor, newsroom P1 (#4475) still went red:
epistemic-ingest waited in ContainerCreating on `secret "epistemic-fabric-github-api" not found`,
because no ESO controller and no estate-vault store exist in a throwaway cluster. The stand-in
writes the Secret ESO would have written, under the keys ESO would have used.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import subprocess
import threading
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
SHADOW = REPO / "bin" / "idp-shadow"


def load_shadow():
    loader = importlib.machinery.SourceFileLoader("idp_shadow", str(SHADOW))
    spec = importlib.util.spec_from_loader("idp_shadow", loader)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def epistemic_external_secrets():
    docs = yaml.safe_load_all(
        (REPO / "platform/epistemic-fabric/external-secret.yaml").read_text()
    )
    return [d for d in docs if d and d.get("kind") == "ExternalSecret"]


def test_each_stand_in_carries_the_keys_eso_would_write():
    shadow = load_shadow()
    got = {
        s["metadata"]["name"]: (s["metadata"]["namespace"], sorted(s["stringData"]))
        for s in shadow.vault_stand_ins(epistemic_external_secrets())
    }
    assert got["epistemic-fabric-github-api"] == ("epistemic-fabric", ["token"])
    assert got["epistemic-fabric-github"] == ("epistemic-fabric", ["webhook_secret"])
    assert got["github-app-pem"] == ("epistemic-fabric", ["key"])


def test_the_stand_in_creates_each_secret_once_and_stops(monkeypatch):
    shadow = load_shadow()
    items = epistemic_external_secrets()
    stop = threading.Event()
    listed, created = [], []

    def fake_kube(argv, check=True, timeout=300):
        listed.append(argv)
        if len(listed) == 3:
            stop.set()
        return subprocess.CompletedProcess(argv, 0, json.dumps({"items": items}), "")

    def fake_run(argv, input=None, **kw):
        created.append(json.loads(input)["metadata"]["name"])
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(shadow, "kube", fake_kube)
    monkeypatch.setattr(shadow.subprocess, "run", fake_run)
    shadow.stand_in_vault(stop, every=0)
    assert len(listed) == 3
    assert sorted(created) == sorted(
        s["metadata"]["name"] for s in shadow.vault_stand_ins(items)
    )
