"""Incident 2026-08-25: the catalogue probes hit /healthcheck, a path the new Backstage backend
does not serve. The app-backend catch-all answered it with index.html, so the probe returned
200 text/html for any path (/nonsense-path measured 200 too) and a pod with no plugin mounted
still read Ready. Rule (rung 4): every probe on a Backstage workload targets an endpoint under
/.backstage/health/v1/, which answers JSON only after the backend has started."""
import pathlib
import subprocess

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
OVERLAY = ROOT / "platform" / "backstage" / "overlays" / "oke"
HEALTH = "/.backstage/health/v1/"


def _probes(rendered):
    for d in yaml.safe_load_all(rendered):
        if d and d.get("kind") == "Deployment":
            for c in d["spec"]["template"]["spec"]["containers"]:
                for name in ("startupProbe", "readinessProbe", "livenessProbe"):
                    if name in c:
                        yield d["metadata"]["name"], name, c[name].get("httpGet", {}).get("path")


def test_every_backstage_probe_targets_the_backend_health_api():
    rendered = subprocess.run(["kubectl", "kustomize", "--load-restrictor", "LoadRestrictionsNone",
                               str(OVERLAY)], check=True, capture_output=True, text=True).stdout
    probes = list(_probes(rendered))
    assert probes, "catalogue renders no probes"
    bad = [p for p in probes if not (p[2] or "").startswith(HEALTH)]
    assert bad == [], f"probes served by the SPA fallback, not the backend: {bad}"


def test_the_incident_path_is_refused():
    doc = {"kind": "Deployment", "metadata": {"name": "x"}, "spec": {"template": {"spec": {"containers": [
        {"name": "c", "readinessProbe": {"httpGet": {"path": "/healthcheck"}}}]}}}}
    assert [p for p in _probes(yaml.safe_dump(doc)) if not p[2].startswith(HEALTH)]
