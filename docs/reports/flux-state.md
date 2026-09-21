# Flux: what is applied

Read from the cluster receipt taken at 2026-09-21T18:01:07Z. Every Kustomization and HelmRelease, with the revision Flux last applied. **Suspended** is a switch somebody turned off on purpose (temporal, commerce, commerce-data, event-bus), not a defect; **Unknown** is a row Flux has never graded.

**121 objects: 100 ready, 20 not ready, 0 unknown, 1 suspended.**

## Not ready right now

- **HelmRelease commerce/lago** since 2026-09-18T21:16:37Z: Could not determine release state: unable to determine state for release with status 'uninstalling'
- **HelmRelease crossplane-system/crossplane** since 2026-09-16T17:08:05Z: Helm upgrade failed for release crossplane-system/crossplane with chart crossplane@1.15.1: create: failed to create: admission webhook "oke-resource-leak-protection.oke.com" denied the request: OKE resource leak protection rejected the request. Cluster has 2650 secrets and the limit is 2000. See https://docs.oracle.com/iaas/Content/ContEng/Tasks/contengprotectingclustersfromresourceleaks.htm for details.
- **Kustomization flux-system/backstage** since 2026-09-21T18:00:26Z: health check failed after 988.586734ms: failed early due to stalled resources: [Deployment/backstage/catalogue status: 'Failed']
- **Kustomization flux-system/calico** since 2026-09-21T17:57:38Z: GlobalNetworkPolicy/deny-direct-ai-vendor-egress dry-run failed: no matches for kind "GlobalNetworkPolicy" in version "projectcalico.org/v3" 
- **Kustomization flux-system/chaos** since 2026-09-21T17:59:31Z: dependency 'flux-system/backstage' is not ready
- **Kustomization flux-system/commerce** since 2026-09-21T17:54:43Z: health check failed after 15m0.02659664s: timeout waiting for: [HelmRelease/commerce/lago status: 'InProgress']
- **Kustomization flux-system/crossplane** since 2026-09-21T17:59:27Z: health check failed after 51.590164ms: failed early due to stalled resources: [HelmRelease/crossplane-system/crossplane status: 'Failed']
- **Kustomization flux-system/crossplane-providerconfig** since 2026-09-16T11:53:07Z: dependency 'flux-system/crossplane-providers' is not ready
- **Kustomization flux-system/crossplane-providers** since 2026-09-16T11:53:06Z: dependency 'flux-system/crossplane' is not ready
- **Kustomization flux-system/crossplane-storage-capability** since 2026-09-16T11:53:07Z: dependency 'flux-system/crossplane-providerconfig' is not ready
- **Kustomization flux-system/epistemic-fabric** since 2026-09-21T17:50:35Z: health check failed after 124.157563ms: failed early due to stalled resources: [Deployment/epistemic-fabric/epistemic-ingest-github status: 'Failed']
- **Kustomization flux-system/healthchecks** since 2026-09-21T17:58:31Z: ExternalSecret/healthchecks/healthchecks dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-secrets.io": failed to call webhook: Post "https://external-secrets-webhook.external-secrets.svc:443/validate-external-secrets-io-v1-externalsecret?timeout=15s": EOF 
- **Kustomization flux-system/hermes-agent** since 2026-09-21T17:55:20Z: health check failed after 4m38.653794252s: failed early due to stalled resources: [Deployment/hermes-agent/hermes-agent-gateway status: 'Failed']
- **Kustomization flux-system/idp-agent** since 2026-09-21T17:59:34Z: Service/idp-agent/idp-agent-redis dry-run failed: admission webhook "validate.kyverno.svc-fail" denied the request:   resource Service/idp-agent/idp-agent-redis was blocked due to the following policies   require-catalogue-entity:   service-names-its-entity: 'validation error: Service idp-agent/idp-agent-redis serves a port but names no catalogue entity. Add the label backstage.io/kubernetes-id with the entity name from backstage/**/catalog-info.yaml, and a founder surface if a person opens it (docs/policy/every-interface-is-a-door.md). rule service-names-its-entity failed at path /metadata/labels/backstage.io/kubernetes-id/'  
- **Kustomization flux-system/otto-gateway** since 2026-09-21T17:54:50Z: health check failed after 4m18.568635863s: failed early due to stalled resources: [Deployment/otto-gateway/otto-gateway status: 'Failed']
- **Kustomization flux-system/otto-golden** since 2026-09-21T17:58:16Z: health check failed after 578.919892ms: failed early due to stalled resources: [Deployment/otto-golden/otto-golden status: 'Failed']
- **Kustomization flux-system/prospector** since 2026-09-21T17:59:56Z: health check failed after 203.823509ms: failed early due to stalled resources: [Deployment/prospector/prospector-store-api status: 'Failed']
- **Kustomization flux-system/router-events** since 2026-09-21T18:00:23Z: health check failed after 5m0.120807058s: timeout waiting for: [Deployment/llm/litellm status: 'InProgress']
- **Kustomization flux-system/sandbox-launch** since 2026-09-21T17:59:41Z: health check failed after 100.265537ms: failed early due to stalled resources: [Job/demo-sandbox/arm-voice-bench status: 'Failed']
- **Kustomization flux-system/via-negativa** since 2026-09-21T17:51:00Z: health check failed after 538.38087ms: failed early due to stalled resources: [Deployment/via-negativa/via-negativa-rca status: 'Failed']

