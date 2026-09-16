# Flux: what is applied

Read from the cluster receipt taken at 2026-09-16T07:00:18Z. Every Kustomization and HelmRelease, with the revision Flux last applied. **Suspended** is a switch somebody turned off on purpose (temporal, commerce, commerce-data, event-bus), not a defect; **Unknown** is a row Flux has never graded.

**119 objects: 112 ready, 6 not ready, 0 unknown, 1 suspended.**

## Not ready right now

- **HelmRelease commerce/lago** since 2026-09-16T06:59:21Z: Helm install failed for release commerce/lago with chart lago@1.28.0: create: failed to create: admission webhook "oke-resource-leak-protection.oke.com" denied the request: OKE resource leak protection rejected the request. Cluster has 2650 secrets and the limit is 2000. See https://docs.oracle.com/iaas/Content/ContEng/Tasks/contengprotectingclustersfromresourceleaks.htm for details.
- **Kustomization flux-system/commerce** since 2026-09-16T06:59:15Z: Reconciliation in progress
- **Kustomization flux-system/crossplane-storage-capability** since 2026-09-16T06:55:47Z: Composition/xobjectstoragebuckets.storage.estate.io dry-run failed: failed to create typed patch object (/xobjectstoragebuckets.storage.estate.io; apiextensions.crossplane.io/v1, Kind=Composition): .spec.resources: field not declared in schema 
- **Kustomization flux-system/epistemic-fabric** since 2026-09-16T06:55:28Z: health check failed after 59.049246ms: failed early due to stalled resources: [Deployment/epistemic-fabric/epistemic-ingest-github status: 'Failed']
- **Kustomization flux-system/sandbox-live** since 2026-09-16T07:00:11Z: Reconciliation in progress
- **Kustomization flux-system/via-negativa** since 2026-09-16T06:56:09Z: health check failed after 284.671275ms: failed early due to stalled resources: [Deployment/via-negativa/via-negativa-rca status: 'Failed']

## Every row

