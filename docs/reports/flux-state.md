# Flux: what is applied

Read from the cluster receipt taken at 2026-09-03T09:15:10Z. Every Kustomization and HelmRelease, with the revision Flux last applied. **Suspended** is a switch somebody turned off on purpose (temporal, commerce, commerce-data, event-bus), not a defect; **Unknown** is a row Flux has never graded.

**81 objects: 75 ready, 2 not ready, 0 unknown, 4 suspended.**

## Not ready right now

- **Kustomization flux-system/hermes-agent** since 2026-09-03T09:07:05Z: Reconciliation in progress
- **Kustomization flux-system/notify** since 2026-09-03T09:06:56Z: Reconciliation in progress

## Every row

| Kind | Namespace | Name | State | Applied revision | Since | Message |
|---|---|---|---|---|---|---|
| Kustomization | flux-system | hermes-agent | Not ready | main@e613758 | 2026-09-03T09:07:05Z | Reconciliation in progress |
| Kustomization | flux-system | notify | Not ready | main@d691cb8 | 2026-09-03T09:06:56Z | Reconciliation in progress |
| Kustomization | flux-system | commerce | Suspended |  |  |  |
| Kustomization | flux-system | commerce-data | Suspended |  |  |  |
| Kustomization | flux-system | event-bus | Suspended |  |  |  |
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
| HelmRelease | observability | superset | Ready | 0.22.4 | 2026-09-03T04:49:46Z |  |
| HelmRelease | observability-agent | k8s-infra | Ready | 0.17.0 | 2026-08-31T03:17:25Z |  |
| HelmRelease | reloader | reloader | Ready | 2.2.16 | 2026-08-31T07:11:24Z |  |
| HelmRelease | robusta | robusta | Ready | 0.48.0 | 2026-08-31T07:12:01Z |  |
| HelmRelease | spire-mgmt | spire | Ready | 0.30.1 | 2026-08-31T07:12:31Z |  |
| HelmRelease | spire-mgmt | spire-crds | Ready | 0.6.1 | 2026-08-31T07:12:02Z |  |
| HelmRelease | tailscale | tailscale-operator | Ready | 1.102.3 | 2026-09-02T16:32:30Z |  |
| HelmRelease | temporal | temporal | Ready | 1.6.0 | 2026-08-29T19:01:39Z |  |
| Kustomization | flux-system | alerts | Ready | main@d691cb8 | 2026-09-03T09:07:24Z |  |
| Kustomization | flux-system | alerts-github | Ready | main@d691cb8 | 2026-09-03T09:06:57Z |  |
| Kustomization | flux-system | alerts-secret | Ready | main@d691cb8 | 2026-09-03T09:07:04Z |  |
| Kustomization | flux-system | autoscaler | Ready | main@d691cb8 | 2026-09-03T09:07:00Z |  |
| Kustomization | flux-system | backstage | Ready | main@d691cb8 | 2026-09-03T09:07:06Z |  |
| Kustomization | flux-system | backstage-namespace | Ready | main@d691cb8 | 2026-09-03T09:14:58Z |  |
| Kustomization | flux-system | chaos | Ready | main@d691cb8 | 2026-09-03T09:07:36Z |  |
| Kustomization | flux-system | chaos-mesh | Ready | main@d691cb8 | 2026-09-03T09:05:53Z |  |
| Kustomization | flux-system | cluster-state | Ready | main@d691cb8 | 2026-09-03T09:06:25Z |  |
| Kustomization | flux-system | dagster | Ready | main@d691cb8 | 2026-09-03T09:07:03Z |  |
| Kustomization | flux-system | dns | Ready | main@d691cb8 | 2026-09-03T09:06:25Z |  |
| Kustomization | flux-system | drills | Ready | main@d691cb8 | 2026-09-03T09:07:03Z |  |
| Kustomization | flux-system | edge | Ready | main@d691cb8 | 2026-09-03T09:05:51Z |  |
| Kustomization | flux-system | estate-catalog | Ready | latest@sha256:6ea0df74cfe64b1d0087f3f9eb | 2026-09-03T09:08:50Z |  |
| Kustomization | flux-system | external-secrets | Ready | main@d691cb8 | 2026-09-03T09:06:20Z |  |
| Kustomization | flux-system | flux-system | Ready | main@d691cb8 | 2026-09-03T09:05:24Z |  |
| Kustomization | flux-system | gateway-api-crds | Ready | v1.5.1@e7677b7 | 2026-09-03T09:15:03Z |  |
| Kustomization | flux-system | guacamole | Ready | main@d691cb8 | 2026-09-03T09:07:32Z |  |
| Kustomization | flux-system | healing | Ready | main@d691cb8 | 2026-09-03T09:06:59Z |  |
| Kustomization | flux-system | healing-analyzer | Ready | main@d691cb8 | 2026-09-03T09:07:05Z |  |
| Kustomization | flux-system | healthchecks | Ready | main@d691cb8 | 2026-09-03T09:07:27Z |  |
| Kustomization | flux-system | hindsight | Ready | main@d691cb8 | 2026-09-03T09:07:05Z |  |
| Kustomization | flux-system | human-vault | Ready | main@d691cb8 | 2026-09-03T09:07:02Z |  |
| Kustomization | flux-system | identity | Ready | main@d691cb8 | 2026-09-03T09:07:01Z |  |
| Kustomization | flux-system | image-automation | Ready | main@d691cb8 | 2026-09-03T09:07:00Z |  |
| Kustomization | flux-system | infra-crew | Ready | main@d691cb8 | 2026-09-03T09:06:59Z |  |
| Kustomization | flux-system | keda | Ready | main@d691cb8 | 2026-09-03T09:07:01Z |  |
| Kustomization | flux-system | kyverno | Ready | main@d691cb8 | 2026-09-03T09:05:22Z |  |
| Kustomization | flux-system | llm | Ready | main@d691cb8 | 2026-09-03T09:06:58Z |  |
| Kustomization | flux-system | mcp | Ready | main@d691cb8 | 2026-09-03T09:07:27Z |  |
| Kustomization | flux-system | metrics-server | Ready | main@d691cb8 | 2026-09-03T09:06:24Z |  |
| Kustomization | flux-system | monitoring | Ready | main@d691cb8 | 2026-09-03T09:06:56Z |  |
| Kustomization | flux-system | monitoring-rules | Ready | main@d691cb8 | 2026-09-03T09:06:58Z |  |
| Kustomization | flux-system | observability | Ready | main@d691cb8 | 2026-09-03T09:06:25Z |  |
| Kustomization | flux-system | observability-collector | Ready | main@d691cb8 | 2026-09-03T09:05:54Z |  |
| Kustomization | flux-system | otto-golden | Ready | main@d691cb8 | 2026-09-03T09:07:01Z |  |
| Kustomization | flux-system | otto-golden-secret | Ready | main@d691cb8 | 2026-09-03T09:06:58Z |  |
| Kustomization | flux-system | priority-classes | Ready | main@d691cb8 | 2026-09-03T09:05:21Z |  |
| Kustomization | flux-system | prospector | Ready | main@3da7ac7 | 2026-09-03T09:13:53Z |  |
| Kustomization | flux-system | prospector-platform | Ready | main@d691cb8 | 2026-09-03T09:06:24Z |  |
| Kustomization | flux-system | reloader | Ready | main@d691cb8 | 2026-09-03T09:07:04Z |  |
| Kustomization | flux-system | robusta | Ready | main@d691cb8 | 2026-09-03T09:06:55Z |  |
| Kustomization | flux-system | scheduling | Ready | main@d691cb8 | 2026-09-03T09:05:52Z |  |
| Kustomization | flux-system | science | Ready | main@d691cb8 | 2026-09-03T09:06:57Z |  |
| Kustomization | flux-system | secret-store | Ready | main@d691cb8 | 2026-09-03T09:06:50Z |  |
| Kustomization | flux-system | spire | Ready | main@d691cb8 | 2026-09-03T09:06:20Z |  |
| Kustomization | flux-system | staging | Ready | main@d691cb8 | 2026-09-03T09:05:22Z |  |
| Kustomization | flux-system | tailscale | Ready | main@d691cb8 | 2026-09-03T09:07:03Z |  |
| Kustomization | flux-system | verification | Ready | main@d691cb8 | 2026-09-03T09:06:55Z |  |
