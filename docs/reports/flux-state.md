# Flux: what is applied

Read from the cluster receipt taken at 2026-09-19T16:45:19Z. Every Kustomization and HelmRelease, with the revision Flux last applied. **Suspended** is a switch somebody turned off on purpose (temporal, commerce, commerce-data, event-bus), not a defect; **Unknown** is a row Flux has never graded.

**121 objects: 82 ready, 38 not ready, 0 unknown, 1 suspended.**

## Not ready right now

- **HelmRelease commerce/lago** since 2026-09-18T21:16:37Z: Could not determine release state: unable to determine state for release with status 'uninstalling'
- **HelmRelease crossplane-system/crossplane** since 2026-09-16T17:08:05Z: Helm upgrade failed for release crossplane-system/crossplane with chart crossplane@1.15.1: create: failed to create: admission webhook "oke-resource-leak-protection.oke.com" denied the request: OKE resource leak protection rejected the request. Cluster has 2650 secrets and the limit is 2000. See https://docs.oracle.com/iaas/Content/ContEng/Tasks/contengprotectingclustersfromresourceleaks.htm for details.
- **Kustomization flux-system/agent-workforce** since 2026-09-19T16:44:55Z: dependency 'flux-system/llm' is not ready
- **Kustomization flux-system/alerts** since 2026-09-19T16:44:41Z: dependency 'flux-system/alerts-secret' is not ready
- **Kustomization flux-system/alerts-secret** since 2026-09-19T16:45:11Z: Reconciliation in progress
- **Kustomization flux-system/backstage** since 2026-09-19T16:44:57Z: dependency 'flux-system/estate-db-migrate' is not ready
- **Kustomization flux-system/calico** since 2026-09-19T16:43:56Z: GlobalNetworkPolicy/deny-direct-ai-vendor-egress dry-run failed: no matches for kind "GlobalNetworkPolicy" in version "projectcalico.org/v3" 
- **Kustomization flux-system/chaos** since 2026-09-19T16:44:10Z: dependency 'flux-system/chaos-mesh' is not ready
- **Kustomization flux-system/commerce** since 2026-09-19T16:42:07Z: Reconciliation in progress
- **Kustomization flux-system/commerce-data** since 2026-09-19T16:44:41Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/crossplane** since 2026-09-19T16:44:58Z: health check failed after 30.725417ms: failed early due to stalled resources: [HelmRelease/crossplane-system/crossplane status: 'Failed']
- **Kustomization flux-system/crossplane-providerconfig** since 2026-09-16T11:53:07Z: dependency 'flux-system/crossplane-providers' is not ready
- **Kustomization flux-system/crossplane-providers** since 2026-09-16T11:53:06Z: dependency 'flux-system/crossplane' is not ready
- **Kustomization flux-system/crossplane-storage-capability** since 2026-09-16T11:53:07Z: dependency 'flux-system/crossplane-providerconfig' is not ready
- **Kustomization flux-system/dagster** since 2026-09-19T16:44:55Z: dependency 'flux-system/estate-db-migrate' is not ready
- **Kustomization flux-system/drills** since 2026-09-19T16:44:41Z: dependency 'flux-system/github-app-creds' is not ready
- **Kustomization flux-system/epistemic-fabric** since 2026-09-19T16:44:44Z: dependency 'flux-system/github-app-creds' is not ready
- **Kustomization flux-system/estate-db-migrate** since 2026-09-19T16:45:13Z: Reconciliation in progress
- **Kustomization flux-system/guacamole** since 2026-09-19T16:44:52Z: dependency 'flux-system/tailscale' is not ready
- **Kustomization flux-system/healing-analyzer** since 2026-09-19T16:44:10Z: dependency 'flux-system/healing-k8sgpt' is not ready
- **Kustomization flux-system/healing-k8sgpt** since 2026-09-19T16:44:51Z: dependency 'flux-system/llm' is not ready
- **Kustomization flux-system/healthchecks** since 2026-09-19T16:44:56Z: dependency 'flux-system/estate-db-migrate' is not ready
- **Kustomization flux-system/hermes-agent** since 2026-09-19T16:44:55Z: health check failed after 3.839971427s: failed early due to stalled resources: [Deployment/hermes-agent/hermes-agent-gateway status: 'Failed']
- **Kustomization flux-system/hindsight** since 2026-09-19T16:44:56Z: dependency 'flux-system/llm' is not ready
- **Kustomization flux-system/idp-agent** since 2026-09-19T16:44:50Z: Service/idp-agent/idp-agent-redis dry-run failed: admission webhook "validate.kyverno.svc-fail" denied the request:   resource Service/idp-agent/idp-agent-redis was blocked due to the following policies   require-catalogue-entity:   service-names-its-entity: 'validation error: Service idp-agent/idp-agent-redis serves a port but names no catalogue entity. Add the label backstage.io/kubernetes-id with the entity name from backstage/**/catalog-info.yaml, and a founder surface if a person opens it (docs/policy/every-interface-is-a-door.md). rule service-names-its-entity failed at path /metadata/labels/backstage.io/kubernetes-id/'  
- **Kustomization flux-system/llm** since 2026-09-19T16:44:55Z: dependency 'flux-system/estate-db-migrate' is not ready
- **Kustomization flux-system/mcp** since 2026-09-19T16:44:41Z: dependency 'flux-system/github-app-creds' is not ready
- **Kustomization flux-system/observability** since 2026-09-19T16:44:55Z: dependency 'flux-system/observability-collector' is not ready
- **Kustomization flux-system/otto-gateway** since 2026-09-19T16:44:56Z: health check failed after 4.183493994s: failed early due to stalled resources: [Deployment/otto-gateway/otto-gateway status: 'Failed']
- **Kustomization flux-system/otto-golden** since 2026-09-19T16:44:41Z: dependency 'flux-system/otto-golden-secret' is not ready
- **Kustomization flux-system/prospector** since 2026-09-19T16:37:46Z: health check failed after 138.882323ms: failed early due to stalled resources: [Deployment/prospector/prospector-store-api status: 'Failed']
- **Kustomization flux-system/research-engine** since 2026-09-19T16:44:56Z: dependency 'flux-system/llm' is not ready
- **Kustomization flux-system/router-events** since 2026-09-19T16:44:21Z: dependency 'flux-system/llm' is not ready
- **Kustomization flux-system/sandbox-launch** since 2026-09-19T16:44:11Z: health check failed after 93.542266ms: failed early due to stalled resources: [Job/demo-sandbox/arm-voice-bench status: 'Failed']
- **Kustomization flux-system/science** since 2026-09-19T16:44:10Z: dependency 'flux-system/observability' is not ready
- **Kustomization flux-system/temporal** since 2026-09-19T16:44:56Z: dependency 'flux-system/estate-db-migrate' is not ready
- **Kustomization flux-system/verification** since 2026-09-19T16:45:11Z: Reconciliation in progress
- **Kustomization flux-system/via-negativa** since 2026-09-19T16:44:56Z: dependency 'flux-system/llm' is not ready

