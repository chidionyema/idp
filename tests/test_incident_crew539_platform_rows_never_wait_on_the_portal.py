"""Incident crew#539 (cluster-state 33161593926, 2026-08-28 10:00Z): one stalled catalogue rollout
(Deployment/backstage/catalogue, idp#557) held 15 Flux Kustomizations Not Ready — observability,
temporal, spire, hindsight, keda, monitoring, cluster-state, image-automation — because five rows in
clusters/oke/ carried `dependsOn: [backstage]` and the backstage row has `wait: true` with a 5m
timeout. Founder: "One broken deployment is holding the estate."

The rule: the portal is a consumer of the platform, never a dependency of it. No Flux Kustomization
under clusters/ may depend on `backstage` except `chaos` (its experiments kill portal pods, so it
is the one row that must wait for them to exist). Rung 4.
"""

import pathlib

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
CLUSTERS = ROOT / "clusters"
PORTAL = "backstage"
# The product row (founder 2026-09-03, blueprint phase 1): dns waited on it for a secret it held.
PRODUCT = "prospector-platform"
# The product's own app row rides on its platform row by design; every other row is a platform row.
PRODUCT_ROWS = {"prospector"}
ALLOWED = {"chaos"}


def _docs(path: pathlib.Path):
    try:
        return [d for d in yaml.safe_load_all(path.read_text()) if isinstance(d, dict)]
    except yaml.YAMLError:
        return []


def rows_waiting_on_the_portal(clusters: pathlib.Path = CLUSTERS) -> list[str]:
    """Kustomizations whose dependsOn names the portal row, minus the allow-list."""
    bad = []
    for path in sorted(clusters.rglob("*.yaml")):
        for d in _docs(path):
            if d.get("kind") != "Kustomization" or "toolkit.fluxcd.io" not in str(
                d.get("apiVersion")
            ):
                continue
            name = (d.get("metadata") or {}).get("name")
            deps = {
                x.get("name")
                for x in ((d.get("spec") or {}).get("dependsOn") or [])
                if isinstance(x, dict)
            }
            if PORTAL in deps and name not in ALLOWED:
                bad.append(f"{path.relative_to(clusters)}: {name}")
    return bad


def test_no_platform_row_waits_on_the_portal():
    assert rows_waiting_on_the_portal() == []


def test_chaos_still_waits_on_the_portal():
    """The allow-list is not a silent miss: the one legitimate edge is present."""
    found = {
        (d.get("metadata") or {}).get("name")
        for path in CLUSTERS.rglob("*.yaml")
        for d in _docs(path)
        if d.get("kind") == "Kustomization"
        and PORTAL
        in {
            x.get("name")
            for x in ((d.get("spec") or {}).get("dependsOn") or [])
            if isinstance(x, dict)
        }
    }
    assert found == ALLOWED


def test_detects_a_new_portal_edge(tmp_path):
    (tmp_path / "x.yaml").write_text(
        "apiVersion: kustomize.toolkit.fluxcd.io/v1\nkind: Kustomization\nmetadata:\n  name: spire\n"
        "spec:\n  dependsOn:\n    - name: backstage\n"
    )
    assert rows_waiting_on_the_portal(tmp_path) == ["x.yaml: spire"]


def test_no_platform_row_waits_on_the_product():
    """Founder 2026-09-03 (blueprint phase 1): the dns row waited on prospector-platform because the
    cloudflare-api-token ExternalSecret lived there; a product red held DNS back. The secret rides
    in platform/dns now, and no row may wait on the product row again."""
    bad = []
    for path in sorted((ROOT / "clusters/oke").glob("*.yaml")):
        for d in yaml.safe_load_all(path.read_text()):
            if not isinstance(d, dict) or d.get("kind") != "Kustomization":
                continue
            deps = {
                x.get("name")
                for x in ((d.get("spec") or {}).get("dependsOn") or [])
                if isinstance(x, dict)
            }
            if PRODUCT in deps and d["metadata"]["name"] not in PRODUCT_ROWS:
                bad.append(f"{path.name}: {d['metadata']['name']}")
    assert bad == []
