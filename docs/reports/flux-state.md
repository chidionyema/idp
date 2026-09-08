# Flux: what is applied

Read from the cluster receipt taken at 2026-09-08T04:00:14Z. Every Kustomization and HelmRelease, with the revision Flux last applied. **Suspended** is a switch somebody turned off on purpose (temporal, commerce, commerce-data, event-bus), not a defect; **Unknown** is a row Flux has never graded.

**109 objects: 96 ready, 11 not ready, 0 unknown, 2 suspended.**

## Not ready right now

- **HelmRelease commerce/lago** since 2026-09-08T03:07:00Z: Helm install failed for release commerce/lago with chart lago@1.28.0: failed pre-install: timeout waiting for: [Job/commerce/lago-migrate-db status: 'InProgress']
- **HelmRelease observability/langfuse** since 2026-09-07T21:12:08Z: dependency 'observability/signoz' is not ready
- **HelmRelease observability/signoz** since 2026-09-08T03:22:45Z: Helm rollback to previous release observability/signoz.v58 with chart signoz@0.138.0 failed: release signoz failed: timeout waiting for: [Deployment/observability/signoz-clickhouse-operator status: 'InProgress']
- **Kustomization flux-system/chaos** since 2026-09-08T02:16:30Z: dependency 'flux-system/observability' is not ready
- **Kustomization flux-system/commerce** since 2026-09-08T03:57:06Z: health check failed after 22.137042ms: failed early due to stalled resources: [HelmRelease/commerce/lago status: 'Failed']
- **Kustomization flux-system/gvisor-runtime** since 2026-09-08T00:53:14Z: dependency 'flux-system/nodesoftware-operator' is not ready
- **Kustomization flux-system/image-automation** since 2026-09-08T03:55:52Z: ClusterSecretStore/ghcr-pull dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.clustersecretstore.external-secrets.io": failed to call webhook: Post "https://external-secrets-webhook.external-secrets.svc:443/validate-external-secrets-io-v1-clustersecretstore?timeout=5s": EOF 
- **Kustomization flux-system/nodesoftware-operator** since 2026-09-08T03:57:06Z: dependency 'flux-system/image-automation' is not ready
- **Kustomization flux-system/observability** since 2026-09-08T03:46:19Z: Reconciliation in progress
- **Kustomization flux-system/otto-gateway** since 2026-09-08T03:56:45Z: health check failed after 366.125894ms: failed early due to stalled resources: [Job/otto-gateway/otto-memory-store-5 status: 'Failed']
- **Kustomization flux-system/science** since 2026-09-07T21:13:12Z: dependency 'flux-system/observability' is not ready

## Every row

