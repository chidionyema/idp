# Flux: what is applied

Read from the cluster receipt taken at 2026-09-17T07:00:56Z. Every Kustomization and HelmRelease, with the revision Flux last applied. **Suspended** is a switch somebody turned off on purpose (temporal, commerce, commerce-data, event-bus), not a defect; **Unknown** is a row Flux has never graded.

**120 objects: 102 ready, 17 not ready, 0 unknown, 1 suspended.**

## Not ready right now

- **HelmRelease commerce/lago** since 2026-09-17T06:54:40Z: Helm install failed for release commerce/lago with chart lago@1.28.0: create: failed to create: admission webhook "oke-resource-leak-protection.oke.com" denied the request: OKE resource leak protection rejected the request. Cluster has 2650 secrets and the limit is 2000. See https://docs.oracle.com/iaas/Content/ContEng/Tasks/contengprotectingclustersfromresourceleaks.htm for details.
- **HelmRelease crossplane-system/crossplane** since 2026-09-16T17:08:05Z: Helm upgrade failed for release crossplane-system/crossplane with chart crossplane@1.15.1: create: failed to create: admission webhook "oke-resource-leak-protection.oke.com" denied the request: OKE resource leak protection rejected the request. Cluster has 2650 secrets and the limit is 2000. See https://docs.oracle.com/iaas/Content/ContEng/Tasks/contengprotectingclustersfromresourceleaks.htm for details.
- **Kustomization flux-system/autoscaler** since 2026-09-17T06:58:40Z: ExternalSecret/kube-system/oke-autoscaler dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-secrets.io": failed to call webhook: Post "https://external-secrets-webhook.external-secrets.svc:443/validate-external-secrets-io-v1-externalsecret?timeout=15s": context deadline exceeded 
- **Kustomization flux-system/commerce** since 2026-09-17T06:54:34Z: Reconciliation in progress
- **Kustomization flux-system/crossplane** since 2026-09-17T06:57:03Z: health check failed after 40.851368ms: failed early due to stalled resources: [HelmRelease/crossplane-system/crossplane status: 'Failed']
- **Kustomization flux-system/crossplane-providerconfig** since 2026-09-16T11:53:07Z: dependency 'flux-system/crossplane-providers' is not ready
- **Kustomization flux-system/crossplane-providers** since 2026-09-16T11:53:06Z: dependency 'flux-system/crossplane' is not ready
- **Kustomization flux-system/crossplane-storage-capability** since 2026-09-16T11:53:07Z: dependency 'flux-system/crossplane-providerconfig' is not ready
- **Kustomization flux-system/epistemic-fabric** since 2026-09-17T06:58:42Z: health check failed after 67.396938ms: failed early due to stalled resources: [Deployment/epistemic-fabric/epistemic-ingest-github status: 'Failed']
- **Kustomization flux-system/guacamole** since 2026-09-17T07:00:18Z: Reconciliation in progress
- **Kustomization flux-system/hermes-agent** since 2026-09-17T06:58:48Z: Reconciliation in progress
- **Kustomization flux-system/human-vault-bridge** since 2026-09-17T06:43:24Z: dependency 'flux-system/human-vault' is not ready
- **Kustomization flux-system/idp-agent** since 2026-09-17T06:58:53Z: Service/idp-agent/idp-agent-redis dry-run failed: admission webhook "validate.kyverno.svc-fail" denied the request:   resource Service/idp-agent/idp-agent-redis was blocked due to the following policies   require-catalogue-entity:   service-names-its-entity: 'validation error: Service idp-agent/idp-agent-redis serves a port but names no catalogue entity. Add the label backstage.io/kubernetes-id with the entity name from backstage/**/catalog-info.yaml, and a founder surface if a person opens it (docs/policy/every-interface-is-a-door.md). rule service-names-its-entity failed at path /metadata/labels/backstage.io/kubernetes-id/'  
- **Kustomization flux-system/notify** since 2026-09-17T06:58:36Z: ExternalSecret/notify/notify-channels dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-secrets.io": failed to call webhook: Post "https://external-secrets-webhook.external-secrets.svc:443/validate-external-secrets-io-v1-externalsecret?timeout=15s": context deadline exceeded 
- **Kustomization flux-system/otto-gateway** since 2026-09-17T06:58:49Z: Reconciliation in progress
- **Kustomization flux-system/otto-golden** since 2026-09-17T06:58:46Z: health check failed after 389.764432ms: failed early due to stalled resources: [Deployment/otto-golden/otto-golden status: 'Failed']
- **Kustomization flux-system/via-negativa** since 2026-09-17T06:49:58Z: health check failed after 260.9657ms: failed early due to stalled resources: [Deployment/via-negativa/via-negativa-rca status: 'Failed']

