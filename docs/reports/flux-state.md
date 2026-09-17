# Flux: what is applied

Read from the cluster receipt taken at 2026-09-17T21:45:19Z. Every Kustomization and HelmRelease, with the revision Flux last applied. **Suspended** is a switch somebody turned off on purpose (temporal, commerce, commerce-data, event-bus), not a defect; **Unknown** is a row Flux has never graded.

**121 objects: 98 ready, 22 not ready, 0 unknown, 1 suspended.**

## Not ready right now

- **HelmRelease commerce/lago** since 2026-09-17T21:39:08Z: Running 'install' action with timeout of 20m0s
- **HelmRelease crossplane-system/crossplane** since 2026-09-16T17:08:05Z: Helm upgrade failed for release crossplane-system/crossplane with chart crossplane@1.15.1: create: failed to create: admission webhook "oke-resource-leak-protection.oke.com" denied the request: OKE resource leak protection rejected the request. Cluster has 2650 secrets and the limit is 2000. See https://docs.oracle.com/iaas/Content/ContEng/Tasks/contengprotectingclustersfromresourceleaks.htm for details.
- **Kustomization flux-system/backstage** since 2026-09-17T21:36:14Z: ExternalSecret/backstage/backstage-github dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-secrets.io": failed to call webhook: Post "https://external-secrets-webhook.external-secrets.svc:443/validate-external-secrets-io-v1-externalsecret?timeout=15s": context deadline exceeded 
- **Kustomization flux-system/calico** since 2026-09-17T21:42:13Z: GlobalNetworkPolicy/deny-direct-ai-vendor-egress dry-run failed: no matches for kind "GlobalNetworkPolicy" in version "projectcalico.org/v3" 
- **Kustomization flux-system/chaos** since 2026-09-17T21:36:25Z: dependency 'flux-system/backstage' is not ready
- **Kustomization flux-system/commerce** since 2026-09-17T21:40:00Z: Reconciliation in progress
- **Kustomization flux-system/commerce-data** since 2026-09-17T21:45:09Z: Reconciliation in progress
- **Kustomization flux-system/crossplane** since 2026-09-17T21:43:27Z: health check failed after 92.507895ms: failed early due to stalled resources: [HelmRelease/crossplane-system/crossplane status: 'Failed']
- **Kustomization flux-system/crossplane-providerconfig** since 2026-09-16T11:53:07Z: dependency 'flux-system/crossplane-providers' is not ready
- **Kustomization flux-system/crossplane-providers** since 2026-09-16T11:53:06Z: dependency 'flux-system/crossplane' is not ready
- **Kustomization flux-system/crossplane-storage-capability** since 2026-09-16T11:53:07Z: dependency 'flux-system/crossplane-providerconfig' is not ready
- **Kustomization flux-system/epistemic-fabric** since 2026-09-17T21:36:07Z: health check failed after 363.348186ms: failed early due to stalled resources: [Deployment/epistemic-fabric/epistemic-ingest-github status: 'Failed']
- **Kustomization flux-system/flux-webhook** since 2026-09-17T21:45:00Z: Reconciliation in progress
- **Kustomization flux-system/github-app-creds** since 2026-09-17T21:45:05Z: ExternalSecret/flux-system/github-app dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-secrets.io": failed to call webhook: Post "https://external-secrets-webhook.external-secrets.svc:443/validate-external-secrets-io-v1-externalsecret?timeout=15s": context deadline exceeded 
- **Kustomization flux-system/hermes-agent** since 2026-09-17T21:36:25Z: ExternalSecret/hermes-agent/hermes-agent-a2a dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-secrets.io": failed to call webhook: Post "https://external-secrets-webhook.external-secrets.svc:443/validate-external-secrets-io-v1-externalsecret?timeout=15s": context deadline exceeded 
- **Kustomization flux-system/idp-agent** since 2026-09-17T21:35:38Z: Service/idp-agent/idp-agent-redis dry-run failed: admission webhook "validate.kyverno.svc-fail" denied the request:   resource Service/idp-agent/idp-agent-redis was blocked due to the following policies   require-catalogue-entity:   service-names-its-entity: 'validation error: Service idp-agent/idp-agent-redis serves a port but names no catalogue entity. Add the label backstage.io/kubernetes-id with the entity name from backstage/**/catalog-info.yaml, and a founder surface if a person opens it (docs/policy/every-interface-is-a-door.md). rule service-names-its-entity failed at path /metadata/labels/backstage.io/kubernetes-id/'  
- **Kustomization flux-system/jit** since 2026-09-17T21:42:27Z: Deployment/jit/jit-broker dry-run failed (Invalid): Deployment.apps "jit-broker" is invalid: spec.template.spec.containers[0].env[9].valueFrom: Invalid value: "": may not be specified when `value` is not empty 
- **Kustomization flux-system/otto-gateway** since 2026-09-17T21:35:38Z: health check failed after 1.558781581s: failed early due to stalled resources: [Deployment/otto-gateway/otto-gateway status: 'Failed']
- **Kustomization flux-system/otto-golden** since 2026-09-17T21:35:45Z: health check failed after 586.792357ms: failed early due to stalled resources: [Deployment/otto-golden/otto-golden status: 'Failed']
- **Kustomization flux-system/prospector** since 2026-09-17T21:45:12Z: Reconciliation in progress
- **Kustomization flux-system/router-events** since 2026-09-17T21:35:52Z: health check failed after 5m0.152730182s: timeout waiting for: [Deployment/llm/litellm status: 'InProgress']
- **Kustomization flux-system/via-negativa** since 2026-09-17T21:35:42Z: health check failed after 311.478977ms: failed early due to stalled resources: [Deployment/via-negativa/via-negativa-rca status: 'Failed']

