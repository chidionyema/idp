# Flux: what is applied

Read from the cluster receipt taken at 2026-09-18T12:30:24Z. Every Kustomization and HelmRelease, with the revision Flux last applied. **Suspended** is a switch somebody turned off on purpose (temporal, commerce, commerce-data, event-bus), not a defect; **Unknown** is a row Flux has never graded.

**121 objects: 86 ready, 34 not ready, 0 unknown, 1 suspended.**

## Not ready right now

- **HelmRelease commerce/lago** since 2026-09-18T01:52:05Z: Helm install failed for release commerce/lago with chart lago@1.28.0: failed early due to stalled resources: [Deployment/commerce/lago-worker status: 'Failed']
- **HelmRelease crossplane-system/crossplane** since 2026-09-16T17:08:05Z: Helm upgrade failed for release crossplane-system/crossplane with chart crossplane@1.15.1: create: failed to create: admission webhook "oke-resource-leak-protection.oke.com" denied the request: OKE resource leak protection rejected the request. Cluster has 2650 secrets and the limit is 2000. See https://docs.oracle.com/iaas/Content/ContEng/Tasks/contengprotectingclustersfromresourceleaks.htm for details.
- **Kustomization flux-system/agent-workforce** since 2026-09-18T12:25:51Z: dependency 'flux-system/llm' is not ready
- **Kustomization flux-system/backstage** since 2026-09-18T12:24:55Z: dependency 'flux-system/estate-db-migrate' is not ready
- **Kustomization flux-system/calico** since 2026-09-18T12:23:47Z: GlobalNetworkPolicy/deny-direct-ai-vendor-egress dry-run failed: no matches for kind "GlobalNetworkPolicy" in version "projectcalico.org/v3" 
- **Kustomization flux-system/chaos** since 2026-09-18T12:25:04Z: dependency 'flux-system/observability' is not ready
- **Kustomization flux-system/cluster-state** since 2026-09-18T12:24:46Z: CronJob/backstage/cluster-state dry-run failed (InternalError): Internal error occurred: failed calling webhook "mutate.kyverno.svc-fail": failed to call webhook: Post "https://kyverno-svc.kyverno.svc:443/mutate/fail?timeout=10s": EOF 
- **Kustomization flux-system/commerce** since 2026-09-18T12:24:16Z: dependency 'flux-system/commerce-data' is not ready
- **Kustomization flux-system/commerce-data** since 2026-09-18T12:25:20Z: dependency 'flux-system/estate-db' is not ready
- **Kustomization flux-system/crossplane** since 2026-09-18T12:24:57Z: health check failed after 33.74629ms: failed early due to stalled resources: [HelmRelease/crossplane-system/crossplane status: 'Failed']
- **Kustomization flux-system/crossplane-providerconfig** since 2026-09-16T11:53:07Z: dependency 'flux-system/crossplane-providers' is not ready
- **Kustomization flux-system/crossplane-providers** since 2026-09-16T11:53:06Z: dependency 'flux-system/crossplane' is not ready
- **Kustomization flux-system/crossplane-storage-capability** since 2026-09-16T11:53:07Z: dependency 'flux-system/crossplane-providerconfig' is not ready
- **Kustomization flux-system/dagster** since 2026-09-18T12:24:55Z: dependency 'flux-system/estate-db-migrate' is not ready
- **Kustomization flux-system/epistemic-fabric** since 2026-09-18T12:25:50Z: health check failed after 78.270418ms: failed early due to stalled resources: [Deployment/epistemic-fabric/epistemic-ingest-github status: 'Failed']
- **Kustomization flux-system/estate-db** since 2026-09-18T12:25:16Z: Cluster/estate-db/estate dry-run failed (InternalError): Internal error occurred: failed calling webhook "vcluster.cnpg.io": failed to call webhook: Post "https://cnpg-webhook-service.estate-db.svc:443/validate-postgresql-cnpg-io-v1-cluster?timeout=10s": EOF 
- **Kustomization flux-system/estate-db-migrate** since 2026-09-18T12:23:48Z: dependency 'flux-system/estate-db' is not ready
- **Kustomization flux-system/guacamole** since 2026-09-18T12:25:21Z: dependency 'flux-system/estate-db-migrate' is not ready
- **Kustomization flux-system/healing-analyzer** since 2026-09-18T12:23:55Z: dependency 'flux-system/healing-k8sgpt' is not ready
- **Kustomization flux-system/healing-k8sgpt** since 2026-09-18T12:25:14Z: dependency 'flux-system/llm' is not ready
- **Kustomization flux-system/healthchecks** since 2026-09-18T12:25:20Z: dependency 'flux-system/estate-db-migrate' is not ready
- **Kustomization flux-system/hermes-agent** since 2026-09-18T12:29:37Z: health check failed after 3m50.673012273s: failed early due to stalled resources: [Deployment/hermes-agent/hermes-agent-gateway status: 'Failed']
- **Kustomization flux-system/hindsight** since 2026-09-18T12:24:49Z: dependency 'flux-system/llm' is not ready
- **Kustomization flux-system/idp-agent** since 2026-09-18T12:25:30Z: Service/idp-agent/idp-agent-redis dry-run failed: admission webhook "validate.kyverno.svc-fail" denied the request:   resource Service/idp-agent/idp-agent-redis was blocked due to the following policies   require-catalogue-entity:   service-names-its-entity: 'validation error: Service idp-agent/idp-agent-redis serves a port but names no catalogue entity. Add the label backstage.io/kubernetes-id with the entity name from backstage/**/catalog-info.yaml, and a founder surface if a person opens it (docs/policy/every-interface-is-a-door.md). rule service-names-its-entity failed at path /metadata/labels/backstage.io/kubernetes-id/'  
- **Kustomization flux-system/llm** since 2026-09-18T12:25:17Z: dependency 'flux-system/estate-db-migrate' is not ready
- **Kustomization flux-system/observability** since 2026-09-18T12:25:13Z: dependency 'flux-system/estate-db-migrate' is not ready
- **Kustomization flux-system/otto-gateway** since 2026-09-18T12:29:20Z: health check failed after 3m31.785431273s: failed early due to stalled resources: [Deployment/otto-gateway/otto-gateway status: 'Failed']
- **Kustomization flux-system/otto-golden** since 2026-09-18T12:25:23Z: health check failed after 411.377068ms: failed early due to stalled resources: [Deployment/otto-golden/otto-golden status: 'Failed']
- **Kustomization flux-system/prospector** since 2026-09-18T12:28:43Z: health check failed after 304.096733ms: failed early due to stalled resources: [Deployment/prospector/prospector-store-api status: 'Failed']
- **Kustomization flux-system/research-engine** since 2026-09-18T12:25:16Z: dependency 'flux-system/llm' is not ready
- **Kustomization flux-system/router-events** since 2026-09-18T12:24:15Z: dependency 'flux-system/llm' is not ready
- **Kustomization flux-system/science** since 2026-09-18T12:23:45Z: dependency 'flux-system/observability' is not ready
- **Kustomization flux-system/temporal** since 2026-09-18T12:24:55Z: dependency 'flux-system/estate-db-migrate' is not ready
- **Kustomization flux-system/via-negativa** since 2026-09-18T12:25:20Z: dependency 'flux-system/llm' is not ready

