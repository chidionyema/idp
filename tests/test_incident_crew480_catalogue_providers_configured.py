"""crew#480: the catalogue discovers itself instead of a session running `bin/catalog-gen` by
hand. Two Backstage entity providers do the discovery:

  1. `@backstage/plugin-catalog-backend-module-github` (catalog.providers.github,
     backstage/app-config.container.yaml) scans org chidionyema on a schedule for any
     `catalog-info.yaml` and ingests it -- no laptop, no cron.
  2. The Kubernetes plugin's cluster locator (kubernetes.clusterLocatorMethods) reads the
     estate's own OKE cluster through the pod's mounted service account.

LAW 46: neither provider may carry a literal hostname, zone or account for the cluster it talks
to. `authProvider: serviceAccount` with no `serviceAccountToken` means the actual URL is unused at
runtime (Backstage falls back to the in-cluster client), so the config values that stand in for it
must still be `${ENV}` substitutions, not bare strings -- the whole point being that the same file
runs against any cluster the estate points it at, never one baked in.

Rung 4 (incident test, named for the ticket). Proved both ways in the PR body: passes on this
branch; fails if the github provider or the kubernetes locator is removed, or if the cluster url
reverts to a literal.
"""
import pathlib
import re

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
APP_CONFIG_CONTAINER = ROOT / "backstage" / "app-config.container.yaml"
BACKEND_INDEX = ROOT / "backstage" / "packages" / "backend" / "src" / "index.ts"
BACKEND_PACKAGE_JSON = ROOT / "backstage" / "packages" / "backend" / "package.json"

# A bare literal host: something that looks like a real address (a dot, or "localhost", or an
# IANA-reserved v4/v6 loopback/link-local form) with no `${` substitution anywhere in the same
# scalar. `${K8S_CLUSTER_URL:-https://kubernetes.default.svc}` is fine: the substitution is present,
# so an operator can override it, and the fallback is the universal in-cluster DNS name Kubernetes
# itself defines in every cluster -- not this estate's zone or account.
_LITERAL_HOST = re.compile(r"^(?!.*\$\{)(https?://|[\w.-]+\.[a-z]{2,})", re.IGNORECASE)


def _load_container_config() -> dict:
    text = APP_CONFIG_CONTAINER.read_text()
    docs = [d for d in yaml.safe_load_all(text) if d]
    assert len(docs) == 1, "app-config.container.yaml must stay a single YAML document"
    return docs[0]


def _clusters(cfg: dict) -> list[dict]:
    methods = cfg.get("kubernetes", {}).get("clusterLocatorMethods", [])
    out = []
    for m in methods:
        out.extend(m.get("clusters", []))
    return out


def test_incident_crew480_github_provider_is_registered_in_the_backend():
    text = BACKEND_INDEX.read_text()
    assert "@backstage/plugin-catalog-backend-module-github" in text, (
        "packages/backend/src/index.ts must backend.add() the github catalog entity provider "
        "module, or the config below is dead weight nothing loads"
    )


def test_incident_crew480_github_provider_dependency_is_pinned():
    import json

    pkg = json.loads(BACKEND_PACKAGE_JSON.read_text())
    version = pkg["dependencies"].get("@backstage/plugin-catalog-backend-module-github")
    assert version, "backend package.json must depend on the github catalog provider module"
    assert re.fullmatch(r"\d+\.\d+\.\d+", version), (
        f"dependency must be pinned to an exact version matching this repo's Backstage release "
        f"train (backstage/backstage.json), not a caret range: got {version!r}"
    )


def test_incident_crew480_github_provider_targets_the_org_with_a_schedule():
    cfg = _load_container_config()
    github = cfg.get("catalog", {}).get("providers", {}).get("github")
    assert github, "catalog.providers.github must be configured"
    variant = github.get("default", github)
    assert variant.get("organization") == "chidionyema"
    assert "catalog-info.yaml" in (variant.get("catalogPath") or ""), (
        "catalogPath must filter for catalog-info.yaml, not ingest every file in every repo"
    )
    schedule = variant.get("schedule")
    assert schedule, "the provider must run on a schedule, not only at boot"
    assert schedule.get("frequency"), "schedule.frequency is required"
    assert schedule.get("timeout"), "schedule.timeout is required"


def test_incident_crew480_kubernetes_locator_reads_the_in_cluster_service_account():
    cfg = _load_container_config()
    clusters = _clusters(cfg)
    assert clusters, "kubernetes.clusterLocatorMethods must declare at least one cluster"
    for c in clusters:
        assert c.get("authProvider") == "serviceAccount"
        # serviceAccountToken must be ABSENT: its presence is what makes Backstage fall back to
        # in-cluster discovery via the pod's own mounted credentials instead of a literal token.
        assert "serviceAccountToken" not in c, (
            "a serviceAccountToken here would be a literal credential, and it would stop "
            "Backstage from using the pod's own in-cluster service account"
        )


def test_incident_crew480_no_literal_hostname_in_the_cluster_config():
    cfg = _load_container_config()
    for c in _clusters(cfg):
        for key in ("url", "name"):
            value = str(c.get(key, ""))
            assert "${" in value, (
                f"kubernetes cluster {key}={value!r} carries no ${{ENV}} substitution "
                f"(LAW 46): every session would hit the same cluster forever"
            )


def test_incident_crew480_a_reverted_literal_cluster_url_is_refused(tmp_path):
    """Prove the guard both ways: a copy with the url hardcoded back to a literal must fail the
    same assertion the branch passes with."""
    text = APP_CONFIG_CONTAINER.read_text()
    assert "${K8S_CLUSTER_URL" in text, "fixture assumption: the real file uses a substitution"
    broken = text.replace(
        "url: ${K8S_CLUSTER_URL:-https://kubernetes.default.svc}",
        "url: https://10.0.4.12:6443",
    )
    assert broken != text, "replacement did not match; update the fixture string"
    docs = [d for d in yaml.safe_load_all(broken) if d]
    clusters = _clusters(docs[0])
    literal_found = any(_LITERAL_HOST.match(str(c.get("url", ""))) for c in clusters)
    assert literal_found, "the broken fixture itself must contain a literal host"
    no_subst = [c for c in clusters if "${" not in str(c.get("url", ""))]
    assert no_subst, "reverting to a literal must be the thing the real-file test refuses"
