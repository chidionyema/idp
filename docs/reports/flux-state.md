# Flux: what is applied

Read from the cluster receipt taken at 2026-09-17T07:45:25Z. Every Kustomization and HelmRelease, with the revision Flux last applied. **Suspended** is a switch somebody turned off on purpose (temporal, commerce, commerce-data, event-bus), not a defect; **Unknown** is a row Flux has never graded.

**120 objects: 94 ready, 25 not ready, 0 unknown, 1 suspended.**

## Not ready right now

- **HelmRelease commerce/lago** since 2026-09-17T07:39:40Z: Running 'install' action with timeout of 20m0s
- **HelmRelease crossplane-system/crossplane** since 2026-09-16T17:08:05Z: Helm upgrade failed for release crossplane-system/crossplane with chart crossplane@1.15.1: create: failed to create: admission webhook "oke-resource-leak-protection.oke.com" denied the request: OKE resource leak protection rejected the request. Cluster has 2650 secrets and the limit is 2000. See https://docs.oracle.com/iaas/Content/ContEng/Tasks/contengprotectingclustersfromresourceleaks.htm for details.
- **Kustomization flux-system/alerts** since 2026-09-17T07:32:55Z: dependency 'flux-system/alerts-secret' is not ready
- **Kustomization flux-system/alerts-secret** since 2026-09-17T07:45:10Z: Reconciliation in progress
- **Kustomization flux-system/backstage** since 2026-09-17T07:45:11Z: Reconciliation in progress
- **Kustomization flux-system/commerce** since 2026-09-17T07:39:39Z: Reconciliation in progress
- **Kustomization flux-system/crossplane** since 2026-09-17T07:44:13Z: health check failed after 45.917744ms: failed early due to stalled resources: [HelmRelease/crossplane-system/crossplane status: 'Failed']
- **Kustomization flux-system/crossplane-providerconfig** since 2026-09-16T11:53:07Z: dependency 'flux-system/crossplane-providers' is not ready
- **Kustomization flux-system/crossplane-providers** since 2026-09-16T11:53:06Z: dependency 'flux-system/crossplane' is not ready
- **Kustomization flux-system/crossplane-storage-capability** since 2026-09-16T11:53:07Z: dependency 'flux-system/crossplane-providerconfig' is not ready
- **Kustomization flux-system/epistemic-fabric** since 2026-09-17T07:35:15Z: health check failed after 66.444008ms: failed early due to stalled resources: [Deployment/epistemic-fabric/epistemic-ingest-github status: 'Failed']
- **Kustomization flux-system/estate-db** since 2026-09-17T07:45:11Z: Reconciliation in progress
- **Kustomization flux-system/guacamole** since 2026-09-17T07:45:05Z: dependency 'flux-system/tailscale' is not ready
- **Kustomization flux-system/gvisor-runtime** since 2026-09-17T07:28:49Z: dependency 'flux-system/nodesoftware-operator' is not ready
- **Kustomization flux-system/healthchecks** since 2026-09-17T07:32:56Z: dependency 'flux-system/identity' is not ready
- **Kustomization flux-system/hermes-agent** since 2026-09-17T07:35:08Z: ExternalSecret/hermes-agent/hermes-agent-env dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-secrets.io": failed to call webhook: Post "https://external-secrets-webhook.external-secrets.svc:443/validate-external-secrets-io-v1-externalsecret?timeout=15s": context deadline exceeded 
- **Kustomization flux-system/human-vault** since 2026-09-17T07:45:02Z: ClusterSecretStore/human-vault dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.clustersecretstore.external-secrets.io": failed to call webhook: Post "https://external-secrets-webhook.external-secrets.svc:443/validate-external-secrets-io-v1-clustersecretstore?timeout=15s": context deadline exceeded 
- **Kustomization flux-system/human-vault-bridge** since 2026-09-17T07:32:55Z: dependency 'flux-system/human-vault' is not ready
- **Kustomization flux-system/idp-agent** since 2026-09-17T07:35:13Z: Service/idp-agent/idp-agent-redis dry-run failed: admission webhook "validate.kyverno.svc-fail" denied the request:   resource Service/idp-agent/idp-agent-redis was blocked due to the following policies   require-catalogue-entity:   service-names-its-entity: 'validation error: Service idp-agent/idp-agent-redis serves a port but names no catalogue entity. Add the label backstage.io/kubernetes-id with the entity name from backstage/**/catalog-info.yaml, and a founder surface if a person opens it (docs/policy/every-interface-is-a-door.md). rule service-names-its-entity failed at path /metadata/labels/backstage.io/kubernetes-id/'  
- **Kustomization flux-system/image-automation** since 2026-09-17T07:45:05Z: ClusterSecretStore/ghcr-pull dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.clustersecretstore.external-secrets.io": failed to call webhook: Post "https://external-secrets-webhook.external-secrets.svc:443/validate-external-secrets-io-v1-clustersecretstore?timeout=15s": context deadline exceeded 
- **Kustomization flux-system/nodesoftware-operator** since 2026-09-17T07:35:09Z: dependency 'flux-system/image-automation' is not ready
- **Kustomization flux-system/otto-gateway** since 2026-09-17T07:45:05Z: dependency 'flux-system/alerts-github' is not ready
- **Kustomization flux-system/otto-golden** since 2026-09-17T07:45:10Z: health check failed after 959.479196ms: failed early due to stalled resources: [Deployment/otto-golden/otto-golden status: 'Failed']
- **Kustomization flux-system/temporal** since 2026-09-17T07:35:03Z: dependency 'flux-system/image-automation' is not ready
- **Kustomization flux-system/via-negativa** since 2026-09-17T07:35:38Z: health check failed after 472.171175ms: failed early due to stalled resources: [Deployment/via-negativa/via-negativa-rca status: 'Failed']

