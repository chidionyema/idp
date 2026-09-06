# Flux: what is applied

Read from the cluster receipt taken at 2026-09-06T08:00:14Z. Every Kustomization and HelmRelease, with the revision Flux last applied. **Suspended** is a switch somebody turned off on purpose (temporal, commerce, commerce-data, event-bus), not a defect; **Unknown** is a row Flux has never graded.

**104 objects: 98 ready, 5 not ready, 0 unknown, 1 suspended.**

## Not ready right now

- **HelmRelease commerce/lago** since 2026-09-06T01:07:55Z: Helm upgrade failed for release commerce/lago with chart lago@1.28.0: pre-upgrade hooks failed: timeout waiting for: [Job/commerce/lago-migrate-db status: 'InProgress']
- **Kustomization flux-system/commerce** since 2026-09-06T07:57:17Z: health check failed after 26.125766ms: failed early due to stalled resources: [HelmRelease/commerce/lago status: 'Failed']
- **Kustomization flux-system/otto-gateway** since 2026-09-06T07:57:19Z: health check failed after 438.310639ms: failed early due to stalled resources: [Job/otto-gateway/otto-memory-store-4 status: 'Failed']
- **Kustomization flux-system/rbac** since 2026-09-04T22:11:22Z: dependency 'flux-system/rbac-identity' is not ready
- **Kustomization flux-system/rbac-identity** since 2026-09-06T07:56:05Z: Reconciliation in progress

## Every row

