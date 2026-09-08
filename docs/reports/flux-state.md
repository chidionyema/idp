# Flux: what is applied

Read from the cluster receipt taken at 2026-09-08T04:15:12Z. Every Kustomization and HelmRelease, with the revision Flux last applied. **Suspended** is a switch somebody turned off on purpose (temporal, commerce, commerce-data, event-bus), not a defect; **Unknown** is a row Flux has never graded.

**109 objects: 96 ready, 11 not ready, 0 unknown, 2 suspended.**

## Not ready right now

- **HelmRelease commerce/lago** since 2026-09-08T03:07:00Z: Helm install failed for release commerce/lago with chart lago@1.28.0: failed pre-install: timeout waiting for: [Job/commerce/lago-migrate-db status: 'InProgress']
- **HelmRelease observability/langfuse** since 2026-09-07T21:12:08Z: dependency 'observability/signoz' is not ready
- **HelmRelease observability/signoz** since 2026-09-08T03:22:45Z: Helm rollback to previous release observability/signoz.v58 with chart signoz@0.138.0 failed: release signoz failed: timeout waiting for: [Deployment/observability/signoz-clickhouse-operator status: 'InProgress']
- **Kustomization flux-system/chaos** since 2026-09-08T02:16:30Z: dependency 'flux-system/observability' is not ready
- **Kustomization flux-system/commerce** since 2026-09-08T04:07:07Z: health check failed after 86.517708ms: failed early due to stalled resources: [HelmRelease/commerce/lago status: 'Failed']
- **Kustomization flux-system/gvisor-runtime** since 2026-09-08T00:53:14Z: dependency 'flux-system/nodesoftware-operator' is not ready
- **Kustomization flux-system/nodesoftware-operator** since 2026-09-08T04:06:09Z: health check failed after 98.201035ms: failed early due to stalled resources: [Deployment/nodesoftware-operator/nodesoftware-operator status: 'Failed']
- **Kustomization flux-system/observability** since 2026-09-08T04:06:25Z: health check failed after 20m0.046161652s: timeout waiting for: [Job/observability/langfuse-clickhouse-database status: 'InProgress', HelmRelease/observability/signoz status: 'InProgress', HelmRelease/observability/langfuse status: 'InProgress']
- **Kustomization flux-system/otto-gateway** since 2026-09-08T04:07:47Z: health check failed after 293.780419ms: failed early due to stalled resources: [Job/otto-gateway/otto-memory-store-5 status: 'Failed']
- **Kustomization flux-system/otto-golden** since 2026-09-08T04:15:07Z: Reconciliation in progress
- **Kustomization flux-system/science** since 2026-09-07T21:13:12Z: dependency 'flux-system/observability' is not ready

## Every row

