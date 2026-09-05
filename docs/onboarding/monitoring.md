# Onboarding: monitoring (Prometheus, Alertmanager, the founder-surface probe)

crew#539 DoD item 1. One Prometheus and one Alertmanager (kube-prometheus-stack 88.6.0 in
namespace `monitoring`) evaluate rules every minute and page the founder's Telegram — the same
vault entry the Flux alerts use, so nothing here holds a token. Warnings and criticals also reach
Robusta (`platform/robusta`), which is how a PVC over 90 % fires a playbook (CP14).

Nothing to do per workload for the built-in rules. What fires without touching your service:
- `KubePodNotReady`, `KubePodCrashLooping`, `KubeDeploymentReplicasMismatch` (kube-state-metrics)
- `KubeNodeNotReady`, `KubeNodeUnreachable`
- `TargetDown` for any scrape target, `KubePersistentVolumeFillingUp`
- `FounderSurfaceDown`: a founder surface failed its in-cluster GET for 5 minutes
- `PersistentVolumeAlmostFull`: a PVC under 10 % free for 10 minutes (→ Telegram + Robusta)
- `GatewayRefusals`: the MCP gateway answered 4xx/5xx for 5 minutes; `GatewayMetricsAbsent` when its scrape is gone (crew#498)
- `Watchdog`: always firing; the receipt reads it as proof the pipeline evaluates and delivers

Adding a rule: a `PrometheusRule` in your namespace is honoured (`ruleSelectorNilUsesHelmValues:
false`); the estate's own live in `platform/monitoring/rules/estate.yaml`. Scraping your own metrics: a
`ServiceMonitor` or `PodMonitor` next to your workload, same rule. Every namespace Deployment is
expected to be covered by a rule — `bin/idp-cluster-state` fails when the cluster holds no
PrometheusRule or Alertmanager does not show `Watchdog`.

Probed founder surfaces (`platform/monitoring/rules/founder-surfaces-probe.yaml`) are the URLs of
`backstage/founder/catalog-info.yaml` with `${ESTATE_ZONE}` substituted by Flux; a test keeps the
two lists equal, so add a surface to the catalogue and to the Probe in the same PR.

Demo, from a laptop with no kube path (the CI runner does the same):

    bin/idp-cluster-state
    # ok      cluster-state  ok cluster-state at ... monitoring_rules=N alert_watchdog=1 (M min ago)

Drill (crew#539 DoD item 2, `platform/chaos/langfuse-alert-drill.yaml`): every Monday 03:30Z a
Chaos Mesh Schedule fails every langfuse-web pod for 8 minutes (nobody scales a Deployment from a
laptop, ADR 0005). A Task beside it polls Alertmanager for an active `FounderSurfaceDown` whose
instance is langfuse and Prometheus for `alertmanager_notifications_total{integration="telegram"}`
rising, then writes one line to the drill-receipts bucket from the node's identity:

    ok langfuse-alert-drill FounderSurfaceDown firing for https://langfuse.<zone> telegram_notifications=N after Ns at <time>

`langfuse-alert-drill-first-run.yaml` is the same Workflow run once on the day it is applied, so
the receipt exists before the first Monday. Graded from outside the cluster, no kube path:

    bin/idp-chaos-drill langfuse-alert-drill alert-drill
    # ok      alert-drill  ok langfuse-alert-drill FounderSurfaceDown firing for ... (Hh old, max 194h)

`drills/catalogue.yaml` row `alert-drill` runs that in `oke-check.yml`; a missing, stale or FAIL
receipt is a red job, silence is never green. The receipt's `monitoring.alerts_firing` in
`bin/idp-cluster-state` lists what Alertmanager holds right now.

SigNoz remains the long store for logs, traces and metrics (`docs/onboarding/k8s-infra.md`);
this Prometheus keeps two days and exists to alert. Changing it: edit the `values:` block in
`platform/monitoring/kube-prometheus-stack.yaml`, run `bin/idp-kyverno-render platform/monitoring`,
open the PR.
