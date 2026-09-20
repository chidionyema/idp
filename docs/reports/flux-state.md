# Flux: what is applied

Read from the cluster receipt taken at 2026-09-20T14:00:57Z. Every Kustomization and HelmRelease, with the revision Flux last applied. **Suspended** is a switch somebody turned off on purpose (temporal, commerce, commerce-data, event-bus), not a defect; **Unknown** is a row Flux has never graded.

**121 objects: 101 ready, 19 not ready, 0 unknown, 1 suspended.**

## Not ready right now

- **HelmRelease commerce/lago** since 2026-09-18T21:16:37Z: Could not determine release state: unable to determine state for release with status 'uninstalling'
- **HelmRelease crossplane-system/crossplane** since 2026-09-16T17:08:05Z: Helm upgrade failed for release crossplane-system/crossplane with chart crossplane@1.15.1: create: failed to create: admission webhook "oke-resource-leak-protection.oke.com" denied the request: OKE resource leak protection rejected the request. Cluster has 2650 secrets and the limit is 2000. See https://docs.oracle.com/iaas/Content/ContEng/Tasks/contengprotectingclustersfromresourceleaks.htm for details.
- **Kustomization flux-system/backstage** since 2026-09-20T14:00:12Z: health check failed after 1m32.724546592s: failed early due to stalled resources: [Deployment/backstage/catalogue status: 'Failed']
- **Kustomization flux-system/calico** since 2026-09-20T13:56:38Z: GlobalNetworkPolicy/deny-direct-ai-vendor-egress dry-run failed: no matches for kind "GlobalNetworkPolicy" in version "projectcalico.org/v3" 
- **Kustomization flux-system/chaos** since 2026-09-20T13:49:07Z: dependency 'flux-system/backstage' is not ready
- **Kustomization flux-system/commerce** since 2026-09-20T13:55:29Z: Reconciliation in progress
- **Kustomization flux-system/crossplane** since 2026-09-20T13:57:28Z: health check failed after 55.995224ms: failed early due to stalled resources: [HelmRelease/crossplane-system/crossplane status: 'Failed']
- **Kustomization flux-system/crossplane-providerconfig** since 2026-09-16T11:53:07Z: dependency 'flux-system/crossplane-providers' is not ready
- **Kustomization flux-system/crossplane-providers** since 2026-09-16T11:53:06Z: dependency 'flux-system/crossplane' is not ready
- **Kustomization flux-system/crossplane-storage-capability** since 2026-09-16T11:53:07Z: dependency 'flux-system/crossplane-providerconfig' is not ready
- **Kustomization flux-system/epistemic-fabric** since 2026-09-20T13:58:23Z: health check failed after 202.175057ms: failed early due to stalled resources: [Deployment/epistemic-fabric/epistemic-ingest-github status: 'Failed']
- **Kustomization flux-system/hermes-agent** since 2026-09-20T13:58:31Z: Reconciliation in progress
- **Kustomization flux-system/idp-agent** since 2026-09-20T13:57:58Z: Service/idp-agent/idp-agent-redis dry-run failed: admission webhook "validate.kyverno.svc-fail" denied the request:   resource Service/idp-agent/idp-agent-redis was blocked due to the following policies   require-catalogue-entity:   service-names-its-entity: 'validation error: Service idp-agent/idp-agent-redis serves a port but names no catalogue entity. Add the label backstage.io/kubernetes-id with the entity name from backstage/**/catalog-info.yaml, and a founder surface if a person opens it (docs/policy/every-interface-is-a-door.md). rule service-names-its-entity failed at path /metadata/labels/backstage.io/kubernetes-id/'  
- **Kustomization flux-system/otto-gateway** since 2026-09-20T13:58:31Z: Reconciliation in progress
- **Kustomization flux-system/otto-golden** since 2026-09-20T13:58:04Z: health check failed after 738.520418ms: failed early due to stalled resources: [Deployment/otto-golden/otto-golden status: 'Failed']
- **Kustomization flux-system/prospector** since 2026-09-20T13:52:25Z: health check failed after 500.720256ms: failed early due to stalled resources: [Deployment/prospector/prospector-store-api status: 'Failed']
- **Kustomization flux-system/router-events** since 2026-09-20T13:53:40Z: health check failed after 5m0.08977014s: timeout waiting for: [Deployment/llm/litellm status: 'InProgress']
- **Kustomization flux-system/sandbox-launch** since 2026-09-20T13:57:38Z: health check failed after 93.226582ms: failed early due to stalled resources: [Job/demo-sandbox/arm-voice-bench status: 'Failed']
- **Kustomization flux-system/via-negativa** since 2026-09-20T14:00:18Z: Reconciliation in progress