## Every row

| Kind | Namespace | Name | State | Applied revision | Since | Message |
|---|---|---|---|---|---|---|
| HelmRelease | commerce | lago | Not ready | 1.28.0 | 2026-09-17T21:39:08Z | Running 'install' action with timeout of 20m0s |
| HelmRelease | crossplane-system | crossplane | Not ready | 1.15.1 | 2026-09-16T17:08:05Z | Helm upgrade failed for release crossplane-system/crossplane with chart crossplane@1.15.1: create: failed to create: admission webhook "oke-resource-leak-protec |
| Kustomization | flux-system | backstage | Not ready | main@1d76f3a | 2026-09-17T21:36:14Z | ExternalSecret/backstage/backstage-github dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-secr |
| Kustomization | flux-system | calico | Not ready | main@0df0a74 | 2026-09-17T21:42:13Z | GlobalNetworkPolicy/deny-direct-ai-vendor-egress dry-run failed: no matches for kind "GlobalNetworkPolicy" in version "projectcalico.org/v3"  |
| Kustomization | flux-system | chaos | Not ready | main@cb6f6b2 | 2026-09-17T21:36:25Z | dependency 'flux-system/backstage' is not ready |
| Kustomization | flux-system | commerce | Not ready | main@abea14d | 2026-09-17T21:40:00Z | Reconciliation in progress |
| Kustomization | flux-system | commerce-data | Not ready | main@d3c0330 | 2026-09-17T21:45:09Z | Reconciliation in progress |
| Kustomization | flux-system | crossplane | Not ready | main@8d685ec | 2026-09-17T21:43:27Z | health check failed after 92.507895ms: failed early due to stalled resources: [HelmRelease/crossplane-system/crossplane status: 'Failed'] |
| Kustomization | flux-system | crossplane-providerconfig | Not ready | main@8d685ec | 2026-09-16T11:53:07Z | dependency 'flux-system/crossplane-providers' is not ready |
| Kustomization | flux-system | crossplane-providers | Not ready | main@8d685ec | 2026-09-16T11:53:06Z | dependency 'flux-system/crossplane' is not ready |
| Kustomization | flux-system | crossplane-storage-capability | Not ready | main@8d685ec | 2026-09-16T11:53:07Z | dependency 'flux-system/crossplane-providerconfig' is not ready |
| Kustomization | flux-system | epistemic-fabric | Not ready | main@d3c0330 | 2026-09-17T21:36:07Z | health check failed after 363.348186ms: failed early due to stalled resources: [Deployment/epistemic-fabric/epistemic-ingest-github status: 'Failed'] |
| Kustomization | flux-system | flux-webhook | Not ready | main@d3c0330 | 2026-09-17T21:45:00Z | Reconciliation in progress |
| Kustomization | flux-system | github-app-creds | Not ready | main@d3c0330 | 2026-09-17T21:45:05Z | ExternalSecret/flux-system/github-app dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-secrets. |
| Kustomization | flux-system | hermes-agent | Not ready | main@0df0a74 | 2026-09-17T21:36:25Z | ExternalSecret/hermes-agent/hermes-agent-a2a dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-s |
| Kustomization | flux-system | idp-agent | Not ready | main@d3c0330 | 2026-09-17T21:35:38Z | Service/idp-agent/idp-agent-redis dry-run failed: admission webhook "validate.kyverno.svc-fail" denied the request:   resource Service/idp-agent/idp-agent-redis |
| Kustomization | flux-system | jit | Not ready | main@fd519c9 | 2026-09-17T21:42:27Z | Deployment/jit/jit-broker dry-run failed (Invalid): Deployment.apps "jit-broker" is invalid: spec.template.spec.containers[0].env[9].valueFrom: Invalid value: " |
| Kustomization | flux-system | otto-gateway | Not ready | main@cd9eb71 | 2026-09-17T21:35:38Z | health check failed after 1.558781581s: failed early due to stalled resources: [Deployment/otto-gateway/otto-gateway status: 'Failed'] |
| Kustomization | flux-system | otto-golden | Not ready | main@cd9eb71 | 2026-09-17T21:35:45Z | health check failed after 586.792357ms: failed early due to stalled resources: [Deployment/otto-golden/otto-golden status: 'Failed'] |
| Kustomization | flux-system | prospector | Not ready | main@7453d76 | 2026-09-17T21:45:12Z | Reconciliation in progress |
| Kustomization | flux-system | router-events | Not ready | main@0df0a74 | 2026-09-17T21:35:52Z | health check failed after 5m0.152730182s: timeout waiting for: [Deployment/llm/litellm status: 'InProgress'] |
| Kustomization | flux-system | via-negativa | Not ready | main@d3c0330 | 2026-09-17T21:35:42Z | health check failed after 311.478977ms: failed early due to stalled resources: [Deployment/via-negativa/via-negativa-rca status: 'Failed'] |
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
| Kustomization | flux-system | agent-workforce | Ready | main@d3c0330 | 2026-09-17T21:36:16Z |  |
| Kustomization | flux-system | alerts | Ready | main@d3c0330 | 2026-09-17T21:35:54Z |  |
| Kustomization | flux-system | alerts-github | Ready | main@d3c0330 | 2026-09-17T21:36:20Z |  |
| Kustomization | flux-system | alerts-secret | Ready | main@d3c0330 | 2026-09-17T21:44:23Z |  |
| Kustomization | flux-system | autoscaler | Ready | main@d3c0330 | 2026-09-17T21:35:52Z |  |
| Kustomization | flux-system | backstage-namespace | Ready | main@d3c0330 | 2026-09-17T21:43:14Z |  |
| Kustomization | flux-system | chaos-mesh | Ready | main@d3c0330 | 2026-09-17T21:43:51Z |  |
| Kustomization | flux-system | cluster-state | Ready | main@d3c0330 | 2026-09-17T21:43:48Z |  |
| Kustomization | flux-system | concierge | Ready | main@d3c0330 | 2026-09-17T21:35:40Z |  |
| Kustomization | flux-system | cross-node-drill | Ready | main@d3c0330 | 2026-09-17T21:41:52Z |  |
| Kustomization | flux-system | dagster | Ready | main@d3c0330 | 2026-09-17T21:36:07Z |  |
| Kustomization | flux-system | dns | Ready | main@d3c0330 | 2026-09-17T21:37:25Z |  |
| Kustomization | flux-system | drills | Ready | main@d3c0330 | 2026-09-17T21:36:02Z |  |
| Kustomization | flux-system | edge | Ready | main@d3c0330 | 2026-09-17T21:42:40Z |  |
| Kustomization | flux-system | estate-catalog | Ready | latest@sha256:861a12927adfc2f1d2b147cdc6 | 2026-09-17T21:38:19Z |  |
| Kustomization | flux-system | estate-db | Ready | main@d3c0330 | 2026-09-17T21:44:22Z |  |
| Kustomization | flux-system | estate-db-migrate | Ready | main@d3c0330 | 2026-09-17T21:35:45Z |  |
| Kustomization | flux-system | estate-db-operator | Ready | main@d3c0330 | 2026-09-17T21:43:14Z |  |
| Kustomization | flux-system | event-bus | Ready | main@d3c0330 | 2026-09-17T21:42:07Z |  |
| Kustomization | flux-system | external-secrets | Ready | main@d3c0330 | 2026-09-17T21:43:14Z |  |
| Kustomization | flux-system | feature-register | Ready | main@d3c0330 | 2026-09-17T21:42:25Z |  |
| Kustomization | flux-system | flux-system | Ready | main@d3c0330 | 2026-09-17T21:43:30Z |  |
| Kustomization | flux-system | gateway-api-crds | Ready | v1.5.1@e7677b7 | 2026-09-17T21:41:39Z |  |
| Kustomization | flux-system | guacamole | Ready | main@d3c0330 | 2026-09-17T21:36:30Z |  |
| Kustomization | flux-system | gvisor-runtime | Ready | main@d3c0330 | 2026-09-17T21:44:28Z |  |
| Kustomization | flux-system | healing | Ready | main@d3c0330 | 2026-09-17T21:43:52Z |  |
| Kustomization | flux-system | healing-analyzer | Ready | main@d3c0330 | 2026-09-17T21:37:33Z |  |
| Kustomization | flux-system | healing-k8sgpt | Ready | main@d3c0330 | 2026-09-17T21:37:00Z |  |
| Kustomization | flux-system | healthchecks | Ready | main@d3c0330 | 2026-09-17T21:36:14Z |  |
| Kustomization | flux-system | hindsight | Ready | main@d3c0330 | 2026-09-17T21:36:13Z |  |
| Kustomization | flux-system | human-vault | Ready | main@d3c0330 | 2026-09-17T21:35:36Z |  |
| Kustomization | flux-system | human-vault-bridge | Ready | main@d3c0330 | 2026-09-17T21:35:45Z |  |
| Kustomization | flux-system | identity | Ready | main@d3c0330 | 2026-09-17T21:37:19Z |  |
| Kustomization | flux-system | image-automation | Ready | main@d3c0330 | 2026-09-17T21:36:12Z |  |
| Kustomization | flux-system | keda | Ready | main@d3c0330 | 2026-09-17T21:43:34Z |  |
| Kustomization | flux-system | kyverno | Ready | main@d3c0330 | 2026-09-17T21:41:51Z |  |
| Kustomization | flux-system | llm | Ready | main@d3c0330 | 2026-09-17T21:45:08Z |  |
| Kustomization | flux-system | mcp | Ready | main@d3c0330 | 2026-09-17T21:37:48Z |  |
| Kustomization | flux-system | metrics-server | Ready | main@d3c0330 | 2026-09-17T21:42:59Z |  |
| Kustomization | flux-system | monitoring | Ready | main@d3c0330 | 2026-09-17T21:43:46Z |  |
| Kustomization | flux-system | monitoring-rules | Ready | main@d3c0330 | 2026-09-17T21:34:57Z |  |
| Kustomization | flux-system | nodesoftware-operator | Ready | main@d3c0330 | 2026-09-17T21:45:07Z |  |
| Kustomization | flux-system | notify | Ready | main@d3c0330 | 2026-09-17T21:36:08Z |  |
| Kustomization | flux-system | ns-fences | Ready | main@d3c0330 | 2026-09-17T21:45:00Z |  |
| Kustomization | flux-system | observability | Ready | main@d3c0330 | 2026-09-17T21:36:05Z |  |
| Kustomization | flux-system | observability-collector | Ready | main@d3c0330 | 2026-09-17T21:44:38Z |  |
| Kustomization | flux-system | otto-golden-secret | Ready | main@d3c0330 | 2026-09-17T21:44:08Z |  |
| Kustomization | flux-system | priority-classes | Ready | main@d3c0330 | 2026-09-17T21:42:05Z |  |
| Kustomization | flux-system | prospector-platform | Ready | main@d3c0330 | 2026-09-17T21:37:34Z |  |
| Kustomization | flux-system | rbac | Ready | main@d3c0330 | 2026-09-17T21:43:27Z |  |
| Kustomization | flux-system | rbac-floor | Ready | main@d3c0330 | 2026-09-17T21:42:04Z |  |
| Kustomization | flux-system | rbac-identity | Ready | main@d3c0330 | 2026-09-17T21:44:01Z |  |
| Kustomization | flux-system | reloader | Ready | main@d3c0330 | 2026-09-17T21:37:37Z |  |
| Kustomization | flux-system | research-engine | Ready | main@d3c0330 | 2026-09-17T21:36:16Z |  |
| Kustomization | flux-system | robusta | Ready | main@d3c0330 | 2026-09-17T21:36:00Z |  |
| Kustomization | flux-system | sandbox-launch | Ready | main@d3c0330 | 2026-09-17T21:43:35Z |  |
| Kustomization | flux-system | sandbox-live | Ready | sandbox/launch@4830a6e | 2026-09-17T21:44:26Z |  |
| Kustomization | flux-system | scheduling | Ready | main@d3c0330 | 2026-09-17T21:42:28Z |  |
| Kustomization | flux-system | science | Ready | main@d3c0330 | 2026-09-17T21:36:17Z |  |
| Kustomization | flux-system | searxng | Ready | main@d3c0330 | 2026-09-17T21:43:07Z |  |
| Kustomization | flux-system | secret-store | Ready | main@d3c0330 | 2026-09-17T21:42:33Z |  |
| Kustomization | flux-system | spire | Ready | main@d3c0330 | 2026-09-17T21:42:33Z |  |
| Kustomization | flux-system | staging | Ready | main@d3c0330 | 2026-09-17T21:41:11Z |  |
| Kustomization | flux-system | tailscale | Ready | main@d3c0330 | 2026-09-17T21:40:26Z |  |
| Kustomization | flux-system | temporal | Ready | main@d3c0330 | 2026-09-17T21:36:29Z |  |
| Kustomization | flux-system | trivy | Ready | main@d3c0330 | 2026-09-17T21:43:31Z |  |
| Kustomization | flux-system | verification | Ready | main@d3c0330 | 2026-09-17T21:45:05Z |  |
| Kustomization | flux-system | weave-gitops | Ready | main@d3c0330 | 2026-09-17T21:45:06Z |  |