## Every row

| Kind | Namespace | Name | State | Applied revision | Since | Message |
|---|---|---|---|---|---|---|
| HelmRelease | commerce | lago | Not ready | 1.28.0 | 2026-09-18T21:16:37Z | Could not determine release state: unable to determine state for release with status 'uninstalling' |
| HelmRelease | crossplane-system | crossplane | Not ready | 1.15.1 | 2026-09-16T17:08:05Z | Helm upgrade failed for release crossplane-system/crossplane with chart crossplane@1.15.1: create: failed to create: admission webhook "oke-resource-leak-protec |
| Kustomization | flux-system | agent-workforce | Not ready | main@1121473 | 2026-09-19T16:44:55Z | dependency 'flux-system/llm' is not ready |
| Kustomization | flux-system | alerts | Not ready | main@1121473 | 2026-09-19T16:44:41Z | dependency 'flux-system/alerts-secret' is not ready |
| Kustomization | flux-system | alerts-secret | Not ready | main@1121473 | 2026-09-19T16:45:11Z | Reconciliation in progress |
| Kustomization | flux-system | backstage | Not ready | main@1d76f3a | 2026-09-19T16:44:57Z | dependency 'flux-system/estate-db-migrate' is not ready |
| Kustomization | flux-system | calico | Not ready | main@0df0a74 | 2026-09-19T16:43:56Z | GlobalNetworkPolicy/deny-direct-ai-vendor-egress dry-run failed: no matches for kind "GlobalNetworkPolicy" in version "projectcalico.org/v3"  |
| Kustomization | flux-system | chaos | Not ready | main@cb6f6b2 | 2026-09-19T16:44:10Z | dependency 'flux-system/chaos-mesh' is not ready |
| Kustomization | flux-system | commerce | Not ready | main@abea14d | 2026-09-19T16:42:07Z | Reconciliation in progress |
| Kustomization | flux-system | commerce-data | Not ready | main@1121473 | 2026-09-19T16:44:41Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | crossplane | Not ready | main@8d685ec | 2026-09-19T16:44:58Z | health check failed after 30.725417ms: failed early due to stalled resources: [HelmRelease/crossplane-system/crossplane status: 'Failed'] |
| Kustomization | flux-system | crossplane-providerconfig | Not ready | main@8d685ec | 2026-09-16T11:53:07Z | dependency 'flux-system/crossplane-providers' is not ready |
| Kustomization | flux-system | crossplane-providers | Not ready | main@8d685ec | 2026-09-16T11:53:06Z | dependency 'flux-system/crossplane' is not ready |
| Kustomization | flux-system | crossplane-storage-capability | Not ready | main@8d685ec | 2026-09-16T11:53:07Z | dependency 'flux-system/crossplane-providerconfig' is not ready |
| Kustomization | flux-system | dagster | Not ready | main@1121473 | 2026-09-19T16:44:55Z | dependency 'flux-system/estate-db-migrate' is not ready |
| Kustomization | flux-system | drills | Not ready | main@1121473 | 2026-09-19T16:44:41Z | dependency 'flux-system/github-app-creds' is not ready |
| Kustomization | flux-system | epistemic-fabric | Not ready | main@1121473 | 2026-09-19T16:44:44Z | dependency 'flux-system/github-app-creds' is not ready |
| Kustomization | flux-system | estate-db-migrate | Not ready | main@1121473 | 2026-09-19T16:45:13Z | Reconciliation in progress |
| Kustomization | flux-system | guacamole | Not ready | main@1121473 | 2026-09-19T16:44:52Z | dependency 'flux-system/tailscale' is not ready |
| Kustomization | flux-system | healing-analyzer | Not ready | main@1121473 | 2026-09-19T16:44:10Z | dependency 'flux-system/healing-k8sgpt' is not ready |
| Kustomization | flux-system | healing-k8sgpt | Not ready | main@1121473 | 2026-09-19T16:44:51Z | dependency 'flux-system/llm' is not ready |
| Kustomization | flux-system | healthchecks | Not ready | main@1121473 | 2026-09-19T16:44:56Z | dependency 'flux-system/estate-db-migrate' is not ready |
| Kustomization | flux-system | hermes-agent | Not ready | main@0df0a74 | 2026-09-19T16:44:55Z | health check failed after 3.839971427s: failed early due to stalled resources: [Deployment/hermes-agent/hermes-agent-gateway status: 'Failed'] |
| Kustomization | flux-system | hindsight | Not ready | main@1121473 | 2026-09-19T16:44:56Z | dependency 'flux-system/llm' is not ready |
| Kustomization | flux-system | idp-agent | Not ready | main@f4e74c9 | 2026-09-19T16:44:50Z | Service/idp-agent/idp-agent-redis dry-run failed: admission webhook "validate.kyverno.svc-fail" denied the request:   resource Service/idp-agent/idp-agent-redis |
| Kustomization | flux-system | llm | Not ready | main@1121473 | 2026-09-19T16:44:55Z | dependency 'flux-system/estate-db-migrate' is not ready |
| Kustomization | flux-system | mcp | Not ready | main@1121473 | 2026-09-19T16:44:41Z | dependency 'flux-system/github-app-creds' is not ready |
| Kustomization | flux-system | observability | Not ready | main@1121473 | 2026-09-19T16:44:55Z | dependency 'flux-system/observability-collector' is not ready |
| Kustomization | flux-system | otto-gateway | Not ready | main@cd9eb71 | 2026-09-19T16:44:56Z | health check failed after 4.183493994s: failed early due to stalled resources: [Deployment/otto-gateway/otto-gateway status: 'Failed'] |
| Kustomization | flux-system | otto-golden | Not ready | main@cd9eb71 | 2026-09-19T16:44:41Z | dependency 'flux-system/otto-golden-secret' is not ready |
| Kustomization | flux-system | prospector | Not ready | main@7453d76 | 2026-09-19T16:37:46Z | health check failed after 138.882323ms: failed early due to stalled resources: [Deployment/prospector/prospector-store-api status: 'Failed'] |
| Kustomization | flux-system | research-engine | Not ready | main@1121473 | 2026-09-19T16:44:56Z | dependency 'flux-system/llm' is not ready |
| Kustomization | flux-system | router-events | Not ready | main@0df0a74 | 2026-09-19T16:44:21Z | dependency 'flux-system/llm' is not ready |
| Kustomization | flux-system | sandbox-launch | Not ready | main@ac2a1b1 | 2026-09-19T16:44:11Z | health check failed after 93.542266ms: failed early due to stalled resources: [Job/demo-sandbox/arm-voice-bench status: 'Failed'] |
| Kustomization | flux-system | science | Not ready | main@1121473 | 2026-09-19T16:44:10Z | dependency 'flux-system/observability' is not ready |
| Kustomization | flux-system | temporal | Not ready | main@1121473 | 2026-09-19T16:44:56Z | dependency 'flux-system/estate-db-migrate' is not ready |
| Kustomization | flux-system | verification | Not ready | main@1121473 | 2026-09-19T16:45:11Z | Reconciliation in progress |
| Kustomization | flux-system | via-negativa | Not ready | main@1121473 | 2026-09-19T16:44:56Z | dependency 'flux-system/llm' is not ready |
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
| Kustomization | flux-system | alerts-github | Ready | main@f4e74c9 | 2026-09-19T16:44:53Z |  |
| Kustomization | flux-system | autoscaler | Ready | main@f4e74c9 | 2026-09-19T16:44:43Z |  |
| Kustomization | flux-system | backstage-namespace | Ready | main@f4e74c9 | 2026-09-19T16:44:00Z |  |
| Kustomization | flux-system | chaos-mesh | Ready | main@f4e74c9 | 2026-09-19T16:44:58Z |  |
| Kustomization | flux-system | cluster-state | Ready | main@f4e74c9 | 2026-09-19T16:44:40Z |  |
| Kustomization | flux-system | concierge | Ready | main@f4e74c9 | 2026-09-19T16:44:44Z |  |
| Kustomization | flux-system | cross-node-drill | Ready | main@f4e74c9 | 2026-09-19T16:43:57Z |  |
| Kustomization | flux-system | dns | Ready | main@f4e74c9 | 2026-09-19T16:44:46Z |  |
| Kustomization | flux-system | edge | Ready | main@f4e74c9 | 2026-09-19T16:44:10Z |  |
| Kustomization | flux-system | estate-catalog | Ready | latest@sha256:fa39f4330e28edfd6c6f1c8828 | 2026-09-19T16:40:18Z |  |
| Kustomization | flux-system | estate-db | Ready | main@f4e74c9 | 2026-09-19T16:45:11Z |  |
| Kustomization | flux-system | estate-db-operator | Ready | main@f4e74c9 | 2026-09-19T16:43:58Z |  |
| Kustomization | flux-system | event-bus | Ready | main@f4e74c9 | 2026-09-19T16:44:31Z |  |
| Kustomization | flux-system | external-secrets | Ready | main@f4e74c9 | 2026-09-19T16:44:34Z |  |
| Kustomization | flux-system | feature-register | Ready | main@f4e74c9 | 2026-09-19T16:44:04Z |  |
| Kustomization | flux-system | flux-system | Ready | main@f4e74c9 | 2026-09-19T16:43:58Z |  |
| Kustomization | flux-system | flux-webhook | Ready | main@f4e74c9 | 2026-09-19T16:44:44Z |  |
| Kustomization | flux-system | gateway-api-crds | Ready | v1.5.1@e7677b7 | 2026-09-19T16:44:05Z |  |
| Kustomization | flux-system | github-app-creds | Ready | main@f4e74c9 | 2026-09-19T16:44:47Z |  |
| Kustomization | flux-system | gvisor-runtime | Ready | main@f4e74c9 | 2026-09-19T16:44:56Z |  |
| Kustomization | flux-system | healing | Ready | main@f4e74c9 | 2026-09-19T16:44:39Z |  |
| Kustomization | flux-system | human-vault | Ready | main@f4e74c9 | 2026-09-19T16:44:45Z |  |
| Kustomization | flux-system | human-vault-bridge | Ready | main@f4e74c9 | 2026-09-19T16:44:55Z |  |
| Kustomization | flux-system | identity | Ready | main@f4e74c9 | 2026-09-19T16:44:48Z |  |
| Kustomization | flux-system | image-automation | Ready | main@f4e74c9 | 2026-09-19T16:44:47Z |  |
| Kustomization | flux-system | jit | Ready | main@f4e74c9 | 2026-09-19T16:44:07Z |  |
| Kustomization | flux-system | keda | Ready | main@f4e74c9 | 2026-09-19T16:44:41Z |  |
| Kustomization | flux-system | kyverno | Ready | main@f4e74c9 | 2026-09-19T16:43:59Z |  |
| Kustomization | flux-system | metrics-server | Ready | main@f4e74c9 | 2026-09-19T16:45:07Z |  |
| Kustomization | flux-system | monitoring | Ready | main@f4e74c9 | 2026-09-19T16:44:43Z |  |
| Kustomization | flux-system | monitoring-rules | Ready | main@f4e74c9 | 2026-09-19T16:44:57Z |  |
| Kustomization | flux-system | nodesoftware-operator | Ready | main@f4e74c9 | 2026-09-19T16:44:49Z |  |
| Kustomization | flux-system | notify | Ready | main@f4e74c9 | 2026-09-19T16:44:49Z |  |
| Kustomization | flux-system | ns-fences | Ready | main@f4e74c9 | 2026-09-19T16:44:19Z |  |
| Kustomization | flux-system | observability-collector | Ready | main@f4e74c9 | 2026-09-19T16:45:07Z |  |
| Kustomization | flux-system | otto-golden-secret | Ready | main@f4e74c9 | 2026-09-19T16:45:08Z |  |
| Kustomization | flux-system | priority-classes | Ready | main@f4e74c9 | 2026-09-19T16:44:03Z |  |
| Kustomization | flux-system | prospector-platform | Ready | main@f4e74c9 | 2026-09-19T16:44:39Z |  |
| Kustomization | flux-system | rbac | Ready | main@f4e74c9 | 2026-09-19T16:43:55Z |  |
| Kustomization | flux-system | rbac-floor | Ready | main@f4e74c9 | 2026-09-19T16:43:53Z |  |
| Kustomization | flux-system | rbac-identity | Ready | main@f4e74c9 | 2026-09-19T16:43:53Z |  |
| Kustomization | flux-system | reloader | Ready | main@f4e74c9 | 2026-09-19T16:44:43Z |  |
| Kustomization | flux-system | robusta | Ready | main@f4e74c9 | 2026-09-19T16:45:12Z |  |
| Kustomization | flux-system | sandbox-live | Ready | sandbox/launch@4830a6e | 2026-09-19T16:44:10Z |  |
| Kustomization | flux-system | scheduling | Ready | main@f4e74c9 | 2026-09-19T16:44:37Z |  |
| Kustomization | flux-system | searxng | Ready | main@f4e74c9 | 2026-09-19T16:44:01Z |  |
| Kustomization | flux-system | secret-store | Ready | main@f4e74c9 | 2026-09-19T16:44:41Z |  |
| Kustomization | flux-system | spire | Ready | main@f4e74c9 | 2026-09-19T16:45:07Z |  |
| Kustomization | flux-system | staging | Ready | main@f4e74c9 | 2026-09-19T16:44:01Z |  |
| Kustomization | flux-system | tailscale | Ready | main@f4e74c9 | 2026-09-19T16:45:11Z |  |
| Kustomization | flux-system | trivy | Ready | main@f4e74c9 | 2026-09-19T16:43:54Z |  |
| Kustomization | flux-system | weave-gitops | Ready | main@f4e74c9 | 2026-09-19T16:44:52Z |  |
