# Flux: what is applied

Read from the cluster receipt taken at 2026-09-17T07:15:16Z. Every Kustomization and HelmRelease, with the revision Flux last applied. **Suspended** is a switch somebody turned off on purpose (temporal, commerce, commerce-data, event-bus), not a defect; **Unknown** is a row Flux has never graded.

**120 objects: 103 ready, 16 not ready, 0 unknown, 1 suspended.**

## Not ready right now

- **HelmRelease commerce/lago** since 2026-09-17T07:09:54Z: Helm install failed for release commerce/lago with chart lago@1.28.0: create: failed to create: admission webhook "oke-resource-leak-protection.oke.com" denied the request: OKE resource leak protection rejected the request. Cluster has 2650 secrets and the limit is 2000. See https://docs.oracle.com/iaas/Content/ContEng/Tasks/contengprotectingclustersfromresourceleaks.htm for details.
- **HelmRelease crossplane-system/crossplane** since 2026-09-16T17:08:05Z: Helm upgrade failed for release crossplane-system/crossplane with chart crossplane@1.15.1: create: failed to create: admission webhook "oke-resource-leak-protection.oke.com" denied the request: OKE resource leak protection rejected the request. Cluster has 2650 secrets and the limit is 2000. See https://docs.oracle.com/iaas/Content/ContEng/Tasks/contengprotectingclustersfromresourceleaks.htm for details.
- **Kustomization flux-system/alerts-secret** since 2026-09-17T07:14:08Z: ExternalSecret/flux-system/flux-telegram dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-secrets.io": failed to call webhook: Post "https://external-secrets-webhook.external-secrets.svc:443/validate-external-secrets-io-v1-externalsecret?timeout=15s": context deadline exceeded 
- **Kustomization flux-system/chaos** since 2026-09-17T07:05:45Z: dependency 'flux-system/backstage' is not ready
- **Kustomization flux-system/chaos-mesh** since 2026-09-17T07:15:09Z: Reconciliation in progress
- **Kustomization flux-system/commerce** since 2026-09-17T07:09:36Z: Reconciliation in progress
- **Kustomization flux-system/crossplane** since 2026-09-17T07:15:06Z: health check failed after 55.539169ms: failed early due to stalled resources: [HelmRelease/crossplane-system/crossplane status: 'Failed']
- **Kustomization flux-system/crossplane-providerconfig** since 2026-09-16T11:53:07Z: dependency 'flux-system/crossplane-providers' is not ready
- **Kustomization flux-system/crossplane-providers** since 2026-09-16T11:53:06Z: dependency 'flux-system/crossplane' is not ready
- **Kustomization flux-system/crossplane-storage-capability** since 2026-09-16T11:53:07Z: dependency 'flux-system/crossplane-providerconfig' is not ready
- **Kustomization flux-system/epistemic-fabric** since 2026-09-17T07:14:59Z: health check failed after 96.645619ms: failed early due to stalled resources: [Deployment/epistemic-fabric/epistemic-ingest-github status: 'Failed']
- **Kustomization flux-system/idp-agent** since 2026-09-17T07:14:26Z: Service/idp-agent/idp-agent-redis dry-run failed: admission webhook "validate.kyverno.svc-fail" denied the request:   resource Service/idp-agent/idp-agent-redis was blocked due to the following policies   require-catalogue-entity:   service-names-its-entity: 'validation error: Service idp-agent/idp-agent-redis serves a port but names no catalogue entity. Add the label backstage.io/kubernetes-id with the entity name from backstage/**/catalog-info.yaml, and a founder surface if a person opens it (docs/policy/every-interface-is-a-door.md). rule service-names-its-entity failed at path /metadata/labels/backstage.io/kubernetes-id/'  
- **Kustomization flux-system/monitoring-rules** since 2026-09-17T07:15:09Z: Reconciliation in progress
- **Kustomization flux-system/otto-gateway** since 2026-09-17T07:15:04Z: health check failed after 640.777983ms: failed early due to stalled resources: [Deployment/otto-gateway/otto-gateway status: 'Failed']
- **Kustomization flux-system/otto-golden** since 2026-09-17T07:15:00Z: health check failed after 463.714563ms: failed early due to stalled resources: [Deployment/otto-golden/otto-golden status: 'Failed']
- **Kustomization flux-system/via-negativa** since 2026-09-17T07:05:42Z: health check failed after 413.768695ms: failed early due to stalled resources: [Deployment/via-negativa/via-negativa-rca status: 'Failed']

