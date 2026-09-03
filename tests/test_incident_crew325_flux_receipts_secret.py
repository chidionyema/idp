"""Incident crew#325, 2026-08-26: platform/alerts/provider-github.yaml named secretRef github-app
and nothing produced that Secret, so the reconcile ledger (flux-events.yml) recorded zero events
in 24 hours and a session with no kube path could not read why a workload was down. The rule:
every Provider's secretRef in platform/alerts is the target of an ExternalSecret rendered from
platform/alerts-secret or platform/alerts-github, in the same namespace, and the GitHub App one carries the three keys
Flux's githubdispatch authentication reads."""
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def _render(rel: str) -> list[dict]:
    out = subprocess.run(["kubectl", "kustomize", str(ROOT / rel)], capture_output=True, text=True, check=True).stdout
    return [d for d in yaml.safe_load_all(out) if d]


def test_incident_crew325_every_alert_provider_secret_has_a_producer() -> None:
    providers = [d for rel in ("platform/alerts", "platform/alerts-github") for d in _render(rel) if d["kind"] == "Provider"]
    assert providers
    targets = {
        (d["metadata"]["namespace"], d["spec"]["target"]["name"])
        for rel in ("platform/alerts-secret", "platform/alerts-github")
        for d in _render(rel)
        if d["kind"] == "ExternalSecret"
    }
    for p in providers:
        ref = (p["metadata"]["namespace"], p["spec"]["secretRef"]["name"])
        assert ref in targets, (p["metadata"]["name"], ref, sorted(targets))


def test_incident_crew325_github_dispatch_secret_carries_app_auth_keys() -> None:
    es = next(d for d in _render("platform/alerts-github") if d["metadata"]["name"] == "github-app")
    keys = set(es["spec"]["target"]["template"]["data"])
    assert keys == {"githubAppID", "githubAppInstallationID", "githubAppPrivateKey"}, keys
