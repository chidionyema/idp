"""The shadow reconciles a platform path on the floor production has, not on a bare cluster.

Incident: 2026-09-27. Once the shadow could clone its head (idp#4488), every PR touching
platform/llm, temporal, epistemic-fabric, unified-memory-server or voice-router failed on
`no matches for kind "ExternalSecret"`, and event-bus's nats on `no PriorityClass platform-batch`.
Production installs both before any workload row (clusters/oke/secrets.yaml, priority-classes).
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import re
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def load_shadow():
    loader = importlib.machinery.SourceFileLoader(
        "idp_shadow", str(REPO / "bin" / "idp-shadow")
    )
    spec = importlib.util.spec_from_loader("idp_shadow", loader)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def test_the_floor_is_production_eso_crds_and_priority_classes(monkeypatch):
    shadow = load_shadow()
    applied = []

    def fake_run(argv, input=None, **kw):
        applied.append(json.loads(input))
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(shadow.subprocess, "run", fake_run)
    monkeypatch.setattr(shadow, "wait_ks", lambda name, deadline: (True, "", []))
    assert shadow.flux_floor(0) == []

    pinned = re.search(
        r"chart: external-secrets\s+version: *(\S+)",
        (REPO / "platform/secrets/external-secrets.yaml").read_text(),
    ).group(1)
    srcs = {
        o["metadata"]["name"]: o["spec"]
        for o in applied
        if o["kind"] == "GitRepository"
    }
    assert srcs["shadow-floor-eso"]["ref"] == {"tag": "v" + pinned}
    ks = {
        o["spec"]["path"]: o["spec"]["sourceRef"]["name"]
        for o in applied
        if o["kind"] == "Kustomization"
    }
    assert ks == {
        "./deploy/crds": "shadow-floor-eso",
        "./config/crd/experimental": "shadow-floor-gateway-api",
        "./config/crd": "shadow-floor-keda-http",
        "./traefik/crds": "shadow-floor-traefik",
        "./libcalico-go/config/crd": "shadow-floor-calico",
        "./platform/priority-classes": "shadow",
    }
    assert (REPO / "platform/priority-classes/priorityclasses.yaml").exists()


def test_the_floor_takes_gateway_api_and_keda_http_crds_at_production_versions(
    monkeypatch,
):
    """2026-09-27 after idp#4510: platform/llm failed on no kind "HTTPRoute", and
    unified-memory-server on no kind "HTTPScaledObject". Production lays both."""
    shadow = load_shadow()
    applied = []
    monkeypatch.setattr(
        shadow.subprocess,
        "run",
        lambda argv, input=None, **kw: (
            applied.append(json.loads(input))
            or subprocess.CompletedProcess(argv, 0, "", "")
        ),
    )
    monkeypatch.setattr(shadow, "wait_ks", lambda name, deadline: (True, "", []))
    assert shadow.flux_floor(0) == []
    srcs = {
        o["metadata"]["name"]: o["spec"]
        for o in applied
        if o["kind"] == "GitRepository"
    }

    ingress = (REPO / "clusters/oke/ingress.yaml").read_text()
    gw_tag = re.search(r"gateway-api\s+ref:\s+tag: *(\S+)", ingress).group(1)
    assert srcs["shadow-floor-gateway-api"]["url"] in ingress
    assert srcs["shadow-floor-gateway-api"]["ref"] == {"tag": gw_tag}
    assert "path: ./config/crd/experimental" in ingress

    keda = (REPO / "platform/keda/keda.yaml").read_text()
    http = re.search(r"chart: keda-add-ons-http\s+version: *(\S+)", keda).group(1)
    assert srcs["shadow-floor-keda-http"]["ref"] == {"tag": "v" + http}
    for spec in srcs.values():
        assert spec["ignore"].startswith("/*\n!/")

    # platform/llm's HTTPRoute is on main; HTTPScaledObject arrives with unified-memory's branch
    assert "kind: HTTPRoute" in (REPO / "platform/llm/httproute.yaml").read_text()


def test_the_floor_takes_traefik_and_calico_crds_at_production_versions(monkeypatch):
    """2026-09-27: platform/llm (idp#4516) failed on no kind "Middleware", and platform/calico/raw
    (idp#4375) on no kind "GlobalNetworkPolicy". Production lays both."""
    shadow = load_shadow()
    applied = []
    monkeypatch.setattr(
        shadow.subprocess,
        "run",
        lambda argv, input=None, **kw: (
            applied.append(json.loads(input))
            or subprocess.CompletedProcess(argv, 0, "", "")
        ),
    )
    monkeypatch.setattr(shadow, "wait_ks", lambda name, deadline: (True, "", []))
    assert shadow.flux_floor(0) == []
    srcs = {
        o["metadata"]["name"]: o["spec"]
        for o in applied
        if o["kind"] == "GitRepository"
    }

    traefik = (REPO / "platform/edge/traefik.yaml").read_text()
    chart = re.search(r"chart: traefik\s+version: *(\S+)", traefik).group(1)
    assert srcs["shadow-floor-traefik"]["ref"] == {"tag": "v" + chart}
    assert srcs["shadow-floor-traefik"]["ignore"] == "/*\n!/traefik/crds/\n"

    calico = (REPO / "platform/calico/raw-migration/calico.yaml").read_text()
    node = re.search(r"calico/node:(v[0-9.]+)", calico).group(1)
    assert srcs["shadow-floor-calico"]["ref"] == {"tag": node}
    assert srcs["shadow-floor-calico"]["ignore"] == "/*\n!/libcalico-go/config/\n"

    # the kinds the two failing rows use, so the floor is the one they need
    assert "kind: Middleware" in (REPO / "platform/llm/edge-manners.yaml").read_text()
    gnp = (REPO / "platform/calico/raw/deny-direct-ai-vendor-egress.yaml").read_text()
    assert "apiVersion: crd.projectcalico.org/v1\nkind: GlobalNetworkSet" in gnp


def test_a_floor_that_does_not_converge_fails_the_run_before_any_path(monkeypatch):
    shadow = load_shadow()
    paths = []
    monkeypatch.setattr(shadow, "have", lambda tool: True)
    monkeypatch.setattr(shadow, "serve_tree", lambda: subprocess.Popen(["true"]))
    monkeypatch.setattr(shadow, "flux_source", lambda head: None)
    monkeypatch.setattr(shadow, "flux_floor", lambda deadline: ["no CRDs"])
    monkeypatch.setattr(
        shadow,
        "flux_kustomization",
        lambda name, path, source="shadow": paths.append(path),
    )
    rc, why = shadow.verify("a" * 40, ["platform/llm"])
    assert (rc, why, paths) == (1, ["no CRDs"], [])
