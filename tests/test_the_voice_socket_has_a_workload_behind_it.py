"""Defect 12 of the face audit: the socket the Face page opens has something behind it.

`backstage/packages/app/src/modules/home/useVoiceRouter.ts` has been deployed for months and
opens `wss://<page host>/voice/ws` on the public path. Measured 2026-10-25, the voice-router
namespace held exactly one Deployment -- `voice-router-director`, the /fleet cinema narrator,
which answers /healthz and nothing else -- so /voice/ws fell to the catalogue's public
static-asset rule and the catalogue pod answered 404. The page could hear the founder and had
no one to answer.

This test grades the three things that make the socket reachable, as the cluster receives them:

  1. the route sends exactly `Exact /voice/ws` to Service `voice-router` port 8080 in the
     `voice-router` namespace -- not the catalogue pod, and not a prefix that would swallow
     /voice/turns (which carries conversation text);
  2. that Service selects a Deployment whose container listens on 8080 and does NOT set
     `VOICE_MODE=director` -- the binary's switch (cmd/voice-router/main.go): unset is the
     streaming router, `director` is the narrator. A narrator behind the Face's socket is the
     same 404 with a pod that looks Ready;
  3. the ReferenceGrant admits the backstage HTTPRoute to that Service, because Gateway API
     refuses a cross-namespace backendRef without the target namespace's consent, and the
     spoken-intent hop is declared on both sides of the fence (audit S7: a spoken word and a
     tap must not take two different doors).

Every failure names the file that has to change. There is no skip: a missing manifest is a
failure, not an absence of evidence.
"""

from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
ROUTE = REPO_ROOT / "platform" / "backstage" / "overlays" / "oke" / "httproute.yaml"
DEPLOY = REPO_ROOT / "platform" / "voice-router" / "deploy"
ALLOWANCES = REPO_ROOT / "platform" / "ns-fences" / "allowances.yaml"

SOCKET_PATH = "/voice/ws"


def _docs(path: Path) -> list[dict]:
    assert path.is_file(), (
        f"{path.relative_to(REPO_ROOT)} is missing. The router lane's manifests are the proof "
        "this test grades; without the file there is no socket and no gate."
    )
    return [d for d in yaml.safe_load_all(path.read_text()) if isinstance(d, dict)]


def _socket_rule() -> dict:
    routes = [d for d in _docs(ROUTE) if d.get("kind") == "HTTPRoute"]
    assert routes, f"no HTTPRoute document in {ROUTE.name}"
    rules = [r for route in routes for r in (route.get("spec", {}).get("rules") or [])]
    exact = [
        r
        for r in rules
        if any(
            m.get("path", {}).get("type") == "Exact"
            and m.get("path", {}).get("value") == SOCKET_PATH
            for m in (r.get("matches") or [])
        )
    ]
    assert exact, (
        f"no rule matches `Exact {SOCKET_PATH}` in {ROUTE.name}. The Face's streaming voice "
        "opens that path and falls through to the catalogue's static-asset rule without it "
        "(measured 2026-10-25: 404)."
    )
    assert len(exact) == 1, (
        f"{len(exact)} rules match `Exact {SOCKET_PATH}`; Gateway API refuses no one, so the "
        "first wins and the second is a comment pretending to be a rule."
    )
    return exact[0]


def _backend(rule: dict) -> dict:
    refs = rule.get("backendRefs") or []
    assert len(refs) == 1, (
        f"the {SOCKET_PATH} rule has {len(refs)} backendRefs. One socket, one backend: a second "
        "ref is a silent second answer to the same connection."
    )
    return refs[0]


def _router_workload() -> tuple[dict, dict]:
    deploy = [d for d in _docs(DEPLOY / "router.yaml") if d.get("kind") == "Deployment"]
    assert len(deploy) == 1, (
        f"expected exactly one Deployment in {DEPLOY.relative_to(REPO_ROOT)}/router.yaml, "
        f"found {len(deploy)}. Every other Deployment in this namespace is the narrator "
        "(director.yaml)."
    )
    services = [d for d in _docs(DEPLOY / "router.yaml") if d.get("kind") == "Service"]
    assert len(services) == 1, (
        "router.yaml must carry exactly one Service for the route to name"
    )
    return deploy[0], services[0]


