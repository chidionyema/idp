# Flux: what is applied

Read from the cluster receipt taken at 2026-09-19T11:45:18Z. Every Kustomization and HelmRelease, with the revision Flux last applied. **Suspended** is a switch somebody turned off on purpose (temporal, commerce, commerce-data, event-bus), not a defect; **Unknown** is a row Flux has never graded.

**121 objects: 80 ready, 40 not ready, 0 unknown, 1 suspended.**

## Not ready right now

- **HelmRelease commerce/lago** since 2026-09-18T21:16:37Z: Could not determine release state: unable to determine state for release with status 'uninstalling'
- **HelmRelease crossplane-system/crossplane** since 2026-09-16T17:08:05Z: Helm upgrade failed for release crossplane-system/crossplane with chart crossplane@1.15.1: create: failed to create: admission webhook "oke-resource-leak-protection.oke.com" denied the request: OKE resource leak protection rejected the request. Cluster has 2650 secrets and the limit is 2000. See https://docs.oracle.com/iaas/Content/ContEng/Tasks/contengprotectingclustersfromresourceleaks.htm for details.
- **Kustomization flux-system/alerts-github** since 2026-09-19T11:44:50Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/alerts-secret** since 2026-09-19T11:43:29Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/backstage** since 2026-09-19T11:40:19Z: health check failed after 528.807119ms: failed early due to stalled resources: [Deployment/backstage/catalogue status: 'Failed']
- **Kustomization flux-system/calico** since 2026-09-19T11:44:13Z: GlobalNetworkPolicy/deny-direct-ai-vendor-egress dry-run failed: no matches for kind "GlobalNetworkPolicy" in version "projectcalico.org/v3" 
- **Kustomization flux-system/chaos** since 2026-09-19T11:43:46Z: dependency 'flux-system/monitoring' is not ready
- **Kustomization flux-system/commerce** since 2026-09-19T11:33:22Z: Reconciliation in progress
- **Kustomization flux-system/concierge** since 2026-09-19T11:44:10Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/crossplane** since 2026-09-19T11:41:36Z: health check failed after 96.426618ms: failed early due to stalled resources: [HelmRelease/crossplane-system/crossplane status: 'Failed']
- **Kustomization flux-system/crossplane-providerconfig** since 2026-09-16T11:53:07Z: dependency 'flux-system/crossplane-providers' is not ready
- **Kustomization flux-system/crossplane-providers** since 2026-09-16T11:53:06Z: dependency 'flux-system/crossplane' is not ready
- **Kustomization flux-system/crossplane-storage-capability** since 2026-09-16T11:53:07Z: dependency 'flux-system/crossplane-providerconfig' is not ready
- **Kustomization flux-system/dagster** since 2026-09-19T11:44:23Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/dns** since 2026-09-19T11:42:25Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/epistemic-fabric** since 2026-09-19T11:36:47Z: health check failed after 169.698181ms: failed early due to stalled resources: [Deployment/epistemic-fabric/epistemic-ingest-github status: 'Failed']
- **Kustomization flux-system/estate-db** since 2026-09-19T11:36:32Z: Database/estate-db/aevum-evidence dry-run failed (InternalError): Internal error occurred: failed calling webhook "vdatabase.cnpg.io": failed to call webhook: Post "https://cnpg-webhook-service.estate-db.svc:443/validate-postgresql-cnpg-io-v1-database?timeout=10s": EOF 
- **Kustomization flux-system/flux-webhook** since 2026-09-19T11:43:51Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/healing-analyzer** since 2026-09-19T11:44:05Z: dependency 'flux-system/healing-k8sgpt' is not ready
- **Kustomization flux-system/healing-k8sgpt** since 2026-09-19T11:42:33Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/hermes-agent** since 2026-09-19T11:44:03Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/hindsight** since 2026-09-19T11:43:36Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/human-vault** since 2026-09-19T11:42:29Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/human-vault-bridge** since 2026-09-19T11:42:32Z: dependency 'flux-system/human-vault' is not ready
- **Kustomization flux-system/identity** since 2026-09-19T11:42:57Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/idp-agent** since 2026-09-19T11:36:54Z: Service/idp-agent/idp-agent-redis dry-run failed: admission webhook "validate.kyverno.svc-fail" denied the request:   resource Service/idp-agent/idp-agent-redis was blocked due to the following policies   require-catalogue-entity:   service-names-its-entity: 'validation error: Service idp-agent/idp-agent-redis serves a port but names no catalogue entity. Add the label backstage.io/kubernetes-id with the entity name from backstage/**/catalog-info.yaml, and a founder surface if a person opens it (docs/policy/every-interface-is-a-door.md). rule service-names-its-entity failed at path /metadata/labels/backstage.io/kubernetes-id/'  
- **Kustomization flux-system/image-automation** since 2026-09-19T11:44:16Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/monitoring** since 2026-09-19T11:43:42Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/notify** since 2026-09-19T11:44:35Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/otto-gateway** since 2026-09-19T11:43:16Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/otto-golden** since 2026-09-19T11:42:47Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/prospector** since 2026-09-19T11:42:57Z: health check failed after 596.421901ms: failed early due to stalled resources: [Deployment/prospector/prospector-store-api status: 'Failed']
- **Kustomization flux-system/research-engine** since 2026-09-19T11:41:11Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/router-events** since 2026-09-19T11:40:15Z: Reconciliation in progress
- **Kustomization flux-system/secret-store** since 2026-09-19T11:40:48Z: ClusterSecretStore/estate-vault dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.clustersecretstore.external-secrets.io": failed to call webhook: Post "https://external-secrets-webhook.external-secrets.svc:443/validate-external-secrets-io-v1-clustersecretstore?timeout=15s": EOF 
- **Kustomization flux-system/tailscale** since 2026-09-19T11:44:19Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/temporal** since 2026-09-19T11:44:28Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/verification** since 2026-09-19T11:42:01Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/via-negativa** since 2026-09-19T11:41:06Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/weave-gitops** since 2026-09-19T11:43:09Z: dependency 'flux-system/identity' is not ready

