# Flux: what is applied

Read from the cluster receipt taken at 2026-09-12T17:15:14Z. Every Kustomization and HelmRelease, with the revision Flux last applied. **Suspended** is a switch somebody turned off on purpose (temporal, commerce, commerce-data, event-bus), not a defect; **Unknown** is a row Flux has never graded.

**117 objects: 103 ready, 12 not ready, 0 unknown, 2 suspended.**

## Not ready right now

- **HelmRelease commerce/lago** since 2026-09-12T17:13:32Z: Helm install failed for release commerce/lago with chart lago@1.28.0: failed early due to stalled resources: [Deployment/commerce/lago-api status: 'Failed']
- **Kustomization flux-system/agent-workforce** since 2026-09-12T17:14:51Z: dependency 'flux-system/llm' is not ready
- **Kustomization flux-system/chaos** since 2026-09-12T17:14:37Z: dependency 'flux-system/observability' is not ready
- **Kustomization flux-system/commerce** since 2026-09-12T17:01:34Z: Reconciliation in progress
- **Kustomization flux-system/cyrus** since 2026-09-12T17:14:04Z: Reconciliation in progress
- **Kustomization flux-system/dagster** since 2026-09-12T17:15:09Z: Reconciliation in progress
- **Kustomization flux-system/guacamole** since 2026-09-12T17:14:37Z: dependency 'flux-system/tailscale' is not ready
- **Kustomization flux-system/healing-analyzer** since 2026-09-12T17:12:58Z: dependency 'flux-system/healing-k8sgpt' is not ready
- **Kustomization flux-system/observability** since 2026-09-12T17:13:29Z: dependency 'flux-system/estate-db-migrate' is not ready
- **Kustomization flux-system/router-events** since 2026-09-12T17:12:56Z: dependency 'flux-system/llm' is not ready
- **Kustomization flux-system/science** since 2026-09-12T17:12:58Z: dependency 'flux-system/observability' is not ready
- **Kustomization flux-system/tailscale** since 2026-09-12T17:14:04Z: Reconciliation in progress

## Every row

