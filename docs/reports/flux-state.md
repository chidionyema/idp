# Flux: what is applied

Read from the cluster receipt taken at 2026-09-16T04:00:25Z. Every Kustomization and HelmRelease, with the revision Flux last applied. **Suspended** is a switch somebody turned off on purpose (temporal, commerce, commerce-data, event-bus), not a defect; **Unknown** is a row Flux has never graded.

**119 objects: 96 ready, 22 not ready, 0 unknown, 1 suspended.**

## Not ready right now

- **HelmRelease commerce/lago** since 2026-09-16T01:49:09Z: Helm install failed for release commerce/lago with chart lago@1.28.0: failed early due to stalled resources: [Deployment/commerce/lago-clock-worker status: 'Failed']
- **Kustomization flux-system/agent-workforce** since 2026-09-16T03:53:50Z: dependency 'flux-system/alerts-github' is not ready
- **Kustomization flux-system/alerts-github** since 2026-09-16T03:51:45Z: ExternalSecret/flux-system/github-app dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-secrets.io": failed to call webhook: Post "https://external-secrets-webhook.external-secrets.svc:443/validate-external-secrets-io-v1-externalsecret?timeout=15s": context deadline exceeded 
- **Kustomization flux-system/backstage** since 2026-09-16T03:56:51Z: dependency 'flux-system/estate-db-migrate' is not ready
- **Kustomization flux-system/chaos** since 2026-09-16T03:53:47Z: dependency 'flux-system/observability' is not ready
- **Kustomization flux-system/commerce** since 2026-09-16T03:59:25Z: dependency 'flux-system/commerce-data' is not ready
- **Kustomization flux-system/crossplane-storage-capability** since 2026-09-16T03:50:45Z: Composition/xobjectstoragebuckets.storage.estate.io dry-run failed: failed to create typed patch object (/xobjectstoragebuckets.storage.estate.io; apiextensions.crossplane.io/v1, Kind=Composition): .spec.resources: field not declared in schema 
- **Kustomization flux-system/dagster** since 2026-09-16T03:53:24Z: dependency 'flux-system/estate-db-migrate' is not ready
- **Kustomization flux-system/drills** since 2026-09-16T03:52:00Z: dependency 'flux-system/alerts-github' is not ready
- **Kustomization flux-system/epistemic-fabric** since 2026-09-16T03:50:49Z: health check failed after 48.739133ms: failed early due to stalled resources: [Deployment/epistemic-fabric/epistemic-ingest-github status: 'Failed']
- **Kustomization flux-system/guacamole** since 2026-09-16T03:52:50Z: dependency 'flux-system/estate-db-migrate' is not ready
- **Kustomization flux-system/healthchecks** since 2026-09-16T04:00:19Z: Reconciliation in progress
- **Kustomization flux-system/hermes-agent** since 2026-09-16T03:53:03Z: dependency 'flux-system/alerts-github' is not ready
- **Kustomization flux-system/hindsight** since 2026-09-16T03:53:18Z: dependency 'flux-system/llm' is not ready
- **Kustomization flux-system/image-automation** since 2026-09-16T04:00:09Z: Reconciliation in progress
- **Kustomization flux-system/mcp** since 2026-09-16T03:52:57Z: dependency 'flux-system/alerts-github' is not ready
- **Kustomization flux-system/observability** since 2026-09-16T03:52:54Z: dependency 'flux-system/estate-db-migrate' is not ready
- **Kustomization flux-system/otto-gateway** since 2026-09-16T03:53:05Z: dependency 'flux-system/alerts-github' is not ready
- **Kustomization flux-system/research-engine** since 2026-09-16T03:53:17Z: dependency 'flux-system/llm' is not ready
- **Kustomization flux-system/router-events** since 2026-09-16T03:53:40Z: dependency 'flux-system/llm' is not ready
- **Kustomization flux-system/tailscale** since 2026-09-16T04:00:12Z: Reconciliation in progress
- **Kustomization flux-system/via-negativa** since 2026-09-16T03:53:30Z: dependency 'flux-system/llm' is not ready