| Kind | Namespace | Name | State | Applied revision | Since | Message |
|---|---|---|---|---|---|---|
| HelmRelease | commerce | lago | Not ready | 1.28.0 | 2026-09-06T01:07:55Z | Helm upgrade failed for release commerce/lago with chart lago@1.28.0: pre-upgrade hooks failed: timeout waiting for: [Job/commerce/lago-migrate-db status: 'InPr |
| Kustomization | flux-system | commerce | Not ready | main@d8f9437 | 2026-09-06T07:57:17Z | health check failed after 26.125766ms: failed early due to stalled resources: [HelmRelease/commerce/lago status: 'Failed'] |
| Kustomization | flux-system | otto-gateway | Not ready | main@7b7986f | 2026-09-06T07:57:19Z | health check failed after 438.310639ms: failed early due to stalled resources: [Job/otto-gateway/otto-memory-store-4 status: 'Failed'] |
| Kustomization | flux-system | rbac | Not ready | main@4167db0 | 2026-09-04T22:11:22Z | dependency 'flux-system/rbac-identity' is not ready |
| Kustomization | flux-system | rbac-identity | Not ready | main@4167db0 | 2026-09-06T07:56:05Z | Reconciliation in progress |
| Kustomization | flux-system | temporal | Suspended | main@1b323ac | 2026-08-30T05:54:22Z |  |
| HelmRelease | cert-manager | cert-manager | Ready | v1.21.1 | 2026-08-31T07:10:44Z |  |
| HelmRelease | chaos-mesh | chaos-mesh | Ready | 2.8.4 | 2026-08-31T07:12:00Z |  |
| HelmRelease | dagster | dagster | Ready | 1.13.19 | 2026-09-04T18:15:02Z |  |
| HelmRelease | edge | external-dns | Ready | 1.21.1 | 2026-08-31T07:11:28Z |  |
| HelmRelease | edge | traefik | Ready | 41.3.0 | 2026-08-31T07:10:46Z |  |
| HelmRelease | estate-db | cloudnative-pg | Ready | 0.29.0 | 2026-09-04T13:28:55Z |  |
| HelmRelease | event-bus | nats | Ready | 2.14.6 | 2026-09-04T12:12:19Z |  |
| HelmRelease | external-secrets | external-secrets | Ready | 2.9.0 | 2026-09-02T11:40:21Z |  |
| HelmRelease | healing | descheduler | Ready | 0.36.0 | 2026-08-31T07:11:29Z |  |
| HelmRelease | healing | k8sgpt-operator | Ready | 0.2.29 | 2026-08-31T07:11:29Z |  |
| HelmRelease | hindsight | hindsight | Ready | 0.9.2 | 2026-09-05T03:44:37Z |  |
| HelmRelease | identity | oauth2-proxy | Ready | 10.7.0 | 2026-08-29T07:33:02Z |  |
| HelmRelease | keda | keda | Ready | 2.20.2 | 2026-08-31T07:14:43Z |  |
| HelmRelease | keda | keda-add-ons-http | Ready | 0.15.0 | 2026-08-31T07:14:44Z |  |
| HelmRelease | kyverno | kyverno | Ready | 3.9.0 | 2026-09-06T07:05:08Z |  |
| HelmRelease | metrics-server | metrics-server | Ready | 3.14.0 | 2026-08-31T07:11:28Z |  |
| HelmRelease | monitoring | blackbox | Ready | 11.17.2 | 2026-09-05T04:00:38Z |  |
| HelmRelease | monitoring | kube-prometheus-stack | Ready | 88.6.0 | 2026-09-05T04:00:54Z |  |
| HelmRelease | observability | langfuse | Ready | 2.0.2 | 2026-09-04T18:18:00Z |  |
| HelmRelease | observability | signoz | Ready | 0.138.0 | 2026-08-31T07:12:44Z |  |
| HelmRelease | observability | superset | Ready | 0.22.4 | 2026-09-05T04:17:06Z |  |
| HelmRelease | observability-agent | k8s-infra | Ready | 0.17.0 | 2026-09-03T15:19:29Z |  |
| HelmRelease | reloader | reloader | Ready | 2.2.16 | 2026-08-31T07:11:24Z |  |
| HelmRelease | robusta | robusta | Ready | 0.48.0 | 2026-09-05T03:15:16Z |  |
| HelmRelease | spire-mgmt | spire | Ready | 0.30.1 | 2026-08-31T07:12:31Z |  |
| HelmRelease | spire-mgmt | spire-crds | Ready | 0.6.1 | 2026-08-31T07:12:02Z |  |
| HelmRelease | tailscale | tailscale-operator | Ready | 1.102.3 | 2026-09-02T16:32:30Z |  |
| HelmRelease | temporal | temporal | Ready | 1.6.0 | 2026-08-29T19:01:39Z |  |
| HelmRelease | tigera-operator | tigera-operator | Ready | v3.32.2 | 2026-09-06T07:26:27Z |  |
| HelmRelease | trivy-system | trivy-operator | Ready | 0.36.0 | 2026-09-05T12:41:03Z |  |
| HelmRelease | weave-gitops | weave-gitops | Ready | 4.0.36 | 2026-09-05T12:25:08Z |  |
| Kustomization | flux-system | agent-workforce | Ready | main@d8f9437 | 2026-09-06T07:57:52Z |  |
| Kustomization | flux-system | alerts | Ready | main@d8f9437 | 2026-09-06T07:57:11Z |  |
| Kustomization | flux-system | alerts-github | Ready | main@d8f9437 | 2026-09-06T07:57:09Z |  |
| Kustomization | flux-system | alerts-secret | Ready | main@d8f9437 | 2026-09-06T07:57:07Z |  |
| Kustomization | flux-system | autoscaler | Ready | main@d8f9437 | 2026-09-06T07:57:10Z |  |
| Kustomization | flux-system | backstage | Ready | main@d8f9437 | 2026-09-06T07:57:51Z |  |
| Kustomization | flux-system | backstage-namespace | Ready | main@d8f9437 | 2026-09-06T07:55:57Z |  |
| Kustomization | flux-system | calico | Ready | main@d8f9437 | 2026-09-06T07:56:07Z |  |
| Kustomization | flux-system | chaos | Ready | main@d8f9437 | 2026-09-06T07:58:20Z |  |
| Kustomization | flux-system | chaos-mesh | Ready | main@d8f9437 | 2026-09-06T07:57:04Z |  |
| Kustomization | flux-system | cluster-state | Ready | main@d8f9437 | 2026-09-06T07:57:06Z |  |
| Kustomization | flux-system | commerce-data | Ready | main@d8f9437 | 2026-09-06T07:57:15Z |  |
| Kustomization | flux-system | cyrus | Ready | main@d8f9437 | 2026-09-06T07:57:18Z |  |
| Kustomization | flux-system | dagster | Ready | main@d8f9437 | 2026-09-06T07:57:49Z |  |
| Kustomization | flux-system | dns | Ready | main@d8f9437 | 2026-09-06T07:57:09Z |  |
| Kustomization | flux-system | drills | Ready | main@d8f9437 | 2026-09-06T07:57:13Z |  |
| Kustomization | flux-system | edge | Ready | main@d8f9437 | 2026-09-06T07:56:27Z |  |
| Kustomization | flux-system | estate-catalog | Ready | latest@sha256:3c758d25cff3ea9f4ed4a05d46 | 2026-09-06T07:55:09Z |  |
| Kustomization | flux-system | estate-db | Ready | main@d8f9437 | 2026-09-06T07:57:14Z |  |
| Kustomization | flux-system | estate-db-migrate | Ready | main@d8f9437 | 2026-09-06T07:57:27Z |  |
| Kustomization | flux-system | estate-db-operator | Ready | main@d8f9437 | 2026-09-06T07:55:57Z |  |
| Kustomization | flux-system | event-bus | Ready | main@d8f9437 | 2026-09-06T07:56:28Z |  |
| Kustomization | flux-system | external-secrets | Ready | main@d8f9437 | 2026-09-06T07:56:32Z |  |
| Kustomization | flux-system | feature-register | Ready | main@d8f9437 | 2026-09-06T07:56:00Z |  |
| Kustomization | flux-system | flux-system | Ready | main@d8f9437 | 2026-09-06T07:56:05Z |  |
| Kustomization | flux-system | flux-webhook | Ready | main@d8f9437 | 2026-09-06T07:57:10Z |  |
| Kustomization | flux-system | gateway-api-crds | Ready | v1.5.1@e7677b7 | 2026-09-06T07:56:01Z |  |
| Kustomization | flux-system | guacamole | Ready | main@d8f9437 | 2026-09-06T07:57:51Z |  |
| Kustomization | flux-system | healing | Ready | main@d8f9437 | 2026-09-06T07:58:22Z |  |
| Kustomization | flux-system | healing-analyzer | Ready | main@d8f9437 | 2026-09-06T07:58:52Z |  |
| Kustomization | flux-system | healthchecks | Ready | main@d8f9437 | 2026-09-06T07:57:49Z |  |
| Kustomization | flux-system | hermes-agent | Ready | main@d8f9437 | 2026-09-06T07:57:19Z |  |
| Kustomization | flux-system | hindsight | Ready | main@d8f9437 | 2026-09-06T07:58:21Z |  |
| Kustomization | flux-system | human-vault | Ready | main@d8f9437 | 2026-09-06T07:57:08Z |  |
| Kustomization | flux-system | identity | Ready | main@d8f9437 | 2026-09-06T07:57:14Z |  |
| Kustomization | flux-system | image-automation | Ready | main@d8f9437 | 2026-09-06T07:57:27Z |  |
| Kustomization | flux-system | keda | Ready | main@d8f9437 | 2026-09-06T07:57:05Z |  |
| Kustomization | flux-system | kyverno | Ready | main@d8f9437 | 2026-09-06T07:55:57Z |  |
| Kustomization | flux-system | llm | Ready | main@d8f9437 | 2026-09-06T07:57:51Z |  |
| Kustomization | flux-system | mcp | Ready | main@d8f9437 | 2026-09-06T07:57:15Z |  |
| Kustomization | flux-system | metrics-server | Ready | main@d8f9437 | 2026-09-06T07:57:06Z |  |
| Kustomization | flux-system | monitoring | Ready | main@d8f9437 | 2026-09-06T07:57:12Z |  |
| Kustomization | flux-system | monitoring-rules | Ready | main@d8f9437 | 2026-09-06T07:57:15Z |  |
| Kustomization | flux-system | notify | Ready | main@d8f9437 | 2026-09-06T07:57:12Z |  |
| Kustomization | flux-system | ns-fences | Ready | main@d8f9437 | 2026-09-06T07:56:09Z |  |
| Kustomization | flux-system | observability | Ready | main@d8f9437 | 2026-09-06T07:57:50Z |  |
| Kustomization | flux-system | observability-collector | Ready | main@d8f9437 | 2026-09-06T07:57:04Z |  |
| Kustomization | flux-system | otto-golden | Ready | main@d8f9437 | 2026-09-06T07:57:15Z |  |
| Kustomization | flux-system | otto-golden-secret | Ready | main@d8f9437 | 2026-09-06T07:57:05Z |  |
| Kustomization | flux-system | priority-classes | Ready | main@d8f9437 | 2026-09-06T07:55:57Z |  |
| Kustomization | flux-system | prospector | Ready | main@c49c154 | 2026-09-06T07:58:11Z |  |
| Kustomization | flux-system | prospector-platform | Ready | main@d8f9437 | 2026-09-06T07:56:33Z |  |
| Kustomization | flux-system | reloader | Ready | main@d8f9437 | 2026-09-06T07:57:11Z |  |
| Kustomization | flux-system | research-engine | Ready | main@d8f9437 | 2026-09-06T07:58:20Z |  |
| Kustomization | flux-system | robusta | Ready | main@d8f9437 | 2026-09-06T07:57:06Z |  |
| Kustomization | flux-system | sandbox-launch | Ready | main@d8f9437 | 2026-09-06T07:56:33Z |  |
| Kustomization | flux-system | sandbox-live | Ready | sandbox/launch@18d200f | 2026-09-06T07:59:19Z |  |
| Kustomization | flux-system | scheduling | Ready | main@d8f9437 | 2026-09-06T07:56:33Z |  |
| Kustomization | flux-system | science | Ready | main@d8f9437 | 2026-09-06T07:58:20Z |  |
| Kustomization | flux-system | searxng | Ready | main@d8f9437 | 2026-09-06T07:55:59Z |  |
| Kustomization | flux-system | secret-store | Ready | main@d8f9437 | 2026-09-06T07:56:56Z |  |
| Kustomization | flux-system | spire | Ready | main@d8f9437 | 2026-09-06T07:57:08Z |  |
| Kustomization | flux-system | staging | Ready | main@d8f9437 | 2026-09-06T07:56:00Z |  |
| Kustomization | flux-system | tailscale | Ready | main@d8f9437 | 2026-09-06T07:57:08Z |  |
| Kustomization | flux-system | trivy | Ready | main@d8f9437 | 2026-09-06T07:55:59Z |  |
| Kustomization | flux-system | verification | Ready | main@d8f9437 | 2026-09-06T07:57:10Z |  |
| Kustomization | flux-system | weave-gitops | Ready | main@d8f9437 | 2026-09-06T07:57:17Z |  |
