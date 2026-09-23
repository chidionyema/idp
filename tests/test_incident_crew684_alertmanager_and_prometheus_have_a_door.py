"""crew#684, founder 2026-08-30 08:0xZ: "first i need all cluster monitoring tools now ... top right
of screen backstage ... all monitoring tools".

The class of mistake: a tool was installed as plumbing and never given a door. kube-prometheus-stack
landed (crew#539) as the alert evaluator; the catalogue said "no public address yet" on Alertmanager
and Prometheus, the Tools page showed a git link instead of Open, and for 43 hours a probe of
alertmanager.<zone> and prometheus.<zone> answered nothing while everyone read it as an outage.
This test refuses that state: every monitoring surface in the Watch group has an Open link on a
host, that host has an HTTPRoute behind the one login, the probe watches it, and the login drill
grades it. The listeners are prospector's (deploy/k8s/base/edge.yaml, https-alertmanager /
https-prometheus); their test lives there.
"""

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "backstage/founder/catalog-info.yaml"
ROUTES = ROOT / "platform/monitoring/httproute.yaml"
NAMESPACE = ROOT / "platform/monitoring/namespace.yaml"
KUSTOMIZATION = ROOT / "platform/monitoring/kustomization.yaml"
PROBE = ROOT / "platform/monitoring/rules/founder-surfaces-probe.yaml"
DRILL = ROOT / "bin/idp-login-drill"

DOORS = {
    "founder-alerts": ("alertmanager", "kps-alertmanager", 9093),
    "founder-metrics": ("prometheus", "kps-prometheus", 9090),
}


def _entities() -> dict[str, dict]:
    return {
        d["metadata"]["name"]: d
        for d in yaml.safe_load_all(CATALOG.read_text())
        if d and d.get("spec", {}).get("type") == "founder-surface"
    }


def _routes() -> dict[str, dict]:
    return {
        d["metadata"]["name"]: d for d in yaml.safe_load_all(ROUTES.read_text()) if d
    }


def test_both_monitoring_tools_are_watch_doors_with_an_open_link_and_no_no_address_tag():
    ents = _entities()
    for name, (host, _, _) in DOORS.items():
        e = ents[name]
        assert e["metadata"]["annotations"]["estate/group"] == "Watch", name
        assert "no-address" not in e["metadata"].get("tags", []), name
        opens = [l for l in e["metadata"]["links"] if l["title"] == "Open"]
        assert opens and opens[0]["url"] == f"https://{host}.${{ESTATE_ZONE}}", (
            name,
            opens,
        )
        assert "no public address" not in e["metadata"]["description"], name


def test_each_door_is_an_httproute_behind_the_one_login_on_its_own_listener():
    routes = _routes()
    for entity, (host, svc, port) in DOORS.items():
        r = routes[host]
        assert r["metadata"]["labels"]["backstage.io/kubernetes-id"] == entity
        assert r["metadata"]["namespace"] == "monitoring"
        assert r["spec"]["parentRefs"][0]["sectionName"] == f"https-{host}"
        assert r["spec"]["hostnames"] == [f"{host}.${{ESTATE_ZONE}}"]
        oauth, app = r["spec"]["rules"]
        assert oauth["matches"][0]["path"]["value"] == "/oauth2/"
        assert oauth["backendRefs"][0]["name"] == "oauth2-proxy"
        assert app["filters"][0]["extensionRef"]["name"] == "login-forward-auth"
        assert app["backendRefs"] == [{"name": svc, "port": port}]


def test_the_namespace_may_attach_to_the_edge_and_the_row_ships_the_routes():
    ns = yaml.safe_load(NAMESPACE.read_text())
    assert ns["metadata"]["labels"]["idp.estate/edge-attach"] == "true"
    assert "httproute.yaml" in yaml.safe_load(KUSTOMIZATION.read_text())["resources"]


def test_the_probe_watches_both_doors_and_the_login_drill_grades_them():
    targets = yaml.safe_load(PROBE.read_text())["spec"]["targets"]["staticConfig"][
        "static"
    ]
    drill = DRILL.read_text()
    for host, _, _ in DOORS.values():
        assert f"https://{host}.${{ESTATE_ZONE}}" in targets, host
        assert re.search(rf'"{host}": f"https://{host}\.\{{ZONE\}}/"', drill), host


def test_incident_crew684_a_new_door_is_not_graded_dead_before_it_merges_and_the_chart_pods_are_waived():
    """idp#977 run 33300xxxxxx: founder-links probed alertmanager/prometheus on the pull request and
    read 000 -- the door cannot exist before the PR merges. On pull_request a link absent from
    main's catalogue is NEW; every link is probed on schedule. The two pods are chart-rendered
    StatefulSets, so the availability gate is told so by name instead of going BLIND."""
    wf = (ROOT / ".github/workflows/oke-check.yml").read_text()
    i = wf.index("  founder-links:")
    job = wf[i : wf.index("lycheeverse/lychee-action", i)]
    assert 'github.event_name }}" = pull_request' in job
    assert "FETCH_HEAD:backstage/founder/catalog-info.yaml" in job
    assert "comm -12 founder-links.txt main-links.txt" in job, (
        "only links on main are probed on a PR"
    )
    assert "graded after merge" in job
    av = yaml.safe_load((ROOT / "platform/availability.yaml").read_text())
    waived = {w["surface"]: w for w in av["waivers"]}
    for s in ("monitoring/kps-alertmanager", "monitoring/kps-prometheus"):
        assert waived[s]["issue"] and "kube-prometheus-stack" in waived[s]["reason"], s
    manners = ROOT / "platform/monitoring/edge-manners.yaml"
    kinds = {
        (d["kind"], d["metadata"]["name"], d["metadata"]["namespace"])
        for d in yaml.safe_load_all(manners.read_text())
    }
    assert {
        ("Middleware", "friendly-errors", "monitoring"),
        ("Middleware", "edge-headers", "monitoring"),
    } <= kinds
    assert (
        "edge-manners.yaml"
        in (ROOT / "platform/monitoring/kustomization.yaml").read_text()
    )
