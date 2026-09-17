# Flux: what is applied

Read from the cluster receipt taken at 2026-09-17T20:45:23Z. Every Kustomization and HelmRelease, with the revision Flux last applied. **Suspended** is a switch somebody turned off on purpose (temporal, commerce, commerce-data, event-bus), not a defect; **Unknown** is a row Flux has never graded.

**121 objects: 89 ready, 31 not ready, 0 unknown, 1 suspended.**

## Not ready right now

- **HelmRelease commerce/lago** since 2026-09-17T20:44:25Z: Running 'install' action with timeout of 20m0s
- **HelmRelease crossplane-system/crossplane** since 2026-09-16T17:08:05Z: Helm upgrade failed for release crossplane-system/crossplane with chart crossplane@1.15.1: create: failed to create: admission webhook "oke-resource-leak-protection.oke.com" denied the request: OKE resource leak protection rejected the request. Cluster has 2650 secrets and the limit is 2000. See https://docs.oracle.com/iaas/Content/ContEng/Tasks/contengprotectingclustersfromresourceleaks.htm for details.
- **Kustomization flux-system/agent-workforce** since 2026-09-17T20:43:39Z: dependency 'flux-system/llm' is not ready
- **Kustomization flux-system/backstage** since 2026-09-17T20:44:17Z: health check failed after 430.809927ms: failed early due to stalled resources: [Deployment/backstage/catalogue status: 'Failed']
- **Kustomization flux-system/calico** since 2026-09-17T20:42:05Z: GlobalNetworkPolicy/deny-direct-ai-vendor-egress dry-run failed: no matches for kind "GlobalNetworkPolicy" in version "projectcalico.org/v3" 
- **Kustomization flux-system/chaos** since 2026-09-17T20:44:18Z: dependency 'flux-system/monitoring' is not ready
- **Kustomization flux-system/cluster-state** since 2026-09-17T20:43:46Z: ExternalSecret/backstage/rotation-canary dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-secrets.io": failed to call webhook: Post "https://external-secrets-webhook.external-secrets.svc:443/validate-external-secrets-io-v1-externalsecret?timeout=15s": context deadline exceeded 
- **Kustomization flux-system/commerce** since 2026-09-17T20:41:55Z: dependency 'flux-system/commerce-data' is not ready
- **Kustomization flux-system/commerce-data** since 2026-09-17T20:44:11Z: ExternalSecret/commerce/commerce-payment-provider dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-secrets.io": failed to call webhook: Post "https://external-secrets-webhook.external-secrets.svc:443/validate-external-secrets-io-v1-externalsecret?timeout=15s": context deadline exceeded 
- **Kustomization flux-system/crossplane** since 2026-09-17T20:43:16Z: health check failed after 44.983854ms: failed early due to stalled resources: [HelmRelease/crossplane-system/crossplane status: 'Failed']
- **Kustomization flux-system/crossplane-providerconfig** since 2026-09-16T11:53:07Z: dependency 'flux-system/crossplane-providers' is not ready
- **Kustomization flux-system/crossplane-providers** since 2026-09-16T11:53:06Z: dependency 'flux-system/crossplane' is not ready
- **Kustomization flux-system/crossplane-storage-capability** since 2026-09-16T11:53:07Z: dependency 'flux-system/crossplane-providerconfig' is not ready
- **Kustomization flux-system/epistemic-fabric** since 2026-09-17T20:35:17Z: health check failed after 179.757613ms: failed early due to stalled resources: [Deployment/epistemic-fabric/epistemic-ingest-github status: 'Failed']
- **Kustomization flux-system/healing-k8sgpt** since 2026-09-17T20:45:06Z: dependency 'flux-system/llm' is not ready
- **Kustomization flux-system/hermes-agent** since 2026-09-17T20:35:18Z: health check failed after 254.097468ms: failed early due to stalled resources: [Deployment/hermes-agent/hermes-agent-gateway status: 'Failed']
- **Kustomization flux-system/hindsight** since 2026-09-17T20:35:53Z: dependency 'flux-system/llm' is not ready
- **Kustomization flux-system/human-vault** since 2026-09-17T20:44:40Z: ClusterSecretStore/human-vault dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.clustersecretstore.external-secrets.io": failed to call webhook: Post "https://external-secrets-webhook.external-secrets.svc:443/validate-external-secrets-io-v1-clustersecretstore?timeout=15s": context deadline exceeded 
- **Kustomization flux-system/human-vault-bridge** since 2026-09-17T20:35:10Z: dependency 'flux-system/human-vault' is not ready
- **Kustomization flux-system/idp-agent** since 2026-09-17T20:45:16Z: Deployment/idp-agent/idp-engine dry-run failed (Invalid): Deployment.apps "idp-engine" is invalid: spec.template.spec.containers[0].env[5].valueFrom: Invalid value: "": may not be specified when `value` is not empty 
- **Kustomization flux-system/jit** since 2026-09-17T20:42:14Z: Deployment/jit/jit-broker dry-run failed (Invalid): Deployment.apps "jit-broker" is invalid: spec.template.spec.containers[0].env[9].valueFrom: Invalid value: "": may not be specified when `value` is not empty 
- **Kustomization flux-system/llm** since 2026-09-17T20:44:36Z: ExternalSecret/llm/litellm-cache dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-secrets.io": failed to call webhook: Post "https://external-secrets-webhook.external-secrets.svc:443/validate-external-secrets-io-v1-externalsecret?timeout=15s": context deadline exceeded 
- **Kustomization flux-system/mcp** since 2026-09-17T20:45:00Z: ExternalSecret/mcp/ghcr-pull dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-secrets.io": failed to call webhook: Post "https://external-secrets-webhook.external-secrets.svc:443/validate-external-secrets-io-v1-externalsecret?timeout=15s": context deadline exceeded 
- **Kustomization flux-system/monitoring** since 2026-09-17T20:43:52Z: ExternalSecret/monitoring/alertmanager-telegram dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-secrets.io": failed to call webhook: Post "https://external-secrets-webhook.external-secrets.svc:443/validate-external-secrets-io-v1-externalsecret?timeout=15s": context deadline exceeded 
- **Kustomization flux-system/monitoring-rules** since 2026-09-17T20:44:37Z: dependency 'flux-system/monitoring' is not ready
- **Kustomization flux-system/otto-gateway** since 2026-09-17T20:44:38Z: ExternalSecret/otto-gateway/hermes-agent-env dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-secrets.io": failed to call webhook: Post "https://external-secrets-webhook.external-secrets.svc:443/validate-external-secrets-io-v1-externalsecret?timeout=15s": context deadline exceeded 
- **Kustomization flux-system/otto-golden** since 2026-09-17T20:45:15Z: health check failed after 697.497094ms: failed early due to stalled resources: [Deployment/otto-golden/otto-golden status: 'Failed']
- **Kustomization flux-system/prospector** since 2026-09-17T20:35:29Z: health check failed after 409.619215ms: failed early due to stalled resources: [Deployment/prospector/prospector-store-api status: 'Failed']
- **Kustomization flux-system/research-engine** since 2026-09-17T20:36:00Z: dependency 'flux-system/llm' is not ready
- **Kustomization flux-system/router-events** since 2026-09-17T20:40:06Z: health check failed after 5m0.052007298s: timeout waiting for: [Deployment/llm/litellm status: 'InProgress']
- **Kustomization flux-system/via-negativa** since 2026-09-17T20:35:55Z: dependency 'flux-system/llm' is not ready

