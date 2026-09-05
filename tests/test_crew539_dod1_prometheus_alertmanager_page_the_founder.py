"""crew#539 DoD item 1 (founder, 2026-08-27): the estate is watched by the one Prometheus and the
one Alertmanager, pages reach the founder's Telegram, and the receipt proves the pipeline runs.
Proved offline, no sockets:
  1. the Flux row exists, substitutes ESTATE_ZONE, waits on both HelmReleases, and the CRs
     (Probe, PrometheusRule) apply from a second row after the chart's CRDs exist;
  2. kube-prometheus-stack ships the upstream rule set (KubePodNotReady, KubeNodeNotReady,
     TargetDown come from defaultRules) and honours every PrometheusRule/Probe in the cluster;
  3. Alertmanager's config is rendered from the flux-telegram vault entry (no literal token or
     chat), routes everything to Telegram and warnings on to Robusta (CP14), and mutes Watchdog;
  4. the Probe covers exactly the non-GitHub founder surfaces of the catalogue, and the blackbox
     module accepts the 401/405 those surfaces answer by design (memory: curl-head-probe-405);
  5. the estate's rules carry FounderSurfaceDown and the CP14 PVC>90% alert, and every expr is
     a syntactically valid PromQL expression as far as balanced braces and a `for` go;
  6. the collector reads PrometheusRules and the Alertmanager proxy (RBAC present), the receipt
     head carries monitoring_rules= and alert_watchdog=, and the grader fails on 0 or absent;
  7. the broken-workload Flux Alert lists namespace monitoring (bin/idp-alert-rows is current).
"""

import pathlib
import re
import os
import subprocess
import sys

import yaml

IDP = pathlib.Path(__file__).resolve().parents[1]
MON = IDP / "platform/monitoring"


def docs(rel):
    return [d for d in yaml.safe_load_all((IDP / rel).read_text()) if d]


def one(rel, kind, name=None):
    (d,) = [
        d
        for d in docs(rel)
        if d["kind"] == kind and (name is None or d["metadata"]["name"] == name)
    ]
    return d


def test_flux_row_substitutes_the_zone_and_waits_on_both_releases():
    row = one("clusters/oke/platform.yaml", "Kustomization", "monitoring")
    assert row["spec"]["path"] == "./platform/monitoring"
    assert row["spec"]["wait"] is True and row["spec"]["prune"] is True
    subs = row["spec"]["postBuild"]["substituteFrom"]
    assert {"kind": "ConfigMap", "name": "estate-config"} in subs
    deps = {d["name"] for d in row["spec"]["dependsOn"]}
    # crew#573: this line read `{"edge", "secret-store", "robusta"} <= deps` and it held the estate
    # blind. It encoded "robusta is wired in" as a Flux dependency, but the wiring is the webhook
    # receiver in alertmanager-config.yaml, which test_alertmanager_routes_to_telegram... below
    # asserts directly. As a `dependsOn` it only meant "no Prometheus unless robusta is healthy":
    # robusta's HelmRelease went Failed, this row never became Ready, and oke-check 33172282641
    # found 0 kps- pods in the cluster while hindsight-api crash-looped 13h unremarked.
    assert {"edge", "secret-store"} <= deps, deps
    assert "robusta" not in deps, (
        "robusta consumes this row's alerts; it is never a prerequisite for them (crew#573)"
    )
    hc = {(h["kind"], h["name"], h["namespace"]) for h in row["spec"]["healthChecks"]}
    assert hc == {
        ("HelmRelease", "kube-prometheus-stack", "monitoring"),
        ("HelmRelease", "blackbox", "monitoring"),
    }
    kz = yaml.safe_load((MON / "kustomization.yaml").read_text())
    assert set(kz["resources"]) == {
        "namespace.yaml",
        "alertmanager-config.yaml",
        "kube-prometheus-stack.yaml",
        "blackbox.yaml",
    }
    # the CRs apply from their own row after the chart's CRDs exist (incident 2026-08-25)
    rules = one("clusters/oke/platform.yaml", "Kustomization", "monitoring-rules")
    assert rules["spec"]["path"] == "./platform/monitoring/rules" and rules["spec"][
        "dependsOn"
    ] == [{"name": "monitoring"}]
    assert {"kind": "ConfigMap", "name": "estate-config"} in rules["spec"]["postBuild"][
        "substituteFrom"
    ]
    kz2 = yaml.safe_load((MON / "rules/kustomization.yaml").read_text())
    assert set(kz2["resources"]) == {
        "estate.yaml",
        "founder-surfaces-probe.yaml",
        "founder-mac-screen-sharing-probe.yaml",
        "agentgateway-servicemonitor.yaml",
        "k8sgpt.yaml",
        "capacity.yaml",
    }  # capacity.yaml: crew#645 CP5; K8sGPT findings PrometheusRule, idp#696
    ns = one("platform/monitoring/namespace.yaml", "Namespace")
    assert (
        ns["metadata"]["labels"]["pod-security.kubernetes.io/enforce"] == "restricted"
    )


