# Flux: what is applied

Read from the cluster receipt taken at 2026-09-04T12:15:09Z. Every Kustomization and HelmRelease, with the revision Flux last applied. **Suspended** is a switch somebody turned off on purpose (temporal, commerce, commerce-data, event-bus), not a defect; **Unknown** is a row Flux has never graded.

**86 objects: 80 ready, 3 not ready, 0 unknown, 3 suspended.**

## Not ready right now

- **Kustomization flux-system/hermes-agent** since 2026-09-04T12:07:33Z: Reconciliation in progress
- **Kustomization flux-system/notify** since 2026-09-04T12:09:09Z: Reconciliation in progress
- **Kustomization flux-system/otto-gateway** since 2026-09-04T12:12:46Z: Reconciliation in progress

## Every row

| Kind | Namespace | Name | State | Applied revision | Since | Message |
|---|---|---|---|---|---|---|
| Kustomization | flux-system | hermes-agent | Not ready | main@7e4f1e6 | 2026-09-04T12:07:33Z | Reconciliation in progress |
| Kustomization | flux-system | notify | Not ready | main@5b24fda | 2026-09-04T12:09:09Z | Reconciliation in progress |
| Kustomization | flux-system | otto-gateway | Not ready | main@cf93f87 | 2026-09-04T12:12:46Z | Reconciliation in progress |
| Kustomization | flux-system | commerce | Suspended |  |  |  |
| Kustomization | flux-system | commerce-data | Suspended |  |  |  |
| Kustomization | flux-system | temporal | Suspended | main@1b323ac | 2026-08-30T05:54:22Z |  |
| HelmRelease | cert-manager | cert-manager | Ready | v1.21.1 | 2026-08-31T07:10:44Z |  |
| HelmRelease | chaos-mesh | chaos-mesh | Ready | 2.8.4 | 2026-08-31T07:12:00Z |  |
| HelmRelease | dagster | dagster | Ready | 1.13.19 | 2026-09-02T19:57:44Z |  |
| HelmRelease | edge | external-dns | Ready | 1.21.1 | 2026-08-31T07:11:28Z |  |
| HelmRelease | edge | traefik | Ready | 41.3.0 | 2026-08-31T07:10:46Z |  |
| HelmRelease | event-bus | nats | Ready | 2.14.6 | 2026-09-04T12:12:19Z |  |
| HelmRelease | external-secrets | external-secrets | Ready | 2.9.0 | 2026-09-02T11:40:21Z |  |
| HelmRelease | healing | descheduler | Ready | 0.36.0 | 2026-08-31T07:11:29Z |  |
| HelmRelease | healing | k8sgpt-operator | Ready | 0.2.29 | 2026-08-31T07:11:29Z |  |
| HelmRelease | hindsight | hindsight | Ready | 0.9.2 | 2026-09-02T23:12:33Z |  |
| HelmRelease | identity | oauth2-proxy | Ready | 10.7.0 | 2026-08-29T07:33:02Z |  |
| HelmRelease | keda | keda | Ready | 2.20.2 | 2026-08-31T07:14:43Z |  |
| HelmRelease | keda | keda-add-ons-http | Ready | 0.15.0 | 2026-08-31T07:14:44Z |  |
| HelmRelease | kyverno | kyverno | Ready | 3.9.0 | 2026-09-04T11:31:56Z |  |
| HelmRelease | metrics-server | metrics-server | Ready | 3.14.0 | 2026-08-31T07:11:28Z |  |
| HelmRelease | monitoring | blackbox | Ready | 11.17.2 | 2026-08-31T07:12:07Z |  |
| HelmRelease | monitoring | kube-prometheus-stack | Ready | 88.6.0 | 2026-08-31T07:12:05Z |  |
| HelmRelease | observability | langfuse | Ready | 2.0.2 | 2026-08-31T07:14:04Z |  |
| HelmRelease | observability | signoz | Ready | 0.138.0 | 2026-08-31T07:12:44Z |  |
| HelmRelease | observability | superset | Ready | 0.22.4 | 2026-09-03T13:21:03Z |  |
| HelmRelease | observability-agent | k8s-infra | Ready | 0.17.0 | 2026-09-03T15:19:29Z |  |
| HelmRelease | reloader | reloader | Ready | 2.2.16 | 2026-08-31T07:11:24Z |  |
| HelmRelease | robusta | robusta | Ready | 0.48.0 | 2026-08-31T07:12:01Z |  |
| HelmRelease | spire-mgmt | spire | Ready | 0.30.1 | 2026-08-31T07:12:31Z |  |
| HelmRelease | spire-mgmt | spire-crds | Ready | 0.6.1 | 2026-08-31T07:12:02Z |  |
| HelmRelease | tailscale | tailscale-operator | Ready | 1.102.3 | 2026-09-02T16:32:30Z |  |
| HelmRelease | temporal | temporal | Ready | 1.6.0 | 2026-08-29T19:01:39Z |  |
| HelmRelease | weave-gitops | weave-gitops | Ready | 4.0.36 | 2026-09-04T08:56:00Z |  |
| Kustomization | flux-system | alerts | Ready | main@cf93f87 | 2026-09-04T12:11:51Z |  |
| Kustomization | flux-system | alerts-github | Ready | main@cf93f87 | 2026-09-04T12:11:45Z |  |
| Kustomization | flux-system | alerts-secret | Ready | main@cf93f87 | 2026-09-04T12:11:40Z |  |
| Kustomization | flux-system | autoscaler | Ready | main@cf93f87 | 2026-09-04T12:11:53Z |  |
| Kustomization | flux-system | backstage | Ready | main@cf93f87 | 2026-09-04T12:11:54Z |  |
| Kustomization | flux-system | backstage-namespace | Ready | main@cf93f87 | 2026-09-04T12:11:01Z |  |
| Kustomization | flux-system | chaos | Ready | main@cf93f87 | 2026-09-04T12:12:15Z |  |
| Kustomization | flux-system | chaos-mesh | Ready | main@cf93f87 | 2026-09-04T12:11:38Z |  |
| Kustomization | flux-system | cluster-state | Ready | main@cf93f87 | 2026-09-04T12:11:48Z |  |
| Kustomization | flux-system | dagster | Ready | main@cf93f87 | 2026-09-04T12:11:44Z |  |
| Kustomization | flux-system | dns | Ready | main@cf93f87 | 2026-09-04T12:11:52Z |  |
| Kustomization | flux-system | drills | Ready | main@cf93f87 | 2026-09-04T12:11:46Z |  |
| Kustomization | flux-system | edge | Ready | main@cf93f87 | 2026-09-04T12:11:32Z |  |
| Kustomization | flux-system | estate-catalog | Ready | latest@sha256:f8c09d5b5b7dcd73c8f914f0f5 | 2026-09-04T12:07:07Z |  |
| Kustomization | flux-system | event-bus | Ready | main@cf93f87 | 2026-09-04T12:12:21Z |  |
| Kustomization | flux-system | external-secrets | Ready | main@cf93f87 | 2026-09-04T12:11:34Z |  |
| Kustomization | flux-system | flux-system | Ready | main@cf93f87 | 2026-09-04T12:11:06Z |  |
| Kustomization | flux-system | gateway-api-crds | Ready | v1.5.1@e7677b7 | 2026-09-04T12:11:03Z |  |
| Kustomization | flux-system | guacamole | Ready | main@cf93f87 | 2026-09-04T12:12:02Z |  |
| Kustomization | flux-system | healing | Ready | main@cf93f87 | 2026-09-04T12:12:13Z |  |
| Kustomization | flux-system | healing-analyzer | Ready | main@cf93f87 | 2026-09-04T12:12:14Z |  |
| Kustomization | flux-system | healthchecks | Ready | main@cf93f87 | 2026-09-04T12:12:08Z |  |
| Kustomization | flux-system | hindsight | Ready | main@cf93f87 | 2026-09-04T12:12:11Z |  |
| Kustomization | flux-system | human-vault | Ready | main@cf93f87 | 2026-09-04T12:11:43Z |  |
| Kustomization | flux-system | identity | Ready | main@cf93f87 | 2026-09-04T12:11:50Z |  |
| Kustomization | flux-system | image-automation | Ready | main@cf93f87 | 2026-09-04T12:11:51Z |  |
| Kustomization | flux-system | infra-crew | Ready | main@cf93f87 | 2026-09-04T12:12:05Z |  |
| Kustomization | flux-system | keda | Ready | main@cf93f87 | 2026-09-04T12:11:43Z |  |
| Kustomization | flux-system | kyverno | Ready | main@cf93f87 | 2026-09-04T12:11:01Z |  |
| Kustomization | flux-system | llm | Ready | main@cf93f87 | 2026-09-04T12:12:04Z |  |
| Kustomization | flux-system | mcp | Ready | main@cf93f87 | 2026-09-04T12:12:10Z |  |
| Kustomization | flux-system | metrics-server | Ready | main@cf93f87 | 2026-09-04T12:11:37Z |  |
| Kustomization | flux-system | monitoring | Ready | main@cf93f87 | 2026-09-04T12:11:47Z |  |
| Kustomization | flux-system | monitoring-rules | Ready | main@cf93f87 | 2026-09-04T12:11:57Z |  |
| Kustomization | flux-system | observability | Ready | main@cf93f87 | 2026-09-04T12:12:13Z |  |
| Kustomization | flux-system | observability-collector | Ready | main@cf93f87 | 2026-09-04T12:11:41Z |  |
| Kustomization | flux-system | otto-golden | Ready | main@cf93f87 | 2026-09-04T12:12:06Z |  |
| Kustomization | flux-system | otto-golden-secret | Ready | main@cf93f87 | 2026-09-04T12:11:40Z |  |
| Kustomization | flux-system | priority-classes | Ready | main@cf93f87 | 2026-09-04T12:11:00Z |  |
| Kustomization | flux-system | prospector | Ready | main@9102232 | 2026-09-04T12:08:50Z |  |
| Kustomization | flux-system | prospector-platform | Ready | main@cf93f87 | 2026-09-04T12:11:37Z |  |
| Kustomization | flux-system | reloader | Ready | main@cf93f87 | 2026-09-04T12:11:39Z |  |
| Kustomization | flux-system | robusta | Ready | main@cf93f87 | 2026-09-04T12:11:45Z |  |
| Kustomization | flux-system | scheduling | Ready | main@cf93f87 | 2026-09-04T12:11:35Z |  |
| Kustomization | flux-system | science | Ready | main@cf93f87 | 2026-09-04T12:12:15Z |  |
| Kustomization | flux-system | searxng | Ready | main@cf93f87 | 2026-09-04T12:11:03Z |  |
| Kustomization | flux-system | secret-store | Ready | main@cf93f87 | 2026-09-04T12:11:36Z |  |
| Kustomization | flux-system | spire | Ready | main@cf93f87 | 2026-09-04T12:11:42Z |  |
| Kustomization | flux-system | staging | Ready | main@cf93f87 | 2026-09-04T12:11:00Z |  |
| Kustomization | flux-system | tailscale | Ready | main@cf93f87 | 2026-09-04T12:11:49Z |  |
| Kustomization | flux-system | verification | Ready | main@cf93f87 | 2026-09-04T12:11:55Z |  |
| Kustomization | flux-system | weave-gitops | Ready | main@cf93f87 | 2026-09-04T12:11:56Z |  |
