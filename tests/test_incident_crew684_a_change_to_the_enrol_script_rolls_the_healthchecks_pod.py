"""Incident 2026-08-30 06:3xZ, crew#684: after the portal presented the allowed Host (idp#957) the
Ops tile still read "Healthchecks answered 401" (login drill 33297056184). The enrol script that
sets the project's read-only key was changed at 04:32Z (idp#932) in a plain ConfigMap; the
Deployment spec did not change, the pod never restarted, and the init container never re-ran the
script, so the key the portal sends was never set on the project. Same fault as crew#561's
mac-run (idp#955). Guard: the script is a file rendered by a configMapGenerator, so its ConfigMap
name carries a content hash and the Deployment rolls on every change. Fault class:
instrument-nobody-reads (a ConfigMap edit that reaches nothing).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
HC = ROOT / "platform" / "healthchecks"


def test_the_enrol_script_is_a_generated_configmap() -> None:
    kz = yaml.safe_load((HC / "kustomization.yaml").read_text())
    gens = {g["name"]: g for g in kz.get("configMapGenerator", [])}
    assert gens["healthchecks-enrol"]["files"] == ["enrol.py"]
    assert (HC / "enrol.py").exists()
    manifests = list(yaml.safe_load_all((HC / "healthchecks.yaml").read_text()))
    assert not [m for m in manifests if m and m.get("kind") == "ConfigMap"], (
        "the enrol ConfigMap must not also be written by hand"
    )


def test_the_rendered_deployment_mounts_the_hashed_name() -> None:
    out = subprocess.run(
        ["kubectl", "kustomize", str(HC)], capture_output=True, text=True, check=True
    ).stdout
    docs = [d for d in yaml.safe_load_all(out) if d]
    cms = [
        d["metadata"]["name"]
        for d in docs
        if d["kind"] == "ConfigMap"
        and d["metadata"]["name"].startswith("healthchecks-enrol-")
    ]
    assert len(cms) == 1, cms
    deploy = next(
        d
        for d in docs
        if d["kind"] == "Deployment" and d["metadata"]["name"] == "healthchecks"
    )
    vols = {v["name"]: v for v in deploy["spec"]["template"]["spec"]["volumes"]}
    assert vols["enrol"]["configMap"]["name"] == cms[0]
