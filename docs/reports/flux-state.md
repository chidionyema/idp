# Flux: what is applied

Read from the cluster receipt taken at 2026-09-13T08:00:48Z. Every Kustomization and HelmRelease, with the revision Flux last applied. **Suspended** is a switch somebody turned off on purpose (temporal, commerce, commerce-data, event-bus), not a defect; **Unknown** is a row Flux has never graded.

**117 objects: 97 ready, 18 not ready, 0 unknown, 2 suspended.**

## Not ready right now

- **HelmRelease commerce/lago** since 2026-09-13T07:55:49Z: Helm install failed for release commerce/lago with chart lago@1.28.0: failed early due to stalled resources: [Deployment/commerce/lago-payment-worker status: 'Failed']
- **Kustomization flux-system/agent-workforce** since 2026-09-13T08:00:02Z: dependency 'flux-system/llm' is not ready
- **Kustomization flux-system/alerts** since 2026-09-13T07:58:51Z: dependency 'flux-system/alerts-secret' is not ready
- **Kustomization flux-system/backstage** since 2026-09-13T07:59:55Z: dependency 'flux-system/estate-db-migrate' is not ready
- **Kustomization flux-system/chaos** since 2026-09-13T07:59:26Z: dependency 'flux-system/observability' is not ready
- **Kustomization flux-system/commerce** since 2026-09-13T07:58:46Z: Reconciliation in progress
- **Kustomization flux-system/crossplane-providerconfig** since 2026-09-13T07:59:26Z: dependency 'flux-system/crossplane-providers' is not ready
- **Kustomization flux-system/cyrus** since 2026-09-13T07:51:54Z: Reconciliation in progress
- **Kustomization flux-system/gvisor-runtime** since 2026-09-13T07:58:51Z: dependency 'flux-system/nodesoftware-operator' is not ready
- **Kustomization flux-system/healing-analyzer** since 2026-09-13T07:59:23Z: dependency 'flux-system/healing-k8sgpt' is not ready
- **Kustomization flux-system/healing-k8sgpt** since 2026-09-13T07:59:24Z: dependency 'flux-system/llm' is not ready
- **Kustomization flux-system/hindsight** since 2026-09-13T07:59:55Z: dependency 'flux-system/llm' is not ready
- **Kustomization flux-system/human-vault-bridge** since 2026-09-13T07:59:49Z: dependency 'flux-system/human-vault' is not ready
- **Kustomization flux-system/monitoring-rules** since 2026-09-13T07:59:42Z: dependency 'flux-system/monitoring' is not ready
- **Kustomization flux-system/observability** since 2026-09-13T08:00:09Z: Reconciliation in progress
- **Kustomization flux-system/research-engine** since 2026-09-13T07:59:54Z: dependency 'flux-system/llm' is not ready
- **Kustomization flux-system/router-events** since 2026-09-13T07:58:51Z: dependency 'flux-system/llm' is not ready
- **Kustomization flux-system/science** since 2026-09-13T07:59:20Z: dependency 'flux-system/observability' is not ready

## Every row

