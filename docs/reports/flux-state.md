# Flux: what is applied

Read from the cluster receipt taken at 2026-09-17T20:15:50Z. Every Kustomization and HelmRelease, with the revision Flux last applied. **Suspended** is a switch somebody turned off on purpose (temporal, commerce, commerce-data, event-bus), not a defect; **Unknown** is a row Flux has never graded.

**121 objects: 94 ready, 26 not ready, 0 unknown, 1 suspended.**

## Not ready right now

- **HelmRelease commerce/lago** since 2026-09-17T20:02:05Z: Helm upgrade failed for release commerce/lago with chart lago@1.28.0: failed early due to stalled resources: [Deployment/commerce/lago-billing-worker status: 'Failed']
- **HelmRelease crossplane-system/crossplane** since 2026-09-16T17:08:05Z: Helm upgrade failed for release crossplane-system/crossplane with chart crossplane@1.15.1: create: failed to create: admission webhook "oke-resource-leak-protection.oke.com" denied the request: OKE resource leak protection rejected the request. Cluster has 2650 secrets and the limit is 2000. See https://docs.oracle.com/iaas/Content/ContEng/Tasks/contengprotectingclustersfromresourceleaks.htm for details.
- **Kustomization flux-system/backstage** since 2026-09-17T20:15:00Z: Reconciliation in progress
- **Kustomization flux-system/calico** since 2026-09-17T20:12:02Z: GlobalNetworkPolicy/deny-direct-ai-vendor-egress dry-run failed: no matches for kind "GlobalNetworkPolicy" in version "projectcalico.org/v3" 
- **Kustomization flux-system/chaos** since 2026-09-17T20:13:28Z: dependency 'flux-system/monitoring' is not ready
- **Kustomization flux-system/commerce** since 2026-09-17T20:01:49Z: Reconciliation in progress
- **Kustomization flux-system/crossplane** since 2026-09-17T20:12:49Z: health check failed after 93.627988ms: failed early due to stalled resources: [HelmRelease/crossplane-system/crossplane status: 'Failed']
- **Kustomization flux-system/crossplane-providerconfig** since 2026-09-16T11:53:07Z: dependency 'flux-system/crossplane-providers' is not ready
- **Kustomization flux-system/crossplane-providers** since 2026-09-16T11:53:06Z: dependency 'flux-system/crossplane' is not ready
- **Kustomization flux-system/crossplane-storage-capability** since 2026-09-16T11:53:07Z: dependency 'flux-system/crossplane-providerconfig' is not ready
- **Kustomization flux-system/epistemic-fabric** since 2026-09-17T20:14:58Z: health check failed after 149.748523ms: failed early due to stalled resources: [Deployment/epistemic-fabric/epistemic-ingest-github status: 'Failed']
- **Kustomization flux-system/gvisor-runtime** since 2026-09-17T20:15:13Z: Reconciliation in progress
- **Kustomization flux-system/hermes-agent** since 2026-09-17T20:14:56Z: health check failed after 540.163366ms: failed early due to stalled resources: [Deployment/hermes-agent/hermes-agent-gateway status: 'Failed']
- **Kustomization flux-system/idp-agent** since 2026-09-17T20:14:51Z: Service/idp-agent/idp-agent-redis dry-run failed: admission webhook "validate.kyverno.svc-fail" denied the request:   resource Service/idp-agent/idp-agent-redis was blocked due to the following policies   require-catalogue-entity:   service-names-its-entity: 'validation error: Service idp-agent/idp-agent-redis serves a port but names no catalogue entity. Add the label backstage.io/kubernetes-id with the entity name from backstage/**/catalog-info.yaml, and a founder surface if a person opens it (docs/policy/every-interface-is-a-door.md). rule service-names-its-entity failed at path /metadata/labels/backstage.io/kubernetes-id/'  
- **Kustomization flux-system/jit** since 2026-09-17T20:12:09Z: Deployment/jit/jit-broker dry-run failed (Invalid): Deployment.apps "jit-broker" is invalid: spec.template.spec.containers[0].env[9].valueFrom: Invalid value: "": may not be specified when `value` is not empty 
- **Kustomization flux-system/llm** since 2026-09-17T20:15:13Z: Reconciliation in progress
- **Kustomization flux-system/monitoring** since 2026-09-17T20:13:27Z: ExternalSecret/monitoring/alertmanager-telegram dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-secrets.io": failed to call webhook: Post "https://external-secrets-webhook.external-secrets.svc:443/validate-external-secrets-io-v1-externalsecret?timeout=15s": context deadline exceeded 
- **Kustomization flux-system/monitoring-rules** since 2026-09-17T20:13:13Z: dependency 'flux-system/monitoring' is not ready
- **Kustomization flux-system/otto-gateway** since 2026-09-17T20:13:46Z: health check failed after 1.413741069s: failed early due to stalled resources: [Deployment/otto-gateway/otto-gateway status: 'Failed']
- **Kustomization flux-system/otto-golden** since 2026-09-17T20:14:40Z: dependency 'flux-system/otto-golden-secret' is not ready
- **Kustomization flux-system/otto-golden-secret** since 2026-09-17T20:14:35Z: ExternalSecret/flux-system/otto-webhook dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-secrets.io": failed to call webhook: Post "https://external-secrets-webhook.external-secrets.svc:443/validate-external-secrets-io-v1-externalsecret?timeout=15s": context deadline exceeded 
- **Kustomization flux-system/prospector** since 2026-09-17T20:15:11Z: health check failed after 361.381324ms: failed early due to stalled resources: [Deployment/prospector/prospector-store-api status: 'Failed']
- **Kustomization flux-system/router-events** since 2026-09-17T20:10:02Z: health check failed after 5m0.044570159s: timeout waiting for: [Deployment/llm/litellm status: 'InProgress']
- **Kustomization flux-system/verification** since 2026-09-17T20:14:33Z: ExternalSecret/backstage/verdict-key-wall dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-secrets.io": failed to call webhook: Post "https://external-secrets-webhook.external-secrets.svc:443/validate-external-secrets-io-v1-externalsecret?timeout=15s": context deadline exceeded 
- **Kustomization flux-system/via-negativa** since 2026-09-17T20:15:13Z: dependency 'flux-system/llm' is not ready
- **Kustomization flux-system/weave-gitops** since 2026-09-17T20:14:57Z: dependency 'flux-system/identity' is not ready

