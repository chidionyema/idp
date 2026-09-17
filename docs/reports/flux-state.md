# Flux: what is applied

Read from the cluster receipt taken at 2026-09-17T20:00:23Z. Every Kustomization and HelmRelease, with the revision Flux last applied. **Suspended** is a switch somebody turned off on purpose (temporal, commerce, commerce-data, event-bus), not a defect; **Unknown** is a row Flux has never graded.

**121 objects: 94 ready, 26 not ready, 0 unknown, 1 suspended.**

## Not ready right now

- **HelmRelease commerce/lago** since 2026-09-17T19:51:55Z: Running 'upgrade' action with timeout of 20m0s
- **HelmRelease crossplane-system/crossplane** since 2026-09-16T17:08:05Z: Helm upgrade failed for release crossplane-system/crossplane with chart crossplane@1.15.1: create: failed to create: admission webhook "oke-resource-leak-protection.oke.com" denied the request: OKE resource leak protection rejected the request. Cluster has 2650 secrets and the limit is 2000. See https://docs.oracle.com/iaas/Content/ContEng/Tasks/contengprotectingclustersfromresourceleaks.htm for details.
- **Kustomization flux-system/backstage** since 2026-09-17T19:55:54Z: health check failed after 622.983188ms: failed early due to stalled resources: [Deployment/backstage/catalogue status: 'Failed']
- **Kustomization flux-system/calico** since 2026-09-17T19:54:30Z: GlobalNetworkPolicy/deny-direct-ai-vendor-egress dry-run failed: no matches for kind "GlobalNetworkPolicy" in version "projectcalico.org/v3" 
- **Kustomization flux-system/chaos** since 2026-09-17T19:34:59Z: dependency 'flux-system/backstage' is not ready
- **Kustomization flux-system/commerce** since 2026-09-17T19:51:49Z: health check failed after 15m0.096450142s: timeout waiting for: [HelmRelease/commerce/lago status: 'InProgress']
- **Kustomization flux-system/crossplane** since 2026-09-17T19:56:57Z: health check failed after 64.215584ms: failed early due to stalled resources: [HelmRelease/crossplane-system/crossplane status: 'Failed']
- **Kustomization flux-system/crossplane-providerconfig** since 2026-09-16T11:53:07Z: dependency 'flux-system/crossplane-providers' is not ready
- **Kustomization flux-system/crossplane-providers** since 2026-09-16T11:53:06Z: dependency 'flux-system/crossplane' is not ready
- **Kustomization flux-system/crossplane-storage-capability** since 2026-09-16T11:53:07Z: dependency 'flux-system/crossplane-providerconfig' is not ready
- **Kustomization flux-system/epistemic-fabric** since 2026-09-17T19:55:21Z: health check failed after 79.087187ms: failed early due to stalled resources: [Deployment/epistemic-fabric/epistemic-ingest-github status: 'Failed']
- **Kustomization flux-system/guacamole** since 2026-09-17T19:57:04Z: dependency 'flux-system/tailscale' is not ready
- **Kustomization flux-system/gvisor-runtime** since 2026-09-17T19:46:13Z: dependency 'flux-system/nodesoftware-operator' is not ready
- **Kustomization flux-system/hermes-agent** since 2026-09-17T19:55:43Z: health check failed after 315.213535ms: failed early due to stalled resources: [Deployment/hermes-agent/hermes-agent-gateway status: 'Failed']
- **Kustomization flux-system/idp-agent** since 2026-09-17T19:55:33Z: Deployment/idp-agent/idp-engine dry-run failed (Invalid): Deployment.apps "idp-engine" is invalid: spec.template.spec.containers[0].env[5].valueFrom: Invalid value: "": may not be specified when `value` is not empty 
- **Kustomization flux-system/image-automation** since 2026-09-17T19:57:00Z: ClusterSecretStore/ghcr-pull dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.clustersecretstore.external-secrets.io": failed to call webhook: Post "https://external-secrets-webhook.external-secrets.svc:443/validate-external-secrets-io-v1-clustersecretstore?timeout=15s": context deadline exceeded 
- **Kustomization flux-system/jit** since 2026-09-17T19:55:02Z: Deployment/jit/jit-broker dry-run failed (Invalid): Deployment.apps "jit-broker" is invalid: spec.template.spec.containers[0].env[9].valueFrom: Invalid value: "": may not be specified when `value` is not empty 
- **Kustomization flux-system/nodesoftware-operator** since 2026-09-17T19:46:05Z: dependency 'flux-system/image-automation' is not ready
- **Kustomization flux-system/otto-gateway** since 2026-09-17T19:56:02Z: health check failed after 1.368043796s: failed early due to stalled resources: [Deployment/otto-gateway/otto-gateway status: 'Failed']
- **Kustomization flux-system/otto-golden** since 2026-09-17T19:51:48Z: health check failed after 215.555403ms: failed early due to stalled resources: [Deployment/otto-golden/otto-golden status: 'Failed']
- **Kustomization flux-system/prospector** since 2026-09-17T19:51:49Z: health check failed after 442.633132ms: failed early due to stalled resources: [Deployment/prospector/prospector-store-api status: 'Failed']
- **Kustomization flux-system/router-events** since 2026-09-17T19:52:54Z: health check failed after 5m0.04845476s: timeout waiting for: [Deployment/llm/litellm status: 'InProgress']
- **Kustomization flux-system/tailscale** since 2026-09-17T19:57:12Z: ExternalSecret/tailscale/tailscale-operator-secret dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-secrets.io": failed to call webhook: Post "https://external-secrets-webhook.external-secrets.svc:443/validate-external-secrets-io-v1-externalsecret?timeout=15s": context deadline exceeded 
- **Kustomization flux-system/temporal** since 2026-09-17T19:36:54Z: dependency 'flux-system/image-automation' is not ready
- **Kustomization flux-system/verification** since 2026-09-17T19:56:55Z: ExternalSecret/backstage/verdict-key-wall dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-secrets.io": failed to call webhook: Post "https://external-secrets-webhook.external-secrets.svc:443/validate-external-secrets-io-v1-externalsecret?timeout=15s": context deadline exceeded 
- **Kustomization flux-system/via-negativa** since 2026-09-17T19:54:32Z: health check failed after 298.418231ms: failed early due to stalled resources: [Deployment/via-negativa/via-negativa-rca status: 'Failed']

