# Flux: what is applied

Read from the cluster receipt taken at 2026-09-03T11:00:11Z. Every Kustomization and HelmRelease, with the revision Flux last applied. **Suspended** is a switch somebody turned off on purpose (temporal, commerce, commerce-data, event-bus), not a defect; **Unknown** is a row Flux has never graded.

**82 objects: 34 ready, 43 not ready, 0 unknown, 5 suspended.**

## Not ready right now

- **Kustomization flux-system/alerts** since 2026-09-03T10:59:37Z: dependency 'flux-system/alerts-secret' revision is not up to date
- **Kustomization flux-system/alerts-github** since 2026-09-03T10:59:37Z: dependency 'flux-system/secret-store' revision is not up to date
- **Kustomization flux-system/alerts-secret** since 2026-09-03T10:59:37Z: dependency 'flux-system/secret-store' revision is not up to date
- **Kustomization flux-system/autoscaler** since 2026-09-03T10:59:37Z: dependency 'flux-system/secret-store' revision is not up to date
- **Kustomization flux-system/backstage** since 2026-09-03T10:59:37Z: dependency 'flux-system/external-secrets' is not ready
- **Kustomization flux-system/chaos** since 2026-09-03T10:59:38Z: dependency 'flux-system/chaos-mesh' is not ready
- **Kustomization flux-system/chaos-mesh** since 2026-09-03T10:59:37Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/cluster-state** since 2026-09-03T10:59:37Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/dagster** since 2026-09-03T10:59:37Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/dns** since 2026-09-03T10:59:37Z: dependency 'flux-system/edge' is not ready
- **Kustomization flux-system/drills** since 2026-09-03T10:59:37Z: dependency 'flux-system/alerts-github' is not ready
- **Kustomization flux-system/external-secrets** since 2026-09-03T11:00:03Z: dependency 'flux-system/edge' is not ready
- **Kustomization flux-system/guacamole** since 2026-09-03T10:59:38Z: dependency 'flux-system/identity' is not ready
- **Kustomization flux-system/healing** since 2026-09-03T10:59:38Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/healing-analyzer** since 2026-09-03T10:59:37Z: dependency 'flux-system/healing' revision is not up to date
- **Kustomization flux-system/healthchecks** since 2026-09-03T10:59:38Z: dependency 'flux-system/identity' is not ready
- **Kustomization flux-system/hermes-agent** since 2026-09-03T10:59:38Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/hindsight** since 2026-09-03T10:59:37Z: dependency 'flux-system/secret-store' revision is not up to date
- **Kustomization flux-system/human-vault** since 2026-09-03T10:59:37Z: dependency 'flux-system/external-secrets' is not ready
- **Kustomization flux-system/identity** since 2026-09-03T10:59:37Z: dependency 'flux-system/edge' is not ready
- **Kustomization flux-system/image-automation** since 2026-09-03T10:59:37Z: dependency 'flux-system/secret-store' revision is not up to date
- **Kustomization flux-system/infra-crew** since 2026-09-03T10:59:38Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/keda** since 2026-09-03T10:59:38Z: dependency 'flux-system/observability' revision is not up to date
- **Kustomization flux-system/llm** since 2026-09-03T10:59:37Z: dependency 'flux-system/edge' is not ready
- **Kustomization flux-system/mcp** since 2026-09-03T10:59:38Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/metrics-server** since 2026-09-03T10:59:37Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/monitoring** since 2026-09-03T10:59:37Z: dependency 'flux-system/edge' is not ready
- **Kustomization flux-system/monitoring-rules** since 2026-09-03T10:59:37Z: dependency 'flux-system/monitoring' revision is not up to date
- **Kustomization flux-system/notify** since 2026-09-03T10:59:38Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/observability** since 2026-09-03T10:59:38Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/observability-collector** since 2026-09-03T10:59:37Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/otto-golden** since 2026-09-03T10:59:38Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/otto-golden-secret** since 2026-09-03T10:59:37Z: dependency 'flux-system/secret-store' revision is not up to date
- **Kustomization flux-system/prospector** since 2026-09-03T10:59:38Z: dependency 'flux-system/prospector-platform' is not ready
- **Kustomization flux-system/prospector-platform** since 2026-09-03T10:59:38Z: dependency 'flux-system/edge' is not ready
- **Kustomization flux-system/reloader** since 2026-09-03T10:59:38Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/robusta** since 2026-09-03T10:59:37Z: dependency 'flux-system/secret-store' revision is not up to date
- **Kustomization flux-system/scheduling** since 2026-09-03T11:00:03Z: dependency 'flux-system/edge' is not ready
- **Kustomization flux-system/science** since 2026-09-03T10:59:38Z: dependency 'flux-system/observability' revision is not up to date
- **Kustomization flux-system/secret-store** since 2026-09-03T10:59:38Z: dependency 'flux-system/external-secrets' is not ready
- **Kustomization flux-system/spire** since 2026-09-03T10:59:37Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/tailscale** since 2026-09-03T10:59:37Z: dependency 'flux-system/secret-store' revision is not up to date
- **Kustomization flux-system/verification** since 2026-09-03T10:59:37Z: dependency 'flux-system/external-secrets' is not ready

