# Flux: what is applied

Read from the cluster receipt taken at 2026-09-17T19:45:24Z. Every Kustomization and HelmRelease, with the revision Flux last applied. **Suspended** is a switch somebody turned off on purpose (temporal, commerce, commerce-data, event-bus), not a defect; **Unknown** is a row Flux has never graded.

**121 objects: 87 ready, 33 not ready, 0 unknown, 1 suspended.**

## Not ready right now

- **HelmRelease commerce/lago** since 2026-09-17T19:36:55Z: Helm upgrade failed for release commerce/lago with chart lago@1.28.0: create: failed to create: admission webhook "oke-resource-leak-protection.oke.com" denied the request: OKE resource leak protection rejected the request. Cluster has 2650 secrets and the limit is 2000. See https://docs.oracle.com/iaas/Content/ContEng/Tasks/contengprotectingclustersfromresourceleaks.htm for details.
- **HelmRelease crossplane-system/crossplane** since 2026-09-16T17:08:05Z: Helm upgrade failed for release crossplane-system/crossplane with chart crossplane@1.15.1: create: failed to create: admission webhook "oke-resource-leak-protection.oke.com" denied the request: OKE resource leak protection rejected the request. Cluster has 2650 secrets and the limit is 2000. See https://docs.oracle.com/iaas/Content/ContEng/Tasks/contengprotectingclustersfromresourceleaks.htm for details.
- **Kustomization flux-system/agent-workforce** since 2026-09-17T19:41:53Z: dependency 'flux-system/github-app-creds' is not ready
- **Kustomization flux-system/alerts** since 2026-09-17T19:10:14Z: dependency 'flux-system/alerts-secret' is not ready
- **Kustomization flux-system/alerts-github** since 2026-09-17T19:36:54Z: dependency 'flux-system/github-app-creds' is not ready
- **Kustomization flux-system/alerts-secret** since 2026-09-17T19:36:18Z: ExternalSecret/flux-system/flux-telegram dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-secrets.io": failed to call webhook: Post "https://external-secrets-webhook.external-secrets.svc:443/validate-external-secrets-io-v1-externalsecret?timeout=15s": context deadline exceeded 
- **Kustomization flux-system/backstage** since 2026-09-17T19:35:45Z: health check failed after 10m0.064806419s: timeout waiting for: [Deployment/backstage/catalogue status: 'InProgress']
- **Kustomization flux-system/calico** since 2026-09-17T19:44:28Z: GlobalNetworkPolicy/deny-direct-ai-vendor-egress dry-run failed: no matches for kind "GlobalNetworkPolicy" in version "projectcalico.org/v3" 
- **Kustomization flux-system/chaos** since 2026-09-17T19:34:59Z: dependency 'flux-system/backstage' is not ready
- **Kustomization flux-system/commerce** since 2026-09-17T19:36:47Z: Reconciliation in progress
- **Kustomization flux-system/crossplane** since 2026-09-17T19:36:54Z: health check failed after 39.871758ms: failed early due to stalled resources: [HelmRelease/crossplane-system/crossplane status: 'Failed']
- **Kustomization flux-system/crossplane-providerconfig** since 2026-09-16T11:53:07Z: dependency 'flux-system/crossplane-providers' is not ready
- **Kustomization flux-system/crossplane-providers** since 2026-09-16T11:53:06Z: dependency 'flux-system/crossplane' is not ready
- **Kustomization flux-system/crossplane-storage-capability** since 2026-09-16T11:53:07Z: dependency 'flux-system/crossplane-providerconfig' is not ready
- **Kustomization flux-system/drills** since 2026-09-17T19:36:38Z: dependency 'flux-system/github-app-creds' is not ready
- **Kustomization flux-system/epistemic-fabric** since 2026-09-17T19:45:17Z: Reconciliation in progress
- **Kustomization flux-system/guacamole** since 2026-09-17T19:34:16Z: dependency 'flux-system/tailscale' is not ready
- **Kustomization flux-system/healing-k8sgpt** since 2026-09-17T19:44:29Z: ExternalSecret/healing/k8sgpt dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-secrets.io": failed to call webhook: Post "https://external-secrets-webhook.external-secrets.svc:443/validate-external-secrets-io-v1-externalsecret?timeout=15s": context deadline exceeded 
- **Kustomization flux-system/hermes-agent** since 2026-09-17T19:43:52Z: dependency 'flux-system/github-app-creds' is not ready
- **Kustomization flux-system/hindsight** since 2026-09-17T19:43:13Z: ExternalSecret/hindsight/hindsight-env dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-secrets.io": failed to call webhook: Post "https://external-secrets-webhook.external-secrets.svc:443/validate-external-secrets-io-v1-externalsecret?timeout=15s": context deadline exceeded 
- **Kustomization flux-system/human-vault** since 2026-09-17T19:35:52Z: ClusterSecretStore/human-vault dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.clustersecretstore.external-secrets.io": failed to call webhook: Post "https://external-secrets-webhook.external-secrets.svc:443/validate-external-secrets-io-v1-clustersecretstore?timeout=15s": context deadline exceeded 
- **Kustomization flux-system/human-vault-bridge** since 2026-09-17T19:36:37Z: dependency 'flux-system/human-vault' is not ready
- **Kustomization flux-system/idp-agent** since 2026-09-17T19:36:30Z: dependency 'flux-system/github-app-creds' is not ready
- **Kustomization flux-system/image-automation** since 2026-09-17T19:36:28Z: ClusterSecretStore/ghcr-pull dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.clustersecretstore.external-secrets.io": failed to call webhook: Post "https://external-secrets-webhook.external-secrets.svc:443/validate-external-secrets-io-v1-clustersecretstore?timeout=15s": context deadline exceeded 
- **Kustomization flux-system/jit** since 2026-09-17T19:45:00Z: Deployment/jit/jit-broker dry-run failed (Invalid): Deployment.apps "jit-broker" is invalid: spec.template.spec.containers[0].env[9].valueFrom: Invalid value: "": may not be specified when `value` is not empty 
- **Kustomization flux-system/mcp** since 2026-09-17T19:36:55Z: dependency 'flux-system/github-app-creds' is not ready
- **Kustomization flux-system/otto-gateway** since 2026-09-17T19:42:40Z: dependency 'flux-system/github-app-creds' is not ready
- **Kustomization flux-system/otto-golden** since 2026-09-17T19:41:42Z: health check failed after 10m0.029477231s: timeout waiting for: [Deployment/otto-golden/otto-golden status: 'InProgress']
- **Kustomization flux-system/prospector** since 2026-09-17T19:41:42Z: health check failed after 490.177903ms: failed early due to stalled resources: [Deployment/prospector/prospector-store-api status: 'Failed']
- **Kustomization flux-system/router-events** since 2026-09-17T19:37:53Z: health check failed after 5m0.121238525s: timeout waiting for: [Deployment/llm/litellm status: 'InProgress']
- **Kustomization flux-system/tailscale** since 2026-09-17T19:36:34Z: ExternalSecret/tailscale/tailscale-operator-secret dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-secrets.io": failed to call webhook: Post "https://external-secrets-webhook.external-secrets.svc:443/validate-external-secrets-io-v1-externalsecret?timeout=15s": context deadline exceeded 
- **Kustomization flux-system/temporal** since 2026-09-17T19:36:54Z: dependency 'flux-system/image-automation' is not ready
- **Kustomization flux-system/via-negativa** since 2026-09-17T19:44:31Z: ExternalSecret/via-negativa/via-negativa-db dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-secrets.io": failed to call webhook: Post "https://external-secrets-webhook.external-secrets.svc:443/validate-external-secrets-io-v1-externalsecret?timeout=15s": context deadline exceeded 