## Every row

| Kind | Namespace | Name | State | Applied revision | Since | Message |
|---|---|---|---|---|---|---|
| HelmRelease | commerce | lago | Not ready | 1.28.0 | 2026-09-17T07:39:40Z | Running 'install' action with timeout of 20m0s |
| HelmRelease | crossplane-system | crossplane | Not ready | 1.15.1 | 2026-09-16T17:08:05Z | Helm upgrade failed for release crossplane-system/crossplane with chart crossplane@1.15.1: create: failed to create: admission webhook "oke-resource-leak-protec |
| Kustomization | flux-system | alerts | Not ready | main@5760fb3 | 2026-09-17T07:32:55Z | dependency 'flux-system/alerts-secret' is not ready |
| Kustomization | flux-system | alerts-secret | Not ready | main@5760fb3 | 2026-09-17T07:45:10Z | Reconciliation in progress |
| Kustomization | flux-system | backstage | Not ready | main@7aad2f2 | 2026-09-17T07:45:11Z | Reconciliation in progress |
| Kustomization | flux-system | commerce | Not ready | main@abea14d | 2026-09-17T07:39:39Z | Reconciliation in progress |
| Kustomization | flux-system | crossplane | Not ready | main@8d685ec | 2026-09-17T07:44:13Z | health check failed after 45.917744ms: failed early due to stalled resources: [HelmRelease/crossplane-system/crossplane status: 'Failed'] |
| Kustomization | flux-system | crossplane-providerconfig | Not ready | main@8d685ec | 2026-09-16T11:53:07Z | dependency 'flux-system/crossplane-providers' is not ready |
| Kustomization | flux-system | crossplane-providers | Not ready | main@8d685ec | 2026-09-16T11:53:06Z | dependency 'flux-system/crossplane' is not ready |
| Kustomization | flux-system | crossplane-storage-capability | Not ready | main@8d685ec | 2026-09-16T11:53:07Z | dependency 'flux-system/crossplane-providerconfig' is not ready |
| Kustomization | flux-system | epistemic-fabric | Not ready | main@7aad2f2 | 2026-09-17T07:35:15Z | health check failed after 66.444008ms: failed early due to stalled resources: [Deployment/epistemic-fabric/epistemic-ingest-github status: 'Failed'] |
| Kustomization | flux-system | estate-db | Not ready | main@7aad2f2 | 2026-09-17T07:45:11Z | Reconciliation in progress |
| Kustomization | flux-system | guacamole | Not ready | main@5760fb3 | 2026-09-17T07:45:05Z | dependency 'flux-system/tailscale' is not ready |
| Kustomization | flux-system | gvisor-runtime | Not ready | main@5760fb3 | 2026-09-17T07:28:49Z | dependency 'flux-system/nodesoftware-operator' is not ready |
| Kustomization | flux-system | healthchecks | Not ready | main@5760fb3 | 2026-09-17T07:32:56Z | dependency 'flux-system/identity' is not ready |
| Kustomization | flux-system | hermes-agent | Not ready | main@5760fb3 | 2026-09-17T07:35:08Z | ExternalSecret/hermes-agent/hermes-agent-env dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-s |
| Kustomization | flux-system | human-vault | Not ready | main@5760fb3 | 2026-09-17T07:45:02Z | ClusterSecretStore/human-vault dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.clustersecretstore.external-secrets.io" |
| Kustomization | flux-system | human-vault-bridge | Not ready | main@5760fb3 | 2026-09-17T07:32:55Z | dependency 'flux-system/human-vault' is not ready |
| Kustomization | flux-system | idp-agent | Not ready | main@7aad2f2 | 2026-09-17T07:35:13Z | Service/idp-agent/idp-agent-redis dry-run failed: admission webhook "validate.kyverno.svc-fail" denied the request:   resource Service/idp-agent/idp-agent-redis |
| Kustomization | flux-system | image-automation | Not ready | main@5760fb3 | 2026-09-17T07:45:05Z | ClusterSecretStore/ghcr-pull dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.clustersecretstore.external-secrets.io":  |
| Kustomization | flux-system | nodesoftware-operator | Not ready | main@5760fb3 | 2026-09-17T07:35:09Z | dependency 'flux-system/image-automation' is not ready |
| Kustomization | flux-system | otto-gateway | Not ready | main@cd9eb71 | 2026-09-17T07:45:05Z | dependency 'flux-system/alerts-github' is not ready |
| Kustomization | flux-system | otto-golden | Not ready | main@cd9eb71 | 2026-09-17T07:45:10Z | health check failed after 959.479196ms: failed early due to stalled resources: [Deployment/otto-golden/otto-golden status: 'Failed'] |
| Kustomization | flux-system | temporal | Not ready | main@5760fb3 | 2026-09-17T07:35:03Z | dependency 'flux-system/image-automation' is not ready |
| Kustomization | flux-system | via-negativa | Not ready | main@7aad2f2 | 2026-09-17T07:35:38Z | health check failed after 472.171175ms: failed early due to stalled resources: [Deployment/via-negativa/via-negativa-rca status: 'Failed'] |
| HelmRelease | tigera-operator | tigera-operator | Suspended | v3.32.2 | 2026-09-06T19:38:02Z |  |
| HelmRelease | cert-manager | cert-manager | Ready | v1.21.1 | 2026-09-08T11:56:22Z |  |
| HelmRelease | chaos-mesh | chaos-mesh | Ready | 2.8.4 | 2026-09-15T14:48:03Z |  |
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
| Kustomization | flux-system | agent-workforce | Ready | main@7aad2f2 | 2026-09-17T07:35:37Z |  |
| Kustomization | flux-system | alerts-github | Ready | main@7aad2f2 | 2026-09-17T07:45:06Z |  |
| Kustomization | flux-system | autoscaler | Ready | main@7aad2f2 | 2026-09-17T07:44:08Z |  |
| Kustomization | flux-system | backstage-namespace | Ready | main@7aad2f2 | 2026-09-17T07:43:02Z |  |
| Kustomization | flux-system | calico | Ready | main@7aad2f2 | 2026-09-17T07:42:44Z |  |
| Kustomization | flux-system | chaos | Ready | main@7aad2f2 | 2026-09-17T07:35:40Z |  |
| Kustomization | flux-system | chaos-mesh | Ready | main@7aad2f2 | 2026-09-17T07:43:58Z |  |
| Kustomization | flux-system | cluster-state | Ready | main@7aad2f2 | 2026-09-17T07:43:57Z |  |
| Kustomization | flux-system | commerce-data | Ready | main@7aad2f2 | 2026-09-17T07:35:02Z |  |
| Kustomization | flux-system | concierge | Ready | main@7aad2f2 | 2026-09-17T07:44:10Z |  |
| Kustomization | flux-system | cross-node-drill | Ready | main@7aad2f2 | 2026-09-17T07:43:19Z |  |
| Kustomization | flux-system | dagster | Ready | main@7aad2f2 | 2026-09-17T07:44:47Z |  |
| Kustomization | flux-system | dns | Ready | main@7aad2f2 | 2026-09-17T07:44:11Z |  |
| Kustomization | flux-system | drills | Ready | main@7aad2f2 | 2026-09-17T07:45:08Z |  |
| Kustomization | flux-system | edge | Ready | main@7aad2f2 | 2026-09-17T07:42:49Z |  |
| Kustomization | flux-system | estate-catalog | Ready | latest@sha256:986970bde843ecbe54ee066f67 | 2026-09-17T07:38:34Z |  |
| Kustomization | flux-system | estate-db-migrate | Ready | main@7aad2f2 | 2026-09-17T07:34:58Z |  |
| Kustomization | flux-system | estate-db-operator | Ready | main@7aad2f2 | 2026-09-17T07:42:38Z |  |
| Kustomization | flux-system | event-bus | Ready | main@7aad2f2 | 2026-09-17T07:43:40Z |  |
| Kustomization | flux-system | external-secrets | Ready | main@7aad2f2 | 2026-09-17T07:43:20Z |  |
| Kustomization | flux-system | feature-register | Ready | main@7aad2f2 | 2026-09-17T07:42:35Z |  |
| Kustomization | flux-system | flux-system | Ready | main@7aad2f2 | 2026-09-17T07:42:39Z |  |
| Kustomization | flux-system | flux-webhook | Ready | main@7aad2f2 | 2026-09-17T07:44:40Z |  |
| Kustomization | flux-system | gateway-api-crds | Ready | v1.5.1@e7677b7 | 2026-09-17T07:43:12Z |  |
| Kustomization | flux-system | healing | Ready | main@7aad2f2 | 2026-09-17T07:43:37Z |  |
| Kustomization | flux-system | healing-analyzer | Ready | main@7aad2f2 | 2026-09-17T07:36:04Z |  |
| Kustomization | flux-system | healing-k8sgpt | Ready | main@7aad2f2 | 2026-09-17T07:35:35Z |  |
| Kustomization | flux-system | hindsight | Ready | main@7aad2f2 | 2026-09-17T07:35:36Z |  |
| Kustomization | flux-system | identity | Ready | main@7aad2f2 | 2026-09-17T07:45:05Z |  |
| Kustomization | flux-system | jit | Ready | main@7aad2f2 | 2026-09-17T07:43:45Z |  |
| Kustomization | flux-system | keda | Ready | main@7aad2f2 | 2026-09-17T07:43:29Z |  |
| Kustomization | flux-system | kyverno | Ready | main@7aad2f2 | 2026-09-17T07:42:53Z |  |
| Kustomization | flux-system | llm | Ready | main@7aad2f2 | 2026-09-17T07:44:50Z |  |
| Kustomization | flux-system | mcp | Ready | main@7aad2f2 | 2026-09-17T07:35:17Z |  |
| Kustomization | flux-system | metrics-server | Ready | main@7aad2f2 | 2026-09-17T07:43:43Z |  |
| Kustomization | flux-system | monitoring | Ready | main@7aad2f2 | 2026-09-17T07:44:28Z |  |
| Kustomization | flux-system | monitoring-rules | Ready | main@7aad2f2 | 2026-09-17T07:35:15Z |  |
| Kustomization | flux-system | notify | Ready | main@7aad2f2 | 2026-09-17T07:44:45Z |  |
| Kustomization | flux-system | ns-fences | Ready | main@7aad2f2 | 2026-09-17T07:43:18Z |  |
| Kustomization | flux-system | observability | Ready | main@7aad2f2 | 2026-09-17T07:45:10Z |  |
| Kustomization | flux-system | observability-collector | Ready | main@7aad2f2 | 2026-09-17T07:43:36Z |  |
| Kustomization | flux-system | otto-golden-secret | Ready | main@7aad2f2 | 2026-09-17T07:34:56Z |  |
| Kustomization | flux-system | priority-classes | Ready | main@7aad2f2 | 2026-09-17T07:43:14Z |  |
| Kustomization | flux-system | prospector | Ready | main@7453d76 | 2026-09-17T07:36:49Z |  |
| Kustomization | flux-system | prospector-platform | Ready | main@7aad2f2 | 2026-09-17T07:43:06Z |  |
| Kustomization | flux-system | rbac | Ready | main@7aad2f2 | 2026-09-17T07:43:06Z |  |
| Kustomization | flux-system | rbac-floor | Ready | main@7aad2f2 | 2026-09-17T07:42:27Z |  |
| Kustomization | flux-system | rbac-identity | Ready | main@7aad2f2 | 2026-09-17T07:42:55Z |  |
| Kustomization | flux-system | reloader | Ready | main@7aad2f2 | 2026-09-17T07:34:51Z |  |
| Kustomization | flux-system | research-engine | Ready | main@7aad2f2 | 2026-09-17T07:35:38Z |  |
| Kustomization | flux-system | robusta | Ready | main@7aad2f2 | 2026-09-17T07:44:13Z |  |
| Kustomization | flux-system | router-events | Ready | main@7aad2f2 | 2026-09-17T07:35:09Z |  |
| Kustomization | flux-system | sandbox-launch | Ready | main@7aad2f2 | 2026-09-17T07:43:49Z |  |
| Kustomization | flux-system | sandbox-live | Ready | sandbox/launch@4830a6e | 2026-09-17T07:44:06Z |  |
| Kustomization | flux-system | scheduling | Ready | main@7aad2f2 | 2026-09-17T07:44:01Z |  |
| Kustomization | flux-system | science | Ready | main@7aad2f2 | 2026-09-17T07:35:38Z |  |
| Kustomization | flux-system | searxng | Ready | main@7aad2f2 | 2026-09-17T07:43:25Z |  |
| Kustomization | flux-system | secret-store | Ready | main@7aad2f2 | 2026-09-17T07:43:52Z |  |
| Kustomization | flux-system | spire | Ready | main@7aad2f2 | 2026-09-17T07:43:31Z |  |
| Kustomization | flux-system | staging | Ready | main@7aad2f2 | 2026-09-17T07:42:47Z |  |
| Kustomization | flux-system | tailscale | Ready | main@7aad2f2 | 2026-09-17T07:45:07Z |  |
| Kustomization | flux-system | trivy | Ready | main@7aad2f2 | 2026-09-17T07:42:58Z |  |
| Kustomization | flux-system | verification | Ready | main@7aad2f2 | 2026-09-17T07:44:34Z |  |
| Kustomization | flux-system | weave-gitops | Ready | main@7aad2f2 | 2026-09-17T07:45:10Z |  |
