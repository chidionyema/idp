# Flux: what is applied

Read from the cluster receipt taken at 2026-09-16T02:15:19Z. Every Kustomization and HelmRelease, with the revision Flux last applied. **Suspended** is a switch somebody turned off on purpose (temporal, commerce, commerce-data, event-bus), not a defect; **Unknown** is a row Flux has never graded.

**119 objects: 108 ready, 10 not ready, 0 unknown, 1 suspended.**

## Not ready right now

- **HelmRelease commerce/lago** since 2026-09-16T01:49:09Z: Helm install failed for release commerce/lago with chart lago@1.28.0: failed early due to stalled resources: [Deployment/commerce/lago-clock-worker status: 'Failed']
- **Kustomization flux-system/chaos** since 2026-09-16T02:12:44Z: dependency 'flux-system/observability' is not ready
- **Kustomization flux-system/commerce** since 2026-09-16T02:09:13Z: health check failed after 36.198997ms: failed early due to stalled resources: [HelmRelease/commerce/lago status: 'Failed']
- **Kustomization flux-system/crossplane-storage-capability** since 2026-09-16T02:10:33Z: Composition/xobjectstoragebuckets.storage.estate.io dry-run failed: failed to create typed patch object (/xobjectstoragebuckets.storage.estate.io; apiextensions.crossplane.io/v1, Kind=Composition): .spec.resources: field not declared in schema 
- **Kustomization flux-system/epistemic-fabric** since 2026-09-16T02:10:42Z: health check failed after 50.491033ms: failed early due to stalled resources: [Deployment/epistemic-fabric/epistemic-ingest-github status: 'Failed']
- **Kustomization flux-system/guacamole** since 2026-09-16T02:12:29Z: ExternalSecret/guacamole/guacamole dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-secrets.io": failed to call webhook: Post "https://external-secrets-webhook.external-secrets.svc:443/validate-external-secrets-io-v1-externalsecret?timeout=15s": context deadline exceeded 
- **Kustomization flux-system/human-vault** since 2026-09-16T02:11:01Z: ExternalSecret/external-secrets/bitwarden-access-token dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-secrets.io": failed to call webhook: Post "https://external-secrets-webhook.external-secrets.svc:443/validate-external-secrets-io-v1-externalsecret?timeout=15s": context deadline exceeded 
- **Kustomization flux-system/notify** since 2026-09-16T02:11:05Z: ExternalSecret/notify/notify-channels dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-secrets.io": failed to call webhook: Post "https://external-secrets-webhook.external-secrets.svc:443/validate-external-secrets-io-v1-externalsecret?timeout=15s": context deadline exceeded 
- **Kustomization flux-system/observability** since 2026-09-16T02:12:11Z: ExternalSecret/observability/otlp-ingest-users dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-secrets.io": failed to call webhook: Post "https://external-secrets-webhook.external-secrets.svc:443/validate-external-secrets-io-v1-externalsecret?timeout=15s": context deadline exceeded 
- **Kustomization flux-system/via-negativa** since 2026-09-16T02:11:55Z: health check failed after 430.690435ms: failed early due to stalled resources: [Deployment/via-negativa/via-negativa-rca status: 'Failed']

## Every row