| Kind | Namespace | Name | State | Applied revision | Since | Message |
|---|---|---|---|---|---|---|
| HelmRelease | commerce | lago | Not ready | 1.28.0 | 2026-09-08T03:07:00Z | Helm install failed for release commerce/lago with chart lago@1.28.0: failed pre-install: timeout waiting for: [Job/commerce/lago-migrate-db status: 'InProgress |
| HelmRelease | observability | langfuse | Not ready | 2.0.2 | 2026-09-07T21:12:08Z | dependency 'observability/signoz' is not ready |
| HelmRelease | observability | signoz | Not ready | 0.138.0 | 2026-09-08T03:22:45Z | Helm rollback to previous release observability/signoz.v58 with chart signoz@0.138.0 failed: release signoz failed: timeout waiting for: [Deployment/observabili |
| Kustomization | flux-system | chaos | Not ready | main@a38150d | 2026-09-08T02:16:30Z | dependency 'flux-system/observability' is not ready |
| Kustomization | flux-system | commerce | Not ready | main@6d84a86 | 2026-09-08T03:57:06Z | health check failed after 22.137042ms: failed early due to stalled resources: [HelmRelease/commerce/lago status: 'Failed'] |
| Kustomization | flux-system | gvisor-runtime | Not ready | main@8e1bade | 2026-09-08T00:53:14Z | dependency 'flux-system/nodesoftware-operator' is not ready |
| Kustomization | flux-system | image-automation | Not ready | main@6d84a86 | 2026-09-08T03:55:52Z | ClusterSecretStore/ghcr-pull dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.clustersecretstore.external-secrets.io":  |
| Kustomization | flux-system | nodesoftware-operator | Not ready | main@8e1bade | 2026-09-08T03:57:06Z | dependency 'flux-system/image-automation' is not ready |
| Kustomization | flux-system | observability | Not ready | main@a38150d | 2026-09-08T03:46:19Z | Reconciliation in progress |
| Kustomization | flux-system | otto-gateway | Not ready | main@7dd9f6e | 2026-09-08T03:56:45Z | health check failed after 366.125894ms: failed early due to stalled resources: [Job/otto-gateway/otto-memory-store-5 status: 'Failed'] |
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
| Kustomization | flux-system | agent-workforce | Ready | main@6d84a86 | 2026-09-08T03:55:46Z |  |
| Kustomization | flux-system | alerts | Ready | main@6d84a86 | 2026-09-08T03:57:06Z |  |
| Kustomization | flux-system | alerts-github | Ready | main@6d84a86 | 2026-09-08T03:56:25Z |  |
| Kustomization | flux-system | alerts-secret | Ready | main@6d84a86 | 2026-09-08T03:54:15Z |  |
| Kustomization | flux-system | autoscaler | Ready | main@6d84a86 | 2026-09-08T03:57:09Z |  |
| Kustomization | flux-system | backstage | Ready | main@6d84a86 | 2026-09-08T03:57:51Z |  |
| Kustomization | flux-system | backstage-namespace | Ready | main@6d84a86 | 2026-09-08T03:54:14Z |  |
| Kustomization | flux-system | calico | Ready | main@6d84a86 | 2026-09-08T03:54:47Z |  |
| Kustomization | flux-system | chaos-mesh | Ready | main@6d84a86 | 2026-09-08T03:57:59Z |  |
| Kustomization | flux-system | cluster-state | Ready | main@6d84a86 | 2026-09-08T03:56:29Z |  |
| Kustomization | flux-system | commerce-data | Ready | main@6d84a86 | 2026-09-08T03:56:11Z |  |
| Kustomization | flux-system | cyrus | Ready | main@6d84a86 | 2026-09-08T03:57:03Z |  |
| Kustomization | flux-system | dagster | Ready | main@6d84a86 | 2026-09-08T03:54:14Z |  |
| Kustomization | flux-system | dns | Ready | main@6d84a86 | 2026-09-08T03:56:29Z |  |
| Kustomization | flux-system | drills | Ready | main@6d84a86 | 2026-09-08T03:54:55Z |  |
| Kustomization | flux-system | edge | Ready | main@6d84a86 | 2026-09-08T03:56:23Z |  |
| Kustomization | flux-system | estate-catalog | Ready | latest@sha256:67bb6c94dadcb443d1b4ca9bda | 2026-09-08T03:59:55Z |  |
| Kustomization | flux-system | estate-db | Ready | main@6d84a86 | 2026-09-08T03:56:25Z |  |
| Kustomization | flux-system | estate-db-migrate | Ready | main@6d84a86 | 2026-09-08T03:55:02Z |  |
| Kustomization | flux-system | estate-db-operator | Ready | main@6d84a86 | 2026-09-08T03:56:56Z |  |
| Kustomization | flux-system | event-bus | Ready | main@6d84a86 | 2026-09-08T03:54:54Z |  |
| Kustomization | flux-system | external-secrets | Ready | main@6d84a86 | 2026-09-08T03:54:48Z |  |
| Kustomization | flux-system | feature-register | Ready | main@6d84a86 | 2026-09-08T03:53:47Z |  |
| Kustomization | flux-system | flux-system | Ready | main@6d84a86 | 2026-09-08T03:57:27Z |  |
| Kustomization | flux-system | flux-webhook | Ready | main@6d84a86 | 2026-09-08T03:56:41Z |  |
| Kustomization | flux-system | gateway-api-crds | Ready | v1.5.1@e7677b7 | 2026-09-08T03:53:51Z |  |
| Kustomization | flux-system | guacamole | Ready | main@6d84a86 | 2026-09-08T03:57:40Z |  |
| Kustomization | flux-system | healing | Ready | main@6d84a86 | 2026-09-08T03:57:24Z |  |
| Kustomization | flux-system | healing-analyzer | Ready | main@6d84a86 | 2026-09-08T03:57:28Z |  |
| Kustomization | flux-system | healthchecks | Ready | main@6d84a86 | 2026-09-08T03:57:31Z |  |
| Kustomization | flux-system | hermes-agent | Ready | main@6d84a86 | 2026-09-08T03:56:40Z |  |
| Kustomization | flux-system | hindsight | Ready | main@6d84a86 | 2026-09-08T03:55:21Z |  |
| Kustomization | flux-system | human-vault | Ready | main@6d84a86 | 2026-09-08T03:57:40Z |  |
| Kustomization | flux-system | human-vault-bridge | Ready | main@6d84a86 | 2026-09-08T03:55:32Z |  |
| Kustomization | flux-system | identity | Ready | main@6d84a86 | 2026-09-08T03:56:38Z |  |
| Kustomization | flux-system | jit | Ready | main@6d84a86 | 2026-09-08T03:54:16Z |  |
| Kustomization | flux-system | keda | Ready | main@6d84a86 | 2026-09-08T03:57:31Z |  |
| Kustomization | flux-system | kyverno | Ready | main@6d84a86 | 2026-09-08T03:57:20Z |  |
| Kustomization | flux-system | llm | Ready | main@6d84a86 | 2026-09-08T03:56:46Z |  |
| Kustomization | flux-system | mcp | Ready | main@6d84a86 | 2026-09-08T03:57:43Z |  |
| Kustomization | flux-system | metrics-server | Ready | main@6d84a86 | 2026-09-08T03:56:31Z |  |
| Kustomization | flux-system | monitoring | Ready | main@6d84a86 | 2026-09-08T03:56:59Z |  |
| Kustomization | flux-system | monitoring-rules | Ready | main@6d84a86 | 2026-09-08T03:56:35Z |  |
| Kustomization | flux-system | notify | Ready | main@6d84a86 | 2026-09-08T03:56:06Z |  |
| Kustomization | flux-system | ns-fences | Ready | main@6d84a86 | 2026-09-08T03:56:28Z |  |
| Kustomization | flux-system | observability-collector | Ready | main@6d84a86 | 2026-09-08T03:57:39Z |  |
| Kustomization | flux-system | otto-golden | Ready | main@6d84a86 | 2026-09-08T03:55:54Z |  |
| Kustomization | flux-system | otto-golden-secret | Ready | main@6d84a86 | 2026-09-08T03:58:09Z |  |
| Kustomization | flux-system | priority-classes | Ready | main@6d84a86 | 2026-09-08T03:53:12Z |  |
| Kustomization | flux-system | prospector | Ready | main@7453d76 | 2026-09-08T03:56:13Z |  |
| Kustomization | flux-system | prospector-platform | Ready | main@6d84a86 | 2026-09-08T03:55:21Z |  |
| Kustomization | flux-system | rbac | Ready | main@6d84a86 | 2026-09-08T03:54:24Z |  |
| Kustomization | flux-system | rbac-floor | Ready | main@6d84a86 | 2026-09-08T03:55:30Z |  |
| Kustomization | flux-system | rbac-identity | Ready | main@6d84a86 | 2026-09-08T03:55:49Z |  |
| Kustomization | flux-system | reloader | Ready | main@6d84a86 | 2026-09-08T03:56:27Z |  |
| Kustomization | flux-system | research-engine | Ready | main@6d84a86 | 2026-09-08T03:57:23Z |  |
| Kustomization | flux-system | robusta | Ready | main@6d84a86 | 2026-09-08T03:56:52Z |  |
| Kustomization | flux-system | sandbox-launch | Ready | main@6d84a86 | 2026-09-08T03:55:50Z |  |
| Kustomization | flux-system | sandbox-live | Ready | sandbox/launch@929c1d7 | 2026-09-08T03:59:26Z |  |
| Kustomization | flux-system | scheduling | Ready | main@6d84a86 | 2026-09-08T03:57:11Z |  |
| Kustomization | flux-system | searxng | Ready | main@6d84a86 | 2026-09-08T03:54:53Z |  |
| Kustomization | flux-system | secret-store | Ready | main@6d84a86 | 2026-09-08T03:56:22Z |  |
| Kustomization | flux-system | spire | Ready | main@6d84a86 | 2026-09-08T03:58:00Z |  |
| Kustomization | flux-system | staging | Ready | main@6d84a86 | 2026-09-08T03:56:14Z |  |
| Kustomization | flux-system | tailscale | Ready | main@6d84a86 | 2026-09-08T03:56:05Z |  |
| Kustomization | flux-system | trivy | Ready | main@6d84a86 | 2026-09-08T03:56:03Z |  |
| Kustomization | flux-system | verification | Ready | main@6d84a86 | 2026-09-08T03:58:24Z |  |
| Kustomization | flux-system | weave-gitops | Ready | main@6d84a86 | 2026-09-08T03:56:56Z |  |