## Every row

| Kind | Namespace | Name | State | Applied revision | Since | Message |
|---|---|---|---|---|---|---|
| HelmRelease | commerce | lago | Not ready | 1.28.0 | 2026-09-17T19:51:55Z | Running 'upgrade' action with timeout of 20m0s |
| HelmRelease | crossplane-system | crossplane | Not ready | 1.15.1 | 2026-09-16T17:08:05Z | Helm upgrade failed for release crossplane-system/crossplane with chart crossplane@1.15.1: create: failed to create: admission webhook "oke-resource-leak-protec |
| Kustomization | flux-system | backstage | Not ready | main@1d76f3a | 2026-09-17T19:55:54Z | health check failed after 622.983188ms: failed early due to stalled resources: [Deployment/backstage/catalogue status: 'Failed'] |
| Kustomization | flux-system | calico | Not ready | main@0df0a74 | 2026-09-17T19:54:30Z | GlobalNetworkPolicy/deny-direct-ai-vendor-egress dry-run failed: no matches for kind "GlobalNetworkPolicy" in version "projectcalico.org/v3"  |
| Kustomization | flux-system | chaos | Not ready | main@cb6f6b2 | 2026-09-17T19:34:59Z | dependency 'flux-system/backstage' is not ready |
| Kustomization | flux-system | commerce | Not ready | main@abea14d | 2026-09-17T19:51:49Z | health check failed after 15m0.096450142s: timeout waiting for: [HelmRelease/commerce/lago status: 'InProgress'] |
| Kustomization | flux-system | crossplane | Not ready | main@8d685ec | 2026-09-17T19:56:57Z | health check failed after 64.215584ms: failed early due to stalled resources: [HelmRelease/crossplane-system/crossplane status: 'Failed'] |
| Kustomization | flux-system | crossplane-providerconfig | Not ready | main@8d685ec | 2026-09-16T11:53:07Z | dependency 'flux-system/crossplane-providers' is not ready |
| Kustomization | flux-system | crossplane-providers | Not ready | main@8d685ec | 2026-09-16T11:53:06Z | dependency 'flux-system/crossplane' is not ready |
| Kustomization | flux-system | crossplane-storage-capability | Not ready | main@8d685ec | 2026-09-16T11:53:07Z | dependency 'flux-system/crossplane-providerconfig' is not ready |
| Kustomization | flux-system | epistemic-fabric | Not ready | main@06b2a31 | 2026-09-17T19:55:21Z | health check failed after 79.087187ms: failed early due to stalled resources: [Deployment/epistemic-fabric/epistemic-ingest-github status: 'Failed'] |
| Kustomization | flux-system | guacamole | Not ready | main@06b2a31 | 2026-09-17T19:57:04Z | dependency 'flux-system/tailscale' is not ready |
| Kustomization | flux-system | gvisor-runtime | Not ready | main@06b2a31 | 2026-09-17T19:46:13Z | dependency 'flux-system/nodesoftware-operator' is not ready |
| Kustomization | flux-system | hermes-agent | Not ready | main@0df0a74 | 2026-09-17T19:55:43Z | health check failed after 315.213535ms: failed early due to stalled resources: [Deployment/hermes-agent/hermes-agent-gateway status: 'Failed'] |
| Kustomization | flux-system | idp-agent | Not ready | main@06b2a31 | 2026-09-17T19:55:33Z | Deployment/idp-agent/idp-engine dry-run failed (Invalid): Deployment.apps "idp-engine" is invalid: spec.template.spec.containers[0].env[5].valueFrom: Invalid va |
| Kustomization | flux-system | image-automation | Not ready | main@06b2a31 | 2026-09-17T19:57:00Z | ClusterSecretStore/ghcr-pull dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.clustersecretstore.external-secrets.io":  |
| Kustomization | flux-system | jit | Not ready | main@fd519c9 | 2026-09-17T19:55:02Z | Deployment/jit/jit-broker dry-run failed (Invalid): Deployment.apps "jit-broker" is invalid: spec.template.spec.containers[0].env[9].valueFrom: Invalid value: " |
| Kustomization | flux-system | nodesoftware-operator | Not ready | main@06b2a31 | 2026-09-17T19:46:05Z | dependency 'flux-system/image-automation' is not ready |
| Kustomization | flux-system | otto-gateway | Not ready | main@cd9eb71 | 2026-09-17T19:56:02Z | health check failed after 1.368043796s: failed early due to stalled resources: [Deployment/otto-gateway/otto-gateway status: 'Failed'] |
| Kustomization | flux-system | otto-golden | Not ready | main@cd9eb71 | 2026-09-17T19:51:48Z | health check failed after 215.555403ms: failed early due to stalled resources: [Deployment/otto-golden/otto-golden status: 'Failed'] |
| Kustomization | flux-system | prospector | Not ready | main@7453d76 | 2026-09-17T19:51:49Z | health check failed after 442.633132ms: failed early due to stalled resources: [Deployment/prospector/prospector-store-api status: 'Failed'] |
| Kustomization | flux-system | router-events | Not ready | main@0df0a74 | 2026-09-17T19:52:54Z | health check failed after 5m0.04845476s: timeout waiting for: [Deployment/llm/litellm status: 'InProgress'] |
| Kustomization | flux-system | tailscale | Not ready | main@06b2a31 | 2026-09-17T19:57:12Z | ExternalSecret/tailscale/tailscale-operator-secret dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.exte |
| Kustomization | flux-system | temporal | Not ready | main@06b2a31 | 2026-09-17T19:36:54Z | dependency 'flux-system/image-automation' is not ready |
| Kustomization | flux-system | verification | Not ready | main@06b2a31 | 2026-09-17T19:56:55Z | ExternalSecret/backstage/verdict-key-wall dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-secr |
| Kustomization | flux-system | via-negativa | Not ready | main@06b2a31 | 2026-09-17T19:54:32Z | health check failed after 298.418231ms: failed early due to stalled resources: [Deployment/via-negativa/via-negativa-rca status: 'Failed'] |
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
| Kustomization | flux-system | agent-workforce | Ready | main@06b2a31 | 2026-09-17T19:55:20Z |  |
| Kustomization | flux-system | alerts | Ready | main@06b2a31 | 2026-09-17T19:57:03Z |  |
| Kustomization | flux-system | alerts-github | Ready | main@06b2a31 | 2026-09-17T19:55:46Z |  |
| Kustomization | flux-system | alerts-secret | Ready | main@06b2a31 | 2026-09-17T19:56:32Z |  |
| Kustomization | flux-system | autoscaler | Ready | main@06b2a31 | 2026-09-17T19:56:16Z |  |
| Kustomization | flux-system | backstage-namespace | Ready | main@06b2a31 | 2026-09-17T19:55:10Z |  |
| Kustomization | flux-system | chaos-mesh | Ready | main@06b2a31 | 2026-09-17T19:56:22Z |  |
| Kustomization | flux-system | cluster-state | Ready | main@06b2a31 | 2026-09-17T19:54:51Z |  |
| Kustomization | flux-system | commerce-data | Ready | main@06b2a31 | 2026-09-17T19:57:07Z |  |
| Kustomization | flux-system | concierge | Ready | main@06b2a31 | 2026-09-17T19:56:09Z |  |
| Kustomization | flux-system | cross-node-drill | Ready | main@06b2a31 | 2026-09-17T19:54:21Z |  |
| Kustomization | flux-system | dagster | Ready | main@06b2a31 | 2026-09-17T19:57:06Z |  |
| Kustomization | flux-system | dns | Ready | main@06b2a31 | 2026-09-17T19:57:27Z |  |
| Kustomization | flux-system | drills | Ready | main@06b2a31 | 2026-09-17T19:55:38Z |  |
| Kustomization | flux-system | edge | Ready | main@06b2a31 | 2026-09-17T19:54:56Z |  |
| Kustomization | flux-system | estate-catalog | Ready | latest@sha256:e399bd3ac53bff7e1a908ea3e6 | 2026-09-17T19:53:59Z |  |
| Kustomization | flux-system | estate-db | Ready | main@06b2a31 | 2026-09-17T19:55:24Z |  |
| Kustomization | flux-system | estate-db-migrate | Ready | main@06b2a31 | 2026-09-17T19:57:34Z |  |
| Kustomization | flux-system | estate-db-operator | Ready | main@06b2a31 | 2026-09-17T19:54:15Z |  |
| Kustomization | flux-system | event-bus | Ready | main@06b2a31 | 2026-09-17T19:54:16Z |  |
| Kustomization | flux-system | external-secrets | Ready | main@06b2a31 | 2026-09-17T19:55:30Z |  |
| Kustomization | flux-system | feature-register | Ready | main@06b2a31 | 2026-09-17T19:56:53Z |  |
| Kustomization | flux-system | flux-system | Ready | main@06b2a31 | 2026-09-17T19:54:21Z |  |
| Kustomization | flux-system | flux-webhook | Ready | main@06b2a31 | 2026-09-17T19:55:58Z |  |
| Kustomization | flux-system | gateway-api-crds | Ready | v1.5.1@e7677b7 | 2026-09-17T19:54:31Z |  |
| Kustomization | flux-system | github-app-creds | Ready | main@06b2a31 | 2026-09-17T19:55:17Z |  |
| Kustomization | flux-system | healing | Ready | main@06b2a31 | 2026-09-17T19:55:38Z |  |
| Kustomization | flux-system | healing-analyzer | Ready | main@06b2a31 | 2026-09-17T19:55:02Z |  |
| Kustomization | flux-system | healing-k8sgpt | Ready | main@06b2a31 | 2026-09-17T19:54:31Z |  |
| Kustomization | flux-system | healthchecks | Ready | main@06b2a31 | 2026-09-17T19:56:42Z |  |
| Kustomization | flux-system | hindsight | Ready | main@06b2a31 | 2026-09-17T19:53:14Z |  |
| Kustomization | flux-system | human-vault | Ready | main@06b2a31 | 2026-09-17T19:55:56Z |  |
| Kustomization | flux-system | human-vault-bridge | Ready | main@06b2a31 | 2026-09-17T19:56:35Z |  |
| Kustomization | flux-system | identity | Ready | main@06b2a31 | 2026-09-17T19:57:04Z |  |
| Kustomization | flux-system | keda | Ready | main@06b2a31 | 2026-09-17T19:56:57Z |  |
| Kustomization | flux-system | kyverno | Ready | main@06b2a31 | 2026-09-17T19:54:58Z |  |
| Kustomization | flux-system | llm | Ready | main@06b2a31 | 2026-09-17T19:56:30Z |  |
| Kustomization | flux-system | mcp | Ready | main@06b2a31 | 2026-09-17T19:56:08Z |  |
| Kustomization | flux-system | metrics-server | Ready | main@06b2a31 | 2026-09-17T19:54:31Z |  |
| Kustomization | flux-system | monitoring | Ready | main@06b2a31 | 2026-09-17T19:54:37Z |  |
| Kustomization | flux-system | monitoring-rules | Ready | main@06b2a31 | 2026-09-17T19:56:03Z |  |
| Kustomization | flux-system | notify | Ready | main@06b2a31 | 2026-09-17T19:56:41Z |  |
| Kustomization | flux-system | ns-fences | Ready | main@06b2a31 | 2026-09-17T19:56:13Z |  |
| Kustomization | flux-system | observability | Ready | main@06b2a31 | 2026-09-17T19:53:39Z |  |
| Kustomization | flux-system | observability-collector | Ready | main@06b2a31 | 2026-09-17T19:57:27Z |  |
| Kustomization | flux-system | otto-golden-secret | Ready | main@06b2a31 | 2026-09-17T19:56:35Z |  |
| Kustomization | flux-system | priority-classes | Ready | main@06b2a31 | 2026-09-17T19:54:01Z |  |
| Kustomization | flux-system | prospector-platform | Ready | main@06b2a31 | 2026-09-17T19:56:19Z |  |
| Kustomization | flux-system | rbac | Ready | main@06b2a31 | 2026-09-17T19:56:17Z |  |
| Kustomization | flux-system | rbac-floor | Ready | main@06b2a31 | 2026-09-17T19:54:43Z |  |
| Kustomization | flux-system | rbac-identity | Ready | main@06b2a31 | 2026-09-17T19:54:56Z |  |
| Kustomization | flux-system | reloader | Ready | main@06b2a31 | 2026-09-17T19:56:13Z |  |
| Kustomization | flux-system | research-engine | Ready | main@06b2a31 | 2026-09-17T19:52:58Z |  |
| Kustomization | flux-system | robusta | Ready | main@06b2a31 | 2026-09-17T19:57:10Z |  |
| Kustomization | flux-system | sandbox-launch | Ready | main@06b2a31 | 2026-09-17T19:55:04Z |  |
| Kustomization | flux-system | sandbox-live | Ready | sandbox/launch@4830a6e | 2026-09-17T20:00:10Z |  |
| Kustomization | flux-system | scheduling | Ready | main@06b2a31 | 2026-09-17T19:55:03Z |  |
| Kustomization | flux-system | science | Ready | main@06b2a31 | 2026-09-17T19:54:06Z |  |
| Kustomization | flux-system | searxng | Ready | main@06b2a31 | 2026-09-17T19:54:44Z |  |
| Kustomization | flux-system | secret-store | Ready | main@06b2a31 | 2026-09-17T19:54:14Z |  |
| Kustomization | flux-system | spire | Ready | main@06b2a31 | 2026-09-17T19:54:09Z |  |
| Kustomization | flux-system | staging | Ready | main@06b2a31 | 2026-09-17T19:54:21Z |  |
| Kustomization | flux-system | trivy | Ready | main@06b2a31 | 2026-09-17T19:55:41Z |  |
| Kustomization | flux-system | weave-gitops | Ready | main@06b2a31 | 2026-09-17T19:53:38Z |  |
