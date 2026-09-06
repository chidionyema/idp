"""Binds features/gates/front-door-login.feature (ADR 0007, crew#269, crew#297). The step parses every
YAML document under platform/ for real: no user database, no Authelia, oauth2-proxy in front of every route."""

import re
from pathlib import Path

import pytest
import yaml
from pytest_bdd import given, scenarios, then

scenarios("features/gates/front-door-login.feature")

IDP = Path(__file__).resolve().parents[3]
PLATFORM = IDP / "platform"


def api_key_enforced(cfg: str) -> bool:
    """True when an agentgateway config carries a strict apiKey policy with a hashed key: the
    two-part proof an `idp.estate/auth: api-key` route must show (crew#458)."""
    return "apiKey:" in cfg and "mode: strict" in cfg and "keyHash: sha256:" in cfg


def _docs() -> list[tuple[Path, dict]]:
    out = []
    for p in sorted(PLATFORM.rglob("*.y*ml")):
        try:
            docs = list(yaml.safe_load_all(p.read_text()))
        except yaml.YAMLError:
            continue  # templates Flux substitutes; nothing here is a Middleware or ExternalSecret
        out.extend((p, d) for d in docs if isinstance(d, dict) and "kind" in d)
    return out


@pytest.fixture
def state() -> dict:
    return {}


@given("every file under platform/")
def _platform(state: dict) -> None:
    state["docs"] = _docs()
    assert state["docs"], "platform/ holds no Kubernetes manifest"


@then("no ExternalSecret renders a users file and no ForwardAuth points at authelia")
def _no_user_db(state: dict) -> None:
    for p, d in state["docs"]:
        if d["kind"] == "ExternalSecret":
            keys = [
                str(x.get("secretKey", ""))
                + str(x.get("remoteRef", {}).get("property", ""))
                for x in d.get("spec", {}).get("data", [])
            ]
            keys += list(
                (
                    d.get("spec", {}).get("target", {}).get("template", {}).get("data")
                    or {}
                ).keys()
            )
            # crew#516 CP5: the one `users` key allowed is the htpasswd line a basicAuth Middleware in
            # the same file reads for a route annotated edge-basic-auth (one program credential,
            # written by platform/oci/otlp-ingest.tf, not a person's password).
            readers = {
                str(m.get("spec", {}).get("basicAuth", {}).get("secret", ""))
                for pp, m in state["docs"]
                if pp == p and m["kind"] == "Middleware"
            }
            if d["metadata"]["name"] not in readers:
                assert not any("users" in k.lower() for k in keys), (
                    f"{p}: {d['metadata']['name']} renders a users file"
                )
        if d["kind"] == "Middleware":
            addr = str(d.get("spec", {}).get("forwardAuth", {}).get("address", ""))
            assert "authelia" not in addr, (
                f"{p}: {d['metadata']['name']} forwards auth to authelia"
            )