## Every row

| Kind | Namespace | Name | State | Applied revision | Since | Message |
|---|---|---|---|---|---|---|
| HelmRelease | commerce | lago | Not ready | 1.28.0 | 2026-09-18T21:16:37Z | Could not determine release state: unable to determine state for release with status 'uninstalling' |
| HelmRelease | crossplane-system | crossplane | Not ready | 1.15.1 | 2026-09-16T17:08:05Z | Helm upgrade failed for release crossplane-system/crossplane with chart crossplane@1.15.1: create: failed to create: admission webhook "oke-resource-leak-protec |
| Kustomization | flux-system | backstage | Not ready | main@1d76f3a | 2026-09-21T18:00:26Z | health check failed after 988.586734ms: failed early due to stalled resources: [Deployment/backstage/catalogue status: 'Failed'] |
| Kustomization | flux-system | calico | Not ready | main@0df0a74 | 2026-09-21T17:57:38Z | GlobalNetworkPolicy/deny-direct-ai-vendor-egress dry-run failed: no matches for kind "GlobalNetworkPolicy" in version "projectcalico.org/v3"  |
| Kustomization | flux-system | chaos | Not ready | main@cb6f6b2 | 2026-09-21T17:59:31Z | dependency 'flux-system/backstage' is not ready |
| Kustomization | flux-system | commerce | Not ready | main@abea14d | 2026-09-21T17:54:43Z | health check failed after 15m0.02659664s: timeout waiting for: [HelmRelease/commerce/lago status: 'InProgress'] |
| Kustomization | flux-system | crossplane | Not ready | main@8d685ec | 2026-09-21T17:59:27Z | health check failed after 51.590164ms: failed early due to stalled resources: [HelmRelease/crossplane-system/crossplane status: 'Failed'] |
| Kustomization | flux-system | crossplane-providerconfig | Not ready | main@8d685ec | 2026-09-16T11:53:07Z | dependency 'flux-system/crossplane-providers' is not ready |
| Kustomization | flux-system | crossplane-providers | Not ready | main@8d685ec | 2026-09-16T11:53:06Z | dependency 'flux-system/crossplane' is not ready |
| Kustomization | flux-system | crossplane-storage-capability | Not ready | main@8d685ec | 2026-09-16T11:53:07Z | dependency 'flux-system/crossplane-providerconfig' is not ready |
| Kustomization | flux-system | epistemic-fabric | Not ready | main@26f947f | 2026-09-21T17:50:35Z | health check failed after 124.157563ms: failed early due to stalled resources: [Deployment/epistemic-fabric/epistemic-ingest-github status: 'Failed'] |
| Kustomization | flux-system | healthchecks | Not ready | main@26f947f | 2026-09-21T17:58:31Z | ExternalSecret/healthchecks/healthchecks dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-secre |
| Kustomization | flux-system | hermes-agent | Not ready | main@0df0a74 | 2026-09-21T17:55:20Z | health check failed after 4m38.653794252s: failed early due to stalled resources: [Deployment/hermes-agent/hermes-agent-gateway status: 'Failed'] |
| Kustomization | flux-system | idp-agent | Not ready | main@26f947f | 2026-09-21T17:59:34Z | Service/idp-agent/idp-agent-redis dry-run failed: admission webhook "validate.kyverno.svc-fail" denied the request:   resource Service/idp-agent/idp-agent-redis |
| Kustomization | flux-system | otto-gateway | Not ready | main@cd9eb71 | 2026-09-21T17:54:50Z | health check failed after 4m18.568635863s: failed early due to stalled resources: [Deployment/otto-gateway/otto-gateway status: 'Failed'] |
| Kustomization | flux-system | otto-golden | Not ready | main@cd9eb71 | 2026-09-21T17:58:16Z | health check failed after 578.919892ms: failed early due to stalled resources: [Deployment/otto-golden/otto-golden status: 'Failed'] |
| Kustomization | flux-system | prospector | Not ready | main@7453d76 | 2026-09-21T17:59:56Z | health check failed after 203.823509ms: failed early due to stalled resources: [Deployment/prospector/prospector-store-api status: 'Failed'] |
| Kustomization | flux-system | router-events | Not ready | main@0df0a74 | 2026-09-21T18:00:23Z | health check failed after 5m0.120807058s: timeout waiting for: [Deployment/llm/litellm status: 'InProgress'] |
| Kustomization | flux-system | sandbox-launch | Not ready | main@ac2a1b1 | 2026-09-21T17:59:41Z | health check failed after 100.265537ms: failed early due to stalled resources: [Job/demo-sandbox/arm-voice-bench status: 'Failed'] |
| Kustomization | flux-system | via-negativa | Not ready | main@26f947f | 2026-09-21T17:51:00Z | health check failed after 538.38087ms: failed early due to stalled resources: [Deployment/via-negativa/via-negativa-rca status: 'Failed'] |
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
| Kustomization | flux-system | agent-workforce | Ready | main@26f947f | 2026-09-21T17:57:36Z |  |
| Kustomization | flux-system | alerts | Ready | main@26f947f | 2026-09-21T17:59:18Z |  |
| Kustomization | flux-system | alerts-github | Ready | main@26f947f | 2026-09-21T17:58:37Z |  |
| Kustomization | flux-system | alerts-secret | Ready | main@26f947f | 2026-09-21T18:00:00Z |  |
| Kustomization | flux-system | autoscaler | Ready | main@26f947f | 2026-09-21T17:57:19Z |  |
| Kustomization | flux-system | backstage-namespace | Ready | main@26f947f | 2026-09-21T17:56:02Z |  |
| Kustomization | flux-system | chaos-mesh | Ready | main@26f947f | 2026-09-21T17:58:36Z |  |
| Kustomization | flux-system | cluster-state | Ready | main@26f947f | 2026-09-21T17:58:30Z |  |
| Kustomization | flux-system | commerce-data | Ready | main@26f947f | 2026-09-21T17:58:30Z |  |
| Kustomization | flux-system | concierge | Ready | main@26f947f | 2026-09-21T17:59:12Z |  |
| Kustomization | flux-system | cross-node-drill | Ready | main@26f947f | 2026-09-21T17:56:46Z |  |
| Kustomization | flux-system | dagster | Ready | main@26f947f | 2026-09-21T17:58:09Z |  |
| Kustomization | flux-system | dns | Ready | main@26f947f | 2026-09-21T17:59:05Z |  |
| Kustomization | flux-system | drills | Ready | main@26f947f | 2026-09-21T17:58:22Z |  |
| Kustomization | flux-system | edge | Ready | main@26f947f | 2026-09-21T17:58:55Z |  |
| Kustomization | flux-system | estate-catalog | Ready | latest@sha256:ec63ed2ed0b316a651899e32b8 | 2026-09-21T17:50:39Z |  |
| Kustomization | flux-system | estate-db | Ready | main@26f947f | 2026-09-21T17:50:27Z |  |
| Kustomization | flux-system | estate-db-migrate | Ready | main@26f947f | 2026-09-21T17:58:17Z |  |
| Kustomization | flux-system | estate-db-operator | Ready | main@26f947f | 2026-09-21T17:57:34Z |  |
| Kustomization | flux-system | event-bus | Ready | main@26f947f | 2026-09-21T17:57:00Z |  |
| Kustomization | flux-system | external-secrets | Ready | main@26f947f | 2026-09-21T17:59:50Z |  |
| Kustomization | flux-system | feature-register | Ready | main@26f947f | 2026-09-21T17:56:54Z |  |
| Kustomization | flux-system | flux-system | Ready | main@26f947f | 2026-09-21T17:50:57Z |  |
| Kustomization | flux-system | flux-webhook | Ready | main@26f947f | 2026-09-21T17:59:24Z |  |
| Kustomization | flux-system | gateway-api-crds | Ready | v1.5.1@e7677b7 | 2026-09-21T17:55:24Z |  |
| Kustomization | flux-system | github-app-creds | Ready | main@26f947f | 2026-09-21T17:57:19Z |  |
| Kustomization | flux-system | guacamole | Ready | main@26f947f | 2026-09-21T17:59:59Z |  |
| Kustomization | flux-system | gvisor-runtime | Ready | main@26f947f | 2026-09-21T17:59:39Z |  |
| Kustomization | flux-system | healing | Ready | main@26f947f | 2026-09-21T17:58:18Z |  |
| Kustomization | flux-system | healing-analyzer | Ready | main@26f947f | 2026-09-21T18:00:15Z |  |
| Kustomization | flux-system | healing-k8sgpt | Ready | main@26f947f | 2026-09-21T17:58:25Z |  |
| Kustomization | flux-system | hindsight | Ready | main@26f947f | 2026-09-21T17:57:37Z |  |
| Kustomization | flux-system | human-vault | Ready | main@26f947f | 2026-09-21T17:58:46Z |  |
| Kustomization | flux-system | human-vault-bridge | Ready | main@26f947f | 2026-09-21T17:58:49Z |  |
| Kustomization | flux-system | identity | Ready | main@26f947f | 2026-09-21T18:00:03Z |  |
| Kustomization | flux-system | image-automation | Ready | main@26f947f | 2026-09-21T17:57:21Z |  |
| Kustomization | flux-system | jit | Ready | main@26f947f | 2026-09-21T17:59:23Z |  |
| Kustomization | flux-system | keda | Ready | main@26f947f | 2026-09-21T18:00:06Z |  |
| Kustomization | flux-system | kyverno | Ready | main@26f947f | 2026-09-21T17:57:06Z |  |
| Kustomization | flux-system | llm | Ready | main@26f947f | 2026-09-21T17:57:46Z |  |
| Kustomization | flux-system | mcp | Ready | main@26f947f | 2026-09-21T17:58:02Z |  |
| Kustomization | flux-system | metrics-server | Ready | main@26f947f | 2026-09-21T18:00:12Z |  |
| Kustomization | flux-system | monitoring | Ready | main@26f947f | 2026-09-21T17:58:47Z |  |
| Kustomization | flux-system | monitoring-rules | Ready | main@26f947f | 2026-09-21T17:58:23Z |  |
| Kustomization | flux-system | nodesoftware-operator | Ready | main@26f947f | 2026-09-21T17:59:21Z |  |
| Kustomization | flux-system | notify | Ready | main@26f947f | 2026-09-21T17:58:53Z |  |
| Kustomization | flux-system | ns-fences | Ready | main@26f947f | 2026-09-21T17:55:59Z |  |
| Kustomization | flux-system | observability | Ready | main@26f947f | 2026-09-21T17:59:03Z |  |
| Kustomization | flux-system | observability-collector | Ready | main@26f947f | 2026-09-21T17:59:38Z |  |
| Kustomization | flux-system | otto-golden-secret | Ready | main@26f947f | 2026-09-21T17:50:45Z |  |
| Kustomization | flux-system | priority-classes | Ready | main@26f947f | 2026-09-21T18:00:17Z |  |
| Kustomization | flux-system | prospector-platform | Ready | main@26f947f | 2026-09-21T17:59:23Z |  |
| Kustomization | flux-system | rbac | Ready | main@26f947f | 2026-09-21T17:57:54Z |  |
| Kustomization | flux-system | rbac-floor | Ready | main@26f947f | 2026-09-21T17:59:25Z |  |
| Kustomization | flux-system | rbac-identity | Ready | main@26f947f | 2026-09-21T17:58:58Z |  |
| Kustomization | flux-system | reloader | Ready | main@26f947f | 2026-09-21T17:56:39Z |  |
| Kustomization | flux-system | research-engine | Ready | main@26f947f | 2026-09-21T18:00:19Z |  |
| Kustomization | flux-system | robusta | Ready | main@26f947f | 2026-09-21T17:58:01Z |  |
| Kustomization | flux-system | sandbox-live | Ready | sandbox/launch@4830a6e | 2026-09-21T17:59:50Z |  |
| Kustomization | flux-system | scheduling | Ready | main@26f947f | 2026-09-21T17:58:49Z |  |
| Kustomization | flux-system | science | Ready | main@26f947f | 2026-09-21T18:00:03Z |  |
| Kustomization | flux-system | searxng | Ready | main@26f947f | 2026-09-21T17:56:27Z |  |
| Kustomization | flux-system | secret-store | Ready | main@26f947f | 2026-09-21T17:58:53Z |  |
| Kustomization | flux-system | spire | Ready | main@26f947f | 2026-09-21T17:58:22Z |  |
| Kustomization | flux-system | staging | Ready | main@26f947f | 2026-09-21T18:00:06Z |  |
| Kustomization | flux-system | tailscale | Ready | main@26f947f | 2026-09-21T17:58:07Z |  |
| Kustomization | flux-system | temporal | Ready | main@26f947f | 2026-09-21T17:59:30Z |  |
| Kustomization | flux-system | trivy | Ready | main@26f947f | 2026-09-21T17:57:33Z |  |
| Kustomization | flux-system | verification | Ready | main@26f947f | 2026-09-21T17:59:13Z |  |
| Kustomization | flux-system | weave-gitops | Ready | main@26f947f | 2026-09-21T18:00:19Z |  |