## Every row

| Kind | Namespace | Name | State | Applied revision | Since | Message |
|---|---|---|---|---|---|---|
| Kustomization | flux-system | alerts | Not ready | main@44e7427 | 2026-09-03T10:59:37Z | dependency 'flux-system/alerts-secret' revision is not up to date |
| Kustomization | flux-system | alerts-github | Not ready | main@44e7427 | 2026-09-03T10:59:37Z | dependency 'flux-system/secret-store' revision is not up to date |
| Kustomization | flux-system | alerts-secret | Not ready | main@44e7427 | 2026-09-03T10:59:37Z | dependency 'flux-system/secret-store' revision is not up to date |
| Kustomization | flux-system | autoscaler | Not ready | main@44e7427 | 2026-09-03T10:59:37Z | dependency 'flux-system/secret-store' revision is not up to date |
| Kustomization | flux-system | backstage | Not ready | main@44e7427 | 2026-09-03T10:59:37Z | dependency 'flux-system/external-secrets' is not ready |
| Kustomization | flux-system | chaos | Not ready | main@44e7427 | 2026-09-03T10:59:38Z | dependency 'flux-system/chaos-mesh' is not ready |
| Kustomization | flux-system | chaos-mesh | Not ready | main@44e7427 | 2026-09-03T10:59:37Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | cluster-state | Not ready | main@44e7427 | 2026-09-03T10:59:37Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | dagster | Not ready | main@44e7427 | 2026-09-03T10:59:37Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | dns | Not ready | main@44e7427 | 2026-09-03T10:59:37Z | dependency 'flux-system/edge' is not ready |
| Kustomization | flux-system | drills | Not ready | main@44e7427 | 2026-09-03T10:59:37Z | dependency 'flux-system/alerts-github' is not ready |
| Kustomization | flux-system | external-secrets | Not ready | main@44e7427 | 2026-09-03T11:00:03Z | dependency 'flux-system/edge' is not ready |
| Kustomization | flux-system | guacamole | Not ready | main@44e7427 | 2026-09-03T10:59:38Z | dependency 'flux-system/identity' is not ready |
| Kustomization | flux-system | healing | Not ready | main@44e7427 | 2026-09-03T10:59:38Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | healing-analyzer | Not ready | main@44e7427 | 2026-09-03T10:59:37Z | dependency 'flux-system/healing' revision is not up to date |
| Kustomization | flux-system | healthchecks | Not ready | main@44e7427 | 2026-09-03T10:59:38Z | dependency 'flux-system/identity' is not ready |
| Kustomization | flux-system | hermes-agent | Not ready | main@44e7427 | 2026-09-03T10:59:38Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | hindsight | Not ready | main@44e7427 | 2026-09-03T10:59:37Z | dependency 'flux-system/secret-store' revision is not up to date |
| Kustomization | flux-system | human-vault | Not ready | main@44e7427 | 2026-09-03T10:59:37Z | dependency 'flux-system/external-secrets' is not ready |
| Kustomization | flux-system | identity | Not ready | main@44e7427 | 2026-09-03T10:59:37Z | dependency 'flux-system/edge' is not ready |
| Kustomization | flux-system | image-automation | Not ready | main@44e7427 | 2026-09-03T10:59:37Z | dependency 'flux-system/secret-store' revision is not up to date |
| Kustomization | flux-system | infra-crew | Not ready | main@44e7427 | 2026-09-03T10:59:38Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | keda | Not ready | main@44e7427 | 2026-09-03T10:59:38Z | dependency 'flux-system/observability' revision is not up to date |
| Kustomization | flux-system | llm | Not ready | main@44e7427 | 2026-09-03T10:59:37Z | dependency 'flux-system/edge' is not ready |
| Kustomization | flux-system | mcp | Not ready | main@44e7427 | 2026-09-03T10:59:38Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | metrics-server | Not ready | main@44e7427 | 2026-09-03T10:59:37Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | monitoring | Not ready | main@44e7427 | 2026-09-03T10:59:37Z | dependency 'flux-system/edge' is not ready |
| Kustomization | flux-system | monitoring-rules | Not ready | main@44e7427 | 2026-09-03T10:59:37Z | dependency 'flux-system/monitoring' revision is not up to date |
| Kustomization | flux-system | notify | Not ready | main@44e7427 | 2026-09-03T10:59:38Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | observability | Not ready | main@44e7427 | 2026-09-03T10:59:38Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | observability-collector | Not ready | main@44e7427 | 2026-09-03T10:59:37Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | otto-golden | Not ready | main@44e7427 | 2026-09-03T10:59:38Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | otto-golden-secret | Not ready | main@44e7427 | 2026-09-03T10:59:37Z | dependency 'flux-system/secret-store' revision is not up to date |
| Kustomization | flux-system | prospector | Not ready | main@b6ce2fc | 2026-09-03T10:59:38Z | dependency 'flux-system/prospector-platform' is not ready |
| Kustomization | flux-system | prospector-platform | Not ready | main@44e7427 | 2026-09-03T10:59:38Z | dependency 'flux-system/edge' is not ready |
| Kustomization | flux-system | reloader | Not ready | main@44e7427 | 2026-09-03T10:59:38Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | robusta | Not ready | main@44e7427 | 2026-09-03T10:59:37Z | dependency 'flux-system/secret-store' revision is not up to date |
| Kustomization | flux-system | scheduling | Not ready | main@44e7427 | 2026-09-03T11:00:03Z | dependency 'flux-system/edge' is not ready |
| Kustomization | flux-system | science | Not ready | main@44e7427 | 2026-09-03T10:59:38Z | dependency 'flux-system/observability' revision is not up to date |
| Kustomization | flux-system | secret-store | Not ready | main@44e7427 | 2026-09-03T10:59:38Z | dependency 'flux-system/external-secrets' is not ready |
| Kustomization | flux-system | spire | Not ready | main@44e7427 | 2026-09-03T10:59:37Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | tailscale | Not ready | main@44e7427 | 2026-09-03T10:59:37Z | dependency 'flux-system/secret-store' revision is not up to date |
| Kustomization | flux-system | verification | Not ready | main@44e7427 | 2026-09-03T10:59:37Z | dependency 'flux-system/external-secrets' is not ready |
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
| HelmRelease | observability | superset | Ready | 0.22.4 | 2026-09-03T04:49:46Z |  |
| HelmRelease | observability-agent | k8s-infra | Ready | 0.17.0 | 2026-08-31T03:17:25Z |  |
| HelmRelease | reloader | reloader | Ready | 2.2.16 | 2026-08-31T07:11:24Z |  |
| HelmRelease | robusta | robusta | Ready | 0.48.0 | 2026-08-31T07:12:01Z |  |
| HelmRelease | spire-mgmt | spire | Ready | 0.30.1 | 2026-08-31T07:12:31Z |  |
| HelmRelease | spire-mgmt | spire-crds | Ready | 0.6.1 | 2026-08-31T07:12:02Z |  |
| HelmRelease | tailscale | tailscale-operator | Ready | 1.102.3 | 2026-09-02T16:32:30Z |  |
| HelmRelease | temporal | temporal | Ready | 1.6.0 | 2026-08-29T19:01:39Z |  |
| Kustomization | flux-system | backstage-namespace | Ready | main@c0a0f3a | 2026-09-03T10:59:37Z |  |
| Kustomization | flux-system | edge | Ready | main@c0a0f3a | 2026-09-03T11:00:05Z |  |
| Kustomization | flux-system | estate-catalog | Ready | latest@sha256:6ea0df74cfe64b1d0087f3f9eb | 2026-09-03T10:59:48Z |  |
| Kustomization | flux-system | flux-system | Ready | main@c0a0f3a | 2026-09-03T10:59:38Z |  |
| Kustomization | flux-system | gateway-api-crds | Ready | v1.5.1@e7677b7 | 2026-09-03T10:59:37Z |  |
| Kustomization | flux-system | kyverno | Ready | main@c0a0f3a | 2026-09-03T10:59:37Z |  |
| Kustomization | flux-system | priority-classes | Ready | main@c0a0f3a | 2026-09-03T10:59:35Z |  |
| Kustomization | flux-system | staging | Ready | main@c0a0f3a | 2026-09-03T10:59:36Z |  |
