# Flux: what is applied

Read from the cluster receipt taken at 2026-09-21T16:45:18Z. Every Kustomization and HelmRelease, with the revision Flux last applied. **Suspended** is a switch somebody turned off on purpose (temporal, commerce, commerce-data, event-bus), not a defect; **Unknown** is a row Flux has never graded.

**121 objects: 74 ready, 46 not ready, 0 unknown, 1 suspended.**

## Not ready right now

- **HelmRelease commerce/lago** since 2026-09-18T21:16:37Z: Could not determine release state: unable to determine state for release with status 'uninstalling'
- **HelmRelease crossplane-system/crossplane** since 2026-09-16T17:08:05Z: Helm upgrade failed for release crossplane-system/crossplane with chart crossplane@1.15.1: create: failed to create: admission webhook "oke-resource-leak-protection.oke.com" denied the request: OKE resource leak protection rejected the request. Cluster has 2650 secrets and the limit is 2000. See https://docs.oracle.com/iaas/Content/ContEng/Tasks/contengprotectingclustersfromresourceleaks.htm for details.
- **Kustomization flux-system/backstage** since 2026-09-21T16:40:13Z: dependency 'flux-system/external-secrets' is not ready
- **Kustomization flux-system/calico** since 2026-09-21T16:37:25Z: GlobalNetworkPolicy/deny-direct-ai-vendor-egress dry-run failed: no matches for kind "GlobalNetworkPolicy" in version "projectcalico.org/v3" 
- **Kustomization flux-system/chaos** since 2026-09-21T16:40:57Z: dependency 'flux-system/chaos-mesh' is not ready
- **Kustomization flux-system/chaos-mesh** since 2026-09-21T16:40:35Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/cluster-state** since 2026-09-21T16:40:36Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/commerce** since 2026-09-21T16:43:03Z: dependency 'flux-system/commerce-data' is not ready
- **Kustomization flux-system/commerce-data** since 2026-09-21T16:40:23Z: dependency 'flux-system/external-secrets' is not ready
- **Kustomization flux-system/crossplane** since 2026-09-21T16:39:11Z: health check failed after 68.713434ms: failed early due to stalled resources: [HelmRelease/crossplane-system/crossplane status: 'Failed']
- **Kustomization flux-system/crossplane-providerconfig** since 2026-09-16T11:53:07Z: dependency 'flux-system/crossplane-providers' is not ready
- **Kustomization flux-system/crossplane-providers** since 2026-09-16T11:53:06Z: dependency 'flux-system/crossplane' is not ready
- **Kustomization flux-system/crossplane-storage-capability** since 2026-09-16T11:53:07Z: dependency 'flux-system/crossplane-providerconfig' is not ready
- **Kustomization flux-system/dagster** since 2026-09-21T16:41:00Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/dns** since 2026-09-21T16:39:59Z: dependency 'flux-system/edge' is not ready
- **Kustomization flux-system/edge** since 2026-09-21T16:37:30Z: ClusterPolicy/flux-only-writes dry-run failed (InternalError): Internal error occurred: failed calling webhook "mutate-policy.kyverno.svc": failed to call webhook: Post "https://kyverno-svc.kyverno.svc:443/policymutate?timeout=10s": EOF 
- **Kustomization flux-system/epistemic-fabric** since 2026-09-21T16:40:13Z: health check failed after 119.716914ms: failed early due to stalled resources: [Deployment/epistemic-fabric/epistemic-ingest-github status: 'Failed']
- **Kustomization flux-system/external-secrets** since 2026-09-21T16:38:35Z: dependency 'flux-system/edge' is not ready
- **Kustomization flux-system/flux-webhook** since 2026-09-21T16:39:47Z: dependency 'flux-system/edge' is not ready
- **Kustomization flux-system/guacamole** since 2026-09-21T16:39:57Z: dependency 'flux-system/identity' is not ready
- **Kustomization flux-system/healing** since 2026-09-21T16:40:00Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/healing-k8sgpt** since 2026-09-21T16:40:16Z: dependency 'flux-system/healing' is not ready
- **Kustomization flux-system/healthchecks** since 2026-09-21T16:40:38Z: dependency 'flux-system/identity' is not ready
- **Kustomization flux-system/hermes-agent** since 2026-09-21T16:45:07Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/hindsight** since 2026-09-21T16:41:16Z: dependency 'flux-system/llm' is not ready
- **Kustomization flux-system/human-vault** since 2026-09-21T16:38:58Z: dependency 'flux-system/external-secrets' is not ready
- **Kustomization flux-system/human-vault-bridge** since 2026-09-21T16:39:59Z: dependency 'flux-system/human-vault' is not ready
- **Kustomization flux-system/identity** since 2026-09-21T16:38:23Z: dependency 'flux-system/edge' is not ready
- **Kustomization flux-system/idp-agent** since 2026-09-21T16:39:18Z: Service/idp-agent/idp-agent-redis dry-run failed: admission webhook "validate.kyverno.svc-fail" denied the request:   resource Service/idp-agent/idp-agent-redis was blocked due to the following policies   require-catalogue-entity:   service-names-its-entity: 'validation error: Service idp-agent/idp-agent-redis serves a port but names no catalogue entity. Add the label backstage.io/kubernetes-id with the entity name from backstage/**/catalog-info.yaml, and a founder surface if a person opens it (docs/policy/every-interface-is-a-door.md). rule service-names-its-entity failed at path /metadata/labels/backstage.io/kubernetes-id/'  
- **Kustomization flux-system/llm** since 2026-09-21T16:41:08Z: dependency 'flux-system/edge' is not ready
- **Kustomization flux-system/mcp** since 2026-09-21T16:39:49Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/nodesoftware-operator** since 2026-09-21T16:40:21Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/observability** since 2026-09-21T16:40:05Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/observability-collector** since 2026-09-21T16:40:06Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/otto-gateway** since 2026-09-21T16:44:48Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/otto-golden** since 2026-09-21T16:39:48Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/prospector** since 2026-09-21T16:36:54Z: health check failed after 442.297734ms: failed early due to stalled resources: [Deployment/prospector/prospector-store-api status: 'Failed']
- **Kustomization flux-system/prospector-platform** since 2026-09-21T16:39:34Z: dependency 'flux-system/edge' is not ready
- **Kustomization flux-system/router-events** since 2026-09-21T16:45:10Z: health check failed after 5m0.04662777s: timeout waiting for: [Deployment/llm/litellm status: 'InProgress']
- **Kustomization flux-system/sandbox-launch** since 2026-09-21T16:38:12Z: dependency 'flux-system/edge' is not ready
- **Kustomization flux-system/scheduling** since 2026-09-21T16:39:39Z: dependency 'flux-system/edge' is not ready
- **Kustomization flux-system/science** since 2026-09-21T16:40:50Z: dependency 'flux-system/observability' is not ready
- **Kustomization flux-system/spire** since 2026-09-21T16:40:49Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/temporal** since 2026-09-21T16:39:04Z: dependency 'flux-system/edge' is not ready
- **Kustomization flux-system/via-negativa** since 2026-09-21T16:40:28Z: health check failed after 307.495775ms: failed early due to stalled resources: [Deployment/via-negativa/via-negativa-rca status: 'Failed']
- **Kustomization flux-system/weave-gitops** since 2026-09-21T16:39:43Z: dependency 'flux-system/identity' is not ready