| Kind | Namespace | Name | State | Applied revision | Since | Message |
|---|---|---|---|---|---|---|
| HelmRelease | commerce | lago | Not ready | 1.28.0 | 2026-09-12T17:13:32Z | Helm install failed for release commerce/lago with chart lago@1.28.0: failed early due to stalled resources: [Deployment/commerce/lago-api status: 'Failed'] |
| Kustomization | flux-system | agent-workforce | Not ready | main@b08d18b | 2026-09-12T17:14:51Z | dependency 'flux-system/llm' is not ready |
| Kustomization | flux-system | chaos | Not ready | main@abea14d | 2026-09-12T17:14:37Z | dependency 'flux-system/observability' is not ready |
| Kustomization | flux-system | commerce | Not ready | main@abea14d | 2026-09-12T17:01:34Z | Reconciliation in progress |
| Kustomization | flux-system | cyrus | Not ready | main@17a5ceb | 2026-09-12T17:14:04Z | Reconciliation in progress |
| Kustomization | flux-system | dagster | Not ready | main@b08d18b | 2026-09-12T17:15:09Z | Reconciliation in progress |
| Kustomization | flux-system | guacamole | Not ready | main@5b6aeea | 2026-09-12T17:14:37Z | dependency 'flux-system/tailscale' is not ready |
| Kustomization | flux-system | healing-analyzer | Not ready | main@b08d18b | 2026-09-12T17:12:58Z | dependency 'flux-system/healing-k8sgpt' is not ready |
| Kustomization | flux-system | observability | Not ready | main@b08d18b | 2026-09-12T17:13:29Z | dependency 'flux-system/estate-db-migrate' is not ready |
| Kustomization | flux-system | router-events | Not ready | main@b08d18b | 2026-09-12T17:12:56Z | dependency 'flux-system/llm' is not ready |
| Kustomization | flux-system | science | Not ready | main@b08d18b | 2026-09-12T17:12:58Z | dependency 'flux-system/observability' is not ready |
| Kustomization | flux-system | tailscale | Not ready | main@d3ab8a2 | 2026-09-12T17:14:04Z | Reconciliation in progress |
| HelmRelease | tigera-operator | tigera-operator | Suspended | v3.32.2 | 2026-09-06T19:38:02Z |  |
| Kustomization | flux-system | temporal | Suspended | main@1b323ac | 2026-09-08T20:23:54Z |  |
| HelmRelease | cert-manager | cert-manager | Ready | v1.21.1 | 2026-09-08T11:56:22Z |  |
| HelmRelease | chaos-mesh | chaos-mesh | Ready | 2.8.4 | 2026-09-08T09:36:49Z |  |
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
| Kustomization | flux-system | alerts | Ready | main@fe21b57 | 2026-09-12T17:14:17Z |  |
| Kustomization | flux-system | alerts-github | Ready | main@fe21b57 | 2026-09-12T17:14:20Z |  |
| Kustomization | flux-system | alerts-secret | Ready | main@fe21b57 | 2026-09-12T17:14:01Z |  |
| Kustomization | flux-system | autoscaler | Ready | main@fe21b57 | 2026-09-12T17:13:57Z |  |
| Kustomization | flux-system | backstage | Ready | main@fe21b57 | 2026-09-12T17:14:51Z |  |
| Kustomization | flux-system | backstage-namespace | Ready | main@fe21b57 | 2026-09-12T17:12:20Z |  |
| Kustomization | flux-system | calico | Ready | main@fe21b57 | 2026-09-12T17:12:17Z |  |
| Kustomization | flux-system | chaos-mesh | Ready | main@fe21b57 | 2026-09-12T17:13:59Z |  |
| Kustomization | flux-system | cluster-state | Ready | main@fe21b57 | 2026-09-12T17:13:31Z |  |
| Kustomization | flux-system | commerce-data | Ready | main@fe21b57 | 2026-09-12T17:14:04Z |  |
| Kustomization | flux-system | concierge | Ready | main@fe21b57 | 2026-09-12T17:13:55Z |  |
| Kustomization | flux-system | cross-node-drill | Ready | main@fe21b57 | 2026-09-12T17:12:15Z |  |
| Kustomization | flux-system | crossplane | Ready | main@fe21b57 | 2026-09-12T17:13:28Z |  |
| Kustomization | flux-system | crossplane-providerconfig | Ready | main@fe21b57 | 2026-09-12T17:14:23Z |  |
| Kustomization | flux-system | crossplane-providers | Ready | main@fe21b57 | 2026-09-12T17:14:21Z |  |
| Kustomization | flux-system | dns | Ready | main@fe21b57 | 2026-09-12T17:14:07Z |  |
| Kustomization | flux-system | drills | Ready | main@fe21b57 | 2026-09-12T17:14:37Z |  |
| Kustomization | flux-system | edge | Ready | main@fe21b57 | 2026-09-12T17:12:59Z |  |
| Kustomization | flux-system | estate-catalog | Ready | latest@sha256:667515359df3fe606417ffe52b | 2026-09-12T17:10:39Z |  |
| Kustomization | flux-system | estate-db | Ready | main@fe21b57 | 2026-09-12T17:13:54Z |  |
| Kustomization | flux-system | estate-db-migrate | Ready | main@fe21b57 | 2026-09-12T17:14:41Z |  |
| Kustomization | flux-system | estate-db-operator | Ready | main@fe21b57 | 2026-09-12T17:12:19Z |  |
| Kustomization | flux-system | event-bus | Ready | main@fe21b57 | 2026-09-12T17:12:45Z |  |
| Kustomization | flux-system | external-secrets | Ready | main@fe21b57 | 2026-09-12T17:13:23Z |  |
| Kustomization | flux-system | feature-register | Ready | main@fe21b57 | 2026-09-12T17:12:21Z |  |
| Kustomization | flux-system | flux-system | Ready | main@fe21b57 | 2026-09-12T17:12:21Z |  |
| Kustomization | flux-system | flux-webhook | Ready | main@fe21b57 | 2026-09-12T17:14:25Z |  |
| Kustomization | flux-system | gateway-api-crds | Ready | v1.5.1@e7677b7 | 2026-09-12T17:12:27Z |  |
| Kustomization | flux-system | gvisor-runtime | Ready | main@fe21b57 | 2026-09-12T17:14:58Z |  |
| Kustomization | flux-system | healing | Ready | main@fe21b57 | 2026-09-12T17:13:56Z |  |
| Kustomization | flux-system | healing-k8sgpt | Ready | main@fe21b57 | 2026-09-12T17:14:57Z |  |
| Kustomization | flux-system | healthchecks | Ready | main@fe21b57 | 2026-09-12T17:15:09Z |  |
| Kustomization | flux-system | hermes-agent | Ready | main@fe21b57 | 2026-09-12T17:14:32Z |  |
| Kustomization | flux-system | hindsight | Ready | main@fe21b57 | 2026-09-12T17:14:59Z |  |
| Kustomization | flux-system | human-vault | Ready | main@fe21b57 | 2026-09-12T17:13:58Z |  |
| Kustomization | flux-system | human-vault-bridge | Ready | main@fe21b57 | 2026-09-12T17:14:19Z |  |
| Kustomization | flux-system | identity | Ready | main@fe21b57 | 2026-09-12T17:14:22Z |  |
| Kustomization | flux-system | image-automation | Ready | main@fe21b57 | 2026-09-12T17:14:39Z |  |
| Kustomization | flux-system | jit | Ready | main@fe21b57 | 2026-09-12T17:12:45Z |  |
| Kustomization | flux-system | keda | Ready | main@fe21b57 | 2026-09-12T17:13:30Z |  |
| Kustomization | flux-system | kyverno | Ready | main@fe21b57 | 2026-09-12T17:12:24Z |  |
| Kustomization | flux-system | llm | Ready | main@fe21b57 | 2026-09-12T17:14:56Z |  |
| Kustomization | flux-system | mcp | Ready | main@fe21b57 | 2026-09-12T17:14:36Z |  |
| Kustomization | flux-system | metrics-server | Ready | main@fe21b57 | 2026-09-12T17:14:12Z |  |
| Kustomization | flux-system | monitoring | Ready | main@fe21b57 | 2026-09-12T17:14:04Z |  |
| Kustomization | flux-system | monitoring-rules | Ready | main@fe21b57 | 2026-09-12T17:14:24Z |  |
| Kustomization | flux-system | nodesoftware-operator | Ready | main@fe21b57 | 2026-09-12T17:14:53Z |  |
| Kustomization | flux-system | notify | Ready | main@fe21b57 | 2026-09-12T17:14:01Z |  |
| Kustomization | flux-system | ns-fences | Ready | main@fe21b57 | 2026-09-12T17:12:33Z |  |
| Kustomization | flux-system | observability-collector | Ready | main@fe21b57 | 2026-09-12T17:13:28Z |  |
| Kustomization | flux-system | otto-gateway | Ready | main@fe21b57 | 2026-09-12T17:14:30Z |  |
| Kustomization | flux-system | otto-golden | Ready | main@fe21b57 | 2026-09-12T17:14:10Z |  |
| Kustomization | flux-system | otto-golden-secret | Ready | main@fe21b57 | 2026-09-12T17:13:53Z |  |
| Kustomization | flux-system | priority-classes | Ready | main@fe21b57 | 2026-09-12T17:12:16Z |  |
| Kustomization | flux-system | prospector | Ready | main@7453d76 | 2026-09-12T17:09:51Z |  |
| Kustomization | flux-system | prospector-platform | Ready | main@fe21b57 | 2026-09-12T17:13:57Z |  |
| Kustomization | flux-system | rbac | Ready | main@fe21b57 | 2026-09-12T17:12:48Z |  |
| Kustomization | flux-system | rbac-floor | Ready | main@fe21b57 | 2026-09-12T17:12:14Z |  |
| Kustomization | flux-system | rbac-identity | Ready | main@fe21b57 | 2026-09-12T17:12:23Z |  |
| Kustomization | flux-system | reloader | Ready | main@fe21b57 | 2026-09-12T17:13:59Z |  |
| Kustomization | flux-system | research-engine | Ready | main@fe21b57 | 2026-09-12T17:15:04Z |  |
| Kustomization | flux-system | robusta | Ready | main@fe21b57 | 2026-09-12T17:13:53Z |  |
| Kustomization | flux-system | sandbox-launch | Ready | main@fe21b57 | 2026-09-12T17:13:28Z |  |
| Kustomization | flux-system | sandbox-live | Ready | sandbox/launch@0086dc1 | 2026-09-12T17:14:37Z |  |
| Kustomization | flux-system | scheduling | Ready | main@fe21b57 | 2026-09-12T17:13:27Z |  |
| Kustomization | flux-system | searxng | Ready | main@fe21b57 | 2026-09-12T17:12:25Z |  |
| Kustomization | flux-system | secret-store | Ready | main@fe21b57 | 2026-09-12T17:13:43Z |  |
| Kustomization | flux-system | spire | Ready | main@fe21b57 | 2026-09-12T17:13:57Z |  |
| Kustomization | flux-system | staging | Ready | main@fe21b57 | 2026-09-12T17:12:17Z |  |
| Kustomization | flux-system | trivy | Ready | main@fe21b57 | 2026-09-12T17:12:14Z |  |
| Kustomization | flux-system | verification | Ready | main@fe21b57 | 2026-09-12T17:14:27Z |  |
| Kustomization | flux-system | weave-gitops | Ready | main@fe21b57 | 2026-09-12T17:14:54Z |  |
