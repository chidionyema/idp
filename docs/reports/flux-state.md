# Flux: what is applied

Read from the cluster receipt taken at 2026-09-14T20:45:17Z. Every Kustomization and HelmRelease, with the revision Flux last applied. **Suspended** is a switch somebody turned off on purpose (temporal, commerce, commerce-data, event-bus), not a defect; **Unknown** is a row Flux has never graded.

**116 objects: 109 ready, 5 not ready, 0 unknown, 2 suspended.**

## Not ready right now

- **HelmRelease commerce/lago** since 2026-09-14T20:30:32Z: Helm install failed for release commerce/lago with chart lago@1.28.0: failed early due to stalled resources: [Deployment/commerce/lago-billing-worker status: 'Failed']
- **Kustomization flux-system/cluster-state** since 2026-09-14T20:45:10Z: Reconciliation in progress
- **Kustomization flux-system/commerce** since 2026-09-14T20:33:26Z: Reconciliation in progress
- **Kustomization flux-system/mcp** since 2026-09-14T20:37:24Z: Reconciliation in progress
- **Kustomization flux-system/ns-fences** since 2026-09-14T20:44:55Z: Reconciliation in progress

## Every row

| Kind | Namespace | Name | State | Applied revision | Since | Message |
|---|---|---|---|---|---|---|
| HelmRelease | commerce | lago | Not ready | 1.28.0 | 2026-09-14T20:30:32Z | Helm install failed for release commerce/lago with chart lago@1.28.0: failed early due to stalled resources: [Deployment/commerce/lago-billing-worker status: 'F |
| Kustomization | flux-system | cluster-state | Not ready | main@dcd2a56 | 2026-09-14T20:45:10Z | Reconciliation in progress |
| Kustomization | flux-system | commerce | Not ready | main@abea14d | 2026-09-14T20:33:26Z | Reconciliation in progress |
| Kustomization | flux-system | mcp | Not ready | main@6558812 | 2026-09-14T20:37:24Z | Reconciliation in progress |
| Kustomization | flux-system | ns-fences | Not ready | main@dcd2a56 | 2026-09-14T20:44:55Z | Reconciliation in progress |
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
| HelmRelease | external-secrets | external-secrets | Ready | 2.9.0 | 2026-09-14T20:24:54Z |  |
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
| HelmRelease | observability | signoz | Ready | 0.138.0 | 2026-09-13T10:24:12Z |  |
| HelmRelease | observability | superset | Ready | 0.22.4 | 2026-09-06T19:46:05Z |  |
| HelmRelease | observability-agent | k8s-infra | Ready | 0.17.0 | 2026-09-14T18:09:18Z |  |
| HelmRelease | reloader | reloader | Ready | 2.2.16 | 2026-09-06T19:33:25Z |  |
| HelmRelease | robusta | robusta | Ready | 0.48.0 | 2026-09-06T20:26:45Z |  |
| HelmRelease | spire-mgmt | spire | Ready | 0.30.1 | 2026-09-08T09:39:33Z |  |
| HelmRelease | spire-mgmt | spire-crds | Ready | 0.6.1 | 2026-09-06T20:26:47Z |  |
| HelmRelease | tailscale | tailscale-operator | Ready | 1.102.3 | 2026-09-06T19:33:35Z |  |
| HelmRelease | temporal | temporal | Ready | 1.6.0 | 2026-09-08T23:12:29Z |  |
| HelmRelease | trivy-system | trivy-operator | Ready | 0.36.0 | 2026-09-06T20:26:45Z |  |
| HelmRelease | weave-gitops | weave-gitops | Ready | 4.0.36 | 2026-09-06T20:26:45Z |  |
| Kustomization | flux-system | agent-workforce | Ready | main@dcd2a56 | 2026-09-14T20:37:47Z |  |
| Kustomization | flux-system | alerts | Ready | main@dcd2a56 | 2026-09-14T20:37:30Z |  |
| Kustomization | flux-system | alerts-github | Ready | main@dcd2a56 | 2026-09-14T20:37:14Z |  |
| Kustomization | flux-system | alerts-secret | Ready | main@dcd2a56 | 2026-09-14T20:37:19Z |  |
| Kustomization | flux-system | autoscaler | Ready | main@dcd2a56 | 2026-09-14T20:37:15Z |  |
| Kustomization | flux-system | backstage | Ready | main@dcd2a56 | 2026-09-14T20:37:54Z |  |
| Kustomization | flux-system | backstage-namespace | Ready | main@913f72f | 2026-09-14T20:44:44Z |  |
| Kustomization | flux-system | calico | Ready | main@913f72f | 2026-09-14T20:44:45Z |  |
| Kustomization | flux-system | chaos | Ready | main@dcd2a56 | 2026-09-14T20:38:15Z |  |
| Kustomization | flux-system | chaos-mesh | Ready | main@913f72f | 2026-09-14T20:45:08Z |  |
| Kustomization | flux-system | commerce-data | Ready | main@dcd2a56 | 2026-09-14T20:37:49Z |  |
| Kustomization | flux-system | concierge | Ready | main@dcd2a56 | 2026-09-14T20:37:17Z |  |
| Kustomization | flux-system | cross-node-drill | Ready | main@913f72f | 2026-09-14T20:44:42Z |  |
| Kustomization | flux-system | crossplane | Ready | main@dcd2a56 | 2026-09-14T20:36:45Z |  |
| Kustomization | flux-system | crossplane-providerconfig | Ready | main@dcd2a56 | 2026-09-14T20:37:01Z |  |
| Kustomization | flux-system | crossplane-providers | Ready | main@dcd2a56 | 2026-09-14T20:36:55Z |  |
| Kustomization | flux-system | dagster | Ready | main@dcd2a56 | 2026-09-14T20:37:51Z |  |
| Kustomization | flux-system | dns | Ready | main@dcd2a56 | 2026-09-14T20:37:03Z |  |
| Kustomization | flux-system | drills | Ready | main@dcd2a56 | 2026-09-14T20:37:29Z |  |
| Kustomization | flux-system | edge | Ready | main@913f72f | 2026-09-14T20:45:00Z |  |
| Kustomization | flux-system | estate-catalog | Ready | latest@sha256:0236c7086c505c1fbe232cb327 | 2026-09-14T20:37:55Z |  |
| Kustomization | flux-system | estate-db | Ready | main@dcd2a56 | 2026-09-14T20:37:18Z |  |
| Kustomization | flux-system | estate-db-migrate | Ready | main@dcd2a56 | 2026-09-14T20:37:32Z |  |
| Kustomization | flux-system | estate-db-operator | Ready | main@913f72f | 2026-09-14T20:44:43Z |  |
| Kustomization | flux-system | event-bus | Ready | main@913f72f | 2026-09-14T20:44:46Z |  |
| Kustomization | flux-system | external-secrets | Ready | main@913f72f | 2026-09-14T20:45:07Z |  |
| Kustomization | flux-system | feature-register | Ready | main@913f72f | 2026-09-14T20:44:50Z |  |
| Kustomization | flux-system | flux-system | Ready | main@913f72f | 2026-09-14T20:44:55Z |  |
| Kustomization | flux-system | flux-webhook | Ready | main@dcd2a56 | 2026-09-14T20:36:59Z |  |
| Kustomization | flux-system | gateway-api-crds | Ready | v1.5.1@e7677b7 | 2026-09-14T20:44:47Z |  |
| Kustomization | flux-system | guacamole | Ready | main@dcd2a56 | 2026-09-14T20:37:46Z |  |
| Kustomization | flux-system | gvisor-runtime | Ready | main@dcd2a56 | 2026-09-14T20:37:46Z |  |
| Kustomization | flux-system | healing | Ready | main@dcd2a56 | 2026-09-14T20:36:43Z |  |
| Kustomization | flux-system | healing-analyzer | Ready | main@dcd2a56 | 2026-09-14T20:38:44Z |  |
| Kustomization | flux-system | healing-k8sgpt | Ready | main@dcd2a56 | 2026-09-14T20:38:14Z |  |
| Kustomization | flux-system | healthchecks | Ready | main@dcd2a56 | 2026-09-14T20:37:51Z |  |
| Kustomization | flux-system | hermes-agent | Ready | main@dcd2a56 | 2026-09-14T20:37:35Z |  |
| Kustomization | flux-system | hindsight | Ready | main@dcd2a56 | 2026-09-14T20:38:12Z |  |
| Kustomization | flux-system | human-vault | Ready | main@dcd2a56 | 2026-09-14T20:36:58Z |  |
| Kustomization | flux-system | human-vault-bridge | Ready | main@dcd2a56 | 2026-09-14T20:37:33Z |  |
| Kustomization | flux-system | identity | Ready | main@dcd2a56 | 2026-09-14T20:37:18Z |  |
| Kustomization | flux-system | image-automation | Ready | main@dcd2a56 | 2026-09-14T20:37:00Z |  |
| Kustomization | flux-system | jit | Ready | main@913f72f | 2026-09-14T20:45:03Z |  |
| Kustomization | flux-system | keda | Ready | main@dcd2a56 | 2026-09-14T20:36:43Z |  |
| Kustomization | flux-system | kyverno | Ready | main@913f72f | 2026-09-14T20:44:49Z |  |
| Kustomization | flux-system | llm | Ready | main@dcd2a56 | 2026-09-14T20:37:45Z |  |
| Kustomization | flux-system | metrics-server | Ready | main@dcd2a56 | 2026-09-14T20:36:46Z |  |
| Kustomization | flux-system | monitoring | Ready | main@dcd2a56 | 2026-09-14T20:37:00Z |  |
| Kustomization | flux-system | monitoring-rules | Ready | main@dcd2a56 | 2026-09-14T20:37:17Z |  |
| Kustomization | flux-system | nodesoftware-operator | Ready | main@dcd2a56 | 2026-09-14T20:37:16Z |  |
| Kustomization | flux-system | notify | Ready | main@dcd2a56 | 2026-09-14T20:37:02Z |  |
| Kustomization | flux-system | observability | Ready | main@dcd2a56 | 2026-09-14T20:37:56Z |  |
| Kustomization | flux-system | observability-collector | Ready | main@dcd2a56 | 2026-09-14T20:36:44Z |  |
| Kustomization | flux-system | otto-gateway | Ready | main@dcd2a56 | 2026-09-14T20:37:35Z |  |
| Kustomization | flux-system | otto-golden | Ready | main@dcd2a56 | 2026-09-14T20:37:03Z |  |
| Kustomization | flux-system | otto-golden-secret | Ready | main@dcd2a56 | 2026-09-14T20:36:57Z |  |
| Kustomization | flux-system | priority-classes | Ready | main@913f72f | 2026-09-14T20:44:41Z |  |
| Kustomization | flux-system | prospector | Ready | main@7453d76 | 2026-09-14T20:38:41Z |  |
| Kustomization | flux-system | prospector-platform | Ready | main@913f72f | 2026-09-14T20:45:10Z |  |
| Kustomization | flux-system | rbac | Ready | main@913f72f | 2026-09-14T20:44:56Z |  |
| Kustomization | flux-system | rbac-floor | Ready | main@913f72f | 2026-09-14T20:44:52Z |  |
| Kustomization | flux-system | rbac-identity | Ready | main@913f72f | 2026-09-14T20:44:47Z |  |
| Kustomization | flux-system | reloader | Ready | main@dcd2a56 | 2026-09-14T20:36:57Z |  |
| Kustomization | flux-system | research-engine | Ready | main@dcd2a56 | 2026-09-14T20:38:14Z |  |
| Kustomization | flux-system | robusta | Ready | main@dcd2a56 | 2026-09-14T20:37:16Z |  |
| Kustomization | flux-system | router-events | Ready | main@dcd2a56 | 2026-09-14T20:37:53Z |  |
| Kustomization | flux-system | sandbox-launch | Ready | main@913f72f | 2026-09-14T20:45:05Z |  |
| Kustomization | flux-system | sandbox-live | Ready | sandbox/launch@4830a6e | 2026-09-14T20:44:08Z |  |
| Kustomization | flux-system | scheduling | Ready | main@913f72f | 2026-09-14T20:45:06Z |  |
| Kustomization | flux-system | science | Ready | main@dcd2a56 | 2026-09-14T20:38:22Z |  |
| Kustomization | flux-system | searxng | Ready | main@913f72f | 2026-09-14T20:44:43Z |  |
| Kustomization | flux-system | secret-store | Ready | main@dcd2a56 | 2026-09-14T20:36:51Z |  |
| Kustomization | flux-system | spire | Ready | main@dcd2a56 | 2026-09-14T20:36:44Z |  |
| Kustomization | flux-system | staging | Ready | main@913f72f | 2026-09-14T20:44:55Z |  |
| Kustomization | flux-system | tailscale | Ready | main@dcd2a56 | 2026-09-14T20:36:55Z |  |
| Kustomization | flux-system | trivy | Ready | main@913f72f | 2026-09-14T20:44:48Z |  |
| Kustomization | flux-system | verification | Ready | main@dcd2a56 | 2026-09-14T20:37:18Z |  |
| Kustomization | flux-system | weave-gitops | Ready | main@dcd2a56 | 2026-09-14T20:37:49Z |  |
