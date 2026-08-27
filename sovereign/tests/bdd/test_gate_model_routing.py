"""Binds features/gates/model-routing.feature (crew#284 CP2, crew#313). Steps read the two
router configs and the llm row manifests for real; nothing is mocked."""
from __future__ import annotations

import re
from pathlib import Path

import yaml
from pytest_bdd import given, scenarios, then, when

scenarios("features/gates/model-routing.feature")

ROOT = Path(__file__).resolve().parents[3]
CLUSTER = ROOT / "platform" / "llm"


def _models(path: Path) -> dict[str, dict]:
    cfg = yaml.safe_load(path.read_text())
    return {m["model_name"]: m["litellm_params"] for m in cfg["model_list"]}


def _local(models: dict[str, dict]) -> set[str]:
    return {n for n, p in models.items() if "host.docker.internal" in str(p.get("api_base", ""))}


@given("llm/config.yaml lists the hosted models and the local ollama lane", target_fixture="laptop")
def laptop() -> dict[str, dict]:
    models = _models(ROOT / "llm" / "config.yaml")
    assert _local(models), "the laptop config is expected to carry the ollama lane"
    return models


@when("platform/llm/config.yaml is compared entry for entry", target_fixture="cluster")
def cluster() -> dict[str, dict]:
    return _models(CLUSTER / "config.yaml")


@then("every hosted entry is identical")
def hosted_identical(laptop: dict, cluster: dict) -> None:
    hosted = {n: p for n, p in laptop.items() if n not in _local(laptop)}
    assert {n: cluster[n] for n in hosted} == hosted


@then("no entry points at host.docker.internal")
def no_local(cluster: dict) -> None:
    assert not _local(cluster)


@then("every fallback names a model the cluster serves")
def fallbacks_served(cluster: dict) -> None:
    cfg = yaml.safe_load((CLUSTER / "config.yaml").read_text())
    for entry in cfg["router_settings"]["fallbacks"]:
        for src, targets in entry.items():
            assert src in cluster and set(targets) <= set(cluster), (src, targets)


@given("the prospector edge has a listener https-llm for llm.${ESTATE_ZONE}", target_fixture="listener")
def listener() -> str:
    # The listener lives in prospector (deploy/k8s/base/edge.yaml); here its name is the contract.
    return "https-llm"


@when("the HTTPRoute in namespace llm attaches to it", target_fixture="route")
def route(listener: str) -> dict:
    r = yaml.safe_load((CLUSTER / "httproute.yaml").read_text())
    assert r["spec"]["parentRefs"][0] == {"name": "prospector-edge", "namespace": "prospector", "sectionName": listener}
    return r


@then("external-dns publishes the hostname")
def hostname(route: dict) -> None:
    assert route["spec"]["hostnames"] == ["llm.${ESTATE_ZONE}"]
    ns = yaml.safe_load((CLUSTER / "namespace.yaml").read_text())
    assert ns["metadata"]["labels"]["idp.estate/edge-attach"] == "true"


@then("callers authenticate with the master key from the estate vault")
def master_key() -> None:
    cfg = yaml.safe_load((CLUSTER / "config.yaml").read_text())
    assert cfg["general_settings"]["master_key"] == "os.environ/LITELLM_MASTER_KEY"


@given("the vault holds one JSON secret litellm-upstream", target_fixture="external_secret")
def external_secret() -> dict:
    # Two ExternalSecrets live in the file since the Langfuse callback (crew#325); the rule is about the upstream one.
    es = next(d for d in yaml.safe_load_all((CLUSTER / "external-secret.yaml").read_text()) if d["metadata"]["name"] == "litellm-upstream")
    assert es["spec"]["dataFrom"][0]["extract"]["key"] == "litellm-upstream"
    return es


@when("the ExternalSecret materialises it in namespace llm", target_fixture="secret_name")
def secret_name(external_secret: dict) -> str:
    assert external_secret["metadata"]["namespace"] == "llm"
    return external_secret["spec"]["target"]["name"]


@then("every os.environ reference in the router config resolves from that Secret")
def env_refs(secret_name: str) -> None:
    dep = next(d for d in yaml.safe_load_all((CLUSTER / "litellm.yaml").read_text()) if d["kind"] == "Deployment")
    # idp#253: the Secret is a mounted volume the container exports itself; Kyverno refuses envFrom.
    spec = dep["spec"]["template"]["spec"]
    assert secret_name in {v.get("secret", {}).get("secretName") for v in spec["volumes"]}, "litellm-upstream is not a mounted volume"
    assert "envFrom" not in spec["containers"][0]
    refs = set(re.findall(r"os\.environ/([A-Z_]+)", (CLUSTER / "config.yaml").read_text()))
    documented = set(re.findall(r"([A-Z_]+_KEY)=\1", (CLUSTER / "external-secret.yaml").read_text()))
    assert refs == documented, refs ^ documented