| Kind | Namespace | Name | State | Applied revision | Since | Message |
|---|---|---|---|---|---|---|
| HelmRelease | commerce | lago | Not ready | 1.28.0 | 2026-09-16T01:49:09Z | Helm install failed for release commerce/lago with chart lago@1.28.0: failed early due to stalled resources: [Deployment/commerce/lago-clock-worker status: 'Fai |
| Kustomization | flux-system | chaos | Not ready | main@26584de | 2026-09-16T02:12:44Z | dependency 'flux-system/observability' is not ready |
| Kustomization | flux-system | commerce | Not ready | main@abea14d | 2026-09-16T02:09:13Z | health check failed after 36.198997ms: failed early due to stalled resources: [HelmRelease/commerce/lago status: 'Failed'] |
| Kustomization | flux-system | crossplane-storage-capability | Not ready | main@26584de | 2026-09-16T02:10:33Z | Composition/xobjectstoragebuckets.storage.estate.io dry-run failed: failed to create typed patch object (/xobjectstoragebuckets.storage.estate.io; apiextensions |
| Kustomization | flux-system | epistemic-fabric | Not ready | main@26584de | 2026-09-16T02:10:42Z | health check failed after 50.491033ms: failed early due to stalled resources: [Deployment/epistemic-fabric/epistemic-ingest-github status: 'Failed'] |
| Kustomization | flux-system | guacamole | Not ready | main@26584de | 2026-09-16T02:12:29Z | ExternalSecret/guacamole/guacamole dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-secrets.io" |
| Kustomization | flux-system | human-vault | Not ready | main@26584de | 2026-09-16T02:11:01Z | ExternalSecret/external-secrets/bitwarden-access-token dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret. |
| Kustomization | flux-system | notify | Not ready | main@26584de | 2026-09-16T02:11:05Z | ExternalSecret/notify/notify-channels dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-secrets. |
| Kustomization | flux-system | observability | Not ready | main@26584de | 2026-09-16T02:12:11Z | ExternalSecret/observability/otlp-ingest-users dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external |
| Kustomization | flux-system | via-negativa | Not ready | main@26584de | 2026-09-16T02:11:55Z | health check failed after 430.690435ms: failed early due to stalled resources: [Deployment/via-negativa/via-negativa-rca status: 'Failed'] |
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
| Kustomization | flux-system | agent-workforce | Ready | main@26584de | 2026-09-16T02:12:00Z |  |
| Kustomization | flux-system | alerts | Ready | main@26584de | 2026-09-16T02:09:37Z |  |
| Kustomization | flux-system | alerts-github | Ready | main@26584de | 2026-09-16T02:09:14Z |  |
| Kustomization | flux-system | alerts-secret | Ready | main@26584de | 2026-09-16T02:08:06Z |  |
| Kustomization | flux-system | autoscaler | Ready | main@26584de | 2026-09-16T02:07:50Z |  |
| Kustomization | flux-system | backstage | Ready | main@26584de | 2026-09-16T02:12:17Z |  |
| Kustomization | flux-system | backstage-namespace | Ready | main@26584de | 2026-09-16T02:13:11Z |  |
| Kustomization | flux-system | calico | Ready | main@26584de | 2026-09-16T02:05:40Z |  |
| Kustomization | flux-system | chaos-mesh | Ready | main@26584de | 2026-09-16T02:09:05Z |  |
| Kustomization | flux-system | cluster-state | Ready | main@26584de | 2026-09-16T02:06:02Z |  |
| Kustomization | flux-system | commerce-data | Ready | main@26584de | 2026-09-16T02:11:28Z |  |
| Kustomization | flux-system | concierge | Ready | main@26584de | 2026-09-16T02:10:46Z |  |
| Kustomization | flux-system | cross-node-drill | Ready | main@26584de | 2026-09-16T02:07:56Z |  |
| Kustomization | flux-system | crossplane | Ready | main@26584de | 2026-09-16T02:09:32Z |  |
| Kustomization | flux-system | crossplane-providerconfig | Ready | main@26584de | 2026-09-16T02:08:44Z |  |
| Kustomization | flux-system | crossplane-providers | Ready | main@26584de | 2026-09-16T02:10:07Z |  |
| Kustomization | flux-system | dagster | Ready | main@26584de | 2026-09-16T02:11:38Z |  |
| Kustomization | flux-system | dns | Ready | main@26584de | 2026-09-16T02:07:19Z |  |
| Kustomization | flux-system | drills | Ready | main@26584de | 2026-09-16T02:10:10Z |  |
| Kustomization | flux-system | edge | Ready | main@26584de | 2026-09-16T02:06:10Z |  |
| Kustomization | flux-system | estate-catalog | Ready | latest@sha256:9a2b736d2455d3f2f1fea33be6 | 2026-09-16T02:08:42Z |  |
| Kustomization | flux-system | estate-db | Ready | main@26584de | 2026-09-16T02:09:06Z |  |
| Kustomization | flux-system | estate-db-migrate | Ready | main@26584de | 2026-09-16T02:11:18Z |  |
| Kustomization | flux-system | estate-db-operator | Ready | main@26584de | 2026-09-16T02:11:07Z |  |
| Kustomization | flux-system | event-bus | Ready | main@26584de | 2026-09-16T02:06:33Z |  |
| Kustomization | flux-system | external-secrets | Ready | main@26584de | 2026-09-16T02:15:12Z |  |
| Kustomization | flux-system | feature-register | Ready | main@26584de | 2026-09-16T02:14:15Z |  |
| Kustomization | flux-system | flux-system | Ready | main@26584de | 2026-09-16T02:13:25Z |  |
| Kustomization | flux-system | flux-webhook | Ready | main@26584de | 2026-09-16T02:13:25Z |  |
| Kustomization | flux-system | gateway-api-crds | Ready | v1.5.1@e7677b7 | 2026-09-16T02:15:13Z |  |
| Kustomization | flux-system | gvisor-runtime | Ready | main@26584de | 2026-09-16T02:09:10Z |  |
| Kustomization | flux-system | healing | Ready | main@26584de | 2026-09-16T02:07:55Z |  |
| Kustomization | flux-system | healing-analyzer | Ready | main@26584de | 2026-09-16T02:12:00Z |  |
| Kustomization | flux-system | healing-k8sgpt | Ready | main@26584de | 2026-09-16T02:11:13Z |  |
| Kustomization | flux-system | healthchecks | Ready | main@26584de | 2026-09-16T02:12:27Z |  |
| Kustomization | flux-system | hermes-agent | Ready | main@26584de | 2026-09-16T02:13:05Z |  |
| Kustomization | flux-system | hindsight | Ready | main@26584de | 2026-09-16T02:11:47Z |  |
| Kustomization | flux-system | human-vault-bridge | Ready | main@26584de | 2026-09-16T02:10:23Z |  |
| Kustomization | flux-system | identity | Ready | main@26584de | 2026-09-16T02:10:19Z |  |
| Kustomization | flux-system | image-automation | Ready | main@26584de | 2026-09-16T02:07:13Z |  |
| Kustomization | flux-system | jit | Ready | main@26584de | 2026-09-16T02:05:58Z |  |
| Kustomization | flux-system | keda | Ready | main@26584de | 2026-09-16T02:06:27Z |  |
| Kustomization | flux-system | kyverno | Ready | main@26584de | 2026-09-16T02:14:57Z |  |
| Kustomization | flux-system | llm | Ready | main@26584de | 2026-09-16T02:12:25Z |  |
| Kustomization | flux-system | mcp | Ready | main@26584de | 2026-09-16T02:10:19Z |  |
| Kustomization | flux-system | metrics-server | Ready | main@26584de | 2026-09-16T02:15:09Z |  |
| Kustomization | flux-system | monitoring | Ready | main@26584de | 2026-09-16T02:06:17Z |  |
| Kustomization | flux-system | monitoring-rules | Ready | main@26584de | 2026-09-16T02:14:56Z |  |
| Kustomization | flux-system | nodesoftware-operator | Ready | main@26584de | 2026-09-16T02:08:51Z |  |
| Kustomization | flux-system | ns-fences | Ready | main@26584de | 2026-09-16T02:14:32Z |  |
| Kustomization | flux-system | observability-collector | Ready | main@26584de | 2026-09-16T02:13:39Z |  |
| Kustomization | flux-system | otto-gateway | Ready | main@26584de | 2026-09-16T02:10:37Z |  |
| Kustomization | flux-system | otto-golden | Ready | main@26584de | 2026-09-16T02:07:08Z |  |
| Kustomization | flux-system | otto-golden-secret | Ready | main@26584de | 2026-09-16T02:13:51Z |  |
| Kustomization | flux-system | priority-classes | Ready | main@26584de | 2026-09-16T02:12:44Z |  |
| Kustomization | flux-system | prospector | Ready | main@7453d76 | 2026-09-16T02:09:30Z |  |
| Kustomization | flux-system | prospector-platform | Ready | main@26584de | 2026-09-16T02:13:55Z |  |
| Kustomization | flux-system | rbac | Ready | main@26584de | 2026-09-16T02:14:22Z |  |
| Kustomization | flux-system | rbac-floor | Ready | main@26584de | 2026-09-16T02:05:32Z |  |
| Kustomization | flux-system | rbac-identity | Ready | main@26584de | 2026-09-16T02:07:15Z |  |
| Kustomization | flux-system | reloader | Ready | main@26584de | 2026-09-16T02:08:11Z |  |
| Kustomization | flux-system | research-engine | Ready | main@26584de | 2026-09-16T02:12:16Z |  |
| Kustomization | flux-system | robusta | Ready | main@26584de | 2026-09-16T02:09:37Z |  |
| Kustomization | flux-system | router-events | Ready | main@26584de | 2026-09-16T02:12:53Z |  |
| Kustomization | flux-system | sandbox-launch | Ready | main@26584de | 2026-09-16T02:06:53Z |  |
| Kustomization | flux-system | sandbox-live | Ready | sandbox/launch@4830a6e | 2026-09-16T02:14:22Z |  |
| Kustomization | flux-system | scheduling | Ready | main@26584de | 2026-09-16T02:12:56Z |  |
| Kustomization | flux-system | science | Ready | main@26584de | 2026-09-16T02:08:42Z |  |
| Kustomization | flux-system | searxng | Ready | main@26584de | 2026-09-16T02:14:03Z |  |
| Kustomization | flux-system | secret-store | Ready | main@26584de | 2026-09-16T02:06:21Z |  |
| Kustomization | flux-system | spire | Ready | main@26584de | 2026-09-16T02:08:37Z |  |
| Kustomization | flux-system | staging | Ready | main@26584de | 2026-09-16T02:13:50Z |  |
| Kustomization | flux-system | tailscale | Ready | main@26584de | 2026-09-16T02:08:28Z |  |
| Kustomization | flux-system | temporal | Ready | main@26584de | 2026-09-16T02:11:42Z |  |
| Kustomization | flux-system | trivy | Ready | main@26584de | 2026-09-16T02:12:50Z |  |
| Kustomization | flux-system | verification | Ready | main@26584de | 2026-09-16T02:09:45Z |  |
| Kustomization | flux-system | weave-gitops | Ready | main@26584de | 2026-09-16T02:08:58Z |  |