def test_kube_prometheus_stack_ships_the_upstream_rules_and_honours_every_rule_and_probe():
    hr = one(
        "platform/monitoring/kube-prometheus-stack.yaml",
        "HelmRelease",
        "kube-prometheus-stack",
    )
    assert hr["spec"]["chart"]["spec"]["chart"] == "kube-prometheus-stack"
    v = hr["spec"]["values"]
    assert v["defaultRules"]["create"] is True
    # the general/kubernetes-apps/kubernetes-system groups stay on: KubePodNotReady, TargetDown, KubeNodeNotReady
    off = {k for k, on in v["defaultRules"]["rules"].items() if on is False}
    for must_stay in (
        "general",
        "kubernetesApps",
        "kubernetesSystem",
        "kubernetesStorage",
        "kubeStateMetrics",
        "alertmanager",
        "prometheus",
    ):
        assert must_stay not in off, must_stay
    ps = v["prometheus"]["prometheusSpec"]
    for k in ("rule", "serviceMonitor", "podMonitor", "probe", "scrapeConfig"):
        assert ps[f"{k}SelectorNilUsesHelmValues"] is False, k
    assert (
        v["alertmanager"]["alertmanagerSpec"]["configSecret"] == "alertmanager-telegram"
    )
    assert v["grafana"]["enabled"] is False and v["nodeExporter"]["enabled"] is False
    # requests == limits on every block we size (Guaranteed, crew#539 CP9)
    blocks = [
        v["prometheusOperator"]["resources"],
        v["prometheusOperator"]["prometheusConfigReloader"]["resources"],
        v["kube-state-metrics"]["resources"],
        v["alertmanager"]["alertmanagerSpec"]["resources"],
        ps["resources"],
    ]
    for b in blocks:
        assert b["requests"] == b["limits"], b
    total_m = sum(int(b["requests"]["cpu"][:-1]) for b in blocks)
    assert total_m == 320, total_m  # the number the file's header states
    text = (MON / "kube-prometheus-stack.yaml").read_text()
    assert f"{total_m}m CPU" in text


def test_alertmanager_config_comes_from_the_vault_and_routes_telegram_then_robusta():
    es = one(
        "platform/monitoring/alertmanager-config.yaml",
        "ExternalSecret",
        "alertmanager-telegram",
    )
    assert es["spec"]["dataFrom"] == [{"extract": {"key": "flux-telegram"}}]
    assert es["spec"]["target"]["template"]["engineVersion"] == "v2"
    raw = es["spec"]["target"]["template"]["data"]["alertmanager.yaml"]
    assert "{{ .token }}" in raw and "{{ .channel }}" in raw
    # render the template the way ESO would with placeholder values, then parse it as Alertmanager would
    cfg = yaml.safe_load(
        raw.replace("{{ .token }}", "TOKEN").replace("{{ .channel }}", "-1001")
    )
    assert cfg["route"]["receiver"] == "telegram"
    names = {r["name"] for r in cfg["receivers"]}
    assert names == {
        "null",
        "telegram",
        "robusta",
        "telegram-p1-page",
    }  # crew#684 CP3 adds the P1 page
    routes = cfg["route"]["routes"]
    assert routes[0]["receiver"] == "null" and "Watchdog" in routes[0]["matchers"][0]
    assert routes[1]["receiver"] == "robusta" and routes[1]["continue"] is True
    # crew#684 CP3: an alert with no owner label pages after ten minutes, and still reaches telegram
    assert (
        routes[2]["receiver"] == "telegram-p1-page" and routes[2]["group_wait"] == "10m"
    )
    assert routes[2]["matchers"][0] == 'owner = ""' and routes[2]["continue"] is True
    (tg,) = [r for r in cfg["receivers"] if r["name"] == "telegram"]
    assert tg["telegram_configs"][0]["send_resolved"] is True
    (rb,) = [r for r in cfg["receivers"] if r["name"] == "robusta"]
    assert (
        rb["webhook_configs"][0]["url"]
        == "http://robusta-runner.robusta.svc.cluster.local/api/alerts"
    )
    # no literal token or chat id anywhere in the directory (LAW 21, LAW 46)
    for f in MON.rglob("*.yaml"):
        t = f.read_text()
        assert not re.search(r"\b\d{6,}:[A-Za-z0-9_-]{20,}", t), f
        assert not re.search(r"chat_id:\s*-?\d", t), f


