# Flux: what is applied

Read from the cluster receipt taken at 2026-09-03T14:00:10Z. Every Kustomization and HelmRelease, with the revision Flux last applied. **Suspended** is a switch somebody turned off on purpose (temporal, commerce, commerce-data, event-bus), not a defect; **Unknown** is a row Flux has never graded.

**82 objects: 73 ready, 4 not ready, 0 unknown, 5 suspended.**

## Not ready right now

- **Kustomization flux-system/chaos** since 2026-09-03T13:52:41Z: dependency 'flux-system/observability' is not ready
- **Kustomization flux-system/notify** since 2026-09-03T13:53:03Z: Reconciliation in progress
- **Kustomization flux-system/observability** since 2026-09-03T13:52:40Z: health check failed after 129.855827ms: failed early due to stalled resources: [Job/observability/superset-boardroom-seed status: 'Failed']
- **Kustomization flux-system/science** since 2026-09-03T13:17:35Z: dependency 'flux-system/observability' is not ready

## Every row

| Kind | Namespace | Name | State | Applied revision | Since | Message |
|---|---|---|---|---|---|---|
| Kustomization | flux-system | chaos | Not ready | main@b3affcc | 2026-09-03T13:52:41Z | dependency 'flux-system/observability' is not ready |
| Kustomization | flux-system | notify | Not ready | main@af6c137 | 2026-09-03T13:53:03Z | Reconciliation in progress |
| Kustomization | flux-system | observability | Not ready | main@b3affcc | 2026-09-03T13:52:40Z | health check failed after 129.855827ms: failed early due to stalled resources: [Job/observability/superset-boardroom-seed status: 'Failed'] |
| Kustomization | flux-system | science | Not ready | main@b3affcc | 2026-09-03T13:17:35Z | dependency 'flux-system/observability' is not ready |
| Kustomization | flux-system | commerce | Suspended |  |  |  |
| Kustomization | flux-system | commerce-data | Suspended |  |  |  |
| Kustomization | flux-system | event-bus | Suspended |  |  |  |
| Kustomization | flux-system | otto-gateway | Suspended |  |  |  |
| Kustomization | flux-system | temporal | Suspended | main@1b323ac | 2026-08-30T05:54:22Z |  |
| HelmRelease | cert-manager | cert-manager | Ready | v1.21.1 | 2026-08-31T07:10:44Z |  |
| HelmRelease | chaos-mesh | chaos-mesh | Ready | 2.8.4 | 2026-08-31T07:12:00Z |  |
| HelmRelease | dagster | dagster | Ready | 1.13.19 | 2026-09-02T19:57:44Z |  |
| HelmRelease | edge | external-dns | Ready | 1.21.1 | 2026-08-31T07:11:28Z |  |
| HelmRelease | edge | traefik | Ready | 41.3.0 | 2026-08-31T07:10:46Z |  |
| HelmRelease | external-secrets | external-secrets | Ready | 2.9.0 | 2026-09-02T11:40:21Z |  |
| HelmRelease | healing | descheduler | Ready | 0.36.0 | 2026-08-31T07:11:29Z |  |
| HelmRelease | healing | k8sgpt-operator | Ready | 0.2.29 | 2026-08-31T07:11:29Z |  |
| HelmRelease | hindsight | hindsight | Ready | 0.9.2 | 2026-09-02T23:12:33Z |  |
| HelmRelease | identity | oauth2-proxy | Ready | 10.7.0 | 2026-08-29T07:33:02Z |  |
| HelmRelease | keda | keda | Ready | 2.20.2 | 2026-08-31T07:14:43Z |  |
| HelmRelease | keda | keda-add-ons-http | Ready | 0.15.0 | 2026-08-31T07:14:44Z |  |
| HelmRelease | kyverno | kyverno | Ready | 3.9.0 | 2026-09-02T03:08:09Z |  |
| HelmRelease | metrics-server | metrics-server | Ready | 3.14.0 | 2026-08-31T07:11:28Z |  |
| HelmRelease | monitoring | blackbox | Ready | 11.17.2 | 2026-08-31T07:12:07Z |  |
| HelmRelease | monitoring | kube-prometheus-stack | Ready | 88.6.0 | 2026-08-31T07:12:05Z |  |
| HelmRelease | observability | langfuse | Ready | 2.0.2 | 2026-08-31T07:14:04Z |  |
| HelmRelease | observability | signoz | Ready | 0.138.0 | 2026-08-31T07:12:44Z |  |
| HelmRelease | observability | superset | Ready | 0.22.4 | 2026-09-03T13:21:03Z |  |
| HelmRelease | observability-agent | k8s-infra | Ready | 0.17.0 | 2026-08-31T03:17:25Z |  |
| HelmRelease | reloader | reloader | Ready | 2.2.16 | 2026-08-31T07:11:24Z |  |
| HelmRelease | robusta | robusta | Ready | 0.48.0 | 2026-08-31T07:12:01Z |  |
| HelmRelease | spire-mgmt | spire | Ready | 0.30.1 | 2026-08-31T07:12:31Z |  |
| HelmRelease | spire-mgmt | spire-crds | Ready | 0.6.1 | 2026-08-31T07:12:02Z |  |
| HelmRelease | tailscale | tailscale-operator | Ready | 1.102.3 | 2026-09-02T16:32:30Z |  |
| HelmRelease | temporal | temporal | Ready | 1.6.0 | 2026-08-29T19:01:39Z |  |
| Kustomization | flux-system | alerts | Ready | main@af6c137 | 2026-09-03T13:52:38Z |  |
| Kustomization | flux-system | alerts-github | Ready | main@af6c137 | 2026-09-03T13:52:39Z |  |
| Kustomization | flux-system | alerts-secret | Ready | main@af6c137 | 2026-09-03T13:52:37Z |  |
| Kustomization | flux-system | autoscaler | Ready | main@af6c137 | 2026-09-03T13:53:05Z |  |
| Kustomization | flux-system | backstage | Ready | main@af6c137 | 2026-09-03T13:52:41Z |  |
| Kustomization | flux-system | backstage-namespace | Ready | main@af6c137 | 2026-09-03T13:51:32Z |  |
| Kustomization | flux-system | chaos-mesh | Ready | main@af6c137 | 2026-09-03T13:52:40Z |  |
| Kustomization | flux-system | cluster-state | Ready | main@af6c137 | 2026-09-03T13:52:36Z |  |
| Kustomization | flux-system | dagster | Ready | main@af6c137 | 2026-09-03T13:52:38Z |  |
| Kustomization | flux-system | dns | Ready | main@af6c137 | 2026-09-03T13:53:07Z |  |
| Kustomization | flux-system | drills | Ready | main@af6c137 | 2026-09-03T13:52:42Z |  |
| Kustomization | flux-system | edge | Ready | main@af6c137 | 2026-09-03T13:52:00Z |  |
| Kustomization | flux-system | estate-catalog | Ready | latest@sha256:6ea0df74cfe64b1d0087f3f9eb | 2026-09-03T13:59:51Z |  |
| Kustomization | flux-system | external-secrets | Ready | main@af6c137 | 2026-09-03T13:52:30Z |  |
| Kustomization | flux-system | flux-system | Ready | main@af6c137 | 2026-09-03T13:51:33Z |  |
| Kustomization | flux-system | gateway-api-crds | Ready | v1.5.1@e7677b7 | 2026-09-03T13:51:33Z |  |
| Kustomization | flux-system | guacamole | Ready | main@af6c137 | 2026-09-03T13:52:40Z |  |
| Kustomization | flux-system | healing | Ready | main@af6c137 | 2026-09-03T13:53:37Z |  |
| Kustomization | flux-system | healing-analyzer | Ready | main@af6c137 | 2026-09-03T13:54:02Z |  |
| Kustomization | flux-system | healthchecks | Ready | main@af6c137 | 2026-09-03T13:53:09Z |  |
| Kustomization | flux-system | hermes-agent | Ready | main@af6c137 | 2026-09-03T13:52:43Z |  |
| Kustomization | flux-system | hindsight | Ready | main@af6c137 | 2026-09-03T13:53:34Z |  |
| Kustomization | flux-system | human-vault | Ready | main@af6c137 | 2026-09-03T13:53:06Z |  |
| Kustomization | flux-system | identity | Ready | main@af6c137 | 2026-09-03T13:52:37Z |  |
| Kustomization | flux-system | image-automation | Ready | main@af6c137 | 2026-09-03T13:52:42Z |  |
| Kustomization | flux-system | infra-crew | Ready | main@af6c137 | 2026-09-03T13:53:33Z |  |
| Kustomization | flux-system | keda | Ready | main@af6c137 | 2026-09-03T13:52:35Z |  |
| Kustomization | flux-system | kyverno | Ready | main@af6c137 | 2026-09-03T13:51:31Z |  |
| Kustomization | flux-system | llm | Ready | main@af6c137 | 2026-09-03T13:53:06Z |  |
| Kustomization | flux-system | mcp | Ready | main@af6c137 | 2026-09-03T13:53:10Z |  |
| Kustomization | flux-system | metrics-server | Ready | main@af6c137 | 2026-09-03T13:52:33Z |  |
| Kustomization | flux-system | monitoring | Ready | main@af6c137 | 2026-09-03T13:53:00Z |  |
| Kustomization | flux-system | monitoring-rules | Ready | main@af6c137 | 2026-09-03T13:53:05Z |  |
| Kustomization | flux-system | observability-collector | Ready | main@af6c137 | 2026-09-03T13:52:33Z |  |
| Kustomization | flux-system | otto-golden | Ready | main@af6c137 | 2026-09-03T13:53:09Z |  |
| Kustomization | flux-system | otto-golden-secret | Ready | main@af6c137 | 2026-09-03T13:53:02Z |  |
| Kustomization | flux-system | priority-classes | Ready | main@af6c137 | 2026-09-03T13:51:30Z |  |
| Kustomization | flux-system | prospector | Ready | main@5972126 | 2026-09-03T13:57:06Z |  |
| Kustomization | flux-system | prospector-platform | Ready | main@af6c137 | 2026-09-03T13:52:35Z |  |
| Kustomization | flux-system | reloader | Ready | main@af6c137 | 2026-09-03T13:52:37Z |  |
| Kustomization | flux-system | robusta | Ready | main@af6c137 | 2026-09-03T13:53:06Z |  |
| Kustomization | flux-system | scheduling | Ready | main@af6c137 | 2026-09-03T13:52:04Z |  |
| Kustomization | flux-system | secret-store | Ready | main@af6c137 | 2026-09-03T13:52:34Z |  |
| Kustomization | flux-system | spire | Ready | main@af6c137 | 2026-09-03T13:52:33Z |  |
| Kustomization | flux-system | staging | Ready | main@af6c137 | 2026-09-03T13:51:30Z |  |
| Kustomization | flux-system | tailscale | Ready | main@af6c137 | 2026-09-03T13:52:36Z |  |
| Kustomization | flux-system | verification | Ready | main@af6c137 | 2026-09-03T13:53:02Z |  |