## Every row

| Kind | Namespace | Name | State | Applied revision | Since | Message |
|---|---|---|---|---|---|---|
| HelmRelease | commerce | lago | Not ready | 1.28.0 | 2026-09-16T01:49:09Z | Helm install failed for release commerce/lago with chart lago@1.28.0: failed early due to stalled resources: [Deployment/commerce/lago-clock-worker status: 'Fai |
| Kustomization | flux-system | agent-workforce | Not ready | main@26584de | 2026-09-16T03:53:50Z | dependency 'flux-system/alerts-github' is not ready |
| Kustomization | flux-system | alerts-github | Not ready | main@26584de | 2026-09-16T03:51:45Z | ExternalSecret/flux-system/github-app dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-secrets. |
| Kustomization | flux-system | backstage | Not ready | main@26584de | 2026-09-16T03:56:51Z | dependency 'flux-system/estate-db-migrate' is not ready |
| Kustomization | flux-system | chaos | Not ready | main@26584de | 2026-09-16T03:53:47Z | dependency 'flux-system/observability' is not ready |
| Kustomization | flux-system | commerce | Not ready | main@abea14d | 2026-09-16T03:59:25Z | dependency 'flux-system/commerce-data' is not ready |
| Kustomization | flux-system | crossplane-storage-capability | Not ready | main@26584de | 2026-09-16T03:50:45Z | Composition/xobjectstoragebuckets.storage.estate.io dry-run failed: failed to create typed patch object (/xobjectstoragebuckets.storage.estate.io; apiextensions |
| Kustomization | flux-system | dagster | Not ready | main@26584de | 2026-09-16T03:53:24Z | dependency 'flux-system/estate-db-migrate' is not ready |
| Kustomization | flux-system | drills | Not ready | main@26584de | 2026-09-16T03:52:00Z | dependency 'flux-system/alerts-github' is not ready |
| Kustomization | flux-system | epistemic-fabric | Not ready | main@26584de | 2026-09-16T03:50:49Z | health check failed after 48.739133ms: failed early due to stalled resources: [Deployment/epistemic-fabric/epistemic-ingest-github status: 'Failed'] |
| Kustomization | flux-system | guacamole | Not ready | main@26584de | 2026-09-16T03:52:50Z | dependency 'flux-system/estate-db-migrate' is not ready |
| Kustomization | flux-system | healthchecks | Not ready | main@26584de | 2026-09-16T04:00:19Z | Reconciliation in progress |
| Kustomization | flux-system | hermes-agent | Not ready | main@26584de | 2026-09-16T03:53:03Z | dependency 'flux-system/alerts-github' is not ready |
| Kustomization | flux-system | hindsight | Not ready | main@26584de | 2026-09-16T03:53:18Z | dependency 'flux-system/llm' is not ready |
| Kustomization | flux-system | image-automation | Not ready | main@26584de | 2026-09-16T04:00:09Z | Reconciliation in progress |
| Kustomization | flux-system | mcp | Not ready | main@26584de | 2026-09-16T03:52:57Z | dependency 'flux-system/alerts-github' is not ready |
| Kustomization | flux-system | observability | Not ready | main@26584de | 2026-09-16T03:52:54Z | dependency 'flux-system/estate-db-migrate' is not ready |
| Kustomization | flux-system | otto-gateway | Not ready | main@26584de | 2026-09-16T03:53:05Z | dependency 'flux-system/alerts-github' is not ready |
| Kustomization | flux-system | research-engine | Not ready | main@26584de | 2026-09-16T03:53:17Z | dependency 'flux-system/llm' is not ready |
| Kustomization | flux-system | router-events | Not ready | main@26584de | 2026-09-16T03:53:40Z | dependency 'flux-system/llm' is not ready |
| Kustomization | flux-system | tailscale | Not ready | main@26584de | 2026-09-16T04:00:12Z | Reconciliation in progress |
| Kustomization | flux-system | via-negativa | Not ready | main@26584de | 2026-09-16T03:53:30Z | dependency 'flux-system/llm' is not ready |
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
| Kustomization | flux-system | alerts | Ready | main@26584de | 2026-09-16T03:58:52Z |  |
| Kustomization | flux-system | alerts-secret | Ready | main@26584de | 2026-09-16T03:59:35Z |  |
| Kustomization | flux-system | autoscaler | Ready | main@26584de | 2026-09-16T03:59:42Z |  |
| Kustomization | flux-system | backstage-namespace | Ready | main@26584de | 2026-09-16T03:53:07Z |  |
| Kustomization | flux-system | calico | Ready | main@26584de | 2026-09-16T03:56:28Z |  |
| Kustomization | flux-system | chaos-mesh | Ready | main@26584de | 2026-09-16T03:52:48Z |  |
| Kustomization | flux-system | cluster-state | Ready | main@26584de | 2026-09-16T03:52:58Z |  |
| Kustomization | flux-system | commerce-data | Ready | main@26584de | 2026-09-16T03:59:56Z |  |
| Kustomization | flux-system | concierge | Ready | main@26584de | 2026-09-16T03:50:57Z |  |
| Kustomization | flux-system | cross-node-drill | Ready | main@26584de | 2026-09-16T03:58:22Z |  |
| Kustomization | flux-system | crossplane | Ready | main@26584de | 2026-09-16T03:52:48Z |  |
| Kustomization | flux-system | crossplane-providerconfig | Ready | main@26584de | 2026-09-16T03:58:48Z |  |
| Kustomization | flux-system | crossplane-providers | Ready | main@26584de | 2026-09-16T03:53:23Z |  |
| Kustomization | flux-system | dns | Ready | main@26584de | 2026-09-16T03:49:56Z |  |
| Kustomization | flux-system | edge | Ready | main@26584de | 2026-09-16T03:56:21Z |  |
| Kustomization | flux-system | estate-catalog | Ready | latest@sha256:9a2b736d2455d3f2f1fea33be6 | 2026-09-16T03:58:18Z |  |
| Kustomization | flux-system | estate-db | Ready | main@26584de | 2026-09-16T03:59:28Z |  |
| Kustomization | flux-system | estate-db-migrate | Ready | main@26584de | 2026-09-16T04:00:11Z |  |
| Kustomization | flux-system | estate-db-operator | Ready | main@26584de | 2026-09-16T03:52:38Z |  |
| Kustomization | flux-system | event-bus | Ready | main@26584de | 2026-09-16T03:57:04Z |  |
| Kustomization | flux-system | external-secrets | Ready | main@26584de | 2026-09-16T03:55:12Z |  |
| Kustomization | flux-system | feature-register | Ready | main@26584de | 2026-09-16T03:53:58Z |  |
| Kustomization | flux-system | flux-system | Ready | main@26584de | 2026-09-16T03:54:02Z |  |
| Kustomization | flux-system | flux-webhook | Ready | main@26584de | 2026-09-16T03:53:59Z |  |
| Kustomization | flux-system | gateway-api-crds | Ready | v1.5.1@e7677b7 | 2026-09-16T03:57:17Z |  |
| Kustomization | flux-system | gvisor-runtime | Ready | main@26584de | 2026-09-16T03:53:49Z |  |
| Kustomization | flux-system | healing | Ready | main@26584de | 2026-09-16T03:53:05Z |  |
| Kustomization | flux-system | healing-analyzer | Ready | main@26584de | 2026-09-16T03:53:51Z |  |
| Kustomization | flux-system | healing-k8sgpt | Ready | main@26584de | 2026-09-16T03:52:54Z |  |
| Kustomization | flux-system | human-vault | Ready | main@26584de | 2026-09-16T03:52:05Z |  |
| Kustomization | flux-system | human-vault-bridge | Ready | main@26584de | 2026-09-16T03:52:17Z |  |
| Kustomization | flux-system | identity | Ready | main@26584de | 2026-09-16T03:50:45Z |  |
| Kustomization | flux-system | jit | Ready | main@26584de | 2026-09-16T03:55:25Z |  |
| Kustomization | flux-system | keda | Ready | main@26584de | 2026-09-16T03:53:39Z |  |
| Kustomization | flux-system | kyverno | Ready | main@26584de | 2026-09-16T03:54:15Z |  |
| Kustomization | flux-system | llm | Ready | main@26584de | 2026-09-16T04:00:18Z |  |
| Kustomization | flux-system | metrics-server | Ready | main@26584de | 2026-09-16T03:52:18Z |  |
| Kustomization | flux-system | monitoring | Ready | main@26584de | 2026-09-16T03:59:09Z |  |
| Kustomization | flux-system | monitoring-rules | Ready | main@26584de | 2026-09-16T03:55:31Z |  |
| Kustomization | flux-system | nodesoftware-operator | Ready | main@26584de | 2026-09-16T03:53:10Z |  |
| Kustomization | flux-system | notify | Ready | main@26584de | 2026-09-16T03:53:23Z |  |
| Kustomization | flux-system | ns-fences | Ready | main@26584de | 2026-09-16T03:55:52Z |  |
| Kustomization | flux-system | observability-collector | Ready | main@26584de | 2026-09-16T03:53:00Z |  |
| Kustomization | flux-system | otto-golden | Ready | main@26584de | 2026-09-16T03:53:15Z |  |
| Kustomization | flux-system | otto-golden-secret | Ready | main@26584de | 2026-09-16T03:54:55Z |  |
| Kustomization | flux-system | priority-classes | Ready | main@26584de | 2026-09-16T03:52:31Z |  |
| Kustomization | flux-system | prospector | Ready | main@7453d76 | 2026-09-16T03:59:24Z |  |
| Kustomization | flux-system | prospector-platform | Ready | main@26584de | 2026-09-16T03:55:06Z |  |
| Kustomization | flux-system | rbac | Ready | main@26584de | 2026-09-16T03:59:10Z |  |
| Kustomization | flux-system | rbac-floor | Ready | main@26584de | 2026-09-16T03:56:17Z |  |
| Kustomization | flux-system | rbac-identity | Ready | main@26584de | 2026-09-16T04:00:13Z |  |
| Kustomization | flux-system | reloader | Ready | main@26584de | 2026-09-16T03:57:54Z |  |
| Kustomization | flux-system | robusta | Ready | main@26584de | 2026-09-16T03:50:51Z |  |
| Kustomization | flux-system | sandbox-launch | Ready | main@26584de | 2026-09-16T03:57:22Z |  |
| Kustomization | flux-system | sandbox-live | Ready | sandbox/launch@4830a6e | 2026-09-16T03:59:54Z |  |
| Kustomization | flux-system | scheduling | Ready | main@26584de | 2026-09-16T03:52:43Z |  |
| Kustomization | flux-system | science | Ready | main@26584de | 2026-09-16T03:52:19Z |  |
| Kustomization | flux-system | searxng | Ready | main@26584de | 2026-09-16T03:54:06Z |  |
| Kustomization | flux-system | secret-store | Ready | main@26584de | 2026-09-16T03:58:20Z |  |
| Kustomization | flux-system | spire | Ready | main@26584de | 2026-09-16T03:53:12Z |  |
| Kustomization | flux-system | staging | Ready | main@26584de | 2026-09-16T03:54:11Z |  |
| Kustomization | flux-system | temporal | Ready | main@26584de | 2026-09-16T03:51:23Z |  |
| Kustomization | flux-system | trivy | Ready | main@26584de | 2026-09-16T03:52:52Z |  |
| Kustomization | flux-system | verification | Ready | main@26584de | 2026-09-16T03:50:28Z |  |
| Kustomization | flux-system | weave-gitops | Ready | main@26584de | 2026-09-16T03:59:36Z |  |