def founder_surface_urls():
    text = (IDP / "backstage/founder/catalog-info.yaml").read_text()
    urls = re.findall(r'url: "(https?://[^"]+)"', text)
    return sorted({u for u in urls if not u.startswith("https://github.com/")})


def test_probe_targets_are_exactly_the_founder_surfaces_and_the_module_accepts_401_and_405():
    probe = one(
        "platform/monitoring/rules/founder-surfaces-probe.yaml",
        "Probe",
        "founder-surfaces",
    )
    targets = sorted(probe["spec"]["targets"]["staticConfig"]["static"])
    assert targets == founder_surface_urls(), targets
    # the estate's own hostnames are never literal (LAW 46); vendor consoles and Telegram are the only ones without the placeholder
    assert all(
        "${ESTATE_ZONE}" in t
        or t.startswith(
            ("https://cloud.oracle.com/", "https://t.me/", "https://cursor.com/")
        )
        for t in targets
    ), targets
    assert (
        probe["spec"]["module"] == "founder"
        and probe["spec"]["jobName"] == "founder-surfaces"
    )
    hr = one("platform/monitoring/blackbox.yaml", "HelmRelease", "blackbox")
    mod = hr["spec"]["values"]["config"]["modules"]["founder"]["http"]
    assert mod["method"] == "GET"
    assert {200, 401, 405, 302} <= set(mod["valid_status_codes"])
    assert probe["spec"]["prober"]["url"].startswith(
        hr["spec"]["values"]["fullnameOverride"] + ".monitoring.svc"
    )
    sc = hr["spec"]["values"]["securityContext"]
    assert sc["seccompProfile"]["type"] == "RuntimeDefault"


def test_estate_rules_carry_founder_surface_down_and_the_cp14_pvc_alert():
    pr = one("platform/monitoring/rules/estate.yaml", "PrometheusRule", "estate")
    rules = {r["alert"]: r for g in pr["spec"]["groups"] for r in g["rules"]}
    # A superset check, not an equality one. This assertion used to pin the exact set of alert
    # names, so every alert added to the estate failed a test about alerts that already existed --
    # a test reading the estate's own file back to itself rather than judging the world (founder,
    # 2026-09-04). What it is actually for is that these six exist and are shaped correctly.
    assert {
        "FounderSurfaceDown",
        "MacScreenSharingOff",
        "PersistentVolumeAlmostFull",
        "GatewayRefusals",
        "GatewayMetricsAbsent",
        "OttoDown",
    } <= set(rules)
    assert (
        rules["FounderSurfaceDown"]["expr"]
        == 'probe_success{job="founder-surfaces"} == 0'
    )
    assert rules["FounderSurfaceDown"]["labels"]["severity"] == "critical"
    pvc = rules["PersistentVolumeAlmostFull"]
    assert (
        "kubelet_volume_stats_available_bytes / kubelet_volume_stats_capacity_bytes < 0.10"
        in pvc["expr"]
    )
    assert (
        pvc["labels"]["severity"] == "warning"
    )  # the severity Alertmanager forwards to Robusta
    for r in rules.values():
        assert r["expr"].count("{") == r["expr"].count("}") and r["for"].endswith("m")
        assert r["annotations"]["summary"]


def test_collector_reads_rules_and_the_alertmanager_proxy_and_the_grader_fails_on_zero():
    cs = (IDP / "platform/state/cluster-state.yaml").read_text()
    role = one(
        "platform/state/cluster-state.yaml", "ClusterRole", "cluster-state-reader"
    )
    grants = {
        (g, r, v)
        for rule in role["rules"]
        for g in rule["apiGroups"]
        for r in rule["resources"]
        for v in rule["verbs"]
    }
    assert ("monitoring.coreos.com", "prometheusrules", "list") in grants
    assert ("", "services/proxy", "get") in grants
    (proxy,) = [rule for rule in role["rules"] if "services/proxy" in rule["resources"]]
    assert proxy["resourceNames"] == ["kps-alertmanager:9093"]
    assert "/apis/monitoring.coreos.com/v1/prometheusrules" in cs
    assert "services/kps-alertmanager:9093/proxy/api/v2/alerts" in cs
    assert "monitoring_rules={monitoring_rules} alert_watchdog={alert_watchdog}" in cs
    grader = (IDP / "bin/idp-cluster-state").read_text()
    assert 'if "monitoring_rules" not in kv or "alert_watchdog" not in kv' in grader
    assert (
        'int(kv["monitoring_rules"]) == 0 or int(kv["alert_watchdog"]) == 0' in grader
    )


