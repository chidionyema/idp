"""crew#307 follow-up, founder 2026-08-29: after the catalogue namespace was rebuilt a person saw
Traefik's raw "no available server" text. "thats amateur". Every door on the edge -- the store
front, the store API and every platform hostname -- showed the same string whenever its pod
restarted, and none carried edge headers or an access log. These tests keep the edge's manners:
every application rule on every HTTPRoute runs friendly-errors and edge-headers, the status page
exists for each status the middleware rewrites, and Traefik is configured to reach it."""
import glob
import pathlib

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
ROUTE_FILES = sorted(
    set(glob.glob(str(ROOT / "platform/*/httproute.yaml")))
    | {str(ROOT / "platform/backstage/overlays/oke/httproute.yaml")}
)


def _docs(path):
    return [d for d in yaml.safe_load_all(pathlib.Path(path).read_text()) if d]


def _app_rules():
    for f in ROUTE_FILES:
        for d in _docs(f):
            if d.get("kind") != "HTTPRoute":
                continue
            for rule in d["spec"].get("rules", []):
                if "backendRefs" in rule:
                    yield f, d["metadata"]["name"], rule


def test_every_application_rule_answers_errors_with_the_status_page_and_sets_edge_headers():
    seen = 0
    for f, name, rule in _app_rules():
        names = {
            fl["extensionRef"]["name"]
            for fl in rule.get("filters", [])
            if fl.get("type") == "ExtensionRef" and fl["extensionRef"]["kind"] == "Middleware"
        }
        assert {"friendly-errors", "edge-headers"} <= names, f"{f}: rule of {name} lacks {names}"
        seen += 1
    assert seen >= 10, seen


def test_every_route_namespace_carries_both_middlewares_and_wires_them():
    for f in ROUTE_FILES:
        ns = next(d["metadata"]["namespace"] for d in _docs(f) if d.get("kind") == "HTTPRoute")
        mw = pathlib.Path(f).with_name("edge-manners.yaml")
        assert mw.exists(), mw
        kinds = {(d["kind"], d["metadata"]["name"]) for d in _docs(mw)}
        assert {("Middleware", "friendly-errors"), ("Middleware", "edge-headers")} <= kinds, mw
        assert all(d["metadata"]["namespace"] == ns for d in _docs(mw)), mw
        assert "edge-manners.yaml" in (mw.parent / "kustomization.yaml").read_text(), mw.parent


def test_the_status_page_serves_every_status_the_middleware_rewrites():
    docs = _docs(ROOT / "platform/edge/status-page.yaml")
    cm = next(d for d in docs if d["kind"] == "ConfigMap")
    mw = next(d for d in _docs(ROOT / "platform/guacamole/edge-manners.yaml") if d["metadata"]["name"] == "friendly-errors")
    lo, hi = (int(x) for x in mw["spec"]["errors"]["status"][0].split("-"))
    for code in range(lo, hi + 1):
        assert f"{code}.html" in cm["data"], code
        assert "no available server" not in cm["data"][f"{code}.html"]
        assert "starting up" in cm["data"][f"{code}.html"]
    dep = next(d for d in docs if d["kind"] == "Deployment")
    assert dep["spec"]["replicas"] >= 2
    assert dep["spec"]["template"]["spec"]["priorityClassName"] == "infrastructure-critical"
    assert "status-page.yaml" in (ROOT / "platform/edge/kustomization.yaml").read_text()


def test_traefik_can_reach_the_status_page_across_namespaces_and_writes_an_access_log():
    values = next(d for d in _docs(ROOT / "platform/edge/traefik.yaml") if d["kind"] == "HelmRelease")["spec"]["values"]
    assert values["providers"]["kubernetesCRD"]["allowCrossNamespace"] is True
    assert values["accessLog"]["enabled"] is True
    assert values["accessLog"]["format"] == "json"


def test_no_door_advertises_its_web_server():
    for f in glob.glob(str(ROOT / "platform/**/edge-manners.yaml"), recursive=True):
        mw = next(d for d in _docs(f) if d["metadata"]["name"] == "edge-headers")
        h = mw["spec"]["headers"]
        assert h["customResponseHeaders"]["Server"] == ""
        assert h["customResponseHeaders"]["X-Powered-By"] == ""
        assert h["stsSeconds"] >= 31536000 and h["contentTypeNosniff"] is True
