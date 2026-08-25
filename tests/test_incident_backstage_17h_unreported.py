"""Incident 2026-08-25: the Backstage catalogue sat in ImagePullBackOff for 17 hours and no one
was told. Rule (R35 scenario 4, crew#250): a broken workload is reported within ten minutes.
Flux reports it only if (a) every cluster Kustomization with health checks waits on them, so a
stalled workload becomes an error event, and (b) an Alert forwards Kustomization errors from
flux-system and HelmRelease errors from every namespace a HelmRelease lives in."""
import glob
import pathlib

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _docs(pattern):
    for f in sorted(glob.glob(str(ROOT / pattern), recursive=True)):
        for d in yaml.safe_load_all(pathlib.Path(f).read_text()):
            if d:
                yield f, d


def test_every_cluster_kustomization_with_health_checks_waits():
    for f, d in _docs("clusters/*/*.yaml"):
        if d.get("kind") == "Kustomization" and d["spec"].get("healthChecks"):
            assert d["spec"].get("wait") is True, f"{f}: {d['metadata']['name']} has healthChecks but wait is not true"
            assert d["spec"].get("timeout"), f"{f}: {d['metadata']['name']} has no timeout, so it never stalls"


def test_alert_covers_every_namespace_that_holds_a_helmrelease():
    alerts = [d for _, d in _docs("platform/alerts/*.yaml") if d.get("kind") == "Alert"]
    assert alerts, "no Alert in platform/alerts"
    covered = {(s["kind"], s.get("namespace")) for a in alerts for s in a["spec"]["eventSources"] if s["name"] == "*"}
    assert ("Kustomization", "flux-system") in covered
    hr_namespaces = {d["metadata"]["namespace"] for _, d in _docs("platform/**/*.yaml") if d.get("kind") == "HelmRelease"}
    missing = {ns for ns in hr_namespaces if ("HelmRelease", ns) not in covered}
    assert not missing, f"HelmRelease namespaces with no alert: {sorted(missing)}"
    assert all(a["spec"]["eventSeverity"] == "error" for a in alerts)