## Every row

| Kind | Namespace | Name | State | Applied revision | Since | Message |
|---|---|---|---|---|---|---|
| HelmRelease | commerce | lago | Not ready | 1.28.0 | 2026-09-17T20:44:25Z | Running 'install' action with timeout of 20m0s |
| HelmRelease | crossplane-system | crossplane | Not ready | 1.15.1 | 2026-09-16T17:08:05Z | Helm upgrade failed for release crossplane-system/crossplane with chart crossplane@1.15.1: create: failed to create: admission webhook "oke-resource-leak-protec |
| Kustomization | flux-system | agent-workforce | Not ready | main@d3c0330 | 2026-09-17T20:43:39Z | dependency 'flux-system/llm' is not ready |
| Kustomization | flux-system | backstage | Not ready | main@1d76f3a | 2026-09-17T20:44:17Z | health check failed after 430.809927ms: failed early due to stalled resources: [Deployment/backstage/catalogue status: 'Failed'] |
| Kustomization | flux-system | calico | Not ready | main@0df0a74 | 2026-09-17T20:42:05Z | GlobalNetworkPolicy/deny-direct-ai-vendor-egress dry-run failed: no matches for kind "GlobalNetworkPolicy" in version "projectcalico.org/v3"  |
| Kustomization | flux-system | chaos | Not ready | main@cb6f6b2 | 2026-09-17T20:44:18Z | dependency 'flux-system/monitoring' is not ready |
| Kustomization | flux-system | cluster-state | Not ready | main@d3c0330 | 2026-09-17T20:43:46Z | ExternalSecret/backstage/rotation-canary dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-secre |
| Kustomization | flux-system | commerce | Not ready | main@abea14d | 2026-09-17T20:41:55Z | dependency 'flux-system/commerce-data' is not ready |
| Kustomization | flux-system | commerce-data | Not ready | main@d3c0330 | 2026-09-17T20:44:11Z | ExternalSecret/commerce/commerce-payment-provider dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.exter |
| Kustomization | flux-system | crossplane | Not ready | main@8d685ec | 2026-09-17T20:43:16Z | health check failed after 44.983854ms: failed early due to stalled resources: [HelmRelease/crossplane-system/crossplane status: 'Failed'] |
| Kustomization | flux-system | crossplane-providerconfig | Not ready | main@8d685ec | 2026-09-16T11:53:07Z | dependency 'flux-system/crossplane-providers' is not ready |
| Kustomization | flux-system | crossplane-providers | Not ready | main@8d685ec | 2026-09-16T11:53:06Z | dependency 'flux-system/crossplane' is not ready |
| Kustomization | flux-system | crossplane-storage-capability | Not ready | main@8d685ec | 2026-09-16T11:53:07Z | dependency 'flux-system/crossplane-providerconfig' is not ready |
| Kustomization | flux-system | epistemic-fabric | Not ready | main@d3c0330 | 2026-09-17T20:35:17Z | health check failed after 179.757613ms: failed early due to stalled resources: [Deployment/epistemic-fabric/epistemic-ingest-github status: 'Failed'] |
| Kustomization | flux-system | healing-k8sgpt | Not ready | main@d3c0330 | 2026-09-17T20:45:06Z | dependency 'flux-system/llm' is not ready |
| Kustomization | flux-system | hermes-agent | Not ready | main@0df0a74 | 2026-09-17T20:35:18Z | health check failed after 254.097468ms: failed early due to stalled resources: [Deployment/hermes-agent/hermes-agent-gateway status: 'Failed'] |
| Kustomization | flux-system | hindsight | Not ready | main@d3c0330 | 2026-09-17T20:35:53Z | dependency 'flux-system/llm' is not ready |
| Kustomization | flux-system | human-vault | Not ready | main@d3c0330 | 2026-09-17T20:44:40Z | ClusterSecretStore/human-vault dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.clustersecretstore.external-secrets.io" |
| Kustomization | flux-system | human-vault-bridge | Not ready | main@d3c0330 | 2026-09-17T20:35:10Z | dependency 'flux-system/human-vault' is not ready |
| Kustomization | flux-system | idp-agent | Not ready | main@d3c0330 | 2026-09-17T20:45:16Z | Deployment/idp-agent/idp-engine dry-run failed (Invalid): Deployment.apps "idp-engine" is invalid: spec.template.spec.containers[0].env[5].valueFrom: Invalid va |
| Kustomization | flux-system | jit | Not ready | main@fd519c9 | 2026-09-17T20:42:14Z | Deployment/jit/jit-broker dry-run failed (Invalid): Deployment.apps "jit-broker" is invalid: spec.template.spec.containers[0].env[9].valueFrom: Invalid value: " |
| Kustomization | flux-system | llm | Not ready | main@d3c0330 | 2026-09-17T20:44:36Z | ExternalSecret/llm/litellm-cache dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-secrets.io":  |
| Kustomization | flux-system | mcp | Not ready | main@d3c0330 | 2026-09-17T20:45:00Z | ExternalSecret/mcp/ghcr-pull dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-secrets.io": fail |
| Kustomization | flux-system | monitoring | Not ready | main@d3c0330 | 2026-09-17T20:43:52Z | ExternalSecret/monitoring/alertmanager-telegram dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.externa |
| Kustomization | flux-system | monitoring-rules | Not ready | main@d3c0330 | 2026-09-17T20:44:37Z | dependency 'flux-system/monitoring' is not ready |
| Kustomization | flux-system | otto-gateway | Not ready | main@cd9eb71 | 2026-09-17T20:44:38Z | ExternalSecret/otto-gateway/hermes-agent-env dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-s |
| Kustomization | flux-system | otto-golden | Not ready | main@cd9eb71 | 2026-09-17T20:45:15Z | health check failed after 697.497094ms: failed early due to stalled resources: [Deployment/otto-golden/otto-golden status: 'Failed'] |
| Kustomization | flux-system | prospector | Not ready | main@7453d76 | 2026-09-17T20:35:29Z | health check failed after 409.619215ms: failed early due to stalled resources: [Deployment/prospector/prospector-store-api status: 'Failed'] |
| Kustomization | flux-system | research-engine | Not ready | main@d3c0330 | 2026-09-17T20:36:00Z | dependency 'flux-system/llm' is not ready |
| Kustomization | flux-system | router-events | Not ready | main@0df0a74 | 2026-09-17T20:40:06Z | health check failed after 5m0.052007298s: timeout waiting for: [Deployment/llm/litellm status: 'InProgress'] |
| Kustomization | flux-system | via-negativa | Not ready | main@d3c0330 | 2026-09-17T20:35:55Z | dependency 'flux-system/llm' is not ready |
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
| Kustomization | flux-system | alerts | Ready | main@d3c0330 | 2026-09-17T20:44:55Z |  |
| Kustomization | flux-system | alerts-github | Ready | main@d3c0330 | 2026-09-17T20:35:32Z |  |
| Kustomization | flux-system | alerts-secret | Ready | main@d3c0330 | 2026-09-17T20:44:02Z |  |
| Kustomization | flux-system | autoscaler | Ready | main@d3c0330 | 2026-09-17T20:44:31Z |  |
| Kustomization | flux-system | backstage-namespace | Ready | main@d3c0330 | 2026-09-17T20:43:06Z |  |
| Kustomization | flux-system | chaos-mesh | Ready | main@d3c0330 | 2026-09-17T20:43:02Z |  |
| Kustomization | flux-system | concierge | Ready | main@d3c0330 | 2026-09-17T20:44:37Z |  |
| Kustomization | flux-system | cross-node-drill | Ready | main@d3c0330 | 2026-09-17T20:41:51Z |  |
| Kustomization | flux-system | dagster | Ready | main@d3c0330 | 2026-09-17T20:44:33Z |  |
| Kustomization | flux-system | dns | Ready | main@d3c0330 | 2026-09-17T20:45:03Z |  |
| Kustomization | flux-system | drills | Ready | main@d3c0330 | 2026-09-17T20:44:42Z |  |
| Kustomization | flux-system | edge | Ready | main@d3c0330 | 2026-09-17T20:42:39Z |  |
| Kustomization | flux-system | estate-catalog | Ready | latest@sha256:861a12927adfc2f1d2b147cdc6 | 2026-09-17T20:45:07Z |  |
| Kustomization | flux-system | estate-db | Ready | main@d3c0330 | 2026-09-17T20:43:45Z |  |
| Kustomization | flux-system | estate-db-migrate | Ready | main@d3c0330 | 2026-09-17T20:44:02Z |  |
| Kustomization | flux-system | estate-db-operator | Ready | main@d3c0330 | 2026-09-17T20:42:40Z |  |
| Kustomization | flux-system | event-bus | Ready | main@d3c0330 | 2026-09-17T20:42:27Z |  |
| Kustomization | flux-system | external-secrets | Ready | main@d3c0330 | 2026-09-17T20:43:24Z |  |
| Kustomization | flux-system | feature-register | Ready | main@d3c0330 | 2026-09-17T20:43:19Z |  |
| Kustomization | flux-system | flux-system | Ready | main@d3c0330 | 2026-09-17T20:43:13Z |  |
| Kustomization | flux-system | flux-webhook | Ready | main@d3c0330 | 2026-09-17T20:44:36Z |  |
| Kustomization | flux-system | gateway-api-crds | Ready | v1.5.1@e7677b7 | 2026-09-17T20:41:47Z |  |
| Kustomization | flux-system | github-app-creds | Ready | main@d3c0330 | 2026-09-17T20:44:04Z |  |
| Kustomization | flux-system | guacamole | Ready | main@d3c0330 | 2026-09-17T20:44:06Z |  |
| Kustomization | flux-system | gvisor-runtime | Ready | main@d3c0330 | 2026-09-17T20:45:14Z |  |
| Kustomization | flux-system | healing | Ready | main@d3c0330 | 2026-09-17T20:43:34Z |  |
| Kustomization | flux-system | healing-analyzer | Ready | main@d3c0330 | 2026-09-17T20:44:39Z |  |
| Kustomization | flux-system | healthchecks | Ready | main@d3c0330 | 2026-09-17T20:44:06Z |  |
| Kustomization | flux-system | identity | Ready | main@d3c0330 | 2026-09-17T20:35:30Z |  |
| Kustomization | flux-system | image-automation | Ready | main@d3c0330 | 2026-09-17T20:45:10Z |  |
| Kustomization | flux-system | keda | Ready | main@d3c0330 | 2026-09-17T20:42:36Z |  |
| Kustomization | flux-system | kyverno | Ready | main@d3c0330 | 2026-09-17T20:43:02Z |  |
| Kustomization | flux-system | metrics-server | Ready | main@d3c0330 | 2026-09-17T20:42:42Z |  |
| Kustomization | flux-system | nodesoftware-operator | Ready | main@d3c0330 | 2026-09-17T20:44:14Z |  |
| Kustomization | flux-system | notify | Ready | main@d3c0330 | 2026-09-17T20:45:08Z |  |
| Kustomization | flux-system | ns-fences | Ready | main@d3c0330 | 2026-09-17T20:43:32Z |  |
| Kustomization | flux-system | observability | Ready | main@d3c0330 | 2026-09-17T20:44:16Z |  |
| Kustomization | flux-system | observability-collector | Ready | main@d3c0330 | 2026-09-17T20:43:20Z |  |
| Kustomization | flux-system | otto-golden-secret | Ready | main@d3c0330 | 2026-09-17T20:44:54Z |  |
| Kustomization | flux-system | priority-classes | Ready | main@d3c0330 | 2026-09-17T20:42:22Z |  |
| Kustomization | flux-system | prospector-platform | Ready | main@d3c0330 | 2026-09-17T20:44:34Z |  |
| Kustomization | flux-system | rbac | Ready | main@d3c0330 | 2026-09-17T20:43:18Z |  |
| Kustomization | flux-system | rbac-floor | Ready | main@d3c0330 | 2026-09-17T20:42:23Z |  |
| Kustomization | flux-system | rbac-identity | Ready | main@d3c0330 | 2026-09-17T20:43:41Z |  |
| Kustomization | flux-system | reloader | Ready | main@d3c0330 | 2026-09-17T20:35:27Z |  |
| Kustomization | flux-system | robusta | Ready | main@d3c0330 | 2026-09-17T20:35:06Z |  |
| Kustomization | flux-system | sandbox-launch | Ready | main@d3c0330 | 2026-09-17T20:43:28Z |  |
| Kustomization | flux-system | sandbox-live | Ready | sandbox/launch@4830a6e | 2026-09-17T20:44:21Z |  |
| Kustomization | flux-system | scheduling | Ready | main@d3c0330 | 2026-09-17T20:42:19Z |  |
| Kustomization | flux-system | science | Ready | main@d3c0330 | 2026-09-17T20:44:26Z |  |
| Kustomization | flux-system | searxng | Ready | main@d3c0330 | 2026-09-17T20:42:39Z |  |
| Kustomization | flux-system | secret-store | Ready | main@d3c0330 | 2026-09-17T20:43:12Z |  |
| Kustomization | flux-system | spire | Ready | main@d3c0330 | 2026-09-17T20:44:00Z |  |
| Kustomization | flux-system | staging | Ready | main@d3c0330 | 2026-09-17T20:41:34Z |  |
| Kustomization | flux-system | tailscale | Ready | main@d3c0330 | 2026-09-17T20:35:28Z |  |
| Kustomization | flux-system | temporal | Ready | main@d3c0330 | 2026-09-17T20:44:11Z |  |
| Kustomization | flux-system | trivy | Ready | main@d3c0330 | 2026-09-17T20:43:26Z |  |
| Kustomization | flux-system | verification | Ready | main@d3c0330 | 2026-09-17T20:45:09Z |  |
| Kustomization | flux-system | weave-gitops | Ready | main@d3c0330 | 2026-09-17T20:35:12Z |  |