| Kind | Namespace | Name | State | Applied revision | Since | Message |
|---|---|---|---|---|---|---|
| HelmRelease | commerce | lago | Not ready | 1.28.0 | 2026-09-08T03:07:00Z | Helm install failed for release commerce/lago with chart lago@1.28.0: failed pre-install: timeout waiting for: [Job/commerce/lago-migrate-db status: 'InProgress |
| HelmRelease | observability | langfuse | Not ready | 2.0.2 | 2026-09-07T21:12:08Z | dependency 'observability/signoz' is not ready |
| HelmRelease | observability | signoz | Not ready | 0.138.0 | 2026-09-08T03:22:45Z | Helm rollback to previous release observability/signoz.v58 with chart signoz@0.138.0 failed: release signoz failed: timeout waiting for: [Deployment/observabili |
| Kustomization | flux-system | chaos | Not ready | main@a38150d | 2026-09-08T02:16:30Z | dependency 'flux-system/observability' is not ready |
| Kustomization | flux-system | commerce | Not ready | main@6d84a86 | 2026-09-08T04:07:07Z | health check failed after 86.517708ms: failed early due to stalled resources: [HelmRelease/commerce/lago status: 'Failed'] |
| Kustomization | flux-system | gvisor-runtime | Not ready | main@8e1bade | 2026-09-08T00:53:14Z | dependency 'flux-system/nodesoftware-operator' is not ready |
| Kustomization | flux-system | nodesoftware-operator | Not ready | main@8e1bade | 2026-09-08T04:06:09Z | health check failed after 98.201035ms: failed early due to stalled resources: [Deployment/nodesoftware-operator/nodesoftware-operator status: 'Failed'] |
| Kustomization | flux-system | observability | Not ready | main@a38150d | 2026-09-08T04:06:25Z | health check failed after 20m0.046161652s: timeout waiting for: [Job/observability/langfuse-clickhouse-database status: 'InProgress', HelmRelease/observability/ |
| Kustomization | flux-system | otto-gateway | Not ready | main@7dd9f6e | 2026-09-08T04:07:47Z | health check failed after 293.780419ms: failed early due to stalled resources: [Job/otto-gateway/otto-memory-store-5 status: 'Failed'] |
| Kustomization | flux-system | otto-golden | Not ready | main@6d84a86 | 2026-09-08T04:15:07Z | Reconciliation in progress |
| Kustomization | flux-system | science | Not ready | main@a38150d | 2026-09-07T21:13:12Z | dependency 'flux-system/observability' is not ready |
| HelmRelease | tigera-operator | tigera-operator | Suspended | v3.32.2 | 2026-09-06T19:38:02Z |  |
| Kustomization | flux-system | temporal | Suspended | main@1b323ac | 2026-08-30T05:54:22Z |  |
| HelmRelease | cert-manager | cert-manager | Ready | v1.21.1 | 2026-09-06T19:34:17Z |  |
| HelmRelease | chaos-mesh | chaos-mesh | Ready | 2.8.4 | 2026-09-06T19:34:33Z |  |
| HelmRelease | dagster | dagster | Ready | 1.13.19 | 2026-09-08T00:49:13Z |  |
| HelmRelease | edge | external-dns | Ready | 1.21.1 | 2026-09-06T19:33:35Z |  |
| HelmRelease | edge | traefik | Ready | 41.3.0 | 2026-09-06T19:35:13Z |  |
| HelmRelease | estate-db | cloudnative-pg | Ready | 0.29.0 | 2026-09-06T19:45:25Z |  |
| HelmRelease | event-bus | nats | Ready | 2.14.6 | 2026-09-06T19:39:37Z |  |
| HelmRelease | external-secrets | external-secrets | Ready | 2.9.0 | 2026-09-06T19:33:05Z |  |
| HelmRelease | healing | descheduler | Ready | 0.36.0 | 2026-09-06T19:34:32Z |  |
| HelmRelease | healing | k8sgpt-operator | Ready | 0.2.29 | 2026-09-06T19:33:00Z |  |
| HelmRelease | hindsight | hindsight | Ready | 0.9.2 | 2026-09-06T20:26:45Z |  |
| HelmRelease | identity | oauth2-proxy | Ready | 10.7.0 | 2026-09-06T19:35:13Z |  |
| HelmRelease | keda | keda | Ready | 2.20.2 | 2026-09-06T19:34:17Z |  |
| HelmRelease | keda | keda-add-ons-http | Ready | 0.15.0 | 2026-09-06T19:35:13Z |  |
| HelmRelease | kyverno | kyverno | Ready | 3.9.0 | 2026-09-06T20:26:45Z |  |
| HelmRelease | metrics-server | metrics-server | Ready | 3.14.0 | 2026-09-06T19:34:02Z |  |
| HelmRelease | monitoring | blackbox | Ready | 11.17.2 | 2026-09-06T19:47:10Z |  |
| HelmRelease | monitoring | kube-prometheus-stack | Ready | 88.6.0 | 2026-09-06T20:26:45Z |  |
| HelmRelease | observability | superset | Ready | 0.22.4 | 2026-09-06T19:46:05Z |  |
| HelmRelease | observability-agent | k8s-infra | Ready | 0.17.0 | 2026-09-08T02:42:15Z |  |
| HelmRelease | reloader | reloader | Ready | 2.2.16 | 2026-09-06T19:33:25Z |  |
| HelmRelease | robusta | robusta | Ready | 0.48.0 | 2026-09-06T20:26:45Z |  |
| HelmRelease | spire-mgmt | spire | Ready | 0.30.1 | 2026-09-06T20:27:16Z |  |
| HelmRelease | spire-mgmt | spire-crds | Ready | 0.6.1 | 2026-09-06T20:26:47Z |  |
| HelmRelease | tailscale | tailscale-operator | Ready | 1.102.3 | 2026-09-06T19:33:35Z |  |
| HelmRelease | temporal | temporal | Ready | 1.6.0 | 2026-09-06T19:33:25Z |  |
| HelmRelease | trivy-system | trivy-operator | Ready | 0.36.0 | 2026-09-06T20:26:45Z |  |
| HelmRelease | weave-gitops | weave-gitops | Ready | 4.0.36 | 2026-09-06T20:26:45Z |  |
| Kustomization | flux-system | agent-workforce | Ready | main@6d84a86 | 2026-09-08T04:05:45Z |  |
| Kustomization | flux-system | alerts | Ready | main@6d84a86 | 2026-09-08T04:07:08Z |  |
| Kustomization | flux-system | alerts-github | Ready | main@6d84a86 | 2026-09-08T04:06:39Z |  |
| Kustomization | flux-system | alerts-secret | Ready | main@6d84a86 | 2026-09-08T04:14:36Z |  |
| Kustomization | flux-system | autoscaler | Ready | main@6d84a86 | 2026-09-08T04:07:29Z |  |
| Kustomization | flux-system | backstage | Ready | main@6d84a86 | 2026-09-08T04:08:09Z |  |
| Kustomization | flux-system | backstage-namespace | Ready | main@6d84a86 | 2026-09-08T04:13:57Z |  |
| Kustomization | flux-system | calico | Ready | main@6d84a86 | 2026-09-08T04:14:54Z |  |
| Kustomization | flux-system | chaos-mesh | Ready | main@6d84a86 | 2026-09-08T04:08:07Z |  |
| Kustomization | flux-system | cluster-state | Ready | main@6d84a86 | 2026-09-08T04:06:01Z |  |
| Kustomization | flux-system | commerce-data | Ready | main@6d84a86 | 2026-09-08T04:05:46Z |  |
| Kustomization | flux-system | cyrus | Ready | main@6d84a86 | 2026-09-08T04:07:49Z |  |
| Kustomization | flux-system | dagster | Ready | main@6d84a86 | 2026-09-08T04:14:43Z |  |
| Kustomization | flux-system | dns | Ready | main@6d84a86 | 2026-09-08T04:06:30Z |  |
| Kustomization | flux-system | drills | Ready | main@6d84a86 | 2026-09-08T04:04:47Z |  |
| Kustomization | flux-system | edge | Ready | main@6d84a86 | 2026-09-08T04:06:47Z |  |
| Kustomization | flux-system | estate-catalog | Ready | latest@sha256:67bb6c94dadcb443d1b4ca9bda | 2026-09-08T04:10:20Z |  |
| Kustomization | flux-system | estate-db | Ready | main@6d84a86 | 2026-09-08T04:06:39Z |  |
| Kustomization | flux-system | estate-db-migrate | Ready | main@6d84a86 | 2026-09-08T04:05:27Z |  |
| Kustomization | flux-system | estate-db-operator | Ready | main@6d84a86 | 2026-09-08T04:06:59Z |  |
| Kustomization | flux-system | event-bus | Ready | main@6d84a86 | 2026-09-08T04:15:02Z |  |
| Kustomization | flux-system | external-secrets | Ready | main@6d84a86 | 2026-09-08T04:14:44Z |  |
| Kustomization | flux-system | feature-register | Ready | main@6d84a86 | 2026-09-08T04:13:24Z |  |
| Kustomization | flux-system | flux-system | Ready | main@6d84a86 | 2026-09-08T04:07:43Z |  |
| Kustomization | flux-system | flux-webhook | Ready | main@6d84a86 | 2026-09-08T04:07:05Z |  |
| Kustomization | flux-system | gateway-api-crds | Ready | v1.5.1@e7677b7 | 2026-09-08T04:14:28Z |  |
| Kustomization | flux-system | guacamole | Ready | main@6d84a86 | 2026-09-08T04:07:52Z |  |
| Kustomization | flux-system | healing | Ready | main@6d84a86 | 2026-09-08T04:07:50Z |  |
| Kustomization | flux-system | healing-analyzer | Ready | main@6d84a86 | 2026-09-08T04:08:15Z |  |
| Kustomization | flux-system | healthchecks | Ready | main@6d84a86 | 2026-09-08T04:07:55Z |  |
| Kustomization | flux-system | hermes-agent | Ready | main@6d84a86 | 2026-09-08T04:06:14Z |  |
| Kustomization | flux-system | hindsight | Ready | main@6d84a86 | 2026-09-08T04:05:57Z |  |
| Kustomization | flux-system | human-vault | Ready | main@6d84a86 | 2026-09-08T04:07:29Z |  |
| Kustomization | flux-system | human-vault-bridge | Ready | main@6d84a86 | 2026-09-08T04:05:27Z |  |
| Kustomization | flux-system | identity | Ready | main@6d84a86 | 2026-09-08T04:06:35Z |  |
| Kustomization | flux-system | image-automation | Ready | main@6d84a86 | 2026-09-08T04:05:54Z |  |
| Kustomization | flux-system | jit | Ready | main@6d84a86 | 2026-09-08T04:14:42Z |  |
| Kustomization | flux-system | keda | Ready | main@6d84a86 | 2026-09-08T04:07:38Z |  |
| Kustomization | flux-system | kyverno | Ready | main@6d84a86 | 2026-09-08T04:07:30Z |  |
| Kustomization | flux-system | llm | Ready | main@6d84a86 | 2026-09-08T04:06:41Z |  |
| Kustomization | flux-system | mcp | Ready | main@6d84a86 | 2026-09-08T04:07:57Z |  |
| Kustomization | flux-system | metrics-server | Ready | main@6d84a86 | 2026-09-08T04:06:03Z |  |
| Kustomization | flux-system | monitoring | Ready | main@6d84a86 | 2026-09-08T04:07:24Z |  |
| Kustomization | flux-system | monitoring-rules | Ready | main@6d84a86 | 2026-09-08T04:06:35Z |  |
| Kustomization | flux-system | notify | Ready | main@6d84a86 | 2026-09-08T04:06:10Z |  |
| Kustomization | flux-system | ns-fences | Ready | main@6d84a86 | 2026-09-08T04:07:09Z |  |
| Kustomization | flux-system | observability-collector | Ready | main@6d84a86 | 2026-09-08T04:08:03Z |  |
| Kustomization | flux-system | otto-golden-secret | Ready | main@6d84a86 | 2026-09-08T04:08:10Z |  |
| Kustomization | flux-system | priority-classes | Ready | main@6d84a86 | 2026-09-08T04:13:18Z |  |
| Kustomization | flux-system | prospector | Ready | main@7453d76 | 2026-09-08T04:06:27Z |  |
| Kustomization | flux-system | prospector-platform | Ready | main@6d84a86 | 2026-09-08T04:05:19Z |  |
| Kustomization | flux-system | rbac | Ready | main@6d84a86 | 2026-09-08T04:13:50Z |  |
| Kustomization | flux-system | rbac-floor | Ready | main@6d84a86 | 2026-09-08T04:05:20Z |  |
| Kustomization | flux-system | rbac-identity | Ready | main@6d84a86 | 2026-09-08T04:05:40Z |  |
| Kustomization | flux-system | reloader | Ready | main@6d84a86 | 2026-09-08T04:06:20Z |  |
| Kustomization | flux-system | research-engine | Ready | main@6d84a86 | 2026-09-08T04:06:57Z |  |
| Kustomization | flux-system | robusta | Ready | main@6d84a86 | 2026-09-08T04:07:17Z |  |
| Kustomization | flux-system | sandbox-launch | Ready | main@6d84a86 | 2026-09-08T04:05:46Z |  |
| Kustomization | flux-system | sandbox-live | Ready | sandbox/launch@929c1d7 | 2026-09-08T04:14:36Z |  |
| Kustomization | flux-system | scheduling | Ready | main@6d84a86 | 2026-09-08T04:07:35Z |  |
| Kustomization | flux-system | searxng | Ready | main@6d84a86 | 2026-09-08T04:05:21Z |  |
| Kustomization | flux-system | secret-store | Ready | main@6d84a86 | 2026-09-08T04:06:06Z |  |
| Kustomization | flux-system | spire | Ready | main@6d84a86 | 2026-09-08T04:08:19Z |  |
| Kustomization | flux-system | staging | Ready | main@6d84a86 | 2026-09-08T04:06:28Z |  |
| Kustomization | flux-system | tailscale | Ready | main@6d84a86 | 2026-09-08T04:06:02Z |  |
| Kustomization | flux-system | trivy | Ready | main@6d84a86 | 2026-09-08T04:06:04Z |  |
| Kustomization | flux-system | verification | Ready | main@6d84a86 | 2026-09-08T04:08:03Z |  |
| Kustomization | flux-system | weave-gitops | Ready | main@6d84a86 | 2026-09-08T04:06:33Z |  |