## Every row

| Kind | Namespace | Name | State | Applied revision | Since | Message |
|---|---|---|---|---|---|---|
| HelmRelease | commerce | lago | Not ready | 1.28.0 | 2026-09-18T21:16:37Z | Could not determine release state: unable to determine state for release with status 'uninstalling' |
| HelmRelease | crossplane-system | crossplane | Not ready | 1.15.1 | 2026-09-16T17:08:05Z | Helm upgrade failed for release crossplane-system/crossplane with chart crossplane@1.15.1: create: failed to create: admission webhook "oke-resource-leak-protec |
| Kustomization | flux-system | backstage | Not ready | main@1d76f3a | 2026-09-20T14:00:12Z | health check failed after 1m32.724546592s: failed early due to stalled resources: [Deployment/backstage/catalogue status: 'Failed'] |
| Kustomization | flux-system | calico | Not ready | main@0df0a74 | 2026-09-20T13:56:38Z | GlobalNetworkPolicy/deny-direct-ai-vendor-egress dry-run failed: no matches for kind "GlobalNetworkPolicy" in version "projectcalico.org/v3"  |
| Kustomization | flux-system | chaos | Not ready | main@cb6f6b2 | 2026-09-20T13:49:07Z | dependency 'flux-system/backstage' is not ready |
| Kustomization | flux-system | commerce | Not ready | main@abea14d | 2026-09-20T13:55:29Z | Reconciliation in progress |
| Kustomization | flux-system | crossplane | Not ready | main@8d685ec | 2026-09-20T13:57:28Z | health check failed after 55.995224ms: failed early due to stalled resources: [HelmRelease/crossplane-system/crossplane status: 'Failed'] |
| Kustomization | flux-system | crossplane-providerconfig | Not ready | main@8d685ec | 2026-09-16T11:53:07Z | dependency 'flux-system/crossplane-providers' is not ready |
| Kustomization | flux-system | crossplane-providers | Not ready | main@8d685ec | 2026-09-16T11:53:06Z | dependency 'flux-system/crossplane' is not ready |
| Kustomization | flux-system | crossplane-storage-capability | Not ready | main@8d685ec | 2026-09-16T11:53:07Z | dependency 'flux-system/crossplane-providerconfig' is not ready |
| Kustomization | flux-system | epistemic-fabric | Not ready | main@a7f5a42 | 2026-09-20T13:58:23Z | health check failed after 202.175057ms: failed early due to stalled resources: [Deployment/epistemic-fabric/epistemic-ingest-github status: 'Failed'] |
| Kustomization | flux-system | hermes-agent | Not ready | main@0df0a74 | 2026-09-20T13:58:31Z | Reconciliation in progress |
| Kustomization | flux-system | idp-agent | Not ready | main@a7f5a42 | 2026-09-20T13:57:58Z | Service/idp-agent/idp-agent-redis dry-run failed: admission webhook "validate.kyverno.svc-fail" denied the request:   resource Service/idp-agent/idp-agent-redis |
| Kustomization | flux-system | otto-gateway | Not ready | main@cd9eb71 | 2026-09-20T13:58:31Z | Reconciliation in progress |
| Kustomization | flux-system | otto-golden | Not ready | main@cd9eb71 | 2026-09-20T13:58:04Z | health check failed after 738.520418ms: failed early due to stalled resources: [Deployment/otto-golden/otto-golden status: 'Failed'] |
| Kustomization | flux-system | prospector | Not ready | main@7453d76 | 2026-09-20T13:52:25Z | health check failed after 500.720256ms: failed early due to stalled resources: [Deployment/prospector/prospector-store-api status: 'Failed'] |
| Kustomization | flux-system | router-events | Not ready | main@0df0a74 | 2026-09-20T13:53:40Z | health check failed after 5m0.08977014s: timeout waiting for: [Deployment/llm/litellm status: 'InProgress'] |
| Kustomization | flux-system | sandbox-launch | Not ready | main@ac2a1b1 | 2026-09-20T13:57:38Z | health check failed after 93.226582ms: failed early due to stalled resources: [Job/demo-sandbox/arm-voice-bench status: 'Failed'] |
| Kustomization | flux-system | via-negativa | Not ready | main@a7f5a42 | 2026-09-20T14:00:18Z | Reconciliation in progress |
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
| Kustomization | flux-system | agent-workforce | Ready | main@a7f5a42 | 2026-09-20T13:48:39Z |  |
| Kustomization | flux-system | alerts | Ready | main@a7f5a42 | 2026-09-20T13:58:17Z |  |
| Kustomization | flux-system | alerts-github | Ready | main@a7f5a42 | 2026-09-20T14:00:18Z |  |
| Kustomization | flux-system | alerts-secret | Ready | main@a7f5a42 | 2026-09-20T13:58:02Z |  |
| Kustomization | flux-system | autoscaler | Ready | main@a7f5a42 | 2026-09-20T13:58:01Z |  |
| Kustomization | flux-system | backstage-namespace | Ready | main@a7f5a42 | 2026-09-20T13:56:12Z |  |
| Kustomization | flux-system | chaos-mesh | Ready | main@a7f5a42 | 2026-09-20T13:57:49Z |  |
| Kustomization | flux-system | cluster-state | Ready | main@a7f5a42 | 2026-09-20T13:58:12Z |  |
| Kustomization | flux-system | commerce-data | Ready | main@a7f5a42 | 2026-09-20T13:58:12Z |  |
| Kustomization | flux-system | concierge | Ready | main@a7f5a42 | 2026-09-20T13:57:50Z |  |
| Kustomization | flux-system | cross-node-drill | Ready | main@a7f5a42 | 2026-09-20T13:56:58Z |  |
| Kustomization | flux-system | dagster | Ready | main@a7f5a42 | 2026-09-20T13:48:51Z |  |
| Kustomization | flux-system | dns | Ready | main@a7f5a42 | 2026-09-20T13:58:14Z |  |
| Kustomization | flux-system | drills | Ready | main@a7f5a42 | 2026-09-20T13:58:23Z |  |
| Kustomization | flux-system | edge | Ready | main@a7f5a42 | 2026-09-20T13:57:22Z |  |
| Kustomization | flux-system | estate-catalog | Ready | latest@sha256:af7ecfd48a761c3d204d5e8b48 | 2026-09-20T13:52:07Z |  |
| Kustomization | flux-system | estate-db | Ready | main@a7f5a42 | 2026-09-20T13:57:56Z |  |
| Kustomization | flux-system | estate-db-migrate | Ready | main@a7f5a42 | 2026-09-20T14:00:16Z |  |
| Kustomization | flux-system | estate-db-operator | Ready | main@a7f5a42 | 2026-09-20T13:56:59Z |  |
| Kustomization | flux-system | event-bus | Ready | main@a7f5a42 | 2026-09-20T13:57:03Z |  |
| Kustomization | flux-system | external-secrets | Ready | main@a7f5a42 | 2026-09-20T13:56:48Z |  |
| Kustomization | flux-system | feature-register | Ready | main@a7f5a42 | 2026-09-20T13:56:41Z |  |
| Kustomization | flux-system | flux-system | Ready | main@a7f5a42 | 2026-09-20T13:57:07Z |  |
| Kustomization | flux-system | flux-webhook | Ready | main@a7f5a42 | 2026-09-20T13:57:51Z |  |
| Kustomization | flux-system | gateway-api-crds | Ready | v1.5.1@e7677b7 | 2026-09-20T13:56:54Z |  |
| Kustomization | flux-system | github-app-creds | Ready | main@a7f5a42 | 2026-09-20T13:58:14Z |  |
| Kustomization | flux-system | guacamole | Ready | main@a7f5a42 | 2026-09-20T13:58:22Z |  |
| Kustomization | flux-system | gvisor-runtime | Ready | main@a7f5a42 | 2026-09-20T13:58:34Z |  |
| Kustomization | flux-system | healing | Ready | main@a7f5a42 | 2026-09-20T13:57:35Z |  |
| Kustomization | flux-system | healing-analyzer | Ready | main@a7f5a42 | 2026-09-20T13:49:06Z |  |
| Kustomization | flux-system | healing-k8sgpt | Ready | main@a7f5a42 | 2026-09-20T13:48:36Z |  |
| Kustomization | flux-system | healthchecks | Ready | main@a7f5a42 | 2026-09-20T13:58:21Z |  |
| Kustomization | flux-system | hindsight | Ready | main@a7f5a42 | 2026-09-20T13:48:35Z |  |
| Kustomization | flux-system | human-vault | Ready | main@a7f5a42 | 2026-09-20T13:58:06Z |  |
| Kustomization | flux-system | human-vault-bridge | Ready | main@a7f5a42 | 2026-09-20T13:58:31Z |  |
| Kustomization | flux-system | identity | Ready | main@a7f5a42 | 2026-09-20T13:57:57Z |  |
| Kustomization | flux-system | image-automation | Ready | main@a7f5a42 | 2026-09-20T13:57:59Z |  |
| Kustomization | flux-system | jit | Ready | main@a7f5a42 | 2026-09-20T13:57:36Z |  |
| Kustomization | flux-system | keda | Ready | main@a7f5a42 | 2026-09-20T13:57:04Z |  |
| Kustomization | flux-system | kyverno | Ready | main@a7f5a42 | 2026-09-20T13:56:09Z |  |
| Kustomization | flux-system | llm | Ready | main@a7f5a42 | 2026-09-20T13:58:04Z |  |
| Kustomization | flux-system | mcp | Ready | main@a7f5a42 | 2026-09-20T13:57:46Z |  |
| Kustomization | flux-system | metrics-server | Ready | main@a7f5a42 | 2026-09-20T13:57:34Z |  |
| Kustomization | flux-system | monitoring | Ready | main@a7f5a42 | 2026-09-20T13:58:36Z |  |
| Kustomization | flux-system | monitoring-rules | Ready | main@a7f5a42 | 2026-09-20T13:48:20Z |  |
| Kustomization | flux-system | nodesoftware-operator | Ready | main@a7f5a42 | 2026-09-20T13:58:31Z |  |
| Kustomization | flux-system | notify | Ready | main@a7f5a42 | 2026-09-20T13:57:58Z |  |
| Kustomization | flux-system | ns-fences | Ready | main@a7f5a42 | 2026-09-20T13:57:21Z |  |
| Kustomization | flux-system | observability | Ready | main@a7f5a42 | 2026-09-20T13:58:31Z |  |
| Kustomization | flux-system | observability-collector | Ready | main@a7f5a42 | 2026-09-20T13:57:17Z |  |
| Kustomization | flux-system | otto-golden-secret | Ready | main@a7f5a42 | 2026-09-20T13:57:23Z |  |
| Kustomization | flux-system | priority-classes | Ready | main@a7f5a42 | 2026-09-20T13:56:44Z |  |
| Kustomization | flux-system | prospector-platform | Ready | main@a7f5a42 | 2026-09-20T13:56:53Z |  |
| Kustomization | flux-system | rbac | Ready | main@a7f5a42 | 2026-09-20T13:56:52Z |  |
| Kustomization | flux-system | rbac-floor | Ready | main@a7f5a42 | 2026-09-20T13:56:50Z |  |
| Kustomization | flux-system | rbac-identity | Ready | main@a7f5a42 | 2026-09-20T13:56:49Z |  |
| Kustomization | flux-system | reloader | Ready | main@a7f5a42 | 2026-09-20T13:58:05Z |  |
| Kustomization | flux-system | research-engine | Ready | main@a7f5a42 | 2026-09-20T13:58:20Z |  |
| Kustomization | flux-system | robusta | Ready | main@a7f5a42 | 2026-09-20T13:57:26Z |  |
| Kustomization | flux-system | sandbox-live | Ready | sandbox/launch@4830a6e | 2026-09-20T13:58:20Z |  |
| Kustomization | flux-system | scheduling | Ready | main@a7f5a42 | 2026-09-20T13:57:40Z |  |
| Kustomization | flux-system | science | Ready | main@a7f5a42 | 2026-09-20T13:49:04Z |  |
| Kustomization | flux-system | searxng | Ready | main@a7f5a42 | 2026-09-20T13:56:52Z |  |
| Kustomization | flux-system | secret-store | Ready | main@a7f5a42 | 2026-09-20T13:57:31Z |  |
| Kustomization | flux-system | spire | Ready | main@a7f5a42 | 2026-09-20T13:57:50Z |  |
| Kustomization | flux-system | staging | Ready | main@a7f5a42 | 2026-09-20T13:56:34Z |  |
| Kustomization | flux-system | tailscale | Ready | main@a7f5a42 | 2026-09-20T13:58:07Z |  |
| Kustomization | flux-system | temporal | Ready | main@a7f5a42 | 2026-09-20T13:48:29Z |  |
| Kustomization | flux-system | trivy | Ready | main@a7f5a42 | 2026-09-20T13:56:03Z |  |
| Kustomization | flux-system | verification | Ready | main@a7f5a42 | 2026-09-20T13:58:05Z |  |
| Kustomization | flux-system | weave-gitops | Ready | main@a7f5a42 | 2026-09-20T13:58:16Z |  |
