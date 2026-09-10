# Flux: what is applied

Read from the cluster receipt taken at 2026-09-10T08:00:58Z. Every Kustomization and HelmRelease, with the revision Flux last applied. **Suspended** is a switch somebody turned off on purpose (temporal, commerce, commerce-data, event-bus), not a defect; **Unknown** is a row Flux has never graded.

**114 objects: 89 ready, 23 not ready, 0 unknown, 2 suspended.**

## Not ready right now

- **HelmRelease commerce/lago** since 2026-09-09T17:12:02Z: Helm install failed for release commerce/lago with chart lago@1.28.0: failed early due to stalled resources: [Deployment/commerce/lago-api status: 'Failed']
- **Kustomization flux-system/agent-workforce** since 2026-09-10T07:41:36Z: dependency 'flux-system/llm' is not ready
- **Kustomization flux-system/backstage** since 2026-09-10T07:40:42Z: dependency 'flux-system/estate-db-migrate' is not ready
- **Kustomization flux-system/chaos** since 2026-09-10T07:40:42Z: dependency 'flux-system/observability' is not ready
- **Kustomization flux-system/cluster-state** since 2026-09-10T07:51:41Z: Reconciliation in progress
- **Kustomization flux-system/commerce** since 2026-09-09T16:43:19Z: dependency 'flux-system/commerce-data' is not ready
- **Kustomization flux-system/commerce-data** since 2026-09-10T07:40:42Z: dependency 'flux-system/estate-db' is not ready
- **Kustomization flux-system/cyrus** since 2026-09-10T07:51:39Z: Reconciliation in progress
- **Kustomization flux-system/dagster** since 2026-09-10T07:40:42Z: dependency 'flux-system/estate-db-migrate' is not ready
- **Kustomization flux-system/estate-db** since 2026-09-10T07:55:44Z: Reconciliation in progress
- **Kustomization flux-system/estate-db-migrate** since 2026-09-09T16:22:08Z: dependency 'flux-system/estate-db' is not ready
- **Kustomization flux-system/guacamole** since 2026-09-10T07:41:36Z: dependency 'flux-system/estate-db-migrate' is not ready
- **Kustomization flux-system/healing-analyzer** since 2026-09-09T12:14:17Z: dependency 'flux-system/healing-k8sgpt' is not ready
- **Kustomization flux-system/healing-k8sgpt** since 2026-09-10T07:40:42Z: dependency 'flux-system/llm' is not ready
- **Kustomization flux-system/healthchecks** since 2026-09-10T07:41:35Z: dependency 'flux-system/estate-db-migrate' is not ready
- **Kustomization flux-system/hindsight** since 2026-09-10T07:40:42Z: dependency 'flux-system/llm' is not ready
- **Kustomization flux-system/llm** since 2026-09-10T07:40:42Z: dependency 'flux-system/estate-db-migrate' is not ready
- **Kustomization flux-system/mcp** since 2026-09-10T07:51:39Z: Reconciliation in progress
- **Kustomization flux-system/monitoring-rules** since 2026-09-10T07:51:19Z: dependency 'flux-system/monitoring' is not ready
- **Kustomization flux-system/observability** since 2026-09-10T07:40:42Z: dependency 'flux-system/estate-db-migrate' is not ready
- **Kustomization flux-system/otto-gateway** since 2026-09-10T07:51:34Z: health check failed after 2.11162045s: failed early due to stalled resources: [Job/otto-gateway/otto-memory-store-6 status: 'Failed']
- **Kustomization flux-system/research-engine** since 2026-09-10T07:40:42Z: dependency 'flux-system/llm' is not ready
- **Kustomization flux-system/science** since 2026-09-09T16:33:56Z: dependency 'flux-system/observability' is not ready

## Every row

