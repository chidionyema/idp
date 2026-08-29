"""idp#648 (2026-08-29): the backstage Namespace moved between Flux rows, the old prune:true row
garbage-collected it, and it sat Terminating for 16+ min with the catalogue 404 (oke-check run
33226089358). Three fences, one incident: the namespace can never be pruned again; diagnose
prints why a namespace is Terminating; a named playbook clears what holds it."""

import re
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_every_platform_namespace_object_is_never_pruned():
    bad = []
    for f in ROOT.glob("platform/*/namespace/base/namespace.yaml"):
        for doc in yaml.safe_load_all(f.read_text()):
            if doc and doc.get("kind") == "Namespace":
                labels = (doc.get("metadata") or {}).get("labels") or {}
                if labels.get("kustomize.toolkit.fluxcd.io/prune") != "disabled":
                    bad.append(str(f.relative_to(ROOT)))
    assert not bad, f"a Namespace that moves rows gets pruned by the old row: {bad}"


def test_namespace_unstick_is_a_named_playbook_in_script_and_workflow():
    names = subprocess.run(
        [str(ROOT / "bin/idp-oke-break-glass"), "--list"], capture_output=True, text=True, check=True
    ).stdout.split()
    assert "namespace-unstick" in names
    wf = yaml.safe_load((ROOT / ".github/workflows/oke-check.yml").read_text())
    options = wf[True]["workflow_dispatch"]["inputs"]["playbook"]["options"]
    assert "namespace-unstick" in options


def test_diagnose_prints_why_a_namespace_is_terminating():
    src = (ROOT / "bin/idp-oke-break-glass").read_text()
    body = src[src.index("pb_diagnose()") : src.index("\npb_", src.index("pb_diagnose()") + 1)]
    assert "namespaces-terminating" in body
    assert re.search(r'phase=="Terminating".*status\.conditions', body), "the condition, not just the name"


def test_unstick_never_forces_the_namespace_finalizer_itself():
    src = (ROOT / "bin/idp-oke-break-glass").read_text()
    body = src[src.index("pb_namespace_unstick()") : src.index("# node-drain:")]
    assert "finalize" not in body.replace("finalizers", ""), "no `kubectl replace --raw .../finalize`"
    assert '"finalizers":null' in body
    assert "flux reconcile kustomization backstage-namespace" in body
