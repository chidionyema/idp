"""crew#561, 2026-08-30. Otto could not run a command on the founder's Mac for three days, and the
whole of it was that the fix kept being merged into something the pod never read.

mac-run is mounted with `subPath`, and Kubernetes never updates a subPath mount in place: only a
pod restart does. idp#949 (05:45:19Z) rewrote the script so it uses the mounted key directly and
copies nothing. Flux applied it. otto-parity 33295694219 at 05:59Z still printed
`cp: cannot create regular file '/tmp/mac-run.id_ed25519': Permission denied` -- a line the new
script does not contain, because the pod was still running the old one.

idp#955 (06:13:45Z) hung a Reloader annotation naming the ConfigMap off the Deployment. That could
not work either, and this is the part worth pinning: Reloader restarts a pod when it OBSERVES the
ConfigMap change. The change had already happened, 28 minutes before the annotation existed. There
was nothing left to observe. `Kustomization/hermes-agent` reconciled green at 06:45Z, and
otto-parity 33297784151 at 06:53Z printed the same `cp` line.

A content hash in the name is what actually rolls the pod, because it changes the Deployment's own
spec rather than asking a controller to notice something. Same fix as platform/healthchecks
(idp#962). Fault class: fix-proved-on-the-wrong-surface -- three receipts said "merged and applied"
and none of them read the running pod.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
HERMES = ROOT / "platform" / "hermes-agent"
GATEWAY = HERMES / "gateway.yaml"


def _deployment() -> dict:
    for doc in yaml.safe_load_all(GATEWAY.read_text()):
        if doc and doc.get("kind") == "Deployment":
            return doc
    raise AssertionError("no Deployment in gateway.yaml")


def _subpath_configmaps(dep: dict) -> set[str]:
    spec = dep["spec"]["template"]["spec"]
    by_volume = {
        v["name"]: v["configMap"]["name"]
        for v in spec.get("volumes", [])
        if "configMap" in v
    }
    out = set()
    for c in spec.get("containers", []) + spec.get("initContainers", []):
        for m in c.get("volumeMounts", []):
            if m.get("subPath") and m["name"] in by_volume:
                out.add(by_volume[m["name"]])
    return out


def test_every_subpath_configmap_the_gateway_mounts_is_generated() -> None:
    """A hand-written ConfigMap behind a subPath mount is the crew#561 outage, exactly."""
    kz = yaml.safe_load((HERMES / "kustomization.yaml").read_text())
    generated = {g["name"] for g in kz.get("configMapGenerator", [])}
    mounted = _subpath_configmaps(_deployment())
    assert "hermes-agent-mac-run" in mounted, (
        "mac-run is no longer a subPath mount: retire this test"
    )
    ungenerated = mounted - generated
    assert not ungenerated, (
        f"subPath ConfigMap(s) {sorted(ungenerated)} are written by hand, so their names never "
        "change and the pod keeps the copy it started with. Render them with a configMapGenerator."
    )
    assert "mac-run.yaml" not in kz["resources"], (
        "the hand-written mac-run ConfigMap is back alongside the generator"
    )
    assert (HERMES / "mac-run.tpl").exists()
    assert not (HERMES / "mac-run.yaml").exists()


def test_the_script_still_uses_the_mounted_key_and_copies_nothing() -> None:
    """idp#949's actual content, pinned where a reader can see it (the `cp` is the outage)."""
    script = (HERMES / "mac-run.tpl").read_text()
    assert "\ncp " not in script and " cp " not in script, (
        "mac-run copies the key again; ssh reads the mount directly (row key-direct)"
    )
    assert 'exec ssh -i "$src"' in script


def test_the_rendered_deployment_mounts_the_hashed_name() -> None:
    out = subprocess.run(
        ["kubectl", "kustomize", str(HERMES)],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    docs = [d for d in yaml.safe_load_all(out) if d]
    hashed = [
        d["metadata"]["name"]
        for d in docs
        if d["kind"] == "ConfigMap"
        and d["metadata"]["name"].startswith("hermes-agent-mac-run-")
    ]
    assert len(hashed) == 1, hashed
    deploy = next(
        d
        for d in docs
        if d["kind"] == "Deployment" and d["metadata"]["name"] == "hermes-agent-gateway"
    )
    vols = {v["name"]: v for v in deploy["spec"]["template"]["spec"]["volumes"]}
    assert vols["mac-run"]["configMap"]["name"] == hashed[0]


def test_a_reloader_annotation_is_not_the_guard_for_mac_run() -> None:
    """idp#955's annotation is removed on purpose: a hashed name can never match a static one."""
    ann = (
        _deployment()["metadata"]
        .get("annotations", {})
        .get("configmap.reloader.stakater.com/reload", "")
    )
    assert "hermes-agent-mac-run" not in ann, (
        "a Reloader annotation naming mac-run is dead weight once the name carries a hash, and it "
        "reads as a guard while guarding nothing (crew#561, otto-parity 33297784151)"
    )
