# Flux: what is applied

Read from the cluster receipt taken at 2026-09-16T19:45:18Z. Every Kustomization and HelmRelease, with the revision Flux last applied. **Suspended** is a switch somebody turned off on purpose (temporal, commerce, commerce-data, event-bus), not a defect; **Unknown** is a row Flux has never graded.

**120 objects: 105 ready, 14 not ready, 0 unknown, 1 suspended.**

## Not ready right now

- **HelmRelease commerce/lago** since 2026-09-16T19:33:00Z: Helm install failed for release commerce/lago with chart lago@1.28.0: create: failed to create: admission webhook "oke-resource-leak-protection.oke.com" denied the request: OKE resource leak protection rejected the request. Cluster has 2650 secrets and the limit is 2000. See https://docs.oracle.com/iaas/Content/ContEng/Tasks/contengprotectingclustersfromresourceleaks.htm for details.
- **HelmRelease crossplane-system/crossplane** since 2026-09-16T17:08:05Z: Helm upgrade failed for release crossplane-system/crossplane with chart crossplane@1.15.1: create: failed to create: admission webhook "oke-resource-leak-protection.oke.com" denied the request: OKE resource leak protection rejected the request. Cluster has 2650 secrets and the limit is 2000. See https://docs.oracle.com/iaas/Content/ContEng/Tasks/contengprotectingclustersfromresourceleaks.htm for details.
- **Kustomization flux-system/commerce** since 2026-09-16T19:32:56Z: Reconciliation in progress
- **Kustomization flux-system/crossplane** since 2026-09-16T19:41:51Z: health check failed after 40.774086ms: failed early due to stalled resources: [HelmRelease/crossplane-system/crossplane status: 'Failed']
- **Kustomization flux-system/crossplane-providerconfig** since 2026-09-16T11:53:07Z: dependency 'flux-system/crossplane-providers' is not ready
- **Kustomization flux-system/crossplane-providers** since 2026-09-16T11:53:06Z: dependency 'flux-system/crossplane' is not ready
- **Kustomization flux-system/crossplane-storage-capability** since 2026-09-16T11:53:07Z: dependency 'flux-system/crossplane-providerconfig' is not ready
- **Kustomization flux-system/epistemic-fabric** since 2026-09-16T19:42:49Z: health check failed after 86.289826ms: failed early due to stalled resources: [Deployment/epistemic-fabric/epistemic-ingest-github status: 'Failed']
- **Kustomization flux-system/hermes-agent** since 2026-09-16T19:42:56Z: Reconciliation in progress
- **Kustomization flux-system/hindsight** since 2026-09-16T19:43:28Z: ExternalSecret/hindsight/hindsight-env dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-secrets.io": failed to call webhook: Post "https://external-secrets-webhook.external-secrets.svc:443/validate-external-secrets-io-v1-externalsecret?timeout=15s": context deadline exceeded 
- **Kustomization flux-system/idp-agent** since 2026-09-16T19:42:56Z: Service/idp-agent/idp-agent-redis dry-run failed: admission webhook "validate.kyverno.svc-fail" denied the request:   resource Service/idp-agent/idp-agent-redis was blocked due to the following policies   require-catalogue-entity:   service-names-its-entity: 'validation error: Service idp-agent/idp-agent-redis serves a port but names no catalogue entity. Add the label backstage.io/kubernetes-id with the entity name from backstage/**/catalog-info.yaml, and a founder surface if a person opens it (docs/policy/every-interface-is-a-door.md). rule service-names-its-entity failed at path /metadata/labels/backstage.io/kubernetes-id/'  
- **Kustomization flux-system/otto-gateway** since 2026-09-16T19:43:48Z: ExternalSecret/otto-gateway/hermes-agent-env dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-secrets.io": failed to call webhook: Post "https://external-secrets-webhook.external-secrets.svc:443/validate-external-secrets-io-v1-externalsecret?timeout=15s": context deadline exceeded 
- **Kustomization flux-system/verification** since 2026-09-16T19:43:47Z: ExternalSecret/backstage/verdict-key-wall dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-secrets.io": failed to call webhook: Post "https://external-secrets-webhook.external-secrets.svc:443/validate-external-secrets-io-v1-externalsecret?timeout=15s": context deadline exceeded 
- **Kustomization flux-system/via-negativa** since 2026-09-16T19:43:52Z: health check failed after 317.618319ms: failed early due to stalled resources: [Deployment/via-negativa/via-negativa-rca status: 'Failed']