def grade(line1, body="{}"):
    # run only the python half of bin/idp-cluster-state, with a fresh head, the way the script does
    src = (IDP / "bin/idp-cluster-state").read_text()
    py = src.split("<<'PY'\n", 1)[1].split("\nPY\n", 1)[0]
    head = '{"last-modified": "%s", "date": "%s"}' % (
        (__import__("email.utils").utils.formatdate(usegmt=True),) * 2
    )
    r = subprocess.run(
        [sys.executable, "-c", py, head, line1 + "\n" + body, "60", ""],
        capture_output=True,
        text=True,
        env={**os.environ, "IDP_LIB": str(IDP / "bin" / "lib")},
    )
    return r.returncode, r.stdout.strip()


BASE = (
    "ok cluster-state at 2026-08-27T23:00:00Z nodes=2 ready=2 pods=60 pods_not_ready=0 flux=40 flux_not_ready=0"
    " ds=6 ds_short=0 deploy_short=0 events_warning=0 hostnames=9 spiffe_ids=3 spiffe_workloads=3 svids=3 spire_agents=2"
    " oci_pods=2 oci_static_key_pods=0 policy_exceptions=9 cpu_used_pct=12 cpu_req_pct=45 mem_used_pct=30 mem_req_pct=50 secret_stale_consumers=0"
)


def test_grader_passes_with_rules_and_watchdog_and_fails_without():
    rc, out = grade(BASE + " monitoring_rules=31 alert_watchdog=1")
    assert rc == 0 and out.startswith("ok"), out
    rc, out = grade(BASE)
    assert rc == 1 and "monitoring_rules/alert_watchdog" in out, out
    rc, out = grade(
        BASE + " monitoring_rules=0 alert_watchdog=0",
        '{"monitoring": {"error": "alertmanager: HTTP 503"}}',
    )
    assert rc == 1 and "alert_watchdog=0" in out and "HTTP 503" in out, out
    rc, out = grade(BASE + " monitoring_rules=31 alert_watchdog=0")
    assert rc == 1, out


def test_broken_workload_alert_lists_namespace_monitoring():
    alert = one("platform/alerts/alert.yaml", "Alert", "broken-workload")
    ns = {
        s["namespace"]
        for s in alert["spec"]["eventSources"]
        if s["kind"] == "HelmRelease"
    }
    assert "monitoring" in ns
    assert (IDP / "docs/how-to/onboarding/monitoring.md").exists()
    (row,) = [
        r
        for r in yaml.safe_load((IDP / "drills/catalogue.yaml").read_text())["drills"]
        if r["name"] == "cluster-state"
    ]
    assert "Watchdog" in row["proves"]


def test_gateway_refusals_are_scraped_and_alerted():
    """crew#498 folded into crew#539: the MCP gateway's refusals are a Prometheus alert. The stats
    listener (15020) is exposed as port `metrics` on the Deployment and the Service, the
    ServiceMonitor in rules/ (a monitoring.coreos.com CR, after the CRDs) scrapes it from
    namespace mcp, and GatewayRefusals reads agentgateway_requests_total by status."""
    dep = one("platform/mcp/agentgateway-deploy.yaml", "Deployment", "agentgateway")
    (c,) = [
        c
        for c in dep["spec"]["template"]["spec"]["containers"]
        if c["name"] == "agentgateway"
    ]
    assert {"name": "metrics", "containerPort": 15020} in c["ports"], c["ports"]
    svc = one("platform/mcp/agentgateway-deploy.yaml", "Service", "agentgateway")
    assert {"name": "metrics", "port": 15020, "targetPort": "metrics"} in svc["spec"][
        "ports"
    ]
    sm = one(
        "platform/monitoring/rules/agentgateway-servicemonitor.yaml",
        "ServiceMonitor",
        "agentgateway",
    )
    assert sm["spec"]["namespaceSelector"]["matchNames"] == ["mcp"]
    assert (
        sm["spec"]["selector"]["matchLabels"].items()
        <= svc["metadata"]["labels"].items()
    )
    assert sm["spec"]["endpoints"][0]["port"] == "metrics"
    pr = one("platform/monitoring/rules/estate.yaml", "PrometheusRule", "estate")
    (r,) = [
        r
        for g in pr["spec"]["groups"]
        for r in g["rules"]
        if r.get("alert") == "GatewayRefusals"
    ]
    assert (
        'agentgateway_requests_total{status=~"4..|5.."}' in r["expr"]
        and r["for"] == "5m"
    )
    assert (
        r["labels"]["severity"] == "warning"
    )  # warnings reach Telegram and Robusta both