## Every row

| Kind | Namespace | Name | State | Applied revision | Since | Message |
|---|---|---|---|---|---|---|
| HelmRelease | commerce | lago | Not ready | 1.28.0 | 2026-09-17T20:02:05Z | Helm upgrade failed for release commerce/lago with chart lago@1.28.0: failed early due to stalled resources: [Deployment/commerce/lago-billing-worker status: 'F |
| HelmRelease | crossplane-system | crossplane | Not ready | 1.15.1 | 2026-09-16T17:08:05Z | Helm upgrade failed for release crossplane-system/crossplane with chart crossplane@1.15.1: create: failed to create: admission webhook "oke-resource-leak-protec |
| Kustomization | flux-system | backstage | Not ready | main@1d76f3a | 2026-09-17T20:15:00Z | Reconciliation in progress |
| Kustomization | flux-system | calico | Not ready | main@0df0a74 | 2026-09-17T20:12:02Z | GlobalNetworkPolicy/deny-direct-ai-vendor-egress dry-run failed: no matches for kind "GlobalNetworkPolicy" in version "projectcalico.org/v3"  |
| Kustomization | flux-system | chaos | Not ready | main@cb6f6b2 | 2026-09-17T20:13:28Z | dependency 'flux-system/monitoring' is not ready |
| Kustomization | flux-system | commerce | Not ready | main@abea14d | 2026-09-17T20:01:49Z | Reconciliation in progress |
| Kustomization | flux-system | crossplane | Not ready | main@8d685ec | 2026-09-17T20:12:49Z | health check failed after 93.627988ms: failed early due to stalled resources: [HelmRelease/crossplane-system/crossplane status: 'Failed'] |
| Kustomization | flux-system | crossplane-providerconfig | Not ready | main@8d685ec | 2026-09-16T11:53:07Z | dependency 'flux-system/crossplane-providers' is not ready |
| Kustomization | flux-system | crossplane-providers | Not ready | main@8d685ec | 2026-09-16T11:53:06Z | dependency 'flux-system/crossplane' is not ready |
| Kustomization | flux-system | crossplane-storage-capability | Not ready | main@8d685ec | 2026-09-16T11:53:07Z | dependency 'flux-system/crossplane-providerconfig' is not ready |
| Kustomization | flux-system | epistemic-fabric | Not ready | main@d3c0330 | 2026-09-17T20:14:58Z | health check failed after 149.748523ms: failed early due to stalled resources: [Deployment/epistemic-fabric/epistemic-ingest-github status: 'Failed'] |
| Kustomization | flux-system | gvisor-runtime | Not ready | main@06b2a31 | 2026-09-17T20:15:13Z | Reconciliation in progress |
| Kustomization | flux-system | hermes-agent | Not ready | main@0df0a74 | 2026-09-17T20:14:56Z | health check failed after 540.163366ms: failed early due to stalled resources: [Deployment/hermes-agent/hermes-agent-gateway status: 'Failed'] |
| Kustomization | flux-system | idp-agent | Not ready | main@d3c0330 | 2026-09-17T20:14:51Z | Service/idp-agent/idp-agent-redis dry-run failed: admission webhook "validate.kyverno.svc-fail" denied the request:   resource Service/idp-agent/idp-agent-redis |
| Kustomization | flux-system | jit | Not ready | main@fd519c9 | 2026-09-17T20:12:09Z | Deployment/jit/jit-broker dry-run failed (Invalid): Deployment.apps "jit-broker" is invalid: spec.template.spec.containers[0].env[9].valueFrom: Invalid value: " |
| Kustomization | flux-system | llm | Not ready | main@d3c0330 | 2026-09-17T20:15:13Z | Reconciliation in progress |
| Kustomization | flux-system | monitoring | Not ready | main@d3c0330 | 2026-09-17T20:13:27Z | ExternalSecret/monitoring/alertmanager-telegram dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.externa |
| Kustomization | flux-system | monitoring-rules | Not ready | main@d3c0330 | 2026-09-17T20:13:13Z | dependency 'flux-system/monitoring' is not ready |
| Kustomization | flux-system | otto-gateway | Not ready | main@cd9eb71 | 2026-09-17T20:13:46Z | health check failed after 1.413741069s: failed early due to stalled resources: [Deployment/otto-gateway/otto-gateway status: 'Failed'] |
| Kustomization | flux-system | otto-golden | Not ready | main@cd9eb71 | 2026-09-17T20:14:40Z | dependency 'flux-system/otto-golden-secret' is not ready |
| Kustomization | flux-system | otto-golden-secret | Not ready | main@d3c0330 | 2026-09-17T20:14:35Z | ExternalSecret/flux-system/otto-webhook dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-secret |
| Kustomization | flux-system | prospector | Not ready | main@7453d76 | 2026-09-17T20:15:11Z | health check failed after 361.381324ms: failed early due to stalled resources: [Deployment/prospector/prospector-store-api status: 'Failed'] |
| Kustomization | flux-system | router-events | Not ready | main@0df0a74 | 2026-09-17T20:10:02Z | health check failed after 5m0.044570159s: timeout waiting for: [Deployment/llm/litellm status: 'InProgress'] |
| Kustomization | flux-system | verification | Not ready | main@06b2a31 | 2026-09-17T20:14:33Z | ExternalSecret/backstage/verdict-key-wall dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-secr |
| Kustomization | flux-system | via-negativa | Not ready | main@d3c0330 | 2026-09-17T20:15:13Z | dependency 'flux-system/llm' is not ready |
| Kustomization | flux-system | weave-gitops | Not ready | main@d3c0330 | 2026-09-17T20:14:57Z | dependency 'flux-system/identity' is not ready |
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
| Kustomization | flux-system | agent-workforce | Ready | main@d3c0330 | 2026-09-17T20:05:08Z |  |
| Kustomization | flux-system | alerts | Ready | main@d3c0330 | 2026-09-17T20:13:59Z |  |
| Kustomization | flux-system | alerts-github | Ready | main@d3c0330 | 2026-09-17T20:15:13Z |  |
| Kustomization | flux-system | alerts-secret | Ready | main@d3c0330 | 2026-09-17T20:13:52Z |  |
| Kustomization | flux-system | autoscaler | Ready | main@d3c0330 | 2026-09-17T20:13:45Z |  |
| Kustomization | flux-system | backstage-namespace | Ready | main@d3c0330 | 2026-09-17T20:12:26Z |  |
| Kustomization | flux-system | chaos-mesh | Ready | main@d3c0330 | 2026-09-17T20:12:57Z |  |
| Kustomization | flux-system | cluster-state | Ready | main@d3c0330 | 2026-09-17T20:13:40Z |  |
| Kustomization | flux-system | commerce-data | Ready | main@d3c0330 | 2026-09-17T20:14:37Z |  |
| Kustomization | flux-system | concierge | Ready | main@d3c0330 | 2026-09-17T20:14:04Z |  |
| Kustomization | flux-system | cross-node-drill | Ready | main@d3c0330 | 2026-09-17T20:12:00Z |  |
| Kustomization | flux-system | dagster | Ready | main@d3c0330 | 2026-09-17T20:14:54Z |  |
| Kustomization | flux-system | dns | Ready | main@d3c0330 | 2026-09-17T20:14:06Z |  |
| Kustomization | flux-system | drills | Ready | main@d3c0330 | 2026-09-17T20:14:19Z |  |
| Kustomization | flux-system | edge | Ready | main@d3c0330 | 2026-09-17T20:12:14Z |  |
| Kustomization | flux-system | estate-catalog | Ready | latest@sha256:e399bd3ac53bff7e1a908ea3e6 | 2026-09-17T20:14:59Z |  |
| Kustomization | flux-system | estate-db | Ready | main@d3c0330 | 2026-09-17T20:13:16Z |  |
| Kustomization | flux-system | estate-db-migrate | Ready | main@d3c0330 | 2026-09-17T20:14:18Z |  |
| Kustomization | flux-system | estate-db-operator | Ready | main@d3c0330 | 2026-09-17T20:12:11Z |  |
| Kustomization | flux-system | event-bus | Ready | main@d3c0330 | 2026-09-17T20:12:10Z |  |
| Kustomization | flux-system | external-secrets | Ready | main@d3c0330 | 2026-09-17T20:13:12Z |  |
| Kustomization | flux-system | feature-register | Ready | main@d3c0330 | 2026-09-17T20:12:31Z |  |
| Kustomization | flux-system | flux-system | Ready | main@d3c0330 | 2026-09-17T20:12:22Z |  |
| Kustomization | flux-system | flux-webhook | Ready | main@d3c0330 | 2026-09-17T20:13:50Z |  |
| Kustomization | flux-system | gateway-api-crds | Ready | v1.5.1@e7677b7 | 2026-09-17T20:11:48Z |  |
| Kustomization | flux-system | github-app-creds | Ready | main@d3c0330 | 2026-09-17T20:13:28Z |  |
| Kustomization | flux-system | guacamole | Ready | main@d3c0330 | 2026-09-17T20:04:57Z |  |
| Kustomization | flux-system | healing | Ready | main@d3c0330 | 2026-09-17T20:13:01Z |  |
| Kustomization | flux-system | healing-analyzer | Ready | main@d3c0330 | 2026-09-17T20:15:00Z |  |
| Kustomization | flux-system | healing-k8sgpt | Ready | main@d3c0330 | 2026-09-17T20:05:04Z |  |
| Kustomization | flux-system | healthchecks | Ready | main@d3c0330 | 2026-09-17T20:14:44Z |  |
| Kustomization | flux-system | hindsight | Ready | main@d3c0330 | 2026-09-17T20:15:13Z |  |
| Kustomization | flux-system | human-vault | Ready | main@d3c0330 | 2026-09-17T20:13:42Z |  |
| Kustomization | flux-system | human-vault-bridge | Ready | main@d3c0330 | 2026-09-17T20:14:17Z |  |
| Kustomization | flux-system | identity | Ready | main@d3c0330 | 2026-09-17T20:14:58Z |  |
| Kustomization | flux-system | image-automation | Ready | main@d3c0330 | 2026-09-17T20:14:38Z |  |
| Kustomization | flux-system | keda | Ready | main@d3c0330 | 2026-09-17T20:12:44Z |  |
| Kustomization | flux-system | kyverno | Ready | main@d3c0330 | 2026-09-17T20:12:36Z |  |
| Kustomization | flux-system | mcp | Ready | main@d3c0330 | 2026-09-17T20:14:45Z |  |
| Kustomization | flux-system | metrics-server | Ready | main@d3c0330 | 2026-09-17T20:13:05Z |  |
| Kustomization | flux-system | nodesoftware-operator | Ready | main@d3c0330 | 2026-09-17T20:14:45Z |  |
| Kustomization | flux-system | notify | Ready | main@d3c0330 | 2026-09-17T20:14:11Z |  |
| Kustomization | flux-system | ns-fences | Ready | main@d3c0330 | 2026-09-17T20:12:42Z |  |
| Kustomization | flux-system | observability | Ready | main@d3c0330 | 2026-09-17T20:14:50Z |  |
| Kustomization | flux-system | observability-collector | Ready | main@d3c0330 | 2026-09-17T20:12:44Z |  |
| Kustomization | flux-system | priority-classes | Ready | main@d3c0330 | 2026-09-17T20:11:38Z |  |
| Kustomization | flux-system | prospector-platform | Ready | main@d3c0330 | 2026-09-17T20:14:53Z |  |
| Kustomization | flux-system | rbac | Ready | main@d3c0330 | 2026-09-17T20:12:23Z |  |
| Kustomization | flux-system | rbac-floor | Ready | main@d3c0330 | 2026-09-17T20:12:33Z |  |
| Kustomization | flux-system | rbac-identity | Ready | main@d3c0330 | 2026-09-17T20:12:21Z |  |
| Kustomization | flux-system | reloader | Ready | main@d3c0330 | 2026-09-17T20:14:15Z |  |
| Kustomization | flux-system | research-engine | Ready | main@d3c0330 | 2026-09-17T20:15:01Z |  |
| Kustomization | flux-system | robusta | Ready | main@d3c0330 | 2026-09-17T20:14:40Z |  |
| Kustomization | flux-system | sandbox-launch | Ready | main@d3c0330 | 2026-09-17T20:13:05Z |  |
| Kustomization | flux-system | sandbox-live | Ready | sandbox/launch@4830a6e | 2026-09-17T20:14:44Z |  |
| Kustomization | flux-system | scheduling | Ready | main@d3c0330 | 2026-09-17T20:12:42Z |  |
| Kustomization | flux-system | science | Ready | main@d3c0330 | 2026-09-17T20:14:58Z |  |
| Kustomization | flux-system | searxng | Ready | main@d3c0330 | 2026-09-17T20:11:49Z |  |
| Kustomization | flux-system | secret-store | Ready | main@d3c0330 | 2026-09-17T20:13:13Z |  |
| Kustomization | flux-system | spire | Ready | main@d3c0330 | 2026-09-17T20:13:06Z |  |
| Kustomization | flux-system | staging | Ready | main@d3c0330 | 2026-09-17T20:11:57Z |  |
| Kustomization | flux-system | tailscale | Ready | main@d3c0330 | 2026-09-17T20:15:02Z |  |
| Kustomization | flux-system | temporal | Ready | main@d3c0330 | 2026-09-17T20:14:42Z |  |
| Kustomization | flux-system | trivy | Ready | main@d3c0330 | 2026-09-17T20:12:15Z |  |