## Every row

| Kind | Namespace | Name | State | Applied revision | Since | Message |
|---|---|---|---|---|---|---|
| HelmRelease | commerce | lago | Not ready | 1.28.0 | 2026-09-17T06:54:40Z | Helm install failed for release commerce/lago with chart lago@1.28.0: create: failed to create: admission webhook "oke-resource-leak-protection.oke.com" denied  |
| HelmRelease | crossplane-system | crossplane | Not ready | 1.15.1 | 2026-09-16T17:08:05Z | Helm upgrade failed for release crossplane-system/crossplane with chart crossplane@1.15.1: create: failed to create: admission webhook "oke-resource-leak-protec |
| Kustomization | flux-system | autoscaler | Not ready | main@f6429f8 | 2026-09-17T06:58:40Z | ExternalSecret/kube-system/oke-autoscaler dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-secr |
| Kustomization | flux-system | commerce | Not ready | main@abea14d | 2026-09-17T06:54:34Z | Reconciliation in progress |
| Kustomization | flux-system | crossplane | Not ready | main@8d685ec | 2026-09-17T06:57:03Z | health check failed after 40.851368ms: failed early due to stalled resources: [HelmRelease/crossplane-system/crossplane status: 'Failed'] |
| Kustomization | flux-system | crossplane-providerconfig | Not ready | main@8d685ec | 2026-09-16T11:53:07Z | dependency 'flux-system/crossplane-providers' is not ready |
| Kustomization | flux-system | crossplane-providers | Not ready | main@8d685ec | 2026-09-16T11:53:06Z | dependency 'flux-system/crossplane' is not ready |
| Kustomization | flux-system | crossplane-storage-capability | Not ready | main@8d685ec | 2026-09-16T11:53:07Z | dependency 'flux-system/crossplane-providerconfig' is not ready |
| Kustomization | flux-system | epistemic-fabric | Not ready | main@f6429f8 | 2026-09-17T06:58:42Z | health check failed after 67.396938ms: failed early due to stalled resources: [Deployment/epistemic-fabric/epistemic-ingest-github status: 'Failed'] |
| Kustomization | flux-system | guacamole | Not ready | main@f6429f8 | 2026-09-17T07:00:18Z | Reconciliation in progress |
| Kustomization | flux-system | hermes-agent | Not ready | main@f6429f8 | 2026-09-17T06:58:48Z | Reconciliation in progress |
| Kustomization | flux-system | human-vault-bridge | Not ready | main@37a1cd8 | 2026-09-17T06:43:24Z | dependency 'flux-system/human-vault' is not ready |
| Kustomization | flux-system | idp-agent | Not ready | main@f6429f8 | 2026-09-17T06:58:53Z | Service/idp-agent/idp-agent-redis dry-run failed: admission webhook "validate.kyverno.svc-fail" denied the request:   resource Service/idp-agent/idp-agent-redis |
| Kustomization | flux-system | notify | Not ready | main@f6429f8 | 2026-09-17T06:58:36Z | ExternalSecret/notify/notify-channels dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-secrets. |
| Kustomization | flux-system | otto-gateway | Not ready | main@cd9eb71 | 2026-09-17T06:58:49Z | Reconciliation in progress |
| Kustomization | flux-system | otto-golden | Not ready | main@cd9eb71 | 2026-09-17T06:58:46Z | health check failed after 389.764432ms: failed early due to stalled resources: [Deployment/otto-golden/otto-golden status: 'Failed'] |
| Kustomization | flux-system | via-negativa | Not ready | main@f6429f8 | 2026-09-17T06:49:58Z | health check failed after 260.9657ms: failed early due to stalled resources: [Deployment/via-negativa/via-negativa-rca status: 'Failed'] |
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
| Kustomization | flux-system | agent-workforce | Ready | main@f6429f8 | 2026-09-17T07:00:17Z |  |
| Kustomization | flux-system | alerts | Ready | main@f6429f8 | 2026-09-17T07:00:04Z |  |
| Kustomization | flux-system | alerts-github | Ready | main@f6429f8 | 2026-09-17T06:57:59Z |  |
| Kustomization | flux-system | alerts-secret | Ready | main@f6429f8 | 2026-09-17T06:58:51Z |  |
| Kustomization | flux-system | backstage | Ready | main@f6429f8 | 2026-09-17T06:50:41Z |  |
| Kustomization | flux-system | backstage-namespace | Ready | main@f6429f8 | 2026-09-17T06:55:56Z |  |
| Kustomization | flux-system | calico | Ready | main@f6429f8 | 2026-09-17T06:56:40Z |  |
| Kustomization | flux-system | chaos | Ready | main@f6429f8 | 2026-09-17T06:50:57Z |  |
| Kustomization | flux-system | chaos-mesh | Ready | main@f6429f8 | 2026-09-17T06:56:48Z |  |
| Kustomization | flux-system | cluster-state | Ready | main@f6429f8 | 2026-09-17T06:57:52Z |  |
| Kustomization | flux-system | commerce-data | Ready | main@f6429f8 | 2026-09-17T06:58:48Z |  |
| Kustomization | flux-system | concierge | Ready | main@f6429f8 | 2026-09-17T06:58:16Z |  |
| Kustomization | flux-system | cross-node-drill | Ready | main@f6429f8 | 2026-09-17T06:56:02Z |  |
| Kustomization | flux-system | dagster | Ready | main@f6429f8 | 2026-09-17T06:59:47Z |  |
| Kustomization | flux-system | dns | Ready | main@f6429f8 | 2026-09-17T06:58:46Z |  |
| Kustomization | flux-system | drills | Ready | main@f6429f8 | 2026-09-17T06:58:41Z |  |
| Kustomization | flux-system | edge | Ready | main@f6429f8 | 2026-09-17T06:56:48Z |  |
| Kustomization | flux-system | estate-catalog | Ready | latest@sha256:a04252834a75d463fe8b13d320 | 2026-09-17T06:58:01Z |  |
| Kustomization | flux-system | estate-db | Ready | main@f6429f8 | 2026-09-17T06:57:47Z |  |
| Kustomization | flux-system | estate-db-migrate | Ready | main@f6429f8 | 2026-09-17T06:59:58Z |  |
| Kustomization | flux-system | estate-db-operator | Ready | main@f6429f8 | 2026-09-17T06:56:51Z |  |
| Kustomization | flux-system | event-bus | Ready | main@f6429f8 | 2026-09-17T06:56:21Z |  |
| Kustomization | flux-system | external-secrets | Ready | main@f6429f8 | 2026-09-17T06:57:18Z |  |
| Kustomization | flux-system | feature-register | Ready | main@f6429f8 | 2026-09-17T06:56:14Z |  |
| Kustomization | flux-system | flux-system | Ready | main@f6429f8 | 2026-09-17T06:56:20Z |  |
| Kustomization | flux-system | flux-webhook | Ready | main@f6429f8 | 2026-09-17T07:00:07Z |  |
| Kustomization | flux-system | gateway-api-crds | Ready | v1.5.1@e7677b7 | 2026-09-17T06:56:15Z |  |
| Kustomization | flux-system | gvisor-runtime | Ready | main@f6429f8 | 2026-09-17T06:59:37Z |  |
| Kustomization | flux-system | healing | Ready | main@f6429f8 | 2026-09-17T06:57:21Z |  |
| Kustomization | flux-system | healing-analyzer | Ready | main@f6429f8 | 2026-09-17T06:50:09Z |  |
| Kustomization | flux-system | healing-k8sgpt | Ready | main@f6429f8 | 2026-09-17T06:49:59Z |  |
| Kustomization | flux-system | healthchecks | Ready | main@f6429f8 | 2026-09-17T06:59:18Z |  |
| Kustomization | flux-system | hindsight | Ready | main@f6429f8 | 2026-09-17T07:00:02Z |  |
| Kustomization | flux-system | human-vault | Ready | main@f6429f8 | 2026-09-17T06:59:30Z |  |
| Kustomization | flux-system | identity | Ready | main@f6429f8 | 2026-09-17T06:59:12Z |  |
| Kustomization | flux-system | image-automation | Ready | main@f6429f8 | 2026-09-17T06:58:39Z |  |
| Kustomization | flux-system | jit | Ready | main@f6429f8 | 2026-09-17T06:57:10Z |  |
| Kustomization | flux-system | keda | Ready | main@f6429f8 | 2026-09-17T06:57:15Z |  |
| Kustomization | flux-system | kyverno | Ready | main@f6429f8 | 2026-09-17T06:56:52Z |  |
| Kustomization | flux-system | llm | Ready | main@f6429f8 | 2026-09-17T06:59:22Z |  |
| Kustomization | flux-system | mcp | Ready | main@f6429f8 | 2026-09-17T06:58:58Z |  |
| Kustomization | flux-system | metrics-server | Ready | main@f6429f8 | 2026-09-17T06:56:51Z |  |
| Kustomization | flux-system | monitoring | Ready | main@f6429f8 | 2026-09-17T06:59:36Z |  |
| Kustomization | flux-system | monitoring-rules | Ready | main@f6429f8 | 2026-09-17T06:58:44Z |  |
| Kustomization | flux-system | nodesoftware-operator | Ready | main@f6429f8 | 2026-09-17T06:59:25Z |  |
| Kustomization | flux-system | ns-fences | Ready | main@f6429f8 | 2026-09-17T06:56:48Z |  |
| Kustomization | flux-system | observability | Ready | main@f6429f8 | 2026-09-17T06:49:36Z |  |
| Kustomization | flux-system | observability-collector | Ready | main@f6429f8 | 2026-09-17T06:56:55Z |  |
| Kustomization | flux-system | otto-golden-secret | Ready | main@f6429f8 | 2026-09-17T06:58:08Z |  |
| Kustomization | flux-system | priority-classes | Ready | main@f6429f8 | 2026-09-17T06:56:14Z |  |
| Kustomization | flux-system | prospector | Ready | main@7453d76 | 2026-09-17T06:55:45Z |  |
| Kustomization | flux-system | prospector-platform | Ready | main@f6429f8 | 2026-09-17T06:57:23Z |  |
| Kustomization | flux-system | rbac | Ready | main@f6429f8 | 2026-09-17T06:56:05Z |  |
| Kustomization | flux-system | rbac-floor | Ready | main@f6429f8 | 2026-09-17T06:56:16Z |  |
| Kustomization | flux-system | rbac-identity | Ready | main@f6429f8 | 2026-09-17T06:56:39Z |  |
| Kustomization | flux-system | reloader | Ready | main@f6429f8 | 2026-09-17T06:57:53Z |  |
| Kustomization | flux-system | research-engine | Ready | main@f6429f8 | 2026-09-17T06:50:02Z |  |
| Kustomization | flux-system | robusta | Ready | main@f6429f8 | 2026-09-17T06:59:03Z |  |
| Kustomization | flux-system | router-events | Ready | main@f6429f8 | 2026-09-17T06:50:00Z |  |
| Kustomization | flux-system | sandbox-launch | Ready | main@f6429f8 | 2026-09-17T06:57:22Z |  |
| Kustomization | flux-system | sandbox-live | Ready | sandbox/launch@4830a6e | 2026-09-17T06:59:41Z |  |
| Kustomization | flux-system | scheduling | Ready | main@f6429f8 | 2026-09-17T06:56:41Z |  |
| Kustomization | flux-system | science | Ready | main@f6429f8 | 2026-09-17T07:00:10Z |  |
| Kustomization | flux-system | searxng | Ready | main@f6429f8 | 2026-09-17T06:56:16Z |  |
| Kustomization | flux-system | secret-store | Ready | main@f6429f8 | 2026-09-17T06:58:10Z |  |
| Kustomization | flux-system | spire | Ready | main@f6429f8 | 2026-09-17T06:57:21Z |  |
| Kustomization | flux-system | staging | Ready | main@f6429f8 | 2026-09-17T06:56:30Z |  |
| Kustomization | flux-system | tailscale | Ready | main@f6429f8 | 2026-09-17T06:58:39Z |  |
| Kustomization | flux-system | temporal | Ready | main@f6429f8 | 2026-09-17T06:59:41Z |  |
| Kustomization | flux-system | trivy | Ready | main@f6429f8 | 2026-09-17T06:56:10Z |  |
| Kustomization | flux-system | verification | Ready | main@f6429f8 | 2026-09-17T06:58:14Z |  |
| Kustomization | flux-system | weave-gitops | Ready | main@f6429f8 | 2026-09-17T06:58:41Z |  |
