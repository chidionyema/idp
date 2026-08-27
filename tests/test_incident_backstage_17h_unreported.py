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


def _namespace_of(path, doc):
    """metadata.namespace, or the `namespace:` the directory's kustomization stamps on it
    (idp#133 signoz: the HelmRelease carries none, kustomize sets observability)."""
    if "namespace" in doc["metadata"]:
        return doc["metadata"]["namespace"]
    k = pathlib.Path(path).parent / "kustomization.yaml"
    if k.exists():
        stamped = yaml.safe_load(k.read_text()).get("namespace")
        if stamped:
            return stamped
    raise AssertionError(f"{path}: HelmRelease {doc['metadata']['name']} has no namespace anywhere")


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
    hr_namespaces = {_namespace_of(f, d) for f, d in _docs("platform/**/*.yaml") if d.get("kind") == "HelmRelease"}
    missing = {ns for ns in hr_namespaces if ("HelmRelease", ns) not in covered}
    assert not missing, f"HelmRelease namespaces with no alert: {sorted(missing)}"
    # The founder's channel carries errors only; a machine ledger (githubdispatch, crew#325)
    # is allowed to carry info, because a session reads it and he does not.
    founder = [a for a in alerts if a["spec"]["providerRef"]["name"] == "telegram"]
    assert founder, "no Alert reaches the founder's Telegram channel"
    assert all(a["spec"]["eventSeverity"] == "error" for a in founder)


def test_telegram_channel_survives_substitution_as_a_string():
    """Live incident 2026-08-25: kustomize dropped the quotes around `${channel}`, the
    numeric chat id substituted in as a YAML integer and the Provider dry-run refused it.
    The synced Secret value carries its own quotes; the Provider leaves the scalar bare."""
    es = next(d for d in yaml.safe_load_all(open(ROOT / "platform" / "alerts-secret" / "flux-telegram.yaml")))
    channel = es["spec"]["target"]["template"]["data"]["channel"]
    assert channel.startswith('"') and channel.endswith('"'), channel
    prov = (ROOT / "platform" / "alerts" / "provider.yaml").read_text()
    assert "channel: ${channel}" in prov and 'channel: "${channel}"' not in prov
    rendered = "channel: ${channel}".replace("${channel}", '"123"')
    assert isinstance(yaml.safe_load(rendered)["channel"], str)


# crew#344: the HelmRelease rows are generated from the Flux render by bin/idp-alert-rows, so
# a new namespace is covered without anyone remembering to type it. Both ways: the checked-in
# file must be current, and a file missing a namespace must be refused.
def _alert_rows(root, *args):
    import subprocess
    import sys

    return subprocess.run([sys.executable, str(ROOT / "bin/idp-alert-rows"), *args], capture_output=True, text=True, cwd=root)


def test_incident_crew344_alert_rows_are_generated_and_current():
    r = _alert_rows(ROOT, "--check")
    assert r.returncode == 0 and r.stdout.startswith("ok      alert-rows"), r.stdout + r.stderr


def test_incident_crew344_a_missing_namespace_row_is_refused(tmp_path, monkeypatch):
    import shutil

    alert = ROOT / "platform/alerts/alert.yaml"
    keep = alert.read_text()
    try:
        alert.write_text(keep.replace('      namespace: temporal\n', '', 1))
        r = _alert_rows(ROOT, "--check")
        assert r.returncode == 1 and "stale" in r.stdout, r.stdout + r.stderr
    finally:
        alert.write_text(keep)
