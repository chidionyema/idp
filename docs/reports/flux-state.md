# Flux: what is applied

Read from the cluster receipt taken at 2026-09-04T17:15:10Z. Every Kustomization and HelmRelease, with the revision Flux last applied. **Suspended** is a switch somebody turned off on purpose (temporal, commerce, commerce-data, event-bus), not a defect; **Unknown** is a row Flux has never graded.

**92 objects: 68 ready, 21 not ready, 0 unknown, 3 suspended.**

## Not ready right now

- **Kustomization flux-system/alerts-github** since 2026-09-04T17:07:23Z: Reconciliation in progress
- **Kustomization flux-system/backstage** since 2026-09-04T17:07:01Z: dependency 'flux-system/estate-db-migrate' is not ready
- **Kustomization flux-system/chaos** since 2026-09-04T17:07:30Z: dependency 'flux-system/observability' is not ready
- **Kustomization flux-system/dagster** since 2026-09-04T17:07:01Z: dependency 'flux-system/estate-db-migrate' is not ready
- **Kustomization flux-system/drills** since 2026-09-04T15:44:57Z: dependency 'flux-system/alerts-github' is not ready
- **Kustomization flux-system/estate-db-migrate** since 2026-09-04T17:10:37Z: health check failed after 65.613479ms: failed early due to stalled resources: [Job/hindsight/estate-db-copy-hindsight-r3 status: 'Failed']
- **Kustomization flux-system/guacamole** since 2026-09-04T17:07:01Z: dependency 'flux-system/estate-db-migrate' is not ready
- **Kustomization flux-system/healing** since 2026-09-04T17:07:01Z: dependency 'flux-system/llm' is not ready
- **Kustomization flux-system/healing-analyzer** since 2026-09-04T13:27:56Z: dependency 'flux-system/healing' is not ready
- **Kustomization flux-system/healthchecks** since 2026-09-04T17:07:01Z: dependency 'flux-system/estate-db-migrate' is not ready
- **Kustomization flux-system/hermes-agent** since 2026-09-04T17:07:01Z: dependency 'flux-system/alerts-github' is not ready
- **Kustomization flux-system/hindsight** since 2026-09-04T17:07:01Z: dependency 'flux-system/llm' is not ready
- **Kustomization flux-system/image-automation** since 2026-09-04T17:07:23Z: Reconciliation in progress
- **Kustomization flux-system/infra-crew** since 2026-09-04T17:07:01Z: dependency 'flux-system/alerts-github' is not ready
- **Kustomization flux-system/llm** since 2026-09-04T17:07:01Z: dependency 'flux-system/estate-db-migrate' is not ready
- **Kustomization flux-system/mcp** since 2026-09-04T17:07:01Z: dependency 'flux-system/alerts-github' is not ready
- **Kustomization flux-system/notify** since 2026-09-04T17:07:15Z: Reconciliation in progress
- **Kustomization flux-system/observability** since 2026-09-04T17:07:01Z: dependency 'flux-system/estate-db-migrate' is not ready
- **Kustomization flux-system/otto-gateway** since 2026-09-04T17:07:01Z: dependency 'flux-system/estate-db-migrate' is not ready
- **Kustomization flux-system/research-engine** since 2026-09-04T17:07:01Z: dependency 'flux-system/llm' is not ready
- **Kustomization flux-system/science** since 2026-09-04T13:27:56Z: dependency 'flux-system/observability' is not ready

## Every row