@then("no key is written in the repository")
def no_key_in_repo() -> None:
    for f in CLUSTER.glob("*.yaml"):
        assert not re.search(r"(?i)(api_key|master_key):\s*['\"]?(sk-|[A-Za-z0-9]{32,})", f.read_text()), f


# crew#400/crew#408: the founder picks and adds models in the Admin UI; the console signs in through IDCS.
@given("the router runs the -database image with litellm-db in namespace llm", target_fixture="deployment")
def deployment() -> dict:
    docs = list(yaml.safe_load_all((CLUSTER / "litellm.yaml").read_text()))
    dep = next(d for d in docs if d["kind"] == "Deployment")
    image = dep["spec"]["template"]["spec"]["containers"][0]["image"]
    assert "litellm-database:" in image, image
    pg = list(yaml.safe_load_all((CLUSTER / "postgres.yaml").read_text()))
    assert any(d["kind"] == "StatefulSet" and d["metadata"]["name"] == "litellm-db" for d in pg)
    return dep


@given("general_settings.store_model_in_db is true so a model added in the UI outlives a restart")
def store_model_in_db() -> None:
    cfg = yaml.safe_load((CLUSTER / "config.yaml").read_text())
    assert cfg["general_settings"].get("store_model_in_db") is True


@when("the founder opens https://llm.<zone>/ui and signs in", target_fixture="sso_env")
def sso_env(deployment: dict) -> dict:
    env = {e["name"]: e.get("value", "") for e in deployment["spec"]["template"]["spec"]["containers"][0]["env"]}
    assert env["GENERIC_AUTHORIZATION_ENDPOINT"] == "${ESTATE_OIDC_DOMAIN_URL}/oauth2/v1/authorize"
    assert env["GENERIC_TOKEN_ENDPOINT"] == "${ESTATE_OIDC_DOMAIN_URL}/oauth2/v1/token"
    assert env["PROXY_BASE_URL"] == "https://llm.${ESTATE_ZONE}"
    return env


@then("the console sends the founder to the estate identity domain, the same login as the catalogue")
def same_domain_as_catalogue(sso_env: dict) -> None:
    cfg = yaml.safe_load((ROOT / "clusters" / "oke" / "estate-config.yaml").read_text())
    assert "ESTATE_OIDC_DOMAIN_URL" in cfg["data"], "the domain URL is one value in estate-config"
    tf = (ROOT / "platform" / "oci" / "identity" / "main.tf").read_text()
    assert 'redirect_uris             = ["https://llm.${var.zone}/sso/callback"]' in tf
    assert "oci_identity_domains_app.router_console.id" in tf, "founder_emails are granted the console app"


@then("the OIDC client reaches the pod only from the vault, written by platform/oci/identity")
def client_from_vault(deployment: dict) -> None:
    es = next(d for d in yaml.safe_load_all((CLUSTER / "external-secret.yaml").read_text()) if d["metadata"]["name"] == "litellm-sso")
    keys = {d["secretKey"]: d["remoteRef"]["key"] for d in es["spec"]["data"]}
    assert keys == {"GENERIC_CLIENT_ID": "litellm-sso-client-id", "GENERIC_CLIENT_SECRET": "litellm-sso-client-secret",
                    "PROXY_ADMIN_ID": "litellm-sso-admin-id"}
    tf = (ROOT / "platform" / "oci" / "identity" / "main.tf").read_text()
    for name in keys.values():
        assert f'secret_name    = "{name}"' in tf, name
    spec = deployment["spec"]["template"]["spec"]
    vol = next(v for v in spec["volumes"] if v.get("secret", {}).get("secretName") == "litellm-sso")
    mounts = {m["name"]: m["mountPath"] for m in spec["containers"][0]["volumeMounts"]}
    assert mounts[vol["name"]].startswith("/run/secrets/litellm/")


@then("no console username or password exists anywhere in the repository")
def no_console_password() -> None:
    for f in list(CLUSTER.glob("*.yaml")) + [ROOT / ".github" / "workflows" / "vault-seed.yml"]:
        assert not re.search(r"UI_(USERNAME|PASSWORD)|litellm-ui", f.read_text()), f


@then("every provider key the UI can bind to is an os.environ name the pod already exports")
def provider_keys_exported() -> None:
    doc = (ROOT / "docs" / "onboarding" / "litellm.md").read_text()
    named = set(re.findall(r"os\.environ/([A-Z_]+_API_KEY)", doc))
    exported = set(re.findall(r"([A-Z_]+_API_KEY)=\1", (CLUSTER / "external-secret.yaml").read_text()))
    assert named and named <= exported, named - exported