## Every row

| Kind | Namespace | Name | State | Applied revision | Since | Message |
|---|---|---|---|---|---|---|
| HelmRelease | commerce | lago | Not ready | 1.28.0 | 2026-09-18T21:16:37Z | Could not determine release state: unable to determine state for release with status 'uninstalling' |
| HelmRelease | crossplane-system | crossplane | Not ready | 1.15.1 | 2026-09-16T17:08:05Z | Helm upgrade failed for release crossplane-system/crossplane with chart crossplane@1.15.1: create: failed to create: admission webhook "oke-resource-leak-protec |
| Kustomization | flux-system | backstage | Not ready | main@1d76f3a | 2026-09-21T16:40:13Z | dependency 'flux-system/external-secrets' is not ready |
| Kustomization | flux-system | calico | Not ready | main@0df0a74 | 2026-09-21T16:37:25Z | GlobalNetworkPolicy/deny-direct-ai-vendor-egress dry-run failed: no matches for kind "GlobalNetworkPolicy" in version "projectcalico.org/v3"  |
| Kustomization | flux-system | chaos | Not ready | main@cb6f6b2 | 2026-09-21T16:40:57Z | dependency 'flux-system/chaos-mesh' is not ready |
| Kustomization | flux-system | chaos-mesh | Not ready | main@26f947f | 2026-09-21T16:40:35Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | cluster-state | Not ready | main@26f947f | 2026-09-21T16:40:36Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | commerce | Not ready | main@abea14d | 2026-09-21T16:43:03Z | dependency 'flux-system/commerce-data' is not ready |
| Kustomization | flux-system | commerce-data | Not ready | main@26f947f | 2026-09-21T16:40:23Z | dependency 'flux-system/external-secrets' is not ready |
| Kustomization | flux-system | crossplane | Not ready | main@8d685ec | 2026-09-21T16:39:11Z | health check failed after 68.713434ms: failed early due to stalled resources: [HelmRelease/crossplane-system/crossplane status: 'Failed'] |
| Kustomization | flux-system | crossplane-providerconfig | Not ready | main@8d685ec | 2026-09-16T11:53:07Z | dependency 'flux-system/crossplane-providers' is not ready |
| Kustomization | flux-system | crossplane-providers | Not ready | main@8d685ec | 2026-09-16T11:53:06Z | dependency 'flux-system/crossplane' is not ready |
| Kustomization | flux-system | crossplane-storage-capability | Not ready | main@8d685ec | 2026-09-16T11:53:07Z | dependency 'flux-system/crossplane-providerconfig' is not ready |
| Kustomization | flux-system | dagster | Not ready | main@26f947f | 2026-09-21T16:41:00Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | dns | Not ready | main@26f947f | 2026-09-21T16:39:59Z | dependency 'flux-system/edge' is not ready |
| Kustomization | flux-system | edge | Not ready | main@26f947f | 2026-09-21T16:37:30Z | ClusterPolicy/flux-only-writes dry-run failed (InternalError): Internal error occurred: failed calling webhook "mutate-policy.kyverno.svc": failed to call webho |
| Kustomization | flux-system | epistemic-fabric | Not ready | main@26f947f | 2026-09-21T16:40:13Z | health check failed after 119.716914ms: failed early due to stalled resources: [Deployment/epistemic-fabric/epistemic-ingest-github status: 'Failed'] |
| Kustomization | flux-system | external-secrets | Not ready | main@26f947f | 2026-09-21T16:38:35Z | dependency 'flux-system/edge' is not ready |
| Kustomization | flux-system | flux-webhook | Not ready | main@26f947f | 2026-09-21T16:39:47Z | dependency 'flux-system/edge' is not ready |
| Kustomization | flux-system | guacamole | Not ready | main@26f947f | 2026-09-21T16:39:57Z | dependency 'flux-system/identity' is not ready |
| Kustomization | flux-system | healing | Not ready | main@26f947f | 2026-09-21T16:40:00Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | healing-k8sgpt | Not ready | main@26f947f | 2026-09-21T16:40:16Z | dependency 'flux-system/healing' is not ready |
| Kustomization | flux-system | healthchecks | Not ready | main@26f947f | 2026-09-21T16:40:38Z | dependency 'flux-system/identity' is not ready |
| Kustomization | flux-system | hermes-agent | Not ready | main@0df0a74 | 2026-09-21T16:45:07Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | hindsight | Not ready | main@26f947f | 2026-09-21T16:41:16Z | dependency 'flux-system/llm' is not ready |
| Kustomization | flux-system | human-vault | Not ready | main@26f947f | 2026-09-21T16:38:58Z | dependency 'flux-system/external-secrets' is not ready |
| Kustomization | flux-system | human-vault-bridge | Not ready | main@26f947f | 2026-09-21T16:39:59Z | dependency 'flux-system/human-vault' is not ready |
| Kustomization | flux-system | identity | Not ready | main@26f947f | 2026-09-21T16:38:23Z | dependency 'flux-system/edge' is not ready |
| Kustomization | flux-system | idp-agent | Not ready | main@26f947f | 2026-09-21T16:39:18Z | Service/idp-agent/idp-agent-redis dry-run failed: admission webhook "validate.kyverno.svc-fail" denied the request:   resource Service/idp-agent/idp-agent-redis |
| Kustomization | flux-system | llm | Not ready | main@26f947f | 2026-09-21T16:41:08Z | dependency 'flux-system/edge' is not ready |
| Kustomization | flux-system | mcp | Not ready | main@26f947f | 2026-09-21T16:39:49Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | nodesoftware-operator | Not ready | main@26f947f | 2026-09-21T16:40:21Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | observability | Not ready | main@26f947f | 2026-09-21T16:40:05Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | observability-collector | Not ready | main@26f947f | 2026-09-21T16:40:06Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | otto-gateway | Not ready | main@cd9eb71 | 2026-09-21T16:44:48Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | otto-golden | Not ready | main@cd9eb71 | 2026-09-21T16:39:48Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | prospector | Not ready | main@7453d76 | 2026-09-21T16:36:54Z | health check failed after 442.297734ms: failed early due to stalled resources: [Deployment/prospector/prospector-store-api status: 'Failed'] |
| Kustomization | flux-system | prospector-platform | Not ready | main@26f947f | 2026-09-21T16:39:34Z | dependency 'flux-system/edge' is not ready |
| Kustomization | flux-system | router-events | Not ready | main@0df0a74 | 2026-09-21T16:45:10Z | health check failed after 5m0.04662777s: timeout waiting for: [Deployment/llm/litellm status: 'InProgress'] |
| Kustomization | flux-system | sandbox-launch | Not ready | main@ac2a1b1 | 2026-09-21T16:38:12Z | dependency 'flux-system/edge' is not ready |
| Kustomization | flux-system | scheduling | Not ready | main@26f947f | 2026-09-21T16:39:39Z | dependency 'flux-system/edge' is not ready |
| Kustomization | flux-system | science | Not ready | main@26f947f | 2026-09-21T16:40:50Z | dependency 'flux-system/observability' is not ready |
| Kustomization | flux-system | spire | Not ready | main@26f947f | 2026-09-21T16:40:49Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | temporal | Not ready | main@26f947f | 2026-09-21T16:39:04Z | dependency 'flux-system/edge' is not ready |
| Kustomization | flux-system | via-negativa | Not ready | main@26f947f | 2026-09-21T16:40:28Z | health check failed after 307.495775ms: failed early due to stalled resources: [Deployment/via-negativa/via-negativa-rca status: 'Failed'] |
| Kustomization | flux-system | weave-gitops | Not ready | main@26f947f | 2026-09-21T16:39:43Z | dependency 'flux-system/identity' is not ready |
| HelmRelease | tigera-operator | tigera-operator | Suspended | v3.32.2 | 2026-09-06T19:38:02Z |  |
| HelmRelease | cert-manager | cert-manager | Ready | v1.21.1 | 2026-09-08T11:56:22Z |  |
| HelmRelease | chaos-mesh | chaos-mesh | Ready | 2.8.4 | 2026-09-21T03:13:40Z |  |
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
| Kustomization | flux-system | agent-workforce | Ready | main@26f947f | 2026-09-21T16:38:32Z |  |
| Kustomization | flux-system | alerts | Ready | main@26f947f | 2026-09-21T16:38:32Z |  |
| Kustomization | flux-system | alerts-github | Ready | main@26f947f | 2026-09-21T16:39:46Z |  |
| Kustomization | flux-system | alerts-secret | Ready | main@26f947f | 2026-09-21T16:38:36Z |  |
| Kustomization | flux-system | autoscaler | Ready | main@26f947f | 2026-09-21T16:37:49Z |  |
| Kustomization | flux-system | backstage-namespace | Ready | main@26f947f | 2026-09-21T16:35:41Z |  |
| Kustomization | flux-system | concierge | Ready | main@26f947f | 2026-09-21T16:40:13Z |  |
| Kustomization | flux-system | cross-node-drill | Ready | main@26f947f | 2026-09-21T16:36:04Z |  |
| Kustomization | flux-system | drills | Ready | main@26f947f | 2026-09-21T16:39:04Z |  |
| Kustomization | flux-system | estate-catalog | Ready | latest@sha256:ec63ed2ed0b316a651899e32b8 | 2026-09-21T16:40:43Z |  |
| Kustomization | flux-system | estate-db | Ready | main@26f947f | 2026-09-21T16:38:54Z |  |
| Kustomization | flux-system | estate-db-migrate | Ready | main@26f947f | 2026-09-21T16:39:05Z |  |
| Kustomization | flux-system | estate-db-operator | Ready | main@26f947f | 2026-09-21T16:37:23Z |  |
| Kustomization | flux-system | event-bus | Ready | main@26f947f | 2026-09-21T16:37:24Z |  |
| Kustomization | flux-system | feature-register | Ready | main@26f947f | 2026-09-21T16:36:45Z |  |
| Kustomization | flux-system | flux-system | Ready | main@26f947f | 2026-09-21T16:39:00Z |  |
| Kustomization | flux-system | gateway-api-crds | Ready | v1.5.1@e7677b7 | 2026-09-21T16:44:39Z |  |
| Kustomization | flux-system | github-app-creds | Ready | main@26f947f | 2026-09-21T16:38:39Z |  |
| Kustomization | flux-system | gvisor-runtime | Ready | main@26f947f | 2026-09-21T16:37:52Z |  |
| Kustomization | flux-system | healing-analyzer | Ready | main@26f947f | 2026-09-21T16:40:07Z |  |
| Kustomization | flux-system | image-automation | Ready | main@26f947f | 2026-09-21T16:37:11Z |  |
| Kustomization | flux-system | jit | Ready | main@26f947f | 2026-09-21T16:39:14Z |  |
| Kustomization | flux-system | keda | Ready | main@26f947f | 2026-09-21T16:39:25Z |  |
| Kustomization | flux-system | kyverno | Ready | main@26f947f | 2026-09-21T16:36:05Z |  |
| Kustomization | flux-system | metrics-server | Ready | main@26f947f | 2026-09-21T16:38:12Z |  |
| Kustomization | flux-system | monitoring | Ready | main@26f947f | 2026-09-21T16:37:10Z |  |
| Kustomization | flux-system | monitoring-rules | Ready | main@26f947f | 2026-09-21T16:38:09Z |  |
| Kustomization | flux-system | notify | Ready | main@26f947f | 2026-09-21T16:39:24Z |  |
| Kustomization | flux-system | ns-fences | Ready | main@26f947f | 2026-09-21T16:43:05Z |  |
| Kustomization | flux-system | otto-golden-secret | Ready | main@26f947f | 2026-09-21T16:39:48Z |  |
| Kustomization | flux-system | priority-classes | Ready | main@26f947f | 2026-09-21T16:38:35Z |  |
| Kustomization | flux-system | rbac | Ready | main@26f947f | 2026-09-21T16:37:54Z |  |
| Kustomization | flux-system | rbac-floor | Ready | main@26f947f | 2026-09-21T16:39:49Z |  |
| Kustomization | flux-system | rbac-identity | Ready | main@26f947f | 2026-09-21T16:38:23Z |  |
| Kustomization | flux-system | reloader | Ready | main@26f947f | 2026-09-21T16:37:06Z |  |
| Kustomization | flux-system | research-engine | Ready | main@26f947f | 2026-09-21T16:40:04Z |  |
| Kustomization | flux-system | robusta | Ready | main@26f947f | 2026-09-21T16:38:50Z |  |
| Kustomization | flux-system | sandbox-live | Ready | sandbox/launch@4830a6e | 2026-09-21T16:44:25Z |  |
| Kustomization | flux-system | searxng | Ready | main@26f947f | 2026-09-21T16:37:00Z |  |
| Kustomization | flux-system | secret-store | Ready | main@26f947f | 2026-09-21T16:37:53Z |  |
| Kustomization | flux-system | staging | Ready | main@26f947f | 2026-09-21T16:40:14Z |  |
| Kustomization | flux-system | tailscale | Ready | main@26f947f | 2026-09-21T16:37:35Z |  |
| Kustomization | flux-system | trivy | Ready | main@26f947f | 2026-09-21T16:36:38Z |  |
| Kustomization | flux-system | verification | Ready | main@26f947f | 2026-09-21T16:38:16Z |  |