## Every row

| Kind | Namespace | Name | State | Applied revision | Since | Message |
|---|---|---|---|---|---|---|
| HelmRelease | commerce | lago | Not ready | 1.28.0 | 2026-09-17T07:09:54Z | Helm install failed for release commerce/lago with chart lago@1.28.0: create: failed to create: admission webhook "oke-resource-leak-protection.oke.com" denied  |
| HelmRelease | crossplane-system | crossplane | Not ready | 1.15.1 | 2026-09-16T17:08:05Z | Helm upgrade failed for release crossplane-system/crossplane with chart crossplane@1.15.1: create: failed to create: admission webhook "oke-resource-leak-protec |
| Kustomization | flux-system | alerts-secret | Not ready | main@820a827 | 2026-09-17T07:14:08Z | ExternalSecret/flux-system/flux-telegram dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-secre |
| Kustomization | flux-system | chaos | Not ready | main@f6429f8 | 2026-09-17T07:05:45Z | dependency 'flux-system/backstage' is not ready |
| Kustomization | flux-system | chaos-mesh | Not ready | main@820a827 | 2026-09-17T07:15:09Z | Reconciliation in progress |
| Kustomization | flux-system | commerce | Not ready | main@abea14d | 2026-09-17T07:09:36Z | Reconciliation in progress |
| Kustomization | flux-system | crossplane | Not ready | main@8d685ec | 2026-09-17T07:15:06Z | health check failed after 55.539169ms: failed early due to stalled resources: [HelmRelease/crossplane-system/crossplane status: 'Failed'] |
| Kustomization | flux-system | crossplane-providerconfig | Not ready | main@8d685ec | 2026-09-16T11:53:07Z | dependency 'flux-system/crossplane-providers' is not ready |
| Kustomization | flux-system | crossplane-providers | Not ready | main@8d685ec | 2026-09-16T11:53:06Z | dependency 'flux-system/crossplane' is not ready |
| Kustomization | flux-system | crossplane-storage-capability | Not ready | main@8d685ec | 2026-09-16T11:53:07Z | dependency 'flux-system/crossplane-providerconfig' is not ready |
| Kustomization | flux-system | epistemic-fabric | Not ready | main@820a827 | 2026-09-17T07:14:59Z | health check failed after 96.645619ms: failed early due to stalled resources: [Deployment/epistemic-fabric/epistemic-ingest-github status: 'Failed'] |
| Kustomization | flux-system | idp-agent | Not ready | main@820a827 | 2026-09-17T07:14:26Z | Service/idp-agent/idp-agent-redis dry-run failed: admission webhook "validate.kyverno.svc-fail" denied the request:   resource Service/idp-agent/idp-agent-redis |
| Kustomization | flux-system | monitoring-rules | Not ready | main@820a827 | 2026-09-17T07:15:09Z | Reconciliation in progress |
| Kustomization | flux-system | otto-gateway | Not ready | main@cd9eb71 | 2026-09-17T07:15:04Z | health check failed after 640.777983ms: failed early due to stalled resources: [Deployment/otto-gateway/otto-gateway status: 'Failed'] |
| Kustomization | flux-system | otto-golden | Not ready | main@cd9eb71 | 2026-09-17T07:15:00Z | health check failed after 463.714563ms: failed early due to stalled resources: [Deployment/otto-golden/otto-golden status: 'Failed'] |
| Kustomization | flux-system | via-negativa | Not ready | main@820a827 | 2026-09-17T07:05:42Z | health check failed after 413.768695ms: failed early due to stalled resources: [Deployment/via-negativa/via-negativa-rca status: 'Failed'] |
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
| Kustomization | flux-system | agent-workforce | Ready | main@820a827 | 2026-09-17T07:14:37Z |  |
| Kustomization | flux-system | alerts | Ready | main@820a827 | 2026-09-17T07:13:22Z |  |
| Kustomization | flux-system | alerts-github | Ready | main@820a827 | 2026-09-17T07:14:24Z |  |
| Kustomization | flux-system | autoscaler | Ready | main@820a827 | 2026-09-17T07:13:57Z |  |
| Kustomization | flux-system | backstage | Ready | main@820a827 | 2026-09-17T07:14:58Z |  |
| Kustomization | flux-system | backstage-namespace | Ready | main@820a827 | 2026-09-17T07:11:34Z |  |
| Kustomization | flux-system | calico | Ready | main@820a827 | 2026-09-17T07:12:18Z |  |
| Kustomization | flux-system | cluster-state | Ready | main@820a827 | 2026-09-17T07:13:52Z |  |
| Kustomization | flux-system | commerce-data | Ready | main@820a827 | 2026-09-17T07:05:02Z |  |
| Kustomization | flux-system | concierge | Ready | main@820a827 | 2026-09-17T07:13:32Z |  |
| Kustomization | flux-system | cross-node-drill | Ready | main@820a827 | 2026-09-17T07:11:22Z |  |
| Kustomization | flux-system | dagster | Ready | main@820a827 | 2026-09-17T07:05:34Z |  |
| Kustomization | flux-system | dns | Ready | main@820a827 | 2026-09-17T07:14:08Z |  |
| Kustomization | flux-system | drills | Ready | main@820a827 | 2026-09-17T07:14:55Z |  |
| Kustomization | flux-system | edge | Ready | main@820a827 | 2026-09-17T07:13:28Z |  |
| Kustomization | flux-system | estate-catalog | Ready | latest@sha256:a04252834a75d463fe8b13d320 | 2026-09-17T07:07:32Z |  |
| Kustomization | flux-system | estate-db | Ready | main@820a827 | 2026-09-17T07:04:48Z |  |
| Kustomization | flux-system | estate-db-migrate | Ready | main@820a827 | 2026-09-17T07:05:08Z |  |
| Kustomization | flux-system | estate-db-operator | Ready | main@820a827 | 2026-09-17T07:12:47Z |  |
| Kustomization | flux-system | event-bus | Ready | main@820a827 | 2026-09-17T07:12:29Z |  |
| Kustomization | flux-system | external-secrets | Ready | main@820a827 | 2026-09-17T07:13:10Z |  |
| Kustomization | flux-system | feature-register | Ready | main@820a827 | 2026-09-17T07:12:16Z |  |
| Kustomization | flux-system | flux-system | Ready | main@820a827 | 2026-09-17T07:11:50Z |  |
| Kustomization | flux-system | flux-webhook | Ready | main@820a827 | 2026-09-17T07:14:02Z |  |
| Kustomization | flux-system | gateway-api-crds | Ready | v1.5.1@e7677b7 | 2026-09-17T07:11:37Z |  |
| Kustomization | flux-system | guacamole | Ready | main@820a827 | 2026-09-17T07:05:40Z |  |
| Kustomization | flux-system | gvisor-runtime | Ready | main@820a827 | 2026-09-17T07:14:28Z |  |
| Kustomization | flux-system | healing | Ready | main@820a827 | 2026-09-17T07:14:23Z |  |
| Kustomization | flux-system | healing-analyzer | Ready | main@820a827 | 2026-09-17T07:05:45Z |  |
| Kustomization | flux-system | healing-k8sgpt | Ready | main@820a827 | 2026-09-17T07:05:43Z |  |
| Kustomization | flux-system | healthchecks | Ready | main@820a827 | 2026-09-17T07:05:34Z |  |
| Kustomization | flux-system | hermes-agent | Ready | main@820a827 | 2026-09-17T07:14:56Z |  |
| Kustomization | flux-system | hindsight | Ready | main@820a827 | 2026-09-17T07:05:41Z |  |
| Kustomization | flux-system | human-vault | Ready | main@820a827 | 2026-09-17T07:14:01Z |  |
| Kustomization | flux-system | human-vault-bridge | Ready | main@820a827 | 2026-09-17T07:13:42Z |  |
| Kustomization | flux-system | identity | Ready | main@820a827 | 2026-09-17T07:13:27Z |  |
| Kustomization | flux-system | image-automation | Ready | main@820a827 | 2026-09-17T07:13:52Z |  |
| Kustomization | flux-system | jit | Ready | main@820a827 | 2026-09-17T07:12:31Z |  |
| Kustomization | flux-system | keda | Ready | main@820a827 | 2026-09-17T07:14:10Z |  |
| Kustomization | flux-system | kyverno | Ready | main@820a827 | 2026-09-17T07:12:52Z |  |
| Kustomization | flux-system | llm | Ready | main@820a827 | 2026-09-17T07:05:26Z |  |
| Kustomization | flux-system | mcp | Ready | main@820a827 | 2026-09-17T07:14:28Z |  |
| Kustomization | flux-system | metrics-server | Ready | main@820a827 | 2026-09-17T07:05:06Z |  |
| Kustomization | flux-system | monitoring | Ready | main@820a827 | 2026-09-17T07:14:04Z |  |
| Kustomization | flux-system | nodesoftware-operator | Ready | main@820a827 | 2026-09-17T07:13:59Z |  |
| Kustomization | flux-system | notify | Ready | main@820a827 | 2026-09-17T07:04:53Z |  |
| Kustomization | flux-system | ns-fences | Ready | main@820a827 | 2026-09-17T07:12:56Z |  |
| Kustomization | flux-system | observability | Ready | main@820a827 | 2026-09-17T07:05:38Z |  |
| Kustomization | flux-system | observability-collector | Ready | main@820a827 | 2026-09-17T07:13:36Z |  |
| Kustomization | flux-system | otto-golden-secret | Ready | main@820a827 | 2026-09-17T07:14:42Z |  |
| Kustomization | flux-system | priority-classes | Ready | main@820a827 | 2026-09-17T07:11:59Z |  |
| Kustomization | flux-system | prospector | Ready | main@7453d76 | 2026-09-17T07:05:52Z |  |
| Kustomization | flux-system | prospector-platform | Ready | main@820a827 | 2026-09-17T07:12:41Z |  |
| Kustomization | flux-system | rbac | Ready | main@820a827 | 2026-09-17T07:12:25Z |  |
| Kustomization | flux-system | rbac-floor | Ready | main@820a827 | 2026-09-17T07:11:46Z |  |
| Kustomization | flux-system | rbac-identity | Ready | main@820a827 | 2026-09-17T07:12:27Z |  |
| Kustomization | flux-system | reloader | Ready | main@820a827 | 2026-09-17T07:14:15Z |  |
| Kustomization | flux-system | research-engine | Ready | main@820a827 | 2026-09-17T07:05:45Z |  |
| Kustomization | flux-system | robusta | Ready | main@820a827 | 2026-09-17T07:13:18Z |  |
| Kustomization | flux-system | router-events | Ready | main@820a827 | 2026-09-17T07:05:43Z |  |
| Kustomization | flux-system | sandbox-launch | Ready | main@820a827 | 2026-09-17T07:13:08Z |  |
| Kustomization | flux-system | sandbox-live | Ready | sandbox/launch@4830a6e | 2026-09-17T07:15:07Z |  |
| Kustomization | flux-system | scheduling | Ready | main@820a827 | 2026-09-17T07:14:17Z |  |
| Kustomization | flux-system | science | Ready | main@820a827 | 2026-09-17T07:06:06Z |  |
| Kustomization | flux-system | searxng | Ready | main@820a827 | 2026-09-17T07:12:15Z |  |
| Kustomization | flux-system | secret-store | Ready | main@820a827 | 2026-09-17T07:13:27Z |  |
| Kustomization | flux-system | spire | Ready | main@820a827 | 2026-09-17T07:13:39Z |  |
| Kustomization | flux-system | staging | Ready | main@820a827 | 2026-09-17T07:12:25Z |  |
| Kustomization | flux-system | tailscale | Ready | main@820a827 | 2026-09-17T07:13:07Z |  |
| Kustomization | flux-system | temporal | Ready | main@820a827 | 2026-09-17T07:14:09Z |  |
| Kustomization | flux-system | trivy | Ready | main@820a827 | 2026-09-17T07:11:44Z |  |
| Kustomization | flux-system | verification | Ready | main@820a827 | 2026-09-17T07:13:11Z |  |
| Kustomization | flux-system | weave-gitops | Ready | main@820a827 | 2026-09-17T07:04:50Z |  |