| Kind | Namespace | Name | State | Applied revision | Since | Message |
|---|---|---|---|---|---|---|
| Kustomization | flux-system | alerts-github | Not ready | main@190b364 | 2026-09-04T17:07:23Z | Reconciliation in progress |
| Kustomization | flux-system | backstage | Not ready | main@c61560f | 2026-09-04T17:07:01Z | dependency 'flux-system/estate-db-migrate' is not ready |
| Kustomization | flux-system | chaos | Not ready | main@c61560f | 2026-09-04T17:07:30Z | dependency 'flux-system/observability' is not ready |
| Kustomization | flux-system | dagster | Not ready | main@c61560f | 2026-09-04T17:07:01Z | dependency 'flux-system/estate-db-migrate' is not ready |
| Kustomization | flux-system | drills | Not ready | main@190b364 | 2026-09-04T15:44:57Z | dependency 'flux-system/alerts-github' is not ready |
| Kustomization | flux-system | estate-db-migrate | Not ready | main@5a04c18 | 2026-09-04T17:10:37Z | health check failed after 65.613479ms: failed early due to stalled resources: [Job/hindsight/estate-db-copy-hindsight-r3 status: 'Failed'] |
| Kustomization | flux-system | guacamole | Not ready | main@c61560f | 2026-09-04T17:07:01Z | dependency 'flux-system/estate-db-migrate' is not ready |
| Kustomization | flux-system | healing | Not ready | main@c61560f | 2026-09-04T17:07:01Z | dependency 'flux-system/llm' is not ready |
| Kustomization | flux-system | healing-analyzer | Not ready | main@c61560f | 2026-09-04T13:27:56Z | dependency 'flux-system/healing' is not ready |
| Kustomization | flux-system | healthchecks | Not ready | main@c61560f | 2026-09-04T17:07:01Z | dependency 'flux-system/estate-db-migrate' is not ready |
| Kustomization | flux-system | hermes-agent | Not ready | main@190b364 | 2026-09-04T17:07:01Z | dependency 'flux-system/alerts-github' is not ready |
| Kustomization | flux-system | hindsight | Not ready | main@c61560f | 2026-09-04T17:07:01Z | dependency 'flux-system/llm' is not ready |
| Kustomization | flux-system | image-automation | Not ready | main@190b364 | 2026-09-04T17:07:23Z | Reconciliation in progress |
| Kustomization | flux-system | infra-crew | Not ready | main@c61560f | 2026-09-04T17:07:01Z | dependency 'flux-system/alerts-github' is not ready |
| Kustomization | flux-system | llm | Not ready | main@c61560f | 2026-09-04T17:07:01Z | dependency 'flux-system/estate-db-migrate' is not ready |
| Kustomization | flux-system | mcp | Not ready | main@190b364 | 2026-09-04T17:07:01Z | dependency 'flux-system/alerts-github' is not ready |
| Kustomization | flux-system | notify | Not ready | main@3f61f98 | 2026-09-04T17:07:15Z | Reconciliation in progress |
| Kustomization | flux-system | observability | Not ready | main@c61560f | 2026-09-04T17:07:01Z | dependency 'flux-system/estate-db-migrate' is not ready |
| Kustomization | flux-system | otto-gateway | Not ready | main@c61560f | 2026-09-04T17:07:01Z | dependency 'flux-system/estate-db-migrate' is not ready |
| Kustomization | flux-system | research-engine | Not ready | main@c61560f | 2026-09-04T17:07:01Z | dependency 'flux-system/llm' is not ready |
| Kustomization | flux-system | science | Not ready | main@c61560f | 2026-09-04T13:27:56Z | dependency 'flux-system/observability' is not ready |
| Kustomization | flux-system | commerce | Suspended |  |  |  |
| Kustomization | flux-system | commerce-data | Suspended |  |  |  |
| Kustomization | flux-system | temporal | Suspended | main@1b323ac | 2026-08-30T05:54:22Z |  |
| HelmRelease | cert-manager | cert-manager | Ready | v1.21.1 | 2026-08-31T07:10:44Z |  |
| HelmRelease | chaos-mesh | chaos-mesh | Ready | 2.8.4 | 2026-08-31T07:12:00Z |  |
| HelmRelease | dagster | dagster | Ready | 1.13.19 | 2026-09-02T19:57:44Z |  |
| HelmRelease | edge | external-dns | Ready | 1.21.1 | 2026-08-31T07:11:28Z |  |
| HelmRelease | edge | traefik | Ready | 41.3.0 | 2026-08-31T07:10:46Z |  |
| HelmRelease | estate-db | cloudnative-pg | Ready | 0.29.0 | 2026-09-04T13:28:55Z |  |
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
| Kustomization | flux-system | alerts | Ready | main@5a04c18 | 2026-09-04T17:10:31Z |  |
| Kustomization | flux-system | alerts-secret | Ready | main@5a04c18 | 2026-09-04T17:10:28Z |  |
| Kustomization | flux-system | autoscaler | Ready | main@5a04c18 | 2026-09-04T17:10:24Z |  |
| Kustomization | flux-system | backstage-namespace | Ready | main@5a04c18 | 2026-09-04T17:10:05Z |  |
| Kustomization | flux-system | chaos-mesh | Ready | main@5a04c18 | 2026-09-04T17:10:32Z |  |
| Kustomization | flux-system | cluster-state | Ready | main@5a04c18 | 2026-09-04T17:10:22Z |  |
| Kustomization | flux-system | dns | Ready | main@5a04c18 | 2026-09-04T17:10:35Z |  |
| Kustomization | flux-system | edge | Ready | main@5a04c18 | 2026-09-04T17:10:16Z |  |
| Kustomization | flux-system | estate-catalog | Ready | latest@sha256:80ed3223582b5d09187cc6b80f | 2026-09-04T17:12:03Z |  |
| Kustomization | flux-system | estate-db | Ready | main@5a04c18 | 2026-09-04T17:10:34Z |  |
| Kustomization | flux-system | estate-db-operator | Ready | main@5a04c18 | 2026-09-04T17:10:09Z |  |
| Kustomization | flux-system | event-bus | Ready | main@5a04c18 | 2026-09-04T17:10:08Z |  |
| Kustomization | flux-system | external-secrets | Ready | main@5a04c18 | 2026-09-04T17:10:17Z |  |
| Kustomization | flux-system | flux-system | Ready | main@5a04c18 | 2026-09-04T17:10:14Z |  |
| Kustomization | flux-system | flux-webhook | Ready | main@5a04c18 | 2026-09-04T17:10:29Z |  |
| Kustomization | flux-system | gateway-api-crds | Ready | v1.5.1@e7677b7 | 2026-09-04T17:10:11Z |  |
| Kustomization | flux-system | human-vault | Ready | main@5a04c18 | 2026-09-04T17:10:24Z |  |
| Kustomization | flux-system | identity | Ready | main@5a04c18 | 2026-09-04T17:10:33Z |  |
| Kustomization | flux-system | keda | Ready | main@5a04c18 | 2026-09-04T17:10:19Z |  |
| Kustomization | flux-system | kyverno | Ready | main@5a04c18 | 2026-09-04T17:10:08Z |  |
| Kustomization | flux-system | metrics-server | Ready | main@5a04c18 | 2026-09-04T17:10:19Z |  |
| Kustomization | flux-system | monitoring | Ready | main@5a04c18 | 2026-09-04T17:10:25Z |  |
| Kustomization | flux-system | monitoring-rules | Ready | main@5a04c18 | 2026-09-04T17:10:30Z |  |
| Kustomization | flux-system | observability-collector | Ready | main@5a04c18 | 2026-09-04T17:10:20Z |  |
| Kustomization | flux-system | otto-golden | Ready | main@5a04c18 | 2026-09-04T17:10:39Z |  |
| Kustomization | flux-system | otto-golden-secret | Ready | main@5a04c18 | 2026-09-04T17:10:30Z |  |
| Kustomization | flux-system | priority-classes | Ready | main@5a04c18 | 2026-09-04T17:10:06Z |  |
| Kustomization | flux-system | prospector | Ready | main@6c20302 | 2026-09-04T17:07:15Z |  |
| Kustomization | flux-system | prospector-platform | Ready | main@5a04c18 | 2026-09-04T17:10:21Z |  |
| Kustomization | flux-system | reloader | Ready | main@5a04c18 | 2026-09-04T17:10:26Z |  |
| Kustomization | flux-system | robusta | Ready | main@5a04c18 | 2026-09-04T17:10:31Z |  |
| Kustomization | flux-system | scheduling | Ready | main@5a04c18 | 2026-09-04T17:10:18Z |  |
| Kustomization | flux-system | searxng | Ready | main@5a04c18 | 2026-09-04T17:10:07Z |  |
| Kustomization | flux-system | secret-store | Ready | main@5a04c18 | 2026-09-04T17:10:20Z |  |
| Kustomization | flux-system | spire | Ready | main@5a04c18 | 2026-09-04T17:10:35Z |  |
| Kustomization | flux-system | staging | Ready | main@5a04c18 | 2026-09-04T17:10:07Z |  |
| Kustomization | flux-system | tailscale | Ready | main@5a04c18 | 2026-09-04T17:10:26Z |  |
| Kustomization | flux-system | verification | Ready | main@5a04c18 | 2026-09-04T17:10:23Z |  |
| Kustomization | flux-system | weave-gitops | Ready | main@5a04c18 | 2026-09-04T17:10:36Z |  |