@then(
    "every route outside identity is behind oauth2-proxy, or is a machine API whose own config proves a bearer master key"
)
def _oauth2_proxy_in_front(state: dict) -> None:
    middlewares = {
        d["metadata"]["name"]: str(
            d.get("spec", {}).get("forwardAuth", {}).get("address", "")
        )
        for _, d in state["docs"]
        if d["kind"] == "Middleware"
    }
    routes = [
        (p, d)
        for p, d in state["docs"]
        if d["kind"] == "HTTPRoute" and p.relative_to(PLATFORM).parts[0] != "identity"
    ]
    assert routes, "no HTTPRoute outside platform/identity"
    for p, d in routes:
        refs = [
            f.get("extensionRef", {}).get("name")
            for r in d.get("spec", {}).get("rules", [])
            for f in r.get("filters", [])
        ]
        if any("oauth2-proxy" in middlewares.get(n, "") for n in refs):
            continue
        # A machine API (the model router, crew#284) cannot sit behind a browser login. It may skip
        # oauth2-proxy only when it says so on the route AND its own config shows the key is enforced;
        # the annotation alone is a label, and a label is not a proof.
        auth = (d["metadata"].get("annotations") or {}).get("idp.estate/auth")
        if auth == "langfuse-project-keys":
            # The trace store's public API (crew#325): Langfuse enforces the project keys on
            # /api/public/, so the route may expose that path and nothing else.
            paths = [
                m.get("path", {})
                for r in d["spec"]["rules"]
                for m in r.get("matches", [])
            ]
            # crew#503: /api/auth/ is next-auth (OIDC signin/callback/session); password sign-in is off.
            open_paths = (
                {"type": "PathPrefix", "value": "/api/public/"},
                {"type": "PathPrefix", "value": "/api/auth/"},
            )
            assert paths and all(x in open_paths for x in paths), (
                f"{p}: langfuse-project-keys route exposes {paths}"
            )
            keys = (p.parent / "langfuse.yaml").read_text()
            assert (
                "langfuse-init-public-key" in keys
                and "langfuse-init-secret-key" in keys
            ), f"{p}: langfuse.yaml pulls no project keys"
            continue
        if auth == "api-key":
            # The MCP gateway (crew#458): agentgateway enforces the key itself, and the proof is a
            # strict apiKey policy with a hashed key in the config that sits beside the route.
            gw = p.parent / "agentgateway.yaml"
            assert gw.exists() and api_key_enforced(gw.read_text()), (
                f"{p}: annotated api-key but {gw} enforces no strict apiKey"
            )
            continue
        if auth == "signoz-service-account-key":
            # The log store's dashboards API (crew#631 CP9, idp#1050): SigNoz enforces its own
            # service-account key on /api/v2/dashboards, so the route may expose that path and
            # nothing else, and the prover beside it must measure the refusal with no key.
            paths = [
                m.get("path", {})
                for r in d["spec"]["rules"]
                for m in r.get("matches", [])
            ]
            assert paths and all(
                x == {"type": "PathPrefix", "value": "/api/v2/dashboards"}
                for x in paths
            ), f"{p}: signoz-service-account-key route exposes {paths}"
            probe = (IDP / "probes" / "signoz.py").read_text()
            assert (
                'KEY_HEADER = "SIGNOZ-API-KEY"' in probe
                and "l2.NEGATIVE.no_key_is_refused" in probe
            ), (
                f"{p}: annotated signoz-service-account-key but probes/signoz.py measures no refusal"
            )
            continue
        if auth == "healthchecks-ping-key":
            # The job monitor's ping path (crew#177): the jobs' curl carries the project ping key
            # in the URL, so the route may expose /ping/ and nothing else, and the row must pull
            # that key from the vault and pin it on the project.
            paths = [
                m.get("path", {})
                for r in d["spec"]["rules"]
                for m in r.get("matches", [])
            ]
            assert paths and all(
                x == {"type": "PathPrefix", "value": "/ping/"} for x in paths
            ), f"{p}: healthchecks-ping-key route exposes {paths}"
            assert (
                "healthchecks-ping-key"
                in (p.parent / "external-secret.yaml").read_text()
            ), f"{p}: the row pulls no ping key"
            assert (
                'project.ping_key = os.environ["PING_KEY"]'
                in (p.parent / "enrol.py").read_text()
            ), (
                f"{p}: the row never pins the ping key (idp#962: the enrol script is enrol.py)"
            )
            continue
        if auth == "channel-binding-registry":
            # The customer event door: it carries every channel, and each channel presents a
            # different credential in a different header, so no single edge rule can match one
            # value without going back to one route per channel. The check moved one hop, into
            # the door's first step, which reads the binding table. The proof behind the label:
            # one path only, the credentials come from the estate vault, the seeded row stores a
            # one-way fingerprint and a vault reference rather than a credential, and the
            # deployment provides the exact variable that row's reference resolves to -- without
            # that last link every event on this door is refused.
            layer = p.parent
            paths = [
                m.get("path", {})
                for r in d["spec"]["rules"]
                for m in r.get("matches", [])
            ]
            assert paths and all(
                x == {"type": "PathPrefix", "value": "/webhook/"} for x in paths
            ), f"{p}: channel-binding-registry route exposes {paths}"

            secrets = (layer / "external-secret.yaml").read_text()
            assert "estate-vault" in secrets, (
                f"{p}: annotated channel-binding-registry but no ExternalSecret beside it "
                "pulls a channel credential from the estate vault"
            )

            seed = (layer / "binding-seed.yaml").read_text()
            assert ":'fingerprint'" in seed and "vault://" in seed, (
                f"{p}: the seeded binding row stores no fingerprint and no vault reference"
            )

            reference = re.search(r"'(vault://[^']+)'", seed).group(1)
            resolver_key = (
                "OTTO_CHANNEL_SECRET_"
                + re.sub(r"[^A-Za-z0-9]+", "_", reference).strip("_").upper()
            )
            assert resolver_key in (layer / "deployment.yaml").read_text(), (
                f"{p}: the row points at {reference}, which the door resolves through "
                f"{resolver_key}; nothing in deployment.yaml provides it"
            )
            continue
        if auth == "edge-basic-auth":
            # The collector's ingest door (crew#516 CP5): OTLP /v1/ paths only, and every rule carries a
            # basicAuth Middleware whose Secret an ExternalSecret in the same file pulls from the vault.
            paths = [
                m.get("path", {})
                for r in d["spec"]["rules"]
                for m in r.get("matches", [])
            ]
            assert paths and all(
                x.get("type") == "PathPrefix"
                and x.get("value") in ("/v1/logs", "/v1/traces", "/v1/metrics")
                for x in paths
            ), f"{p}: edge-basic-auth route exposes {paths}"
            basic = {
                m["metadata"]["name"]: str(
                    m.get("spec", {}).get("basicAuth", {}).get("secret", "")
                )
                for pp, m in state["docs"]
                if pp == p
                and m["kind"] == "Middleware"
                and m.get("spec", {}).get("basicAuth")
            }
            pulled = {
                m["metadata"]["name"]
                for pp, m in state["docs"]
                if pp == p and m["kind"] == "ExternalSecret"
            }
            for r in d["spec"]["rules"]:
                names = [
                    f.get("extensionRef", {}).get("name") for f in r.get("filters", [])
                ]
                assert any(n in basic for n in names), (
                    f"{p}: a rule of {d['metadata']['name']} carries no basicAuth Middleware ({names})"
                )
                assert all(basic[n] in pulled for n in names if n in basic), (
                    f"{p}: the basicAuth Secret is pulled by no ExternalSecret in the file"
                )
            continue
        if auth == "public-health-only":
            # A route that carries nothing but a liveness check (crew#768: otto-golden after
            # its webhook moved to the one door). There is no login in front of it because
            # there is nothing behind it to protect -- but that claim is only true while the
            # route stays exactly one unauthenticated GET /healthz, so the annotation is not
            # taken on trust: every match on the route is checked, and one extra path turns
            # this from an exemption into a failure.
            matches = [m for r in d["spec"]["rules"] for m in r.get("matches", [])]
            assert matches and all(
                m.get("path") == {"type": "Exact", "value": "/healthz"}
                and m.get("method") == "GET"
                for m in matches
            ), (
                f"{p}: route {d['metadata']['name']} claims public-health-only "
                f"but exposes {matches}"
            )
            continue
        if auth == "telegram-webhook-secret-token":
            # Otto's Telegram door (crew#736): Telegram's delivery fleet cannot pass a browser
            # login. The adapter registers a secret token with setWebhook and drops any POST that
            # does not echo it (GHSA-3vpc-7q5r-276h) -- so the route may expose exactly /telegram,
            # and gateway.yaml in the same directory must mint that token in-cluster and hand the
            # adapter its URL. The annotation alone is a label; this is the proof behind it.
            # Second accepted proof (founder edict 2026-09-02, gateway physics): the route
            # itself enforces the secret -- every webhook match carries an Exact header
            # match on X-Telegram-Bot-Api-Secret-Token whose value is a Flux substitution
            # variable (never a literal, LAW 46), and only GET /healthz shows besides it.
            rules = d["spec"]["rules"]
            wh = [
                r
                for r in rules
                if any(
                    "telegram" in m.get("path", {}).get("value", "")
                    for m in r.get("matches", [])
                )
            ]
            rest = [m for r in rules if r not in wh for m in r.get("matches", [])]
            if wh and all(
                any(
                    h.get("type") == "Exact"
                    and h.get("name") == "X-Telegram-Bot-Api-Secret-Token"
                    and str(h.get("value", "")).startswith("${")
                    for h in m.get("headers", [])
                )
                for r in wh
                for m in r.get("matches", [])
            ):
                assert all(
                    m.get("path") == {"type": "Exact", "value": "/healthz"}
                    and m.get("method") == "GET"
                    for m in rest
                ), (
                    f"{p}: header-matched telegram route exposes more than GET /healthz: {rest}"
                )
                continue
            paths = [
                m.get("path", {})
                for r in d["spec"]["rules"]
                for m in r.get("matches", [])
            ]
            assert paths and all(
                x == {"type": "Exact", "value": "/telegram"} for x in paths
            ), f"{p}: telegram-webhook route exposes {paths}"
            gw = (p.parent / "gateway.yaml").read_text()
            assert "hermes-agent-webhook" in gw and "TELEGRAM_WEBHOOK_URL" in gw, (
                f"{p}: annotated telegram-webhook-secret-token but gateway.yaml mints no token"
            )
            continue
        if auth == "github-hmac-signature":
            # The Flux webhook receiver (crew#736). GitHub cannot follow an OAuth redirect, so
            # the shared token IS the authentication: the notification-controller verifies
            # X-Hub-Signature-256 against it and answers anything else with a rejection. As
            # everywhere else in this file the annotation is a label and a label is not a proof,
            # so two things are checked -- the route reaches /hook/ and nothing else, and the
            # directory ships a Receiver that actually names a secret to verify against.
            paths = [
                m.get("path", {})
                for r in d["spec"]["rules"]
                for m in r.get("matches", [])
            ]
            assert paths and all(
                x == {"type": "PathPrefix", "value": "/hook/"} for x in paths
            ), f"{p}: github-hmac-signature route exposes {paths}"
            rcv = (p.parent / "receiver.yaml").read_text()
            assert "kind: Receiver" in rcv and "secretRef:" in rcv, (
                f"{p}: annotated github-hmac-signature but receiver.yaml verifies no secret"
            )
            continue
        if auth == "webhook-hmac-signature":
            # Cyrus's delivery door (crew#834 CP3). Linear and GitHub both POST webhook
            # deliveries signed with an HMAC, and neither delivery fleet can follow an OAuth
            # redirect -- so the signature IS the authentication. As everywhere else in this
            # file the annotation is a label and a label is not a proof, so two things are
            # checked: the route reaches /webhook and nothing else, and the directory ships an
            # ExternalSecret that actually pulls the signing secrets it verifies against.
            paths = [
                m.get("path", {})
                for r in d["spec"]["rules"]
                for m in r.get("matches", [])
            ]
            assert paths and all(
                x == {"type": "PathPrefix", "value": "/webhook"} for x in paths
            ), f"{p}: webhook-hmac-signature route exposes {paths}"
            es = (p.parent / "external-secret.yaml").read_text()
            assert "webhook-secret" in es or "webhook_secret" in es, (
                f"{p}: annotated webhook-hmac-signature but external-secret.yaml pulls no signing secret"
            )
            continue
        if auth == "public-demo-page":
            # The buyer sandbox's shop (crew#805 tier 3): a buyer's engineer has no estate
            # login, so the demo door cannot sit behind one. Public is correct only while
            # there is nothing behind the door to protect, and that claim is checked, not
            # trusted: the route must be exactly the seeded shop (the demo-sandbox area, the
            # one catch-all match, the vCluster mirror backend), and the seed it points at
            # must hold no credentials -- no env on its containers, no Secret in the seed,
            # every volume the page ConfigMap.
            assert d["metadata"]["namespace"] == "demo-sandbox", (
                f"{p}: public-demo-page outside the sandbox area"
            )
            assert d["spec"]["hostnames"] == ["sandbox.${ESTATE_ZONE}"], (
                f"{p}: public-demo-page on {d['spec']['hostnames']}"
            )
            matches = [m for r in d["spec"]["rules"] for m in r.get("matches", [])]
            backends = [b for r in d["spec"]["rules"] for b in r.get("backendRefs", [])]
            assert matches == [{"path": {"type": "PathPrefix", "value": "/"}}], (
                f"{p}: public-demo-page matches {matches}"
            )
            assert backends == [
                {"name": "demo-shop-x-demo-x-demo-sandbox", "port": 8080}
            ], f"{p}: public-demo-page serves {backends}"
            hr = next(
                doc
                for doc in yaml.safe_load_all(
                    (PLATFORM / "sandbox/vcluster/helmrelease.yaml").read_text()
                )
                if doc and doc.get("kind") == "HelmRelease"
            )
            seed = [
                doc
                for doc in yaml.safe_load_all(
                    hr["spec"]["values"]["experimental"]["deploy"]["vcluster"][
                        "manifests"
                    ]
                )
                if doc
            ]
            assert not [doc for doc in seed if doc["kind"] == "Secret"], (
                f"{p}: the seeded shop holds a Secret"
            )
            (shop,) = [doc for doc in seed if doc["kind"] == "Deployment"]
            pod = shop["spec"]["template"]["spec"]
            for c in pod["containers"]:
                assert "env" not in c and "envFrom" not in c, (
                    f"{p}: seeded shop container {c['name']} takes env"
                )
            assert all(set(v) == {"name", "configMap"} for v in pod["volumes"]), (
                f"{p}: seeded shop mounts {pod['volumes']}"
            )
            continue
        assert auth == "bearer-master-key", (
            f"{p}: route {d['metadata']['name']} has no oauth2-proxy Middleware in front ({refs}) and no idp.estate/auth annotation"
        )
        cfg = p.parent / "config.yaml"
        assert cfg.exists() and "master_key: os.environ/" in cfg.read_text(), (
            f"{p}: annotated bearer-master-key but {cfg} enforces no master_key"
        )
