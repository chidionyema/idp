"""crew#758 (founder, 2026-08-31: "this should be the backstage ... add it to backstage now",
asked while his agent's logs, monitoring and tracing were scattered across URLs and a laptop
cluster session). A layer's observability is opened from its catalogue page: every platform
Component carries the estate's logs-and-metrics door, and exactly the layers whose own
manifests project LANGFUSE_ keys carry the model-traces door -- a link that promises traces a
workload never sends is the silent-green class. The hostnames are read from the observability
layer's route manifests by the generator, never typed as literals (LAW 46).
"""

import glob
import os

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLUSTER = os.environ.get("CLUSTER", "oke")
OUT = os.path.join(ROOT, "backstage", "platform", "catalog-info.yaml")


def _components():
    return [
        d for d in yaml.safe_load_all(open(OUT)) if d and d.get("kind") == "Component"
    ]


def _layer_paths():
    paths = {}
    for f in glob.glob(os.path.join(ROOT, "clusters", CLUSTER, "*.yaml")):
        for d in yaml.safe_load_all(open(f)):
            if (
                d
                and d.get("kind") == "Kustomization"
                and str(d.get("apiVersion", "")).startswith("kustomize.toolkit")
            ):
                paths[d["metadata"]["name"]] = os.path.normpath(
                    os.path.join(ROOT, d["spec"].get("path", "./"))
                )
    return paths


def test_every_layer_component_carries_the_logs_door():
    for c in _components():
        links = c["metadata"].get("links") or []
        urls = [link["url"] for link in links]
        assert any(u.startswith("https://signoz.") for u in urls), (
            f"{c['metadata']['name']} has no logs-and-metrics link; its page answers nothing when it breaks"
        )
        for u in urls:
            assert u.startswith("https://"), (
                f"{c['metadata']['name']} carries a non-https link: {u}"
            )


def test_traces_door_exists_exactly_where_traces_are_sent():
    paths = _layer_paths()
    sends = set()
    for name, src in paths.items():
        for f in sorted(glob.glob(os.path.join(src, "*.yaml"))):
            try:
                if "LANGFUSE_" in open(f).read():
                    sends.add(name)
                    break
            except OSError:
                continue
    linked = set()
    for c in _components():
        urls = [link["url"] for link in c["metadata"].get("links") or []]
        if any(u.startswith("https://langfuse.") for u in urls):
            linked.add(c["metadata"]["annotations"]["estate/flux-kustomization"])
    assert linked == sends, (
        f"traces links must match the layers that send traces -- link with no traces: "
        f"{sorted(linked - sends)}; traces with no link: {sorted(sends - linked)}"
    )