## Every row

| Kind | Namespace | Name | State | Applied revision | Since | Message |
|---|---|---|---|---|---|---|
| HelmRelease | commerce | lago | Not ready | 1.28.0 | 2026-09-18T21:16:37Z | Could not determine release state: unable to determine state for release with status 'uninstalling' |
| HelmRelease | crossplane-system | crossplane | Not ready | 1.15.1 | 2026-09-16T17:08:05Z | Helm upgrade failed for release crossplane-system/crossplane with chart crossplane@1.15.1: create: failed to create: admission webhook "oke-resource-leak-protec |
| Kustomization | flux-system | alerts-github | Not ready | main@6b17c89 | 2026-09-19T11:44:50Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | alerts-secret | Not ready | main@6b17c89 | 2026-09-19T11:43:29Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | backstage | Not ready | main@1d76f3a | 2026-09-19T11:40:19Z | health check failed after 528.807119ms: failed early due to stalled resources: [Deployment/backstage/catalogue status: 'Failed'] |
| Kustomization | flux-system | calico | Not ready | main@0df0a74 | 2026-09-19T11:44:13Z | GlobalNetworkPolicy/deny-direct-ai-vendor-egress dry-run failed: no matches for kind "GlobalNetworkPolicy" in version "projectcalico.org/v3"  |
| Kustomization | flux-system | chaos | Not ready | main@cb6f6b2 | 2026-09-19T11:43:46Z | dependency 'flux-system/monitoring' is not ready |
| Kustomization | flux-system | commerce | Not ready | main@abea14d | 2026-09-19T11:33:22Z | Reconciliation in progress |
| Kustomization | flux-system | concierge | Not ready | main@6b17c89 | 2026-09-19T11:44:10Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | crossplane | Not ready | main@8d685ec | 2026-09-19T11:41:36Z | health check failed after 96.426618ms: failed early due to stalled resources: [HelmRelease/crossplane-system/crossplane status: 'Failed'] |
| Kustomization | flux-system | crossplane-providerconfig | Not ready | main@8d685ec | 2026-09-16T11:53:07Z | dependency 'flux-system/crossplane-providers' is not ready |
| Kustomization | flux-system | crossplane-providers | Not ready | main@8d685ec | 2026-09-16T11:53:06Z | dependency 'flux-system/crossplane' is not ready |
| Kustomization | flux-system | crossplane-storage-capability | Not ready | main@8d685ec | 2026-09-16T11:53:07Z | dependency 'flux-system/crossplane-providerconfig' is not ready |
| Kustomization | flux-system | dagster | Not ready | main@6b17c89 | 2026-09-19T11:44:23Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | dns | Not ready | main@6b17c89 | 2026-09-19T11:42:25Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | epistemic-fabric | Not ready | main@6b17c89 | 2026-09-19T11:36:47Z | health check failed after 169.698181ms: failed early due to stalled resources: [Deployment/epistemic-fabric/epistemic-ingest-github status: 'Failed'] |
| Kustomization | flux-system | estate-db | Not ready | main@6b17c89 | 2026-09-19T11:36:32Z | Database/estate-db/aevum-evidence dry-run failed (InternalError): Internal error occurred: failed calling webhook "vdatabase.cnpg.io": failed to call webhook: P |
| Kustomization | flux-system | flux-webhook | Not ready | main@6b17c89 | 2026-09-19T11:43:51Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | healing-analyzer | Not ready | main@6b17c89 | 2026-09-19T11:44:05Z | dependency 'flux-system/healing-k8sgpt' is not ready |
| Kustomization | flux-system | healing-k8sgpt | Not ready | main@6b17c89 | 2026-09-19T11:42:33Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | hermes-agent | Not ready | main@0df0a74 | 2026-09-19T11:44:03Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | hindsight | Not ready | main@6b17c89 | 2026-09-19T11:43:36Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | human-vault | Not ready | main@6b17c89 | 2026-09-19T11:42:29Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | human-vault-bridge | Not ready | main@6b17c89 | 2026-09-19T11:42:32Z | dependency 'flux-system/human-vault' is not ready |
| Kustomization | flux-system | identity | Not ready | main@6b17c89 | 2026-09-19T11:42:57Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | idp-agent | Not ready | main@6b17c89 | 2026-09-19T11:36:54Z | Service/idp-agent/idp-agent-redis dry-run failed: admission webhook "validate.kyverno.svc-fail" denied the request:   resource Service/idp-agent/idp-agent-redis |
| Kustomization | flux-system | image-automation | Not ready | main@6b17c89 | 2026-09-19T11:44:16Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | monitoring | Not ready | main@6b17c89 | 2026-09-19T11:43:42Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | notify | Not ready | main@6b17c89 | 2026-09-19T11:44:35Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | otto-gateway | Not ready | main@cd9eb71 | 2026-09-19T11:43:16Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | otto-golden | Not ready | main@cd9eb71 | 2026-09-19T11:42:47Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | prospector | Not ready | main@7453d76 | 2026-09-19T11:42:57Z | health check failed after 596.421901ms: failed early due to stalled resources: [Deployment/prospector/prospector-store-api status: 'Failed'] |
| Kustomization | flux-system | research-engine | Not ready | main@6b17c89 | 2026-09-19T11:41:11Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | router-events | Not ready | main@0df0a74 | 2026-09-19T11:40:15Z | Reconciliation in progress |
| Kustomization | flux-system | secret-store | Not ready | main@6b17c89 | 2026-09-19T11:40:48Z | ClusterSecretStore/estate-vault dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.clustersecretstore.external-secrets.io |
| Kustomization | flux-system | tailscale | Not ready | main@6b17c89 | 2026-09-19T11:44:19Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | temporal | Not ready | main@6b17c89 | 2026-09-19T11:44:28Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | verification | Not ready | main@6b17c89 | 2026-09-19T11:42:01Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | via-negativa | Not ready | main@6b17c89 | 2026-09-19T11:41:06Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | weave-gitops | Not ready | main@6b17c89 | 2026-09-19T11:43:09Z | dependency 'flux-system/identity' is not ready |
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
| HelmRelease | hindsight | hindsight | Ready | 0.9.2 | 2026-09-17T11:41:29Z |  |
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
| Kustomization | flux-system | agent-workforce | Ready | main@6b17c89 | 2026-09-19T11:36:57Z |  |
| Kustomization | flux-system | alerts | Ready | main@6b17c89 | 2026-09-19T11:39:46Z |  |
| Kustomization | flux-system | autoscaler | Ready | main@6b17c89 | 2026-09-19T11:35:36Z |  |
| Kustomization | flux-system | backstage-namespace | Ready | main@6b17c89 | 2026-09-19T11:35:38Z |  |
| Kustomization | flux-system | chaos-mesh | Ready | main@6b17c89 | 2026-09-19T11:35:37Z |  |
| Kustomization | flux-system | cluster-state | Ready | main@6b17c89 | 2026-09-19T11:40:53Z |  |
| Kustomization | flux-system | commerce-data | Ready | main@6b17c89 | 2026-09-19T11:35:10Z |  |
| Kustomization | flux-system | cross-node-drill | Ready | main@6b17c89 | 2026-09-19T11:43:01Z |  |
| Kustomization | flux-system | drills | Ready | main@6b17c89 | 2026-09-19T11:36:09Z |  |
| Kustomization | flux-system | edge | Ready | main@6b17c89 | 2026-09-19T11:44:20Z |  |
| Kustomization | flux-system | estate-catalog | Ready | latest@sha256:ab16209d425f4cc336cf9f58d5 | 2026-09-19T11:36:47Z |  |
| Kustomization | flux-system | estate-db-migrate | Ready | main@6b17c89 | 2026-09-19T11:35:53Z |  |
| Kustomization | flux-system | estate-db-operator | Ready | main@6b17c89 | 2026-09-19T11:36:55Z |  |
| Kustomization | flux-system | event-bus | Ready | main@6b17c89 | 2026-09-19T11:43:00Z |  |
| Kustomization | flux-system | external-secrets | Ready | main@6b17c89 | 2026-09-19T11:42:27Z |  |
| Kustomization | flux-system | feature-register | Ready | main@6b17c89 | 2026-09-19T11:40:08Z |  |
| Kustomization | flux-system | flux-system | Ready | main@6b17c89 | 2026-09-19T11:42:58Z |  |
| Kustomization | flux-system | gateway-api-crds | Ready | v1.5.1@e7677b7 | 2026-09-19T11:39:51Z |  |
| Kustomization | flux-system | github-app-creds | Ready | main@6b17c89 | 2026-09-19T11:36:06Z |  |
| Kustomization | flux-system | guacamole | Ready | main@6b17c89 | 2026-09-19T11:36:18Z |  |
| Kustomization | flux-system | gvisor-runtime | Ready | main@6b17c89 | 2026-09-19T11:42:59Z |  |
| Kustomization | flux-system | healing | Ready | main@6b17c89 | 2026-09-19T11:41:43Z |  |
| Kustomization | flux-system | healthchecks | Ready | main@6b17c89 | 2026-09-19T11:37:42Z |  |
| Kustomization | flux-system | jit | Ready | main@6b17c89 | 2026-09-19T11:42:42Z |  |
| Kustomization | flux-system | keda | Ready | main@6b17c89 | 2026-09-19T11:37:57Z |  |
| Kustomization | flux-system | kyverno | Ready | main@6b17c89 | 2026-09-19T11:40:37Z |  |
| Kustomization | flux-system | llm | Ready | main@6b17c89 | 2026-09-19T11:34:59Z |  |
| Kustomization | flux-system | mcp | Ready | main@6b17c89 | 2026-09-19T11:37:40Z |  |
| Kustomization | flux-system | metrics-server | Ready | main@6b17c89 | 2026-09-19T11:45:11Z |  |
| Kustomization | flux-system | monitoring-rules | Ready | main@6b17c89 | 2026-09-19T11:37:04Z |  |
| Kustomization | flux-system | nodesoftware-operator | Ready | main@6b17c89 | 2026-09-19T11:35:46Z |  |
| Kustomization | flux-system | ns-fences | Ready | main@6b17c89 | 2026-09-19T11:42:51Z |  |
| Kustomization | flux-system | observability | Ready | main@6b17c89 | 2026-09-19T11:37:07Z |  |
| Kustomization | flux-system | observability-collector | Ready | main@6b17c89 | 2026-09-19T11:39:43Z |  |
| Kustomization | flux-system | otto-golden-secret | Ready | main@6b17c89 | 2026-09-19T11:39:21Z |  |
| Kustomization | flux-system | priority-classes | Ready | main@6b17c89 | 2026-09-19T11:37:02Z |  |
| Kustomization | flux-system | prospector-platform | Ready | main@6b17c89 | 2026-09-19T11:38:23Z |  |
| Kustomization | flux-system | rbac | Ready | main@6b17c89 | 2026-09-19T11:43:15Z |  |
| Kustomization | flux-system | rbac-floor | Ready | main@6b17c89 | 2026-09-19T11:43:14Z |  |
| Kustomization | flux-system | rbac-identity | Ready | main@6b17c89 | 2026-09-19T11:45:09Z |  |
| Kustomization | flux-system | reloader | Ready | main@6b17c89 | 2026-09-19T11:37:49Z |  |
| Kustomization | flux-system | robusta | Ready | main@6b17c89 | 2026-09-19T11:40:42Z |  |
| Kustomization | flux-system | sandbox-launch | Ready | main@6b17c89 | 2026-09-19T11:35:39Z |  |
| Kustomization | flux-system | sandbox-live | Ready | sandbox/launch@4830a6e | 2026-09-19T11:45:08Z |  |
| Kustomization | flux-system | scheduling | Ready | main@6b17c89 | 2026-09-19T11:39:11Z |  |
| Kustomization | flux-system | science | Ready | main@6b17c89 | 2026-09-19T11:44:43Z |  |
| Kustomization | flux-system | searxng | Ready | main@6b17c89 | 2026-09-19T11:41:54Z |  |
| Kustomization | flux-system | spire | Ready | main@6b17c89 | 2026-09-19T11:41:31Z |  |
| Kustomization | flux-system | staging | Ready | main@6b17c89 | 2026-09-19T11:37:03Z |  |
| Kustomization | flux-system | trivy | Ready | main@6b17c89 | 2026-09-19T11:42:10Z |  |
