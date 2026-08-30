"""crew#684 CP1: a portal route is only finished when four lists agree.

The class of mistake (idp#914, 2026-08-30): the /tools route shipped with its founder-surface
entity but not its blackbox probe target, and CI went red two suites later. A route the
founder can open lives in four places at once — the page module, the founder-surface
catalogue (crew#401 gate), the login drill's PUBLISHED table, and the founder-surfaces
blackbox probe — and this test refuses a route that is missing from any of them.

It also pins CP1's own substance: the Ops page reads the cluster through the Kubernetes
plugin's proxy (nodes, pods, Kustomizations, HelmReleases), never a script, and the
decision matrix carries the row that chose it.
"""

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
HOME = ROOT / "backstage/packages/app/src/modules/home"
MODULE = HOME / "homeModule.tsx"
CATALOG = ROOT / "backstage/founder/catalog-info.yaml"
DRILL = ROOT / "bin/idp-login-drill"
PROBE = ROOT / "platform/monitoring/rules/founder-surfaces-probe.yaml"
MATRIX = ROOT / "docs/decisions/decision-matrix.yaml"


def portal_routes() -> set[str]:
    """Every PageBlueprint path in the home module, without its leading slash; `/` is the front page."""
    paths = re.findall(r"path:\s*'(/[^']*)'", MODULE.read_text())
    return {p.strip("/") for p in paths if p != "/"}


def door_paths() -> set[str]:
    out = set()
    for doc in yaml.safe_load_all(CATALOG.read_text()):
        if not doc or doc.get("spec", {}).get("type") != "founder-surface":
            continue
        for link in doc.get("metadata", {}).get("links", []):
            m = re.match(
                r"https://catalogue\.\$\{ESTATE_ZONE\}/([^/#?]+)$", link.get("url", "")
            )
            if m:
                out.add(m.group(1))
    return out


def drill_paths() -> set[str]:
    block = re.search(r"PUBLISHED = \((.*?)\n    \)", DRILL.read_text(), re.S)
    assert block, "drill lost its PUBLISHED table"
    return set(re.findall(r'\(\s*"([^"]+)",\s*"text=', block.group(1)))


def probe_paths() -> set[str]:
    probe = yaml.safe_load(PROBE.read_text())
    targets = probe["spec"]["targets"]["staticConfig"]["static"]
    return {
        m.group(1)
        for t in targets
        if (m := re.match(r"https://catalogue\.\$\{ESTATE_ZONE\}/([^/#?]+)$", t))
    }


def test_every_portal_route_is_a_door_a_drill_row_and_a_probe_target():
    routes = portal_routes()
    assert {"tools", "ops"} <= routes, routes
    missing = {
        "founder-surface entity link": routes - door_paths(),
        "login drill PUBLISHED row": routes - drill_paths(),
        "founder-surfaces probe target": routes - probe_paths(),
    }
    assert not any(missing.values()), missing


def test_the_ops_page_reads_the_cluster_through_the_kubernetes_plugin_never_a_script():
    hook = (HOME / "useClusterHealth.ts").read_text()
    assert "kubernetesApiRef" in hook and "kubernetesApi.proxy" in hook
    for path in (
        "/api/v1/nodes",
        "/api/v1/pods",
        "/apis/kustomize.toolkit.fluxcd.io/v1/kustomizations",
        "/apis/helm.toolkit.fluxcd.io/v2/helmreleases",
    ):
        assert path in hook, path
    page = (HOME / "Ops.tsx").read_text()
    assert "The cluster right now" in page, "the drill grades the page on this sentence"
    assert re.search(r'\("ops",\s*"text=The cluster right now"\)', DRILL.read_text())


def test_the_matrix_carries_the_decision_and_it_is_the_kubernetes_plugin():
    matrix = yaml.safe_load(MATRIX.read_text())
    (row,) = [
        d for d in matrix["decisions"] if d["slug"] == "ops-dashboard-cluster-health"
    ]
    assert row["status"] == "decided"
    assert row["decision"] == "kubernetes-plugin-proxy"
    assert {
        "kubernetes-plugin-proxy",
        "headlamp",
        "weaveworks-flux-plugin",
        "estate-mcp",
    } <= set(row["candidates"])
