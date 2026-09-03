# Flux: what is applied

Read from the cluster receipt taken at 2026-09-03T08:00:13Z. Every Kustomization and HelmRelease, with the revision Flux last applied. **Suspended** is a switch somebody turned off on purpose (temporal, commerce, commerce-data, event-bus), not a defect; **Unknown** is a row Flux has never graded.

**81 objects: 76 ready, 1 not ready, 0 unknown, 4 suspended.**

## Not ready right now

- **Kustomization flux-system/notify** since 2026-09-03T08:00:04Z: health check failed after 9m35.096000034s: failed early due to stalled resources: [Deployment/notify/apprise status: 'Failed']

## Every row

| Kind | Namespace | Name | State | Applied revision | Since | Message |
|---|---|---|---|---|---|---|
| Kustomization | flux-system | notify | Not ready | main@43c962d | 2026-09-03T08:00:04Z | health check failed after 9m35.096000034s: failed early due to stalled resources: [Deployment/notify/apprise status: 'Failed'] |
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
| Kustomization | flux-system | alerts | Ready | main@43c962d | 2026-09-03T07:50:30Z |  |
| Kustomization | flux-system | alerts-github | Ready | main@43c962d | 2026-09-03T07:50:31Z |  |
| Kustomization | flux-system | alerts-secret | Ready | main@43c962d | 2026-09-03T08:00:01Z |  |
| Kustomization | flux-system | autoscaler | Ready | main@43c962d | 2026-09-03T07:59:58Z |  |
| Kustomization | flux-system | backstage | Ready | main@43c962d | 2026-09-03T07:50:37Z |  |
| Kustomization | flux-system | backstage-namespace | Ready | main@43c962d | 2026-09-03T07:59:17Z |  |
| Kustomization | flux-system | chaos | Ready | main@43c962d | 2026-09-03T07:51:07Z |  |
| Kustomization | flux-system | chaos-mesh | Ready | main@43c962d | 2026-09-03T07:50:31Z |  |
| Kustomization | flux-system | cluster-state | Ready | main@43c962d | 2026-09-03T07:50:28Z |  |
| Kustomization | flux-system | dagster | Ready | main@43c962d | 2026-09-03T07:50:32Z |  |
| Kustomization | flux-system | dns | Ready | main@43c962d | 2026-09-03T07:50:34Z |  |
| Kustomization | flux-system | drills | Ready | main@43c962d | 2026-09-03T07:51:02Z |  |
| Kustomization | flux-system | edge | Ready | main@43c962d | 2026-09-03T07:59:48Z |  |
| Kustomization | flux-system | estate-catalog | Ready | latest@sha256:365fb683f5b3654ea5ec614999 | 2026-09-03T07:59:10Z |  |
| Kustomization | flux-system | external-secrets | Ready | main@43c962d | 2026-09-03T07:49:56Z |  |
| Kustomization | flux-system | flux-system | Ready | main@43c962d | 2026-09-03T07:59:31Z |  |
| Kustomization | flux-system | gateway-api-crds | Ready | v1.5.1@e7677b7 | 2026-09-03T07:59:02Z |  |
| Kustomization | flux-system | guacamole | Ready | main@43c962d | 2026-09-03T07:51:04Z |  |
| Kustomization | flux-system | healing | Ready | main@43c962d | 2026-09-03T07:50:59Z |  |
| Kustomization | flux-system | healing-analyzer | Ready | main@43c962d | 2026-09-03T07:51:03Z |  |
| Kustomization | flux-system | healthchecks | Ready | main@43c962d | 2026-09-03T07:51:00Z |  |
| Kustomization | flux-system | hermes-agent | Ready | main@43c962d | 2026-09-03T07:50:58Z |  |
| Kustomization | flux-system | hindsight | Ready | main@43c962d | 2026-09-03T08:00:08Z |  |
| Kustomization | flux-system | human-vault | Ready | main@43c962d | 2026-09-03T07:50:35Z |  |
| Kustomization | flux-system | identity | Ready | main@43c962d | 2026-09-03T07:50:35Z |  |
| Kustomization | flux-system | image-automation | Ready | main@43c962d | 2026-09-03T07:50:52Z |  |
| Kustomization | flux-system | infra-crew | Ready | main@43c962d | 2026-09-03T07:50:37Z |  |
| Kustomization | flux-system | keda | Ready | main@43c962d | 2026-09-03T07:51:01Z |  |
| Kustomization | flux-system | kyverno | Ready | main@43c962d | 2026-09-03T07:59:50Z |  |
| Kustomization | flux-system | llm | Ready | main@43c962d | 2026-09-03T08:00:02Z |  |
| Kustomization | flux-system | mcp | Ready | main@43c962d | 2026-09-03T07:51:01Z |  |
| Kustomization | flux-system | metrics-server | Ready | main@43c962d | 2026-09-03T07:50:26Z |  |
| Kustomization | flux-system | monitoring | Ready | main@43c962d | 2026-09-03T07:50:32Z |  |
| Kustomization | flux-system | monitoring-rules | Ready | main@43c962d | 2026-09-03T07:50:33Z |  |
| Kustomization | flux-system | observability | Ready | main@43c962d | 2026-09-03T07:50:36Z |  |
| Kustomization | flux-system | observability-collector | Ready | main@43c962d | 2026-09-03T07:50:25Z |  |
| Kustomization | flux-system | otto-golden | Ready | main@43c962d | 2026-09-03T07:51:00Z |  |
| Kustomization | flux-system | otto-golden-secret | Ready | main@43c962d | 2026-09-03T07:50:33Z |  |
| Kustomization | flux-system | priority-classes | Ready | main@43c962d | 2026-09-03T07:59:34Z |  |
| Kustomization | flux-system | prospector | Ready | main@3da7ac7 | 2026-09-03T07:53:45Z |  |
| Kustomization | flux-system | prospector-platform | Ready | main@43c962d | 2026-09-03T07:50:33Z |  |
| Kustomization | flux-system | reloader | Ready | main@43c962d | 2026-09-03T08:00:07Z |  |
| Kustomization | flux-system | robusta | Ready | main@43c962d | 2026-09-03T07:50:28Z |  |
| Kustomization | flux-system | scheduling | Ready | main@43c962d | 2026-09-03T07:59:33Z |  |
| Kustomization | flux-system | science | Ready | main@43c962d | 2026-09-03T07:51:01Z |  |
| Kustomization | flux-system | secret-store | Ready | main@43c962d | 2026-09-03T07:50:22Z |  |
| Kustomization | flux-system | spire | Ready | main@43c962d | 2026-09-03T07:50:26Z |  |
| Kustomization | flux-system | staging | Ready | main@43c962d | 2026-09-03T07:59:38Z |  |
| Kustomization | flux-system | tailscale | Ready | main@43c962d | 2026-09-03T07:50:31Z |  |
| Kustomization | flux-system | verification | Ready | main@43c962d | 2026-09-03T07:50:29Z |  |
