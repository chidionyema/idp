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


def test_every_health_checked_kustomization_reconciles_within_ten_minutes():
    """The ten-minute claim (R35 scenario 4) only holds if the row re-checks health at least
    that often: a pod that breaks between reconciles is only seen at the next one."""
    slow = []
    for f in sorted(glob.glob(str(ROOT / "clusters" / "*" / "*.yaml"))):
        for d in yaml.safe_load_all(open(f)):
            if d and d.get("kind") == "Kustomization" and (
                d["spec"].get("healthChecks") or d["spec"].get("wait")
            ):
                iv = d["spec"]["interval"]
                if not iv.endswith("m") or int(iv[:-1]) > 10:
                    slow.append((d["metadata"]["name"], iv))
    assert slow == [], slow


def test_alert_covers_every_namespace_that_holds_a_helmrelease():
    alerts = [d for _, d in _docs("platform/alerts/*.yaml") if d.get("kind") == "Alert"]
    assert alerts, "no Alert in platform/alerts"
    covered = {(s["kind"], s.get("namespace")) for a in alerts for s in a["spec"]["eventSources"] if s["name"] == "*"}
    assert ("Kustomization", "flux-system") in covered
    hr_namespaces = {d["metadata"]["namespace"] for _, d in _docs("platform/**/*.yaml") if d.get("kind") == "HelmRelease"}
    missing = {ns for ns in hr_namespaces if ("HelmRelease", ns) not in covered}
    assert not missing, f"HelmRelease namespaces with no alert: {sorted(missing)}"
    assert all(a["spec"]["eventSeverity"] == "error" for a in alerts)


def test_telegram_channel_survives_substitution_as_a_string():
    """Live incident 2026-08-25: kustomize dropped the quotes around `${channel}`, the
    numeric chat id substituted in as a YAML integer and the Provider dry-run refused it.
    The synced Secret value carries its own quotes; the Provider leaves the scalar bare."""
    es = next(d for d in yaml.safe_load_all(open(ROOT / "platform" / "secret-store" / "flux-telegram.yaml")))
    channel = es["spec"]["target"]["template"]["data"]["channel"]
    assert channel.startswith('"') and channel.endswith('"'), channel
    prov = (ROOT / "platform" / "alerts" / "provider.yaml").read_text()
    assert "channel: ${channel}" in prov and 'channel: "${channel}"' not in prov
    rendered = "channel: ${channel}".replace("${channel}", '"123"')
    assert isinstance(yaml.safe_load(rendered)["channel"], str)