def test_the_face_socket_is_routed_to_the_router_not_the_catalogue() -> None:
    backend = _backend(_socket_rule())
    assert backend.get("name") == "voice-router", (
        f"the {SOCKET_PATH} rule points at {backend.get('name')!r}. Only the streaming router "
        "answers a websocket; the catalogue pod answers 404 (the measured defect)."
    )
    assert backend.get("namespace") == "voice-router", (
        "a backendRef without the router's namespace resolves in backstage, where no such "
        "Service exists -- the route would be Accepted and the socket would 500."
    )
    assert int(backend.get("port") or 0) == 8080, (
        f"port {backend.get('port')!r}: the router listens on 8080 (VOICE_ADDR in deploy/router.yaml)."
    )


def test_a_deployment_that_is_the_router_answers_that_service() -> None:
    deploy, service = _router_workload()
    pod = deploy["spec"]["template"]
    labels = pod["metadata"]["labels"]
    selector = service["spec"]["selector"]
    assert all(labels.get(k) == v for k, v in selector.items()), (
        "the Service selector does not match the Deployment's pod labels: the Service has no "
        "endpoints and the route 503s with a healthy-looking pod next to it. "
        f"selector={selector} labels={labels}"
    )

    containers = pod["spec"]["containers"]
    router = [
        c
        for c in containers
        if any(p.get("containerPort") == 8080 for p in c.get("ports") or [])
    ]
    assert router, (
        "no container in the router Deployment declares containerPort 8080; the Service's "
        "targetPort `http` resolves to nothing."
    )
    env = {e["name"]: e.get("value") for e in router[0].get("env") or []}
    assert env.get("VOICE_MODE") != "director", (
        "VOICE_MODE=director in the socket's Deployment runs the /fleet narrator "
        "(cmd/voice-router/main.go), which serves no /voice/ws. The switch must stay unset here."
    )
    assert env.get("VOICE_INTENT_URL"), (
        "VOICE_INTENT_URL is unset: an utterance can never name an estate intent, which is the "
        "whole of audit S7 (a spoken word takes the same door as a tap)."
    )
    assert env["VOICE_INTENT_URL"].startswith(
        "http://fleetview-voice.backstage.svc.cluster.local:"
    ), (
        f"VOICE_INTENT_URL={env['VOICE_INTENT_URL']!r}: it must be the in-cluster fleetview "
        "voice Service, the same POST /voice/intent the Deck's buttons reach through the edge "
        "(platform/backstage/overlays/oke/httproute.yaml)."
    )


def test_the_route_may_reach_across_the_namespace_boundary() -> None:
    grants = [
        d for d in _docs(DEPLOY / "router.yaml") if d.get("kind") == "ReferenceGrant"
    ]
    assert grants, (
        "no ReferenceGrant in router.yaml: Gateway API refuses a backendRef into another "
        "namespace without the target namespace's consent, so the rule above is Accepted and "
        "the socket never resolves."
    )
    grant = grants[0]
    assert grant["metadata"]["namespace"] == "voice-router"
    froms = {(f.get("kind"), f.get("namespace")) for f in grant["spec"]["from"]}
    assert ("HTTPRoute", "backstage") in froms, (
        f"the grant admits {sorted(froms)}; the socket's route lives in backstage."
    )
    tos = {(t.get("kind"), t.get("name")) for t in grant["spec"]["to"]}
    assert ("Service", "voice-router") in tos, (
        f"the grant admits {sorted(tos)}, not the Service."
    )


def test_the_fence_names_both_halves_of_the_intent_hop() -> None:
    """Audit S7 on the wire: the router dials backstage, and backstage admits the router.

    The estate has been cut three times by a declaration on one side only (hindsight, cyrus,
    meridian in allowances.yaml's own comments). `bin/idp-ns-fence-gen` refuses a one-sided flow
    by name; this test states the specific hop so its removal is a failure with a reason rather
    than a generic "a flow is one-sided".
    """
    flows = yaml.safe_load(ALLOWANCES.read_text())["flows"]
    router = flows.get("voice-router") or {}
    backstage = flows.get("backstage") or {}
    assert "backstage" in (router.get("egress") or []), (
        "voice-router does not declare egress to backstage: its VOICE_INTENT_URL times out at "
        "the fence and a spoken utterance silently becomes a question the brain answers."
    )
    assert "voice-router" in (backstage.get("ingress_from") or []), (
        "backstage does not admit voice-router: the other half of the same hop."
    )