| Kind | Namespace | Name | State | Applied revision | Since | Message |
|---|---|---|---|---|---|---|
| HelmRelease | commerce | lago | Not ready | 1.28.0 | 2026-09-16T06:59:21Z | Helm install failed for release commerce/lago with chart lago@1.28.0: create: failed to create: admission webhook "oke-resource-leak-protection.oke.com" denied  |
| Kustomization | flux-system | commerce | Not ready | main@abea14d | 2026-09-16T06:59:15Z | Reconciliation in progress |
| Kustomization | flux-system | crossplane-storage-capability | Not ready | main@f610e0b | 2026-09-16T06:55:47Z | Composition/xobjectstoragebuckets.storage.estate.io dry-run failed: failed to create typed patch object (/xobjectstoragebuckets.storage.estate.io; apiextensions |
| Kustomization | flux-system | epistemic-fabric | Not ready | main@f610e0b | 2026-09-16T06:55:28Z | health check failed after 59.049246ms: failed early due to stalled resources: [Deployment/epistemic-fabric/epistemic-ingest-github status: 'Failed'] |
| Kustomization | flux-system | sandbox-live | Not ready | sandbox/launch@4830a6e | 2026-09-16T07:00:11Z | Reconciliation in progress |
| Kustomization | flux-system | via-negativa | Not ready | main@f610e0b | 2026-09-16T06:56:09Z | health check failed after 284.671275ms: failed early due to stalled resources: [Deployment/via-negativa/via-negativa-rca status: 'Failed'] |
| HelmRelease | tigera-operator | tigera-operator | Suspended | v3.32.2 | 2026-09-06T19:38:02Z |  |
| HelmRelease | cert-manager | cert-manager | Ready | v1.21.1 | 2026-09-08T11:56:22Z |  |
| HelmRelease | chaos-mesh | chaos-mesh | Ready | 2.8.4 | 2026-09-15T14:48:03Z |  |
| HelmRelease | crossplane-system | crossplane | Ready | 2.4.0 | 2026-09-15T23:39:40Z |  |
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
| HelmRelease | temporal | temporal | Ready | 1.6.0 | 2026-09-15T14:03:10Z |  |
| HelmRelease | trivy-system | trivy-operator | Ready | 0.36.0 | 2026-09-06T20:26:45Z |  |
| HelmRelease | weave-gitops | weave-gitops | Ready | 4.0.36 | 2026-09-06T20:26:45Z |  |
| Kustomization | flux-system | agent-workforce | Ready | main@f610e0b | 2026-09-16T06:56:03Z |  |
| Kustomization | flux-system | alerts | Ready | main@f610e0b | 2026-09-16T06:54:54Z |  |
| Kustomization | flux-system | alerts-github | Ready | main@f610e0b | 2026-09-16T06:54:46Z |  |
| Kustomization | flux-system | alerts-secret | Ready | main@f610e0b | 2026-09-16T06:54:51Z |  |
| Kustomization | flux-system | autoscaler | Ready | main@f610e0b | 2026-09-16T06:54:48Z |  |
| Kustomization | flux-system | backstage | Ready | main@f610e0b | 2026-09-16T06:56:02Z |  |
| Kustomization | flux-system | backstage-namespace | Ready | main@f610e0b | 2026-09-16T06:54:13Z |  |
| Kustomization | flux-system | calico | Ready | main@f610e0b | 2026-09-16T06:54:22Z |  |
| Kustomization | flux-system | chaos | Ready | main@f610e0b | 2026-09-16T06:56:06Z |  |
| Kustomization | flux-system | chaos-mesh | Ready | main@f610e0b | 2026-09-16T06:55:16Z |  |
| Kustomization | flux-system | cluster-state | Ready | main@f610e0b | 2026-09-16T06:55:22Z |  |
| Kustomization | flux-system | commerce-data | Ready | main@f610e0b | 2026-09-16T06:55:42Z |  |
| Kustomization | flux-system | concierge | Ready | main@f610e0b | 2026-09-16T06:54:44Z |  |
| Kustomization | flux-system | cross-node-drill | Ready | main@f610e0b | 2026-09-16T06:54:26Z |  |
| Kustomization | flux-system | crossplane | Ready | main@f610e0b | 2026-09-16T06:55:12Z |  |
| Kustomization | flux-system | crossplane-providerconfig | Ready | main@f610e0b | 2026-09-16T06:55:45Z |  |
| Kustomization | flux-system | crossplane-providers | Ready | main@f610e0b | 2026-09-16T06:55:36Z |  |
| Kustomization | flux-system | dagster | Ready | main@f610e0b | 2026-09-16T06:55:51Z |  |
| Kustomization | flux-system | dns | Ready | main@f610e0b | 2026-09-16T06:55:00Z |  |
| Kustomization | flux-system | drills | Ready | main@f610e0b | 2026-09-16T06:54:49Z |  |
| Kustomization | flux-system | edge | Ready | main@f610e0b | 2026-09-16T06:54:35Z |  |
| Kustomization | flux-system | estate-catalog | Ready | latest@sha256:9a2b736d2455d3f2f1fea33be6 | 2026-09-16T06:59:39Z |  |
| Kustomization | flux-system | estate-db | Ready | main@f610e0b | 2026-09-16T06:55:02Z |  |
| Kustomization | flux-system | estate-db-migrate | Ready | main@f610e0b | 2026-09-16T06:55:10Z |  |
| Kustomization | flux-system | estate-db-operator | Ready | main@f610e0b | 2026-09-16T06:54:21Z |  |
| Kustomization | flux-system | event-bus | Ready | main@f610e0b | 2026-09-16T06:54:20Z |  |
| Kustomization | flux-system | external-secrets | Ready | main@f610e0b | 2026-09-16T06:54:36Z |  |
| Kustomization | flux-system | feature-register | Ready | main@f610e0b | 2026-09-16T06:54:18Z |  |
| Kustomization | flux-system | flux-system | Ready | main@f610e0b | 2026-09-16T06:54:23Z |  |
| Kustomization | flux-system | flux-webhook | Ready | main@f610e0b | 2026-09-16T06:54:51Z |  |
| Kustomization | flux-system | gateway-api-crds | Ready | v1.5.1@e7677b7 | 2026-09-16T06:54:29Z |  |
| Kustomization | flux-system | guacamole | Ready | main@f610e0b | 2026-09-16T06:55:55Z |  |
| Kustomization | flux-system | gvisor-runtime | Ready | main@f610e0b | 2026-09-16T06:55:46Z |  |
| Kustomization | flux-system | healing | Ready | main@f610e0b | 2026-09-16T06:55:16Z |  |
| Kustomization | flux-system | healing-analyzer | Ready | main@f610e0b | 2026-09-16T06:56:38Z |  |
| Kustomization | flux-system | healing-k8sgpt | Ready | main@f610e0b | 2026-09-16T06:56:10Z |  |
| Kustomization | flux-system | healthchecks | Ready | main@f610e0b | 2026-09-16T06:55:50Z |  |
| Kustomization | flux-system | hermes-agent | Ready | main@f610e0b | 2026-09-16T06:58:03Z |  |
| Kustomization | flux-system | hindsight | Ready | main@f610e0b | 2026-09-16T06:55:54Z |  |
| Kustomization | flux-system | human-vault | Ready | main@f610e0b | 2026-09-16T06:54:45Z |  |
| Kustomization | flux-system | human-vault-bridge | Ready | main@f610e0b | 2026-09-16T06:54:57Z |  |
| Kustomization | flux-system | identity | Ready | main@f610e0b | 2026-09-16T06:54:47Z |  |
| Kustomization | flux-system | image-automation | Ready | main@f610e0b | 2026-09-16T06:54:41Z |  |
| Kustomization | flux-system | jit | Ready | main@f610e0b | 2026-09-16T06:55:07Z |  |
| Kustomization | flux-system | keda | Ready | main@f610e0b | 2026-09-16T06:55:20Z |  |
| Kustomization | flux-system | kyverno | Ready | main@f610e0b | 2026-09-16T06:54:25Z |  |
| Kustomization | flux-system | llm | Ready | main@f610e0b | 2026-09-16T06:55:49Z |  |
| Kustomization | flux-system | mcp | Ready | main@f610e0b | 2026-09-16T06:55:35Z |  |
| Kustomization | flux-system | metrics-server | Ready | main@f610e0b | 2026-09-16T06:55:12Z |  |
| Kustomization | flux-system | monitoring | Ready | main@f610e0b | 2026-09-16T06:54:50Z |  |
| Kustomization | flux-system | monitoring-rules | Ready | main@f610e0b | 2026-09-16T06:55:03Z |  |
| Kustomization | flux-system | nodesoftware-operator | Ready | main@f610e0b | 2026-09-16T06:55:43Z |  |
| Kustomization | flux-system | notify | Ready | main@f610e0b | 2026-09-16T06:55:19Z |  |
| Kustomization | flux-system | ns-fences | Ready | main@f610e0b | 2026-09-16T06:54:44Z |  |
| Kustomization | flux-system | observability | Ready | main@f610e0b | 2026-09-16T06:56:00Z |  |
| Kustomization | flux-system | observability-collector | Ready | main@f610e0b | 2026-09-16T06:55:14Z |  |
| Kustomization | flux-system | otto-gateway | Ready | main@f610e0b | 2026-09-16T06:55:47Z |  |
| Kustomization | flux-system | otto-golden | Ready | main@f610e0b | 2026-09-16T06:55:24Z |  |
| Kustomization | flux-system | otto-golden-secret | Ready | main@f610e0b | 2026-09-16T06:54:42Z |  |
| Kustomization | flux-system | priority-classes | Ready | main@f610e0b | 2026-09-16T06:54:15Z |  |
| Kustomization | flux-system | prospector | Ready | main@7453d76 | 2026-09-16T06:54:12Z |  |
| Kustomization | flux-system | prospector-platform | Ready | main@f610e0b | 2026-09-16T06:54:56Z |  |
| Kustomization | flux-system | rbac | Ready | main@f610e0b | 2026-09-16T06:54:30Z |  |
| Kustomization | flux-system | rbac-floor | Ready | main@f610e0b | 2026-09-16T06:54:18Z |  |
| Kustomization | flux-system | rbac-identity | Ready | main@f610e0b | 2026-09-16T06:54:17Z |  |
| Kustomization | flux-system | reloader | Ready | main@f610e0b | 2026-09-16T06:54:49Z |  |
| Kustomization | flux-system | research-engine | Ready | main@f610e0b | 2026-09-16T06:55:57Z |  |
| Kustomization | flux-system | robusta | Ready | main@f610e0b | 2026-09-16T06:54:53Z |  |
| Kustomization | flux-system | router-events | Ready | main@f610e0b | 2026-09-16T06:56:07Z |  |
| Kustomization | flux-system | sandbox-launch | Ready | main@f610e0b | 2026-09-16T06:54:38Z |  |
| Kustomization | flux-system | scheduling | Ready | main@f610e0b | 2026-09-16T06:55:09Z |  |
| Kustomization | flux-system | science | Ready | main@f610e0b | 2026-09-16T06:56:05Z |  |
| Kustomization | flux-system | searxng | Ready | main@f610e0b | 2026-09-16T06:54:27Z |  |
| Kustomization | flux-system | secret-store | Ready | main@f610e0b | 2026-09-16T06:54:39Z |  |
| Kustomization | flux-system | spire | Ready | main@f610e0b | 2026-09-16T06:55:14Z |  |
| Kustomization | flux-system | staging | Ready | main@f610e0b | 2026-09-16T06:54:16Z |  |
| Kustomization | flux-system | tailscale | Ready | main@f610e0b | 2026-09-16T06:54:55Z |  |
| Kustomization | flux-system | temporal | Ready | main@f610e0b | 2026-09-16T06:55:53Z |  |
| Kustomization | flux-system | trivy | Ready | main@f610e0b | 2026-09-16T06:54:24Z |  |
| Kustomization | flux-system | verification | Ready | main@f610e0b | 2026-09-16T06:54:45Z |  |
| Kustomization | flux-system | weave-gitops | Ready | main@f610e0b | 2026-09-16T06:54:58Z |  |