## Every row

| Kind | Namespace | Name | State | Applied revision | Since | Message |
|---|---|---|---|---|---|---|
| HelmRelease | commerce | lago | Not ready | 1.28.0 | 2026-09-18T01:52:05Z | Helm install failed for release commerce/lago with chart lago@1.28.0: failed early due to stalled resources: [Deployment/commerce/lago-worker status: 'Failed'] |
| HelmRelease | crossplane-system | crossplane | Not ready | 1.15.1 | 2026-09-16T17:08:05Z | Helm upgrade failed for release crossplane-system/crossplane with chart crossplane@1.15.1: create: failed to create: admission webhook "oke-resource-leak-protec |
| Kustomization | flux-system | agent-workforce | Not ready | main@c744be6 | 2026-09-18T12:25:51Z | dependency 'flux-system/llm' is not ready |
| Kustomization | flux-system | backstage | Not ready | main@1d76f3a | 2026-09-18T12:24:55Z | dependency 'flux-system/estate-db-migrate' is not ready |
| Kustomization | flux-system | calico | Not ready | main@0df0a74 | 2026-09-18T12:23:47Z | GlobalNetworkPolicy/deny-direct-ai-vendor-egress dry-run failed: no matches for kind "GlobalNetworkPolicy" in version "projectcalico.org/v3"  |
| Kustomization | flux-system | chaos | Not ready | main@cb6f6b2 | 2026-09-18T12:25:04Z | dependency 'flux-system/observability' is not ready |
| Kustomization | flux-system | cluster-state | Not ready | main@c744be6 | 2026-09-18T12:24:46Z | CronJob/backstage/cluster-state dry-run failed (InternalError): Internal error occurred: failed calling webhook "mutate.kyverno.svc-fail": failed to call webhoo |
| Kustomization | flux-system | commerce | Not ready | main@abea14d | 2026-09-18T12:24:16Z | dependency 'flux-system/commerce-data' is not ready |
| Kustomization | flux-system | commerce-data | Not ready | main@c744be6 | 2026-09-18T12:25:20Z | dependency 'flux-system/estate-db' is not ready |
| Kustomization | flux-system | crossplane | Not ready | main@8d685ec | 2026-09-18T12:24:57Z | health check failed after 33.74629ms: failed early due to stalled resources: [HelmRelease/crossplane-system/crossplane status: 'Failed'] |
| Kustomization | flux-system | crossplane-providerconfig | Not ready | main@8d685ec | 2026-09-16T11:53:07Z | dependency 'flux-system/crossplane-providers' is not ready |
| Kustomization | flux-system | crossplane-providers | Not ready | main@8d685ec | 2026-09-16T11:53:06Z | dependency 'flux-system/crossplane' is not ready |
| Kustomization | flux-system | crossplane-storage-capability | Not ready | main@8d685ec | 2026-09-16T11:53:07Z | dependency 'flux-system/crossplane-providerconfig' is not ready |
| Kustomization | flux-system | dagster | Not ready | main@c744be6 | 2026-09-18T12:24:55Z | dependency 'flux-system/estate-db-migrate' is not ready |
| Kustomization | flux-system | epistemic-fabric | Not ready | main@fc61353 | 2026-09-18T12:25:50Z | health check failed after 78.270418ms: failed early due to stalled resources: [Deployment/epistemic-fabric/epistemic-ingest-github status: 'Failed'] |
| Kustomization | flux-system | estate-db | Not ready | main@c744be6 | 2026-09-18T12:25:16Z | Cluster/estate-db/estate dry-run failed (InternalError): Internal error occurred: failed calling webhook "vcluster.cnpg.io": failed to call webhook: Post "https |
| Kustomization | flux-system | estate-db-migrate | Not ready | main@c744be6 | 2026-09-18T12:23:48Z | dependency 'flux-system/estate-db' is not ready |
| Kustomization | flux-system | guacamole | Not ready | main@c744be6 | 2026-09-18T12:25:21Z | dependency 'flux-system/estate-db-migrate' is not ready |
| Kustomization | flux-system | healing-analyzer | Not ready | main@c744be6 | 2026-09-18T12:23:55Z | dependency 'flux-system/healing-k8sgpt' is not ready |
| Kustomization | flux-system | healing-k8sgpt | Not ready | main@c744be6 | 2026-09-18T12:25:14Z | dependency 'flux-system/llm' is not ready |
| Kustomization | flux-system | healthchecks | Not ready | main@c744be6 | 2026-09-18T12:25:20Z | dependency 'flux-system/estate-db-migrate' is not ready |
| Kustomization | flux-system | hermes-agent | Not ready | main@0df0a74 | 2026-09-18T12:29:37Z | health check failed after 3m50.673012273s: failed early due to stalled resources: [Deployment/hermes-agent/hermes-agent-gateway status: 'Failed'] |
| Kustomization | flux-system | hindsight | Not ready | main@c744be6 | 2026-09-18T12:24:49Z | dependency 'flux-system/llm' is not ready |
| Kustomization | flux-system | idp-agent | Not ready | main@fc61353 | 2026-09-18T12:25:30Z | Service/idp-agent/idp-agent-redis dry-run failed: admission webhook "validate.kyverno.svc-fail" denied the request:   resource Service/idp-agent/idp-agent-redis |
| Kustomization | flux-system | llm | Not ready | main@c744be6 | 2026-09-18T12:25:17Z | dependency 'flux-system/estate-db-migrate' is not ready |
| Kustomization | flux-system | observability | Not ready | main@c744be6 | 2026-09-18T12:25:13Z | dependency 'flux-system/estate-db-migrate' is not ready |
| Kustomization | flux-system | otto-gateway | Not ready | main@cd9eb71 | 2026-09-18T12:29:20Z | health check failed after 3m31.785431273s: failed early due to stalled resources: [Deployment/otto-gateway/otto-gateway status: 'Failed'] |
| Kustomization | flux-system | otto-golden | Not ready | main@cd9eb71 | 2026-09-18T12:25:23Z | health check failed after 411.377068ms: failed early due to stalled resources: [Deployment/otto-golden/otto-golden status: 'Failed'] |
| Kustomization | flux-system | prospector | Not ready | main@7453d76 | 2026-09-18T12:28:43Z | health check failed after 304.096733ms: failed early due to stalled resources: [Deployment/prospector/prospector-store-api status: 'Failed'] |
| Kustomization | flux-system | research-engine | Not ready | main@c744be6 | 2026-09-18T12:25:16Z | dependency 'flux-system/llm' is not ready |
| Kustomization | flux-system | router-events | Not ready | main@0df0a74 | 2026-09-18T12:24:15Z | dependency 'flux-system/llm' is not ready |
| Kustomization | flux-system | science | Not ready | main@c744be6 | 2026-09-18T12:23:45Z | dependency 'flux-system/observability' is not ready |
| Kustomization | flux-system | temporal | Not ready | main@c744be6 | 2026-09-18T12:24:55Z | dependency 'flux-system/estate-db-migrate' is not ready |
| Kustomization | flux-system | via-negativa | Not ready | main@c744be6 | 2026-09-18T12:25:20Z | dependency 'flux-system/llm' is not ready |
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
| Kustomization | flux-system | alerts | Ready | main@fc61353 | 2026-09-18T12:25:30Z |  |
| Kustomization | flux-system | alerts-github | Ready | main@fc61353 | 2026-09-18T12:25:47Z |  |
| Kustomization | flux-system | alerts-secret | Ready | main@fc61353 | 2026-09-18T12:25:19Z |  |
| Kustomization | flux-system | autoscaler | Ready | main@fc61353 | 2026-09-18T12:25:20Z |  |
| Kustomization | flux-system | backstage-namespace | Ready | main@fc61353 | 2026-09-18T12:23:49Z |  |
| Kustomization | flux-system | chaos-mesh | Ready | main@fc61353 | 2026-09-18T12:24:46Z |  |
| Kustomization | flux-system | concierge | Ready | main@fc61353 | 2026-09-18T12:25:21Z |  |
| Kustomization | flux-system | cross-node-drill | Ready | main@fc61353 | 2026-09-18T12:23:54Z |  |
| Kustomization | flux-system | dns | Ready | main@fc61353 | 2026-09-18T12:25:07Z |  |
| Kustomization | flux-system | drills | Ready | main@fc61353 | 2026-09-18T12:25:52Z |  |
| Kustomization | flux-system | edge | Ready | main@fc61353 | 2026-09-18T12:24:24Z |  |
| Kustomization | flux-system | estate-catalog | Ready | latest@sha256:2bf9c0a8fc6ecf6a89e06ca6bc | 2026-09-18T12:27:32Z |  |
| Kustomization | flux-system | estate-db-operator | Ready | main@fc61353 | 2026-09-18T12:23:49Z |  |
| Kustomization | flux-system | event-bus | Ready | main@fc61353 | 2026-09-18T12:24:33Z |  |
| Kustomization | flux-system | external-secrets | Ready | main@fc61353 | 2026-09-18T12:24:29Z |  |
| Kustomization | flux-system | feature-register | Ready | main@fc61353 | 2026-09-18T12:24:16Z |  |
| Kustomization | flux-system | flux-system | Ready | main@fc61353 | 2026-09-18T12:23:57Z |  |
| Kustomization | flux-system | flux-webhook | Ready | main@fc61353 | 2026-09-18T12:24:58Z |  |
| Kustomization | flux-system | gateway-api-crds | Ready | v1.5.1@e7677b7 | 2026-09-18T12:23:54Z |  |
| Kustomization | flux-system | github-app-creds | Ready | main@fc61353 | 2026-09-18T12:25:21Z |  |
| Kustomization | flux-system | gvisor-runtime | Ready | main@fc61353 | 2026-09-18T12:25:32Z |  |
| Kustomization | flux-system | healing | Ready | main@fc61353 | 2026-09-18T12:24:46Z |  |
| Kustomization | flux-system | human-vault | Ready | main@fc61353 | 2026-09-18T12:25:15Z |  |
| Kustomization | flux-system | human-vault-bridge | Ready | main@fc61353 | 2026-09-18T12:25:23Z |  |
| Kustomization | flux-system | identity | Ready | main@fc61353 | 2026-09-18T12:24:58Z |  |
| Kustomization | flux-system | image-automation | Ready | main@fc61353 | 2026-09-18T12:24:51Z |  |
| Kustomization | flux-system | jit | Ready | main@fc61353 | 2026-09-18T12:24:35Z |  |
| Kustomization | flux-system | keda | Ready | main@fc61353 | 2026-09-18T12:25:06Z |  |
| Kustomization | flux-system | kyverno | Ready | main@fc61353 | 2026-09-18T12:23:48Z |  |
| Kustomization | flux-system | mcp | Ready | main@fc61353 | 2026-09-18T12:25:33Z |  |
| Kustomization | flux-system | metrics-server | Ready | main@fc61353 | 2026-09-18T12:25:00Z |  |
| Kustomization | flux-system | monitoring | Ready | main@fc61353 | 2026-09-18T12:25:00Z |  |
| Kustomization | flux-system | monitoring-rules | Ready | main@fc61353 | 2026-09-18T12:25:06Z |  |
| Kustomization | flux-system | nodesoftware-operator | Ready | main@fc61353 | 2026-09-18T12:25:21Z |  |
| Kustomization | flux-system | notify | Ready | main@fc61353 | 2026-09-18T12:25:01Z |  |
| Kustomization | flux-system | ns-fences | Ready | main@fc61353 | 2026-09-18T12:24:12Z |  |
| Kustomization | flux-system | observability-collector | Ready | main@fc61353 | 2026-09-18T12:25:05Z |  |
| Kustomization | flux-system | otto-golden-secret | Ready | main@fc61353 | 2026-09-18T12:25:04Z |  |
| Kustomization | flux-system | priority-classes | Ready | main@fc61353 | 2026-09-18T12:24:02Z |  |
| Kustomization | flux-system | prospector-platform | Ready | main@fc61353 | 2026-09-18T12:24:49Z |  |
| Kustomization | flux-system | rbac | Ready | main@fc61353 | 2026-09-18T12:24:29Z |  |
| Kustomization | flux-system | rbac-floor | Ready | main@fc61353 | 2026-09-18T12:24:01Z |  |
| Kustomization | flux-system | rbac-identity | Ready | main@fc61353 | 2026-09-18T12:23:59Z |  |
| Kustomization | flux-system | reloader | Ready | main@fc61353 | 2026-09-18T12:24:50Z |  |
| Kustomization | flux-system | robusta | Ready | main@fc61353 | 2026-09-18T12:24:50Z |  |
| Kustomization | flux-system | sandbox-launch | Ready | main@fc61353 | 2026-09-18T12:24:26Z |  |
| Kustomization | flux-system | sandbox-live | Ready | sandbox/launch@4830a6e | 2026-09-18T12:29:43Z |  |
| Kustomization | flux-system | scheduling | Ready | main@fc61353 | 2026-09-18T12:24:32Z |  |
| Kustomization | flux-system | searxng | Ready | main@fc61353 | 2026-09-18T12:23:57Z |  |
| Kustomization | flux-system | secret-store | Ready | main@fc61353 | 2026-09-18T12:24:48Z |  |
| Kustomization | flux-system | spire | Ready | main@fc61353 | 2026-09-18T12:24:48Z |  |
| Kustomization | flux-system | staging | Ready | main@fc61353 | 2026-09-18T12:23:58Z |  |
| Kustomization | flux-system | tailscale | Ready | main@fc61353 | 2026-09-18T12:24:58Z |  |
| Kustomization | flux-system | trivy | Ready | main@fc61353 | 2026-09-18T12:24:00Z |  |
| Kustomization | flux-system | verification | Ready | main@fc61353 | 2026-09-18T12:25:19Z |  |
| Kustomization | flux-system | weave-gitops | Ready | main@fc61353 | 2026-09-18T12:25:26Z |  |
