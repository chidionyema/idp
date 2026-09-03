# Flux: what is applied

Read from the cluster receipt taken at 2026-09-03T15:30:10Z. Every Kustomization and HelmRelease, with the revision Flux last applied. **Suspended** is a switch somebody turned off on purpose (temporal, commerce, commerce-data, event-bus), not a defect; **Unknown** is a row Flux has never graded.

**82 objects: 70 ready, 7 not ready, 0 unknown, 5 suspended.**

## Not ready right now

- **Kustomization flux-system/chaos** since 2026-09-03T14:16:49Z: dependency 'flux-system/observability' is not ready
- **Kustomization flux-system/healing** since 2026-09-03T15:26:45Z: ExternalSecret/healing/k8sgpt dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-secrets.io": failed to call webhook: Post "https://external-secrets-webhook.external-secrets.svc:443/validate-external-secrets-io-v1-externalsecret?timeout=5s": context deadline exceeded 
- **Kustomization flux-system/healing-analyzer** since 2026-09-03T15:27:26Z: dependency 'flux-system/healing' is not ready
- **Kustomization flux-system/mcp** since 2026-09-03T15:27:03Z: ExternalSecret/mcp/ghcr-pull dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-secrets.io": failed to call webhook: Post "https://external-secrets-webhook.external-secrets.svc:443/validate-external-secrets-io-v1-externalsecret?timeout=5s": context deadline exceeded 
- **Kustomization flux-system/notify** since 2026-09-03T15:27:22Z: health check failed after 10m0.024230323s: timeout waiting for: [Deployment/notify/apprise status: 'InProgress']
- **Kustomization flux-system/observability** since 2026-09-03T15:26:56Z: Reconciliation in progress
- **Kustomization flux-system/science** since 2026-09-03T13:17:35Z: dependency 'flux-system/observability' is not ready

## Every row