## Every row

| Kind | Namespace | Name | State | Applied revision | Since | Message |
|---|---|---|---|---|---|---|
| HelmRelease | commerce | lago | Not ready | 1.28.0 | 2026-09-16T19:33:00Z | Helm install failed for release commerce/lago with chart lago@1.28.0: create: failed to create: admission webhook "oke-resource-leak-protection.oke.com" denied  |
| HelmRelease | crossplane-system | crossplane | Not ready | 1.15.1 | 2026-09-16T17:08:05Z | Helm upgrade failed for release crossplane-system/crossplane with chart crossplane@1.15.1: create: failed to create: admission webhook "oke-resource-leak-protec |
| Kustomization | flux-system | commerce | Not ready | main@abea14d | 2026-09-16T19:32:56Z | Reconciliation in progress |
| Kustomization | flux-system | crossplane | Not ready | main@8d685ec | 2026-09-16T19:41:51Z | health check failed after 40.774086ms: failed early due to stalled resources: [HelmRelease/crossplane-system/crossplane status: 'Failed'] |
| Kustomization | flux-system | crossplane-providerconfig | Not ready | main@8d685ec | 2026-09-16T11:53:07Z | dependency 'flux-system/crossplane-providers' is not ready |
| Kustomization | flux-system | crossplane-providers | Not ready | main@8d685ec | 2026-09-16T11:53:06Z | dependency 'flux-system/crossplane' is not ready |
| Kustomization | flux-system | crossplane-storage-capability | Not ready | main@8d685ec | 2026-09-16T11:53:07Z | dependency 'flux-system/crossplane-providerconfig' is not ready |
| Kustomization | flux-system | epistemic-fabric | Not ready | main@a1421eb | 2026-09-16T19:42:49Z | health check failed after 86.289826ms: failed early due to stalled resources: [Deployment/epistemic-fabric/epistemic-ingest-github status: 'Failed'] |
| Kustomization | flux-system | hermes-agent | Not ready | main@a1421eb | 2026-09-16T19:42:56Z | Reconciliation in progress |
| Kustomization | flux-system | hindsight | Not ready | main@a1421eb | 2026-09-16T19:43:28Z | ExternalSecret/hindsight/hindsight-env dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-secrets |
| Kustomization | flux-system | idp-agent | Not ready | main@a1421eb | 2026-09-16T19:42:56Z | Service/idp-agent/idp-agent-redis dry-run failed: admission webhook "validate.kyverno.svc-fail" denied the request:   resource Service/idp-agent/idp-agent-redis |
| Kustomization | flux-system | otto-gateway | Not ready | main@a1421eb | 2026-09-16T19:43:48Z | ExternalSecret/otto-gateway/hermes-agent-env dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-s |
| Kustomization | flux-system | verification | Not ready | main@a1421eb | 2026-09-16T19:43:47Z | ExternalSecret/backstage/verdict-key-wall dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-secr |
| Kustomization | flux-system | via-negativa | Not ready | main@a1421eb | 2026-09-16T19:43:52Z | health check failed after 317.618319ms: failed early due to stalled resources: [Deployment/via-negativa/via-negativa-rca status: 'Failed'] |
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
| Kustomization | flux-system | agent-workforce | Ready | main@a1421eb | 2026-09-16T19:44:01Z |  |
| Kustomization | flux-system | alerts | Ready | main@a1421eb | 2026-09-16T19:43:30Z |  |
| Kustomization | flux-system | alerts-github | Ready | main@a1421eb | 2026-09-16T19:42:14Z |  |
| Kustomization | flux-system | alerts-secret | Ready | main@a1421eb | 2026-09-16T19:42:50Z |  |
| Kustomization | flux-system | autoscaler | Ready | main@a1421eb | 2026-09-16T19:42:46Z |  |
| Kustomization | flux-system | backstage | Ready | main@a1421eb | 2026-09-16T19:43:57Z |  |
| Kustomization | flux-system | backstage-namespace | Ready | main@a1421eb | 2026-09-16T19:40:35Z |  |
| Kustomization | flux-system | calico | Ready | main@a1421eb | 2026-09-16T19:41:34Z |  |
| Kustomization | flux-system | chaos | Ready | main@a1421eb | 2026-09-16T19:44:26Z |  |
| Kustomization | flux-system | chaos-mesh | Ready | main@a1421eb | 2026-09-16T19:42:03Z |  |
| Kustomization | flux-system | cluster-state | Ready | main@a1421eb | 2026-09-16T19:42:17Z |  |
| Kustomization | flux-system | commerce-data | Ready | main@a1421eb | 2026-09-16T19:42:29Z |  |
| Kustomization | flux-system | concierge | Ready | main@a1421eb | 2026-09-16T19:42:56Z |  |
| Kustomization | flux-system | cross-node-drill | Ready | main@a1421eb | 2026-09-16T19:41:13Z |  |
| Kustomization | flux-system | dagster | Ready | main@a1421eb | 2026-09-16T19:43:12Z |  |
| Kustomization | flux-system | dns | Ready | main@a1421eb | 2026-09-16T19:42:31Z |  |
| Kustomization | flux-system | drills | Ready | main@a1421eb | 2026-09-16T19:43:29Z |  |
| Kustomization | flux-system | edge | Ready | main@a1421eb | 2026-09-16T19:41:16Z |  |
| Kustomization | flux-system | estate-catalog | Ready | latest@sha256:a4e47f38e8b20c87a462d3669a | 2026-09-16T19:38:12Z |  |
| Kustomization | flux-system | estate-db | Ready | main@a1421eb | 2026-09-16T19:42:41Z |  |
| Kustomization | flux-system | estate-db-migrate | Ready | main@a1421eb | 2026-09-16T19:42:48Z |  |
| Kustomization | flux-system | estate-db-operator | Ready | main@a1421eb | 2026-09-16T19:40:43Z |  |
| Kustomization | flux-system | event-bus | Ready | main@a1421eb | 2026-09-16T19:41:18Z |  |
| Kustomization | flux-system | external-secrets | Ready | main@a1421eb | 2026-09-16T19:41:25Z |  |
| Kustomization | flux-system | feature-register | Ready | main@a1421eb | 2026-09-16T19:41:11Z |  |
| Kustomization | flux-system | flux-system | Ready | main@a1421eb | 2026-09-16T19:41:07Z |  |
| Kustomization | flux-system | flux-webhook | Ready | main@a1421eb | 2026-09-16T19:44:33Z |  |
| Kustomization | flux-system | gateway-api-crds | Ready | v1.5.1@e7677b7 | 2026-09-16T19:41:25Z |  |
| Kustomization | flux-system | guacamole | Ready | main@a1421eb | 2026-09-16T19:42:55Z |  |
| Kustomization | flux-system | gvisor-runtime | Ready | main@a1421eb | 2026-09-16T19:43:53Z |  |
| Kustomization | flux-system | healing | Ready | main@a1421eb | 2026-09-16T19:42:05Z |  |
| Kustomization | flux-system | healing-analyzer | Ready | main@a1421eb | 2026-09-16T19:43:49Z |  |
| Kustomization | flux-system | healing-k8sgpt | Ready | main@a1421eb | 2026-09-16T19:43:47Z |  |
| Kustomization | flux-system | healthchecks | Ready | main@a1421eb | 2026-09-16T19:43:59Z |  |
| Kustomization | flux-system | human-vault | Ready | main@a1421eb | 2026-09-16T19:42:39Z |  |
| Kustomization | flux-system | human-vault-bridge | Ready | main@a1421eb | 2026-09-16T19:43:00Z |  |
| Kustomization | flux-system | identity | Ready | main@a1421eb | 2026-09-16T19:41:56Z |  |
| Kustomization | flux-system | image-automation | Ready | main@a1421eb | 2026-09-16T19:42:52Z |  |
| Kustomization | flux-system | jit | Ready | main@a1421eb | 2026-09-16T19:41:40Z |  |
| Kustomization | flux-system | keda | Ready | main@a1421eb | 2026-09-16T19:42:01Z |  |
| Kustomization | flux-system | kyverno | Ready | main@a1421eb | 2026-09-16T19:41:00Z |  |
| Kustomization | flux-system | llm | Ready | main@a1421eb | 2026-09-16T19:42:52Z |  |
| Kustomization | flux-system | mcp | Ready | main@a1421eb | 2026-09-16T19:42:31Z |  |
| Kustomization | flux-system | metrics-server | Ready | main@a1421eb | 2026-09-16T19:41:57Z |  |
| Kustomization | flux-system | monitoring | Ready | main@a1421eb | 2026-09-16T19:43:02Z |  |
| Kustomization | flux-system | monitoring-rules | Ready | main@a1421eb | 2026-09-16T19:43:30Z |  |
| Kustomization | flux-system | nodesoftware-operator | Ready | main@a1421eb | 2026-09-16T19:43:50Z |  |
| Kustomization | flux-system | notify | Ready | main@a1421eb | 2026-09-16T19:42:59Z |  |
| Kustomization | flux-system | ns-fences | Ready | main@a1421eb | 2026-09-16T19:41:37Z |  |
| Kustomization | flux-system | observability | Ready | main@a1421eb | 2026-09-16T19:44:02Z |  |
| Kustomization | flux-system | observability-collector | Ready | main@a1421eb | 2026-09-16T19:41:24Z |  |
| Kustomization | flux-system | otto-golden | Ready | main@a1421eb | 2026-09-16T19:43:13Z |  |
| Kustomization | flux-system | otto-golden-secret | Ready | main@a1421eb | 2026-09-16T19:42:18Z |  |
| Kustomization | flux-system | priority-classes | Ready | main@a1421eb | 2026-09-16T19:41:26Z |  |
| Kustomization | flux-system | prospector | Ready | main@7453d76 | 2026-09-16T19:38:20Z |  |
| Kustomization | flux-system | prospector-platform | Ready | main@a1421eb | 2026-09-16T19:42:03Z |  |
| Kustomization | flux-system | rbac | Ready | main@a1421eb | 2026-09-16T19:41:06Z |  |
| Kustomization | flux-system | rbac-floor | Ready | main@a1421eb | 2026-09-16T19:40:36Z |  |
| Kustomization | flux-system | rbac-identity | Ready | main@a1421eb | 2026-09-16T19:40:51Z |  |
| Kustomization | flux-system | reloader | Ready | main@a1421eb | 2026-09-16T19:42:23Z |  |
| Kustomization | flux-system | research-engine | Ready | main@a1421eb | 2026-09-16T19:43:56Z |  |
| Kustomization | flux-system | robusta | Ready | main@a1421eb | 2026-09-16T19:42:49Z |  |
| Kustomization | flux-system | router-events | Ready | main@a1421eb | 2026-09-16T19:43:54Z |  |
| Kustomization | flux-system | sandbox-launch | Ready | main@a1421eb | 2026-09-16T19:41:21Z |  |
| Kustomization | flux-system | sandbox-live | Ready | sandbox/launch@4830a6e | 2026-09-16T19:44:56Z |  |
| Kustomization | flux-system | scheduling | Ready | main@a1421eb | 2026-09-16T19:41:31Z |  |
| Kustomization | flux-system | science | Ready | main@a1421eb | 2026-09-16T19:44:32Z |  |
| Kustomization | flux-system | searxng | Ready | main@a1421eb | 2026-09-16T19:40:56Z |  |
| Kustomization | flux-system | secret-store | Ready | main@a1421eb | 2026-09-16T19:42:12Z |  |
| Kustomization | flux-system | spire | Ready | main@a1421eb | 2026-09-16T19:42:19Z |  |
| Kustomization | flux-system | staging | Ready | main@a1421eb | 2026-09-16T19:41:32Z |  |
| Kustomization | flux-system | tailscale | Ready | main@a1421eb | 2026-09-16T19:42:38Z |  |
| Kustomization | flux-system | temporal | Ready | main@a1421eb | 2026-09-16T19:42:55Z |  |
| Kustomization | flux-system | trivy | Ready | main@a1421eb | 2026-09-16T19:40:52Z |  |
| Kustomization | flux-system | weave-gitops | Ready | main@a1421eb | 2026-09-16T19:42:46Z |  |
