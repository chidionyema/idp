# Flux: what is applied

Read from the cluster receipt taken at 2026-09-16T04:30:50Z. Every Kustomization and HelmRelease, with the revision Flux last applied. **Suspended** is a switch somebody turned off on purpose (temporal, commerce, commerce-data, event-bus), not a defect; **Unknown** is a row Flux has never graded.

**119 objects: 95 ready, 23 not ready, 0 unknown, 1 suspended.**

## Not ready right now

- **HelmRelease commerce/lago** since 2026-09-16T01:49:09Z: Helm install failed for release commerce/lago with chart lago@1.28.0: failed early due to stalled resources: [Deployment/commerce/lago-clock-worker status: 'Failed']
- **Kustomization flux-system/agent-workforce** since 2026-09-16T04:22:54Z: dependency 'flux-system/llm' is not ready
- **Kustomization flux-system/backstage** since 2026-09-16T04:23:20Z: dependency 'flux-system/estate-db-migrate' is not ready
- **Kustomization flux-system/chaos** since 2026-09-16T04:22:29Z: dependency 'flux-system/observability' is not ready
- **Kustomization flux-system/commerce** since 2026-09-16T04:21:16Z: health check failed after 31.896309ms: failed early due to stalled resources: [HelmRelease/commerce/lago status: 'Failed']
- **Kustomization flux-system/crossplane-storage-capability** since 2026-09-16T04:20:49Z: Composition/xobjectstoragebuckets.storage.estate.io dry-run failed: failed to create typed patch object (/xobjectstoragebuckets.storage.estate.io; apiextensions.crossplane.io/v1, Kind=Composition): .spec.resources: field not declared in schema 
- **Kustomization flux-system/dagster** since 2026-09-16T04:30:09Z: dependency 'flux-system/estate-db-migrate' is not ready
- **Kustomization flux-system/epistemic-fabric** since 2026-09-16T04:22:25Z: health check failed after 235.816297ms: failed early due to stalled resources: [Deployment/epistemic-fabric/epistemic-ingest-github status: 'Failed']
- **Kustomization flux-system/estate-db-migrate** since 2026-09-16T04:21:00Z: ExternalSecret/backstage/estate-db-role-backstage dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-secrets.io": failed to call webhook: Post "https://external-secrets-webhook.external-secrets.svc:443/validate-external-secrets-io-v1-externalsecret?timeout=15s": context deadline exceeded 
- **Kustomization flux-system/guacamole** since 2026-09-16T04:20:53Z: dependency 'flux-system/estate-db-migrate' is not ready
- **Kustomization flux-system/gvisor-runtime** since 2026-09-16T04:03:29Z: dependency 'flux-system/nodesoftware-operator' is not ready
- **Kustomization flux-system/healing-analyzer** since 2026-09-16T04:24:02Z: dependency 'flux-system/healing-k8sgpt' is not ready
- **Kustomization flux-system/healing-k8sgpt** since 2026-09-16T04:22:57Z: dependency 'flux-system/llm' is not ready
- **Kustomization flux-system/healthchecks** since 2026-09-16T04:29:34Z: dependency 'flux-system/estate-db-migrate' is not ready
- **Kustomization flux-system/hindsight** since 2026-09-16T04:21:32Z: dependency 'flux-system/llm' is not ready
- **Kustomization flux-system/image-automation** since 2026-09-16T04:21:01Z: ClusterSecretStore/ghcr-pull dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.clustersecretstore.external-secrets.io": failed to call webhook: Post "https://external-secrets-webhook.external-secrets.svc:443/validate-external-secrets-io-v1-clustersecretstore?timeout=15s": context deadline exceeded 
- **Kustomization flux-system/llm** since 2026-09-16T04:20:58Z: dependency 'flux-system/estate-db-migrate' is not ready
- **Kustomization flux-system/nodesoftware-operator** since 2026-09-16T04:02:52Z: dependency 'flux-system/image-automation' is not ready
- **Kustomization flux-system/observability** since 2026-09-16T04:20:52Z: dependency 'flux-system/estate-db-migrate' is not ready
- **Kustomization flux-system/research-engine** since 2026-09-16T04:29:07Z: dependency 'flux-system/llm' is not ready
- **Kustomization flux-system/science** since 2026-09-16T04:22:25Z: dependency 'flux-system/observability' is not ready
- **Kustomization flux-system/temporal** since 2026-09-16T04:01:18Z: dependency 'flux-system/image-automation' is not ready
- **Kustomization flux-system/via-negativa** since 2026-09-16T04:21:20Z: dependency 'flux-system/llm' is not ready