| Kind | Namespace | Name | State | Applied revision | Since | Message |
|---|---|---|---|---|---|---|
| HelmRelease | commerce | lago | Not ready | 1.28.0 | 2026-09-09T17:12:02Z | Helm install failed for release commerce/lago with chart lago@1.28.0: failed early due to stalled resources: [Deployment/commerce/lago-api status: 'Failed'] |
| Kustomization | flux-system | agent-workforce | Not ready | main@c8b4f4a | 2026-09-10T07:41:36Z | dependency 'flux-system/llm' is not ready |
| Kustomization | flux-system | backstage | Not ready | main@bb83118 | 2026-09-10T07:40:42Z | dependency 'flux-system/estate-db-migrate' is not ready |
| Kustomization | flux-system | chaos | Not ready | main@bb83118 | 2026-09-10T07:40:42Z | dependency 'flux-system/observability' is not ready |
| Kustomization | flux-system | cluster-state | Not ready | main@bf63acf | 2026-09-10T07:51:41Z | Reconciliation in progress |
| Kustomization | flux-system | commerce | Not ready | main@5b6aeea | 2026-09-09T16:43:19Z | dependency 'flux-system/commerce-data' is not ready |
| Kustomization | flux-system | commerce-data | Not ready | main@5b6aeea | 2026-09-10T07:40:42Z | dependency 'flux-system/estate-db' is not ready |
| Kustomization | flux-system | cyrus | Not ready | main@17a5ceb | 2026-09-10T07:51:39Z | Reconciliation in progress |
| Kustomization | flux-system | dagster | Not ready | main@5b6aeea | 2026-09-10T07:40:42Z | dependency 'flux-system/estate-db-migrate' is not ready |
| Kustomization | flux-system | estate-db | Not ready | main@5b6aeea | 2026-09-10T07:55:44Z | Reconciliation in progress |
| Kustomization | flux-system | estate-db-migrate | Not ready | main@5b6aeea | 2026-09-09T16:22:08Z | dependency 'flux-system/estate-db' is not ready |
| Kustomization | flux-system | guacamole | Not ready | main@5b6aeea | 2026-09-10T07:41:36Z | dependency 'flux-system/estate-db-migrate' is not ready |
| Kustomization | flux-system | healing-analyzer | Not ready | main@c8b4f4a | 2026-09-09T12:14:17Z | dependency 'flux-system/healing-k8sgpt' is not ready |
| Kustomization | flux-system | healing-k8sgpt | Not ready | main@c8b4f4a | 2026-09-10T07:40:42Z | dependency 'flux-system/llm' is not ready |
| Kustomization | flux-system | healthchecks | Not ready | main@bb83118 | 2026-09-10T07:41:35Z | dependency 'flux-system/estate-db-migrate' is not ready |
| Kustomization | flux-system | hindsight | Not ready | main@c8b4f4a | 2026-09-10T07:40:42Z | dependency 'flux-system/llm' is not ready |
| Kustomization | flux-system | llm | Not ready | main@c8b4f4a | 2026-09-10T07:40:42Z | dependency 'flux-system/estate-db-migrate' is not ready |
| Kustomization | flux-system | mcp | Not ready | main@54b53d2 | 2026-09-10T07:51:39Z | Reconciliation in progress |
| Kustomization | flux-system | monitoring-rules | Not ready | main@fea9804 | 2026-09-10T07:51:19Z | dependency 'flux-system/monitoring' is not ready |
| Kustomization | flux-system | observability | Not ready | main@5b6aeea | 2026-09-10T07:40:42Z | dependency 'flux-system/estate-db-migrate' is not ready |
| Kustomization | flux-system | otto-gateway | Not ready | main@bb83118 | 2026-09-10T07:51:34Z | health check failed after 2.11162045s: failed early due to stalled resources: [Job/otto-gateway/otto-memory-store-6 status: 'Failed'] |
| Kustomization | flux-system | research-engine | Not ready | main@c8b4f4a | 2026-09-10T07:40:42Z | dependency 'flux-system/llm' is not ready |
| Kustomization | flux-system | science | Not ready | main@5b6aeea | 2026-09-09T16:33:56Z | dependency 'flux-system/observability' is not ready |
| HelmRelease | tigera-operator | tigera-operator | Suspended | v3.32.2 | 2026-09-06T19:38:02Z |  |
| Kustomization | flux-system | temporal | Suspended | main@1b323ac | 2026-09-08T20:23:54Z |  |
| HelmRelease | cert-manager | cert-manager | Ready | v1.21.1 | 2026-09-08T11:56:22Z |  |
| HelmRelease | chaos-mesh | chaos-mesh | Ready | 2.8.4 | 2026-09-08T09:36:49Z |  |
| HelmRelease | crossplane-system | crossplane | Ready | 2.4.0 | 2026-09-08T07:05:25Z |  |
| HelmRelease | dagster | dagster | Ready | 1.13.19 | 2026-09-08T06:32:55Z |  |
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
| HelmRelease | observability | langfuse | Ready | 2.0.2 | 2026-09-08T08:30:33Z |  |
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
| Kustomization | flux-system | alerts | Ready | main@7880917 | 2026-09-10T07:51:27Z |  |
| Kustomization | flux-system | alerts-github | Ready | main@7880917 | 2026-09-10T07:51:28Z |  |
| Kustomization | flux-system | alerts-secret | Ready | main@7880917 | 2026-09-10T07:51:21Z |  |
| Kustomization | flux-system | autoscaler | Ready | main@7880917 | 2026-09-10T07:51:23Z |  |
| Kustomization | flux-system | backstage-namespace | Ready | main@7880917 | 2026-09-10T07:50:32Z |  |
| Kustomization | flux-system | calico | Ready | main@7880917 | 2026-09-10T07:50:38Z |  |
| Kustomization | flux-system | chaos-mesh | Ready | main@7880917 | 2026-09-10T07:51:16Z |  |
| Kustomization | flux-system | crossplane | Ready | main@7880917 | 2026-09-10T07:51:13Z |  |
| Kustomization | flux-system | crossplane-providerconfig | Ready | main@7880917 | 2026-09-10T07:51:38Z |  |
| Kustomization | flux-system | crossplane-providers | Ready | main@7880917 | 2026-09-10T07:51:19Z |  |
| Kustomization | flux-system | dns | Ready | main@7880917 | 2026-09-10T07:51:17Z |  |
| Kustomization | flux-system | drills | Ready | main@7880917 | 2026-09-10T07:51:31Z |  |
| Kustomization | flux-system | edge | Ready | main@7880917 | 2026-09-10T07:51:06Z |  |
| Kustomization | flux-system | estate-catalog | Ready | latest@sha256:8ab0d9286bc2769859d864f54d | 2026-09-10T07:51:41Z |  |
| Kustomization | flux-system | estate-db-operator | Ready | main@7880917 | 2026-09-10T07:50:39Z |  |
| Kustomization | flux-system | event-bus | Ready | main@7880917 | 2026-09-10T07:51:02Z |  |
| Kustomization | flux-system | external-secrets | Ready | main@7880917 | 2026-09-10T07:51:09Z |  |
| Kustomization | flux-system | feature-register | Ready | main@7880917 | 2026-09-10T07:50:52Z |  |
| Kustomization | flux-system | flux-system | Ready | main@7880917 | 2026-09-10T07:50:55Z |  |
| Kustomization | flux-system | flux-webhook | Ready | main@7880917 | 2026-09-10T07:51:18Z |  |
| Kustomization | flux-system | gateway-api-crds | Ready | v1.5.1@e7677b7 | 2026-09-10T07:50:45Z |  |
| Kustomization | flux-system | gvisor-runtime | Ready | main@7880917 | 2026-09-10T07:51:39Z |  |
| Kustomization | flux-system | healing | Ready | main@7880917 | 2026-09-10T07:51:11Z |  |
| Kustomization | flux-system | hermes-agent | Ready | main@7880917 | 2026-09-10T07:51:37Z |  |
| Kustomization | flux-system | human-vault | Ready | main@7880917 | 2026-09-10T07:51:25Z |  |
| Kustomization | flux-system | human-vault-bridge | Ready | main@7880917 | 2026-09-10T07:51:29Z |  |
| Kustomization | flux-system | identity | Ready | main@7880917 | 2026-09-10T07:51:32Z |  |
| Kustomization | flux-system | image-automation | Ready | main@7880917 | 2026-09-10T07:51:26Z |  |
| Kustomization | flux-system | jit | Ready | main@7880917 | 2026-09-10T07:50:48Z |  |
| Kustomization | flux-system | keda | Ready | main@7880917 | 2026-09-10T07:51:12Z |  |
| Kustomization | flux-system | kyverno | Ready | main@7880917 | 2026-09-10T07:50:41Z |  |
| Kustomization | flux-system | metrics-server | Ready | main@7880917 | 2026-09-10T07:51:14Z |  |
| Kustomization | flux-system | monitoring | Ready | main@7880917 | 2026-09-10T07:51:19Z |  |
| Kustomization | flux-system | nodesoftware-operator | Ready | main@7880917 | 2026-09-10T07:51:34Z |  |
| Kustomization | flux-system | notify | Ready | main@7880917 | 2026-09-10T07:51:26Z |  |
| Kustomization | flux-system | ns-fences | Ready | main@7880917 | 2026-09-10T07:51:07Z |  |
| Kustomization | flux-system | observability-collector | Ready | main@7880917 | 2026-09-10T07:51:12Z |  |
| Kustomization | flux-system | otto-golden | Ready | main@7880917 | 2026-09-10T07:51:39Z |  |
| Kustomization | flux-system | otto-golden-secret | Ready | main@7880917 | 2026-09-10T07:51:30Z |  |
| Kustomization | flux-system | priority-classes | Ready | main@7880917 | 2026-09-10T07:50:51Z |  |
| Kustomization | flux-system | prospector | Ready | main@7453d76 | 2026-09-10T07:34:32Z |  |
| Kustomization | flux-system | prospector-platform | Ready | main@7880917 | 2026-09-10T07:51:11Z |  |
| Kustomization | flux-system | rbac | Ready | main@7880917 | 2026-09-10T07:51:03Z |  |
| Kustomization | flux-system | rbac-floor | Ready | main@7880917 | 2026-09-10T07:50:35Z |  |
| Kustomization | flux-system | rbac-identity | Ready | main@7880917 | 2026-09-10T07:50:49Z |  |
| Kustomization | flux-system | reloader | Ready | main@7880917 | 2026-09-10T07:51:20Z |  |
| Kustomization | flux-system | robusta | Ready | main@7880917 | 2026-09-10T07:51:24Z |  |
| Kustomization | flux-system | sandbox-launch | Ready | main@7880917 | 2026-09-10T07:51:09Z |  |
| Kustomization | flux-system | sandbox-live | Ready | sandbox/launch@5844e79 | 2026-09-10T07:40:23Z |  |
| Kustomization | flux-system | scheduling | Ready | main@7880917 | 2026-09-10T07:51:07Z |  |
| Kustomization | flux-system | searxng | Ready | main@7880917 | 2026-09-10T07:50:33Z |  |
| Kustomization | flux-system | secret-store | Ready | main@7880917 | 2026-09-10T07:51:14Z |  |
| Kustomization | flux-system | spire | Ready | main@7880917 | 2026-09-10T07:51:17Z |  |
| Kustomization | flux-system | staging | Ready | main@7880917 | 2026-09-10T07:50:37Z |  |
| Kustomization | flux-system | tailscale | Ready | main@7880917 | 2026-09-10T07:51:23Z |  |
| Kustomization | flux-system | trivy | Ready | main@7880917 | 2026-09-10T07:50:42Z |  |
| Kustomization | flux-system | verification | Ready | main@7880917 | 2026-09-10T07:51:27Z |  |
| Kustomization | flux-system | weave-gitops | Ready | main@7880917 | 2026-09-10T07:51:36Z |  |
