"""crew#307, 2026-08-28. The founder opened the portal and his surfaces were gone.

The catalogue Deployment mounted the founder-catalog ConfigMap at /estate/founder, nested inside
the /estate ConfigMap mount. A ConfigMap volume is read-only, so the kubelet cannot create the
`founder` directory inside it: the new pod never started, the rollout stalled from 2026-08-27
16:05, and the portal kept serving the old ReplicaSet -- an image whose app-config never declared
the location. Flux reported it every ten minutes ("health check failed ... Deployment/backstage/
catalogue status: 'Failed'", flux-events runs 33157104551, 33157772740) and nothing read it.

The class of mistake, not the instance: any volumeMount whose path sits inside another mount
backed by a ConfigMap, Secret or DownwardAPI volume. Every rendered overlay in the repository is
walked, so a second one cannot be written anywhere. The fix is a projected volume with an
items[].path that carries the subdirectory.
"""
import subprocess
import pathlib
import yaml
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
OVERLAYS = sorted(p.parent for p in ROOT.glob("platform/*/overlays/*/kustomization.yaml"))
READ_ONLY_SOURCES = ("configMap", "secret", "downwardAPI")


def _render(overlay):
    out = subprocess.run(["kubectl", "kustomize", str(overlay)], capture_output=True, text=True)
    if out.returncode != 0:
        pytest.skip(f"{overlay.relative_to(ROOT)} does not render here: {out.stderr.strip()[:200]}")
    return [d for d in yaml.safe_load_all(out.stdout) if d]


def _pod_specs(docs):
    for d in docs:
        spec = (d.get("spec", {}).get("template", {}) or {}).get("spec")
        if spec:
            yield d["kind"], d["metadata"]["name"], spec


@pytest.mark.parametrize("overlay", OVERLAYS, ids=lambda p: str(p.relative_to(ROOT)))
def test_no_volume_mount_is_nested_inside_a_read_only_volume(overlay):
    for kind, name, spec in _pod_specs(_render(overlay)):
        kinds = {}
        for v in spec.get("volumes", []):
            for src in READ_ONLY_SOURCES:
                if src in v:
                    kinds[v["name"]] = src
        for container in spec.get("containers", []) + spec.get("initContainers", []):
            mounts = [(m["mountPath"].rstrip("/"), m["name"]) for m in container.get("volumeMounts", [])]
            for path, vol in mounts:
                for outer_path, outer_vol in mounts:
                    if outer_path == path or not path.startswith(outer_path + "/"):
                        continue
                    src = kinds.get(outer_vol)
                    assert src is None, (
                        f"{kind}/{name}: volumeMount {path} ({vol}) is nested inside {outer_path} "
                        f"({outer_vol}), a {src} volume the kubelet mounts read-only. The pod will "
                        f"not start. Use one projected volume whose items[].path carries the "
                        f"subdirectory (crew#307)."
                    )