## Every row

| Kind | Namespace | Name | State | Applied revision | Since | Message |
|---|---|---|---|---|---|---|
| HelmRelease | commerce | lago | Not ready | 1.28.0 | 2026-09-17T19:36:55Z | Helm upgrade failed for release commerce/lago with chart lago@1.28.0: create: failed to create: admission webhook "oke-resource-leak-protection.oke.com" denied  |
| HelmRelease | crossplane-system | crossplane | Not ready | 1.15.1 | 2026-09-16T17:08:05Z | Helm upgrade failed for release crossplane-system/crossplane with chart crossplane@1.15.1: create: failed to create: admission webhook "oke-resource-leak-protec |
| Kustomization | flux-system | agent-workforce | Not ready | main@06b2a31 | 2026-09-17T19:41:53Z | dependency 'flux-system/github-app-creds' is not ready |
| Kustomization | flux-system | alerts | Not ready | main@0df0a74 | 2026-09-17T19:10:14Z | dependency 'flux-system/alerts-secret' is not ready |
| Kustomization | flux-system | alerts-github | Not ready | main@06b2a31 | 2026-09-17T19:36:54Z | dependency 'flux-system/github-app-creds' is not ready |
| Kustomization | flux-system | alerts-secret | Not ready | main@fd519c9 | 2026-09-17T19:36:18Z | ExternalSecret/flux-system/flux-telegram dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-secre |
| Kustomization | flux-system | backstage | Not ready | main@1d76f3a | 2026-09-17T19:35:45Z | health check failed after 10m0.064806419s: timeout waiting for: [Deployment/backstage/catalogue status: 'InProgress'] |
| Kustomization | flux-system | calico | Not ready | main@0df0a74 | 2026-09-17T19:44:28Z | GlobalNetworkPolicy/deny-direct-ai-vendor-egress dry-run failed: no matches for kind "GlobalNetworkPolicy" in version "projectcalico.org/v3"  |
| Kustomization | flux-system | chaos | Not ready | main@cb6f6b2 | 2026-09-17T19:34:59Z | dependency 'flux-system/backstage' is not ready |
| Kustomization | flux-system | commerce | Not ready | main@abea14d | 2026-09-17T19:36:47Z | Reconciliation in progress |
| Kustomization | flux-system | crossplane | Not ready | main@8d685ec | 2026-09-17T19:36:54Z | health check failed after 39.871758ms: failed early due to stalled resources: [HelmRelease/crossplane-system/crossplane status: 'Failed'] |
| Kustomization | flux-system | crossplane-providerconfig | Not ready | main@8d685ec | 2026-09-16T11:53:07Z | dependency 'flux-system/crossplane-providers' is not ready |
| Kustomization | flux-system | crossplane-providers | Not ready | main@8d685ec | 2026-09-16T11:53:06Z | dependency 'flux-system/crossplane' is not ready |
| Kustomization | flux-system | crossplane-storage-capability | Not ready | main@8d685ec | 2026-09-16T11:53:07Z | dependency 'flux-system/crossplane-providerconfig' is not ready |
| Kustomization | flux-system | drills | Not ready | main@06b2a31 | 2026-09-17T19:36:38Z | dependency 'flux-system/github-app-creds' is not ready |
| Kustomization | flux-system | epistemic-fabric | Not ready | main@06b2a31 | 2026-09-17T19:45:17Z | Reconciliation in progress |
| Kustomization | flux-system | guacamole | Not ready | main@0df0a74 | 2026-09-17T19:34:16Z | dependency 'flux-system/tailscale' is not ready |
| Kustomization | flux-system | healing-k8sgpt | Not ready | main@06b2a31 | 2026-09-17T19:44:29Z | ExternalSecret/healing/k8sgpt dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-secrets.io": fai |
| Kustomization | flux-system | hermes-agent | Not ready | main@0df0a74 | 2026-09-17T19:43:52Z | dependency 'flux-system/github-app-creds' is not ready |
| Kustomization | flux-system | hindsight | Not ready | main@06b2a31 | 2026-09-17T19:43:13Z | ExternalSecret/hindsight/hindsight-env dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-secrets |
| Kustomization | flux-system | human-vault | Not ready | main@06b2a31 | 2026-09-17T19:35:52Z | ClusterSecretStore/human-vault dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.clustersecretstore.external-secrets.io" |
| Kustomization | flux-system | human-vault-bridge | Not ready | main@06b2a31 | 2026-09-17T19:36:37Z | dependency 'flux-system/human-vault' is not ready |
| Kustomization | flux-system | idp-agent | Not ready | main@06b2a31 | 2026-09-17T19:36:30Z | dependency 'flux-system/github-app-creds' is not ready |
| Kustomization | flux-system | image-automation | Not ready | main@06b2a31 | 2026-09-17T19:36:28Z | ClusterSecretStore/ghcr-pull dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.clustersecretstore.external-secrets.io":  |
| Kustomization | flux-system | jit | Not ready | main@fd519c9 | 2026-09-17T19:45:00Z | Deployment/jit/jit-broker dry-run failed (Invalid): Deployment.apps "jit-broker" is invalid: spec.template.spec.containers[0].env[9].valueFrom: Invalid value: " |
| Kustomization | flux-system | mcp | Not ready | main@06b2a31 | 2026-09-17T19:36:55Z | dependency 'flux-system/github-app-creds' is not ready |
| Kustomization | flux-system | otto-gateway | Not ready | main@cd9eb71 | 2026-09-17T19:42:40Z | dependency 'flux-system/github-app-creds' is not ready |
| Kustomization | flux-system | otto-golden | Not ready | main@cd9eb71 | 2026-09-17T19:41:42Z | health check failed after 10m0.029477231s: timeout waiting for: [Deployment/otto-golden/otto-golden status: 'InProgress'] |
| Kustomization | flux-system | prospector | Not ready | main@7453d76 | 2026-09-17T19:41:42Z | health check failed after 490.177903ms: failed early due to stalled resources: [Deployment/prospector/prospector-store-api status: 'Failed'] |
| Kustomization | flux-system | router-events | Not ready | main@0df0a74 | 2026-09-17T19:37:53Z | health check failed after 5m0.121238525s: timeout waiting for: [Deployment/llm/litellm status: 'InProgress'] |
| Kustomization | flux-system | tailscale | Not ready | main@fd519c9 | 2026-09-17T19:36:34Z | ExternalSecret/tailscale/tailscale-operator-secret dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.exte |
| Kustomization | flux-system | temporal | Not ready | main@06b2a31 | 2026-09-17T19:36:54Z | dependency 'flux-system/image-automation' is not ready |
| Kustomization | flux-system | via-negativa | Not ready | main@06b2a31 | 2026-09-17T19:44:31Z | ExternalSecret/via-negativa/via-negativa-db dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-se |
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
| Kustomization | flux-system | autoscaler | Ready | main@06b2a31 | 2026-09-17T19:36:52Z |  |
| Kustomization | flux-system | backstage-namespace | Ready | main@06b2a31 | 2026-09-17T19:44:39Z |  |
| Kustomization | flux-system | chaos-mesh | Ready | main@06b2a31 | 2026-09-17T19:35:54Z |  |
| Kustomization | flux-system | cluster-state | Ready | main@06b2a31 | 2026-09-17T19:44:50Z |  |
| Kustomization | flux-system | commerce-data | Ready | main@06b2a31 | 2026-09-17T19:36:35Z |  |
| Kustomization | flux-system | concierge | Ready | main@06b2a31 | 2026-09-17T19:35:55Z |  |
| Kustomization | flux-system | cross-node-drill | Ready | main@06b2a31 | 2026-09-17T19:44:36Z |  |
| Kustomization | flux-system | dagster | Ready | main@06b2a31 | 2026-09-17T19:36:37Z |  |
| Kustomization | flux-system | dns | Ready | main@06b2a31 | 2026-09-17T19:37:04Z |  |
| Kustomization | flux-system | edge | Ready | main@06b2a31 | 2026-09-17T19:45:14Z |  |
| Kustomization | flux-system | estate-catalog | Ready | latest@sha256:e399bd3ac53bff7e1a908ea3e6 | 2026-09-17T19:44:15Z |  |
| Kustomization | flux-system | estate-db | Ready | main@06b2a31 | 2026-09-17T19:35:33Z |  |
| Kustomization | flux-system | estate-db-migrate | Ready | main@06b2a31 | 2026-09-17T19:36:40Z |  |
| Kustomization | flux-system | estate-db-operator | Ready | main@06b2a31 | 2026-09-17T19:44:08Z |  |
| Kustomization | flux-system | event-bus | Ready | main@06b2a31 | 2026-09-17T19:44:24Z |  |
| Kustomization | flux-system | external-secrets | Ready | main@06b2a31 | 2026-09-17T19:35:46Z |  |
| Kustomization | flux-system | feature-register | Ready | main@06b2a31 | 2026-09-17T19:36:46Z |  |
| Kustomization | flux-system | flux-system | Ready | main@06b2a31 | 2026-09-17T19:44:32Z |  |
| Kustomization | flux-system | flux-webhook | Ready | main@06b2a31 | 2026-09-17T19:35:00Z |  |
| Kustomization | flux-system | gateway-api-crds | Ready | v1.5.1@e7677b7 | 2026-09-17T19:44:46Z |  |
| Kustomization | flux-system | github-app-creds | Ready | main@06b2a31 | 2026-09-17T19:45:17Z |  |
| Kustomization | flux-system | gvisor-runtime | Ready | main@06b2a31 | 2026-09-17T19:36:40Z |  |
| Kustomization | flux-system | healing | Ready | main@06b2a31 | 2026-09-17T19:35:35Z |  |
| Kustomization | flux-system | healing-analyzer | Ready | main@06b2a31 | 2026-09-17T19:44:09Z |  |
| Kustomization | flux-system | healthchecks | Ready | main@06b2a31 | 2026-09-17T19:36:44Z |  |
| Kustomization | flux-system | identity | Ready | main@06b2a31 | 2026-09-17T19:36:49Z |  |
| Kustomization | flux-system | keda | Ready | main@06b2a31 | 2026-09-17T19:36:46Z |  |
| Kustomization | flux-system | kyverno | Ready | main@06b2a31 | 2026-09-17T19:44:37Z |  |
| Kustomization | flux-system | llm | Ready | main@06b2a31 | 2026-09-17T19:36:51Z |  |
| Kustomization | flux-system | metrics-server | Ready | main@06b2a31 | 2026-09-17T19:44:30Z |  |
| Kustomization | flux-system | monitoring | Ready | main@06b2a31 | 2026-09-17T19:44:34Z |  |
| Kustomization | flux-system | monitoring-rules | Ready | main@06b2a31 | 2026-09-17T19:35:53Z |  |
| Kustomization | flux-system | nodesoftware-operator | Ready | main@06b2a31 | 2026-09-17T19:36:12Z |  |
| Kustomization | flux-system | notify | Ready | main@06b2a31 | 2026-09-17T19:36:38Z |  |
| Kustomization | flux-system | ns-fences | Ready | main@06b2a31 | 2026-09-17T19:35:28Z |  |
| Kustomization | flux-system | observability | Ready | main@06b2a31 | 2026-09-17T19:43:45Z |  |
| Kustomization | flux-system | observability-collector | Ready | main@06b2a31 | 2026-09-17T19:36:55Z |  |
| Kustomization | flux-system | otto-golden-secret | Ready | main@06b2a31 | 2026-09-17T19:36:45Z |  |
| Kustomization | flux-system | priority-classes | Ready | main@06b2a31 | 2026-09-17T19:44:12Z |  |
| Kustomization | flux-system | prospector-platform | Ready | main@06b2a31 | 2026-09-17T19:36:10Z |  |
| Kustomization | flux-system | rbac | Ready | main@06b2a31 | 2026-09-17T19:35:34Z |  |
| Kustomization | flux-system | rbac-floor | Ready | main@06b2a31 | 2026-09-17T19:44:56Z |  |
| Kustomization | flux-system | rbac-identity | Ready | main@06b2a31 | 2026-09-17T19:44:33Z |  |
| Kustomization | flux-system | reloader | Ready | main@06b2a31 | 2026-09-17T19:36:30Z |  |
| Kustomization | flux-system | research-engine | Ready | main@06b2a31 | 2026-09-17T19:42:45Z |  |
| Kustomization | flux-system | robusta | Ready | main@06b2a31 | 2026-09-17T19:36:32Z |  |
| Kustomization | flux-system | sandbox-launch | Ready | main@06b2a31 | 2026-09-17T19:44:55Z |  |
| Kustomization | flux-system | sandbox-live | Ready | sandbox/launch@4830a6e | 2026-09-17T19:44:51Z |  |
| Kustomization | flux-system | scheduling | Ready | main@06b2a31 | 2026-09-17T19:35:36Z |  |
| Kustomization | flux-system | science | Ready | main@06b2a31 | 2026-09-17T19:43:41Z |  |
| Kustomization | flux-system | searxng | Ready | main@06b2a31 | 2026-09-17T19:44:50Z |  |
| Kustomization | flux-system | secret-store | Ready | main@06b2a31 | 2026-09-17T19:44:27Z |  |
| Kustomization | flux-system | spire | Ready | main@06b2a31 | 2026-09-17T19:44:35Z |  |
| Kustomization | flux-system | staging | Ready | main@06b2a31 | 2026-09-17T19:44:01Z |  |
| Kustomization | flux-system | trivy | Ready | main@06b2a31 | 2026-09-17T19:35:29Z |  |
| Kustomization | flux-system | verification | Ready | main@06b2a31 | 2026-09-17T19:36:43Z |  |
| Kustomization | flux-system | weave-gitops | Ready | main@06b2a31 | 2026-09-17T19:44:04Z |  |