| Kind | Namespace | Name | State | Applied revision | Since | Message |
|---|---|---|---|---|---|---|
| HelmRelease | commerce | lago | Not ready | 1.28.0 | 2026-09-13T07:55:49Z | Helm install failed for release commerce/lago with chart lago@1.28.0: failed early due to stalled resources: [Deployment/commerce/lago-payment-worker status: 'F |
| Kustomization | flux-system | agent-workforce | Not ready | main@61db5e2 | 2026-09-13T08:00:02Z | dependency 'flux-system/llm' is not ready |
| Kustomization | flux-system | alerts | Not ready | main@61db5e2 | 2026-09-13T07:58:51Z | dependency 'flux-system/alerts-secret' is not ready |
| Kustomization | flux-system | backstage | Not ready | main@61db5e2 | 2026-09-13T07:59:55Z | dependency 'flux-system/estate-db-migrate' is not ready |
| Kustomization | flux-system | chaos | Not ready | main@61db5e2 | 2026-09-13T07:59:26Z | dependency 'flux-system/observability' is not ready |
| Kustomization | flux-system | commerce | Not ready | main@abea14d | 2026-09-13T07:58:46Z | Reconciliation in progress |
| Kustomization | flux-system | crossplane-providerconfig | Not ready | main@61db5e2 | 2026-09-13T07:59:26Z | dependency 'flux-system/crossplane-providers' is not ready |
| Kustomization | flux-system | cyrus | Not ready | main@17a5ceb | 2026-09-13T07:51:54Z | Reconciliation in progress |
| Kustomization | flux-system | gvisor-runtime | Not ready | main@61db5e2 | 2026-09-13T07:58:51Z | dependency 'flux-system/nodesoftware-operator' is not ready |
| Kustomization | flux-system | healing-analyzer | Not ready | main@61db5e2 | 2026-09-13T07:59:23Z | dependency 'flux-system/healing-k8sgpt' is not ready |
| Kustomization | flux-system | healing-k8sgpt | Not ready | main@61db5e2 | 2026-09-13T07:59:24Z | dependency 'flux-system/llm' is not ready |
| Kustomization | flux-system | hindsight | Not ready | main@61db5e2 | 2026-09-13T07:59:55Z | dependency 'flux-system/llm' is not ready |
| Kustomization | flux-system | human-vault-bridge | Not ready | main@61db5e2 | 2026-09-13T07:59:49Z | dependency 'flux-system/human-vault' is not ready |
| Kustomization | flux-system | monitoring-rules | Not ready | main@61db5e2 | 2026-09-13T07:59:42Z | dependency 'flux-system/monitoring' is not ready |
| Kustomization | flux-system | observability | Not ready | main@61db5e2 | 2026-09-13T08:00:09Z | Reconciliation in progress |
| Kustomization | flux-system | research-engine | Not ready | main@61db5e2 | 2026-09-13T07:59:54Z | dependency 'flux-system/llm' is not ready |
| Kustomization | flux-system | router-events | Not ready | main@61db5e2 | 2026-09-13T07:58:51Z | dependency 'flux-system/llm' is not ready |
| Kustomization | flux-system | science | Not ready | main@61db5e2 | 2026-09-13T07:59:20Z | dependency 'flux-system/observability' is not ready |
| HelmRelease | tigera-operator | tigera-operator | Suspended | v3.32.2 | 2026-09-06T19:38:02Z |  |
| Kustomization | flux-system | temporal | Suspended | main@1b323ac | 2026-09-08T20:23:54Z |  |
| HelmRelease | cert-manager | cert-manager | Ready | v1.21.1 | 2026-09-08T11:56:22Z |  |
| HelmRelease | chaos-mesh | chaos-mesh | Ready | 2.8.4 | 2026-09-13T04:26:37Z |  |
| HelmRelease | crossplane-system | crossplane | Ready | 2.4.0 | 2026-09-08T07:05:25Z |  |
| HelmRelease | dagster | dagster | Ready | 1.13.19 | 2026-09-12T12:32:50Z |  |
| HelmRelease | edge | external-dns | Ready | 1.21.1 | 2026-09-06T19:33:35Z |  |
| HelmRelease | edge | traefik | Ready | 41.3.0 | 2026-09-06T19:35:13Z |  |
| HelmRelease | estate-db | cloudnative-pg | Ready | 0.29.0 | 2026-09-06T19:45:25Z |  |
| HelmRelease | event-bus | nats | Ready | 2.14.6 | 2026-09-06T19:39:37Z |  |
| HelmRelease | external-secrets | external-secrets | Ready | 2.9.0 | 2026-09-08T11:57:40Z |  |
| HelmRelease | healing | descheduler | Ready | 0.36.0 | 2026-09-08T10:45:39Z |  |
| HelmRelease | healing | k8sgpt-operator | Ready | 0.2.29 | 2026-09-08T12:01:53Z |  |
| HelmRelease | hindsight | hindsight | Ready | 0.9.2 | 2026-09-08T18:46:49Z |  |
| HelmRelease | identity | oauth2-proxy | Ready | 10.7.0 | 2026-09-08T10:18:34Z |  |
| HelmRelease | keda | keda | Ready | 2.20.2 | 2026-09-08T10:19:32Z |  |
| HelmRelease | keda | keda-add-ons-http | Ready | 0.15.0 | 2026-09-08T10:20:22Z |  |
| HelmRelease | kyverno | kyverno | Ready | 3.9.0 | 2026-09-08T10:19:02Z |  |
| HelmRelease | metrics-server | metrics-server | Ready | 3.14.0 | 2026-09-06T19:34:02Z |  |
| HelmRelease | monitoring | blackbox | Ready | 11.17.2 | 2026-09-06T19:47:10Z |  |
| HelmRelease | monitoring | kube-prometheus-stack | Ready | 88.6.0 | 2026-09-06T20:26:45Z |  |
| HelmRelease | observability | langfuse | Ready | 2.0.2 | 2026-09-13T03:17:37Z |  |
| HelmRelease | observability | signoz | Ready | 0.138.0 | 2026-09-08T12:05:11Z |  |
| HelmRelease | observability | superset | Ready | 0.22.4 | 2026-09-06T19:46:05Z |  |
| HelmRelease | observability-agent | k8s-infra | Ready | 0.17.0 | 2026-09-09T14:28:44Z |  |
| HelmRelease | reloader | reloader | Ready | 2.2.16 | 2026-09-06T19:33:25Z |  |
| HelmRelease | robusta | robusta | Ready | 0.48.0 | 2026-09-06T20:26:45Z |  |
| HelmRelease | spire-mgmt | spire | Ready | 0.30.1 | 2026-09-08T09:39:33Z |  |
| HelmRelease | spire-mgmt | spire-crds | Ready | 0.6.1 | 2026-09-06T20:26:47Z |  |
| HelmRelease | tailscale | tailscale-operator | Ready | 1.102.3 | 2026-09-06T19:33:35Z |  |
| HelmRelease | temporal | temporal | Ready | 1.6.0 | 2026-09-08T23:12:29Z |  |
| HelmRelease | trivy-system | trivy-operator | Ready | 0.36.0 | 2026-09-06T20:26:45Z |  |
| HelmRelease | weave-gitops | weave-gitops | Ready | 4.0.36 | 2026-09-06T20:26:45Z |  |
| Kustomization | flux-system | alerts-github | Ready | main@e79a547 | 2026-09-13T07:59:45Z |  |
| Kustomization | flux-system | alerts-secret | Ready | main@e79a547 | 2026-09-13T07:59:26Z |  |
| Kustomization | flux-system | autoscaler | Ready | main@e79a547 | 2026-09-13T07:59:54Z |  |
| Kustomization | flux-system | backstage-namespace | Ready | main@e79a547 | 2026-09-13T07:58:54Z |  |
| Kustomization | flux-system | calico | Ready | main@e79a547 | 2026-09-13T07:59:04Z |  |
| Kustomization | flux-system | chaos-mesh | Ready | main@e79a547 | 2026-09-13T07:59:15Z |  |
| Kustomization | flux-system | cluster-state | Ready | main@e79a547 | 2026-09-13T07:59:47Z |  |
| Kustomization | flux-system | commerce-data | Ready | main@e79a547 | 2026-09-13T08:00:09Z |  |
| Kustomization | flux-system | concierge | Ready | main@e79a547 | 2026-09-13T07:59:49Z |  |
| Kustomization | flux-system | cross-node-drill | Ready | main@e79a547 | 2026-09-13T07:58:57Z |  |
| Kustomization | flux-system | crossplane | Ready | main@e79a547 | 2026-09-13T07:59:43Z |  |
| Kustomization | flux-system | crossplane-providers | Ready | main@e79a547 | 2026-09-13T07:59:59Z |  |
| Kustomization | flux-system | dagster | Ready | main@e79a547 | 2026-09-13T08:00:10Z |  |
| Kustomization | flux-system | dns | Ready | main@e79a547 | 2026-09-13T07:59:51Z |  |
| Kustomization | flux-system | drills | Ready | main@e79a547 | 2026-09-13T07:59:58Z |  |
| Kustomization | flux-system | edge | Ready | main@e79a547 | 2026-09-13T07:59:12Z |  |
| Kustomization | flux-system | estate-catalog | Ready | latest@sha256:fa34eea88fd3dd815a9b5b0985 | 2026-09-13T07:53:16Z |  |
| Kustomization | flux-system | estate-db | Ready | main@e79a547 | 2026-09-13T07:59:37Z |  |
| Kustomization | flux-system | estate-db-migrate | Ready | main@e79a547 | 2026-09-13T07:59:56Z |  |
| Kustomization | flux-system | estate-db-operator | Ready | main@e79a547 | 2026-09-13T07:58:59Z |  |
| Kustomization | flux-system | event-bus | Ready | main@e79a547 | 2026-09-13T07:59:07Z |  |
| Kustomization | flux-system | external-secrets | Ready | main@e79a547 | 2026-09-13T07:59:17Z |  |
| Kustomization | flux-system | feature-register | Ready | main@e79a547 | 2026-09-13T07:59:27Z |  |
| Kustomization | flux-system | flux-system | Ready | main@e79a547 | 2026-09-13T07:59:05Z |  |
| Kustomization | flux-system | flux-webhook | Ready | main@e79a547 | 2026-09-13T07:59:25Z |  |
| Kustomization | flux-system | gateway-api-crds | Ready | v1.5.1@e7677b7 | 2026-09-13T07:58:57Z |  |
| Kustomization | flux-system | guacamole | Ready | main@e79a547 | 2026-09-13T08:00:13Z |  |
| Kustomization | flux-system | healing | Ready | main@e79a547 | 2026-09-13T07:59:19Z |  |
| Kustomization | flux-system | healthchecks | Ready | main@e79a547 | 2026-09-13T08:00:06Z |  |
| Kustomization | flux-system | hermes-agent | Ready | main@e79a547 | 2026-09-13T07:59:56Z |  |
| Kustomization | flux-system | human-vault | Ready | main@e79a547 | 2026-09-13T07:59:52Z |  |
| Kustomization | flux-system | identity | Ready | main@e79a547 | 2026-09-13T07:59:51Z |  |
| Kustomization | flux-system | image-automation | Ready | main@e79a547 | 2026-09-13T07:59:24Z |  |
| Kustomization | flux-system | jit | Ready | main@e79a547 | 2026-09-13T07:59:29Z |  |
| Kustomization | flux-system | keda | Ready | main@e79a547 | 2026-09-13T07:59:18Z |  |
| Kustomization | flux-system | kyverno | Ready | main@e79a547 | 2026-09-13T07:58:53Z |  |
| Kustomization | flux-system | llm | Ready | main@e79a547 | 2026-09-13T08:00:07Z |  |
| Kustomization | flux-system | mcp | Ready | main@e79a547 | 2026-09-13T07:59:59Z |  |
| Kustomization | flux-system | metrics-server | Ready | main@e79a547 | 2026-09-13T07:59:22Z |  |
| Kustomization | flux-system | monitoring | Ready | main@e79a547 | 2026-09-13T07:59:43Z |  |
| Kustomization | flux-system | nodesoftware-operator | Ready | main@e79a547 | 2026-09-13T08:00:04Z |  |
| Kustomization | flux-system | notify | Ready | main@e79a547 | 2026-09-13T07:59:49Z |  |
| Kustomization | flux-system | ns-fences | Ready | main@e79a547 | 2026-09-13T07:59:19Z |  |
| Kustomization | flux-system | observability-collector | Ready | main@e79a547 | 2026-09-13T07:59:45Z |  |
| Kustomization | flux-system | otto-gateway | Ready | main@e79a547 | 2026-09-13T08:00:04Z |  |
| Kustomization | flux-system | otto-golden | Ready | main@e79a547 | 2026-09-13T07:59:55Z |  |
| Kustomization | flux-system | otto-golden-secret | Ready | main@e79a547 | 2026-09-13T07:59:23Z |  |
| Kustomization | flux-system | priority-classes | Ready | main@e79a547 | 2026-09-13T07:58:59Z |  |
| Kustomization | flux-system | prospector | Ready | main@7453d76 | 2026-09-13T07:52:02Z |  |
| Kustomization | flux-system | prospector-platform | Ready | main@e79a547 | 2026-09-13T07:59:48Z |  |
| Kustomization | flux-system | rbac | Ready | main@e79a547 | 2026-09-13T07:59:08Z |  |
| Kustomization | flux-system | rbac-floor | Ready | main@e79a547 | 2026-09-13T07:59:02Z |  |
| Kustomization | flux-system | rbac-identity | Ready | main@e79a547 | 2026-09-13T07:59:00Z |  |
| Kustomization | flux-system | reloader | Ready | main@e79a547 | 2026-09-13T07:59:25Z |  |
| Kustomization | flux-system | robusta | Ready | main@e79a547 | 2026-09-13T07:59:39Z |  |
| Kustomization | flux-system | sandbox-launch | Ready | main@e79a547 | 2026-09-13T07:59:20Z |  |
| Kustomization | flux-system | sandbox-live | Ready | sandbox/launch@4830a6e | 2026-09-13T07:59:23Z |  |
| Kustomization | flux-system | scheduling | Ready | main@e79a547 | 2026-09-13T07:59:14Z |  |
| Kustomization | flux-system | searxng | Ready | main@e79a547 | 2026-09-13T07:58:55Z |  |
| Kustomization | flux-system | secret-store | Ready | main@e79a547 | 2026-09-13T07:59:21Z |  |
| Kustomization | flux-system | spire | Ready | main@e79a547 | 2026-09-13T07:59:39Z |  |
| Kustomization | flux-system | staging | Ready | main@e79a547 | 2026-09-13T07:58:56Z |  |
| Kustomization | flux-system | tailscale | Ready | main@e79a547 | 2026-09-13T07:59:46Z |  |
| Kustomization | flux-system | trivy | Ready | main@e79a547 | 2026-09-13T07:58:53Z |  |
| Kustomization | flux-system | verification | Ready | main@e79a547 | 2026-09-13T07:59:52Z |  |
| Kustomization | flux-system | weave-gitops | Ready | main@e79a547 | 2026-09-13T08:00:02Z |  |