| Kind | Namespace | Name | State | Applied revision | Since | Message |
|---|---|---|---|---|---|---|
| Kustomization | flux-system | chaos | Not ready | main@b3affcc | 2026-09-03T14:16:49Z | dependency 'flux-system/observability' is not ready |
| Kustomization | flux-system | healing | Not ready | main@94ffcbc | 2026-09-03T15:26:45Z | ExternalSecret/healing/k8sgpt dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-secrets.io": fai |
| Kustomization | flux-system | healing-analyzer | Not ready | main@94ffcbc | 2026-09-03T15:27:26Z | dependency 'flux-system/healing' is not ready |
| Kustomization | flux-system | mcp | Not ready | main@94ffcbc | 2026-09-03T15:27:03Z | ExternalSecret/mcp/ghcr-pull dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-secrets.io": fail |
| Kustomization | flux-system | notify | Not ready | main@94ffcbc | 2026-09-03T15:27:22Z | health check failed after 10m0.024230323s: timeout waiting for: [Deployment/notify/apprise status: 'InProgress'] |
| Kustomization | flux-system | observability | Not ready | main@b3affcc | 2026-09-03T15:26:56Z | Reconciliation in progress |
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
| HelmRelease | observability-agent | k8s-infra | Ready | 0.17.0 | 2026-09-03T15:19:29Z |  |
| HelmRelease | reloader | reloader | Ready | 2.2.16 | 2026-08-31T07:11:24Z |  |
| HelmRelease | robusta | robusta | Ready | 0.48.0 | 2026-08-31T07:12:01Z |  |
| HelmRelease | spire-mgmt | spire | Ready | 0.30.1 | 2026-08-31T07:12:31Z |  |
| HelmRelease | spire-mgmt | spire-crds | Ready | 0.6.1 | 2026-08-31T07:12:02Z |  |
| HelmRelease | tailscale | tailscale-operator | Ready | 1.102.3 | 2026-09-02T16:32:30Z |  |
| HelmRelease | temporal | temporal | Ready | 1.6.0 | 2026-08-29T19:01:39Z |  |
| Kustomization | flux-system | alerts | Ready | main@94ffcbc | 2026-09-03T15:26:43Z |  |
| Kustomization | flux-system | alerts-github | Ready | main@94ffcbc | 2026-09-03T15:27:03Z |  |
| Kustomization | flux-system | alerts-secret | Ready | main@94ffcbc | 2026-09-03T15:26:33Z |  |
| Kustomization | flux-system | autoscaler | Ready | main@94ffcbc | 2026-09-03T15:27:46Z |  |
| Kustomization | flux-system | backstage | Ready | main@94ffcbc | 2026-09-03T15:27:00Z |  |
| Kustomization | flux-system | backstage-namespace | Ready | main@94ffcbc | 2026-09-03T15:24:53Z |  |
| Kustomization | flux-system | chaos-mesh | Ready | main@94ffcbc | 2026-09-03T15:25:40Z |  |
| Kustomization | flux-system | cluster-state | Ready | main@94ffcbc | 2026-09-03T15:27:39Z |  |
| Kustomization | flux-system | dagster | Ready | main@94ffcbc | 2026-09-03T15:26:13Z |  |
| Kustomization | flux-system | dns | Ready | main@94ffcbc | 2026-09-03T15:26:35Z |  |
| Kustomization | flux-system | drills | Ready | main@94ffcbc | 2026-09-03T15:27:44Z |  |
| Kustomization | flux-system | edge | Ready | main@94ffcbc | 2026-09-03T15:24:53Z |  |
| Kustomization | flux-system | estate-catalog | Ready | latest@sha256:b0ecf85db331dc0714ff5679ce | 2026-09-03T15:20:54Z |  |
| Kustomization | flux-system | external-secrets | Ready | main@94ffcbc | 2026-09-03T15:26:16Z |  |
| Kustomization | flux-system | flux-system | Ready | main@94ffcbc | 2026-09-03T15:25:27Z |  |
| Kustomization | flux-system | gateway-api-crds | Ready | v1.5.1@e7677b7 | 2026-09-03T15:25:06Z |  |
| Kustomization | flux-system | guacamole | Ready | main@94ffcbc | 2026-09-03T15:26:26Z |  |
| Kustomization | flux-system | healthchecks | Ready | main@94ffcbc | 2026-09-03T15:26:06Z |  |
| Kustomization | flux-system | hermes-agent | Ready | main@94ffcbc | 2026-09-03T15:25:36Z |  |
| Kustomization | flux-system | hindsight | Ready | main@94ffcbc | 2026-09-03T15:26:45Z |  |
| Kustomization | flux-system | human-vault | Ready | main@94ffcbc | 2026-09-03T15:27:37Z |  |
| Kustomization | flux-system | identity | Ready | main@94ffcbc | 2026-09-03T15:27:02Z |  |
| Kustomization | flux-system | image-automation | Ready | main@94ffcbc | 2026-09-03T15:28:02Z |  |
| Kustomization | flux-system | infra-crew | Ready | main@94ffcbc | 2026-09-03T15:27:10Z |  |
| Kustomization | flux-system | keda | Ready | main@94ffcbc | 2026-09-03T15:27:46Z |  |
| Kustomization | flux-system | kyverno | Ready | main@94ffcbc | 2026-09-03T15:25:48Z |  |
| Kustomization | flux-system | llm | Ready | main@94ffcbc | 2026-09-03T15:27:16Z |  |
| Kustomization | flux-system | metrics-server | Ready | main@94ffcbc | 2026-09-03T15:26:30Z |  |
| Kustomization | flux-system | monitoring | Ready | main@94ffcbc | 2026-09-03T15:25:16Z |  |
| Kustomization | flux-system | monitoring-rules | Ready | main@94ffcbc | 2026-09-03T15:27:13Z |  |
| Kustomization | flux-system | observability-collector | Ready | main@94ffcbc | 2026-09-03T15:26:11Z |  |
| Kustomization | flux-system | otto-golden | Ready | main@94ffcbc | 2026-09-03T15:27:05Z |  |
| Kustomization | flux-system | otto-golden-secret | Ready | main@94ffcbc | 2026-09-03T15:27:35Z |  |
| Kustomization | flux-system | priority-classes | Ready | main@94ffcbc | 2026-09-03T15:24:57Z |  |
| Kustomization | flux-system | prospector | Ready | main@5972126 | 2026-09-03T15:28:12Z |  |
| Kustomization | flux-system | prospector-platform | Ready | main@94ffcbc | 2026-09-03T15:27:50Z |  |
| Kustomization | flux-system | reloader | Ready | main@94ffcbc | 2026-09-03T15:26:20Z |  |
| Kustomization | flux-system | robusta | Ready | main@94ffcbc | 2026-09-03T15:26:09Z |  |
| Kustomization | flux-system | scheduling | Ready | main@94ffcbc | 2026-09-03T15:25:21Z |  |
| Kustomization | flux-system | secret-store | Ready | main@94ffcbc | 2026-09-03T15:26:33Z |  |
| Kustomization | flux-system | spire | Ready | main@94ffcbc | 2026-09-03T15:26:43Z |  |
| Kustomization | flux-system | staging | Ready | main@94ffcbc | 2026-09-03T15:25:20Z |  |
| Kustomization | flux-system | tailscale | Ready | main@94ffcbc | 2026-09-03T15:27:22Z |  |
| Kustomization | flux-system | verification | Ready | main@94ffcbc | 2026-09-03T15:27:21Z |  |
