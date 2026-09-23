"""crew#561: idp#949 changed mac-run on main, Flux applied the ConfigMap, and otto-parity run
33295458987 still executed the old script (`cp ... /tmp/mac-run.id_ed25519: Permission denied`).

The script is mounted with `subPath`, and a subPath mount never receives a ConfigMap update; only a
pod restart does. Reloader (platform/reloader) restarts the pod when an annotation names the
ConfigMap. This pins: every ConfigMap the gateway mounts by subPath is named in that annotation.
"""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
GATEWAY = ROOT / "platform" / "hermes-agent" / "gateway.yaml"


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


def test_every_subpath_configmap_is_named_in_the_reloader_annotation() -> None:
    dep = _deployment()
    mounted = _subpath_configmaps(dep)
    assert "hermes-agent-mac-run" in mounted, (
        "mac-run is no longer a subPath mount: retire this test"
    )
    ann = (
        dep["metadata"]
        .get("annotations", {})
        .get("configmap.reloader.stakater.com/reload", "")
    )
    named = {x.strip() for x in ann.split(",") if x.strip()}
    missing = mounted - named
    assert not missing, (
        f"subPath ConfigMap(s) {sorted(missing)} change on main but the running pod never sees "
        "them: add each to configmap.reloader.stakater.com/reload on the gateway Deployment"
    )