## Every row

| Kind | Namespace | Name | State | Applied revision | Since | Message |
|---|---|---|---|---|---|---|
| HelmRelease | commerce | lago | Not ready | 1.28.0 | 2026-09-16T01:49:09Z | Helm install failed for release commerce/lago with chart lago@1.28.0: failed early due to stalled resources: [Deployment/commerce/lago-clock-worker status: 'Fai |
| Kustomization | flux-system | agent-workforce | Not ready | main@26584de | 2026-09-16T04:22:54Z | dependency 'flux-system/llm' is not ready |
| Kustomization | flux-system | backstage | Not ready | main@26584de | 2026-09-16T04:23:20Z | dependency 'flux-system/estate-db-migrate' is not ready |
| Kustomization | flux-system | chaos | Not ready | main@26584de | 2026-09-16T04:22:29Z | dependency 'flux-system/observability' is not ready |
| Kustomization | flux-system | commerce | Not ready | main@abea14d | 2026-09-16T04:21:16Z | health check failed after 31.896309ms: failed early due to stalled resources: [HelmRelease/commerce/lago status: 'Failed'] |
| Kustomization | flux-system | crossplane-storage-capability | Not ready | main@26584de | 2026-09-16T04:20:49Z | Composition/xobjectstoragebuckets.storage.estate.io dry-run failed: failed to create typed patch object (/xobjectstoragebuckets.storage.estate.io; apiextensions |
| Kustomization | flux-system | dagster | Not ready | main@26584de | 2026-09-16T04:30:09Z | dependency 'flux-system/estate-db-migrate' is not ready |
| Kustomization | flux-system | epistemic-fabric | Not ready | main@26584de | 2026-09-16T04:22:25Z | health check failed after 235.816297ms: failed early due to stalled resources: [Deployment/epistemic-fabric/epistemic-ingest-github status: 'Failed'] |
| Kustomization | flux-system | estate-db-migrate | Not ready | main@26584de | 2026-09-16T04:21:00Z | ExternalSecret/backstage/estate-db-role-backstage dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.exter |
| Kustomization | flux-system | guacamole | Not ready | main@26584de | 2026-09-16T04:20:53Z | dependency 'flux-system/estate-db-migrate' is not ready |
| Kustomization | flux-system | gvisor-runtime | Not ready | main@26584de | 2026-09-16T04:03:29Z | dependency 'flux-system/nodesoftware-operator' is not ready |
| Kustomization | flux-system | healing-analyzer | Not ready | main@26584de | 2026-09-16T04:24:02Z | dependency 'flux-system/healing-k8sgpt' is not ready |
| Kustomization | flux-system | healing-k8sgpt | Not ready | main@26584de | 2026-09-16T04:22:57Z | dependency 'flux-system/llm' is not ready |
| Kustomization | flux-system | healthchecks | Not ready | main@26584de | 2026-09-16T04:29:34Z | dependency 'flux-system/estate-db-migrate' is not ready |
| Kustomization | flux-system | hindsight | Not ready | main@26584de | 2026-09-16T04:21:32Z | dependency 'flux-system/llm' is not ready |
| Kustomization | flux-system | image-automation | Not ready | main@26584de | 2026-09-16T04:21:01Z | ClusterSecretStore/ghcr-pull dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.clustersecretstore.external-secrets.io":  |
| Kustomization | flux-system | llm | Not ready | main@26584de | 2026-09-16T04:20:58Z | dependency 'flux-system/estate-db-migrate' is not ready |
| Kustomization | flux-system | nodesoftware-operator | Not ready | main@26584de | 2026-09-16T04:02:52Z | dependency 'flux-system/image-automation' is not ready |
| Kustomization | flux-system | observability | Not ready | main@26584de | 2026-09-16T04:20:52Z | dependency 'flux-system/estate-db-migrate' is not ready |
| Kustomization | flux-system | research-engine | Not ready | main@26584de | 2026-09-16T04:29:07Z | dependency 'flux-system/llm' is not ready |
| Kustomization | flux-system | science | Not ready | main@26584de | 2026-09-16T04:22:25Z | dependency 'flux-system/observability' is not ready |
| Kustomization | flux-system | temporal | Not ready | main@26584de | 2026-09-16T04:01:18Z | dependency 'flux-system/image-automation' is not ready |
| Kustomization | flux-system | via-negativa | Not ready | main@26584de | 2026-09-16T04:21:20Z | dependency 'flux-system/llm' is not ready |
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
| Kustomization | flux-system | alerts | Ready | main@26584de | 2026-09-16T04:29:20Z |  |
| Kustomization | flux-system | alerts-github | Ready | main@26584de | 2026-09-16T04:22:03Z |  |
| Kustomization | flux-system | alerts-secret | Ready | main@26584de | 2026-09-16T04:29:10Z |  |
| Kustomization | flux-system | autoscaler | Ready | main@26584de | 2026-09-16T04:29:42Z |  |
| Kustomization | flux-system | backstage-namespace | Ready | main@26584de | 2026-09-16T04:22:50Z |  |
| Kustomization | flux-system | calico | Ready | main@26584de | 2026-09-16T04:26:25Z |  |
| Kustomization | flux-system | chaos-mesh | Ready | main@26584de | 2026-09-16T04:22:30Z |  |
| Kustomization | flux-system | cluster-state | Ready | main@26584de | 2026-09-16T04:22:50Z |  |
| Kustomization | flux-system | commerce-data | Ready | main@26584de | 2026-09-16T04:21:10Z |  |
| Kustomization | flux-system | concierge | Ready | main@26584de | 2026-09-16T04:20:56Z |  |
| Kustomization | flux-system | cross-node-drill | Ready | main@26584de | 2026-09-16T04:29:20Z |  |
| Kustomization | flux-system | crossplane | Ready | main@26584de | 2026-09-16T04:22:26Z |  |
| Kustomization | flux-system | crossplane-providerconfig | Ready | main@26584de | 2026-09-16T04:28:47Z |  |
| Kustomization | flux-system | crossplane-providers | Ready | main@26584de | 2026-09-16T04:23:50Z |  |
| Kustomization | flux-system | dns | Ready | main@26584de | 2026-09-16T04:20:48Z |  |
| Kustomization | flux-system | drills | Ready | main@26584de | 2026-09-16T04:21:53Z |  |
| Kustomization | flux-system | edge | Ready | main@26584de | 2026-09-16T04:26:50Z |  |
| Kustomization | flux-system | estate-catalog | Ready | latest@sha256:9a2b736d2455d3f2f1fea33be6 | 2026-09-16T04:27:53Z |  |
| Kustomization | flux-system | estate-db | Ready | main@26584de | 2026-09-16T04:20:32Z |  |
| Kustomization | flux-system | estate-db-operator | Ready | main@26584de | 2026-09-16T04:22:36Z |  |
| Kustomization | flux-system | event-bus | Ready | main@26584de | 2026-09-16T04:27:22Z |  |
| Kustomization | flux-system | external-secrets | Ready | main@26584de | 2026-09-16T04:25:49Z |  |
| Kustomization | flux-system | feature-register | Ready | main@26584de | 2026-09-16T04:24:35Z |  |
| Kustomization | flux-system | flux-system | Ready | main@26584de | 2026-09-16T04:24:23Z |  |
| Kustomization | flux-system | flux-webhook | Ready | main@26584de | 2026-09-16T04:24:20Z |  |
| Kustomization | flux-system | gateway-api-crds | Ready | v1.5.1@e7677b7 | 2026-09-16T04:27:07Z |  |
| Kustomization | flux-system | healing | Ready | main@26584de | 2026-09-16T04:23:02Z |  |
| Kustomization | flux-system | hermes-agent | Ready | main@26584de | 2026-09-16T04:22:02Z |  |
| Kustomization | flux-system | human-vault | Ready | main@26584de | 2026-09-16T04:21:53Z |  |
| Kustomization | flux-system | human-vault-bridge | Ready | main@26584de | 2026-09-16T04:22:44Z |  |
| Kustomization | flux-system | identity | Ready | main@26584de | 2026-09-16T04:20:25Z |  |
| Kustomization | flux-system | jit | Ready | main@26584de | 2026-09-16T04:25:04Z |  |
| Kustomization | flux-system | keda | Ready | main@26584de | 2026-09-16T04:23:29Z |  |
| Kustomization | flux-system | kyverno | Ready | main@26584de | 2026-09-16T04:24:06Z |  |
| Kustomization | flux-system | mcp | Ready | main@26584de | 2026-09-16T04:22:48Z |  |
| Kustomization | flux-system | metrics-server | Ready | main@26584de | 2026-09-16T04:21:47Z |  |
| Kustomization | flux-system | monitoring | Ready | main@26584de | 2026-09-16T04:29:52Z |  |
| Kustomization | flux-system | monitoring-rules | Ready | main@26584de | 2026-09-16T04:25:18Z |  |
| Kustomization | flux-system | notify | Ready | main@26584de | 2026-09-16T04:23:42Z |  |
| Kustomization | flux-system | ns-fences | Ready | main@26584de | 2026-09-16T04:25:54Z |  |
| Kustomization | flux-system | observability-collector | Ready | main@26584de | 2026-09-16T04:23:00Z |  |
| Kustomization | flux-system | otto-gateway | Ready | main@26584de | 2026-09-16T04:21:54Z |  |
| Kustomization | flux-system | otto-golden | Ready | main@26584de | 2026-09-16T04:24:23Z |  |
| Kustomization | flux-system | otto-golden-secret | Ready | main@26584de | 2026-09-16T04:25:44Z |  |
| Kustomization | flux-system | priority-classes | Ready | main@26584de | 2026-09-16T04:23:27Z |  |
| Kustomization | flux-system | prospector | Ready | main@7453d76 | 2026-09-16T04:28:45Z |  |
| Kustomization | flux-system | prospector-platform | Ready | main@26584de | 2026-09-16T04:24:05Z |  |
| Kustomization | flux-system | rbac | Ready | main@26584de | 2026-09-16T04:21:10Z |  |
| Kustomization | flux-system | rbac-floor | Ready | main@26584de | 2026-09-16T04:26:58Z |  |
| Kustomization | flux-system | rbac-identity | Ready | main@26584de | 2026-09-16T04:20:52Z |  |
| Kustomization | flux-system | reloader | Ready | main@26584de | 2026-09-16T04:27:46Z |  |
| Kustomization | flux-system | robusta | Ready | main@26584de | 2026-09-16T04:21:01Z |  |
| Kustomization | flux-system | router-events | Ready | main@26584de | 2026-09-16T04:20:47Z |  |
| Kustomization | flux-system | sandbox-launch | Ready | main@26584de | 2026-09-16T04:27:55Z |  |
| Kustomization | flux-system | sandbox-live | Ready | sandbox/launch@4830a6e | 2026-09-16T04:30:08Z |  |
| Kustomization | flux-system | scheduling | Ready | main@26584de | 2026-09-16T04:22:46Z |  |
| Kustomization | flux-system | searxng | Ready | main@26584de | 2026-09-16T04:23:29Z |  |
| Kustomization | flux-system | secret-store | Ready | main@26584de | 2026-09-16T04:28:42Z |  |
| Kustomization | flux-system | spire | Ready | main@26584de | 2026-09-16T04:22:26Z |  |
| Kustomization | flux-system | staging | Ready | main@26584de | 2026-09-16T04:24:44Z |  |
| Kustomization | flux-system | tailscale | Ready | main@26584de | 2026-09-16T04:20:47Z |  |
| Kustomization | flux-system | trivy | Ready | main@26584de | 2026-09-16T04:22:48Z |  |
| Kustomization | flux-system | verification | Ready | main@26584de | 2026-09-16T04:21:18Z |  |
| Kustomization | flux-system | weave-gitops | Ready | main@26584de | 2026-09-16T04:30:07Z |  |
