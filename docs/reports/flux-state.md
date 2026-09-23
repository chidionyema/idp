# Flux: what is applied

Read from the cluster receipt taken at 2026-09-23T03:00:24Z. Every Kustomization and HelmRelease, with the revision Flux last applied. **Suspended** is a switch somebody turned off on purpose (temporal, commerce, commerce-data, event-bus), not a defect; **Unknown** is a row Flux has never graded.

**121 objects: 103 ready, 17 not ready, 0 unknown, 1 suspended.**

## Not ready right now

- **HelmRelease commerce/lago** since 2026-09-18T21:16:37Z: Could not determine release state: unable to determine state for release with status 'uninstalling'
- **HelmRelease crossplane-system/crossplane** since 2026-09-16T17:08:05Z: Helm upgrade failed for release crossplane-system/crossplane with chart crossplane@1.15.1: create: failed to create: admission webhook "oke-resource-leak-protection.oke.com" denied the request: OKE resource leak protection rejected the request. Cluster has 2650 secrets and the limit is 2000. See https://docs.oracle.com/iaas/Content/ContEng/Tasks/contengprotectingclustersfromresourceleaks.htm for details.
- **HelmRelease dagster/dagster** since 2026-09-22T05:28:31Z: Helm rollback to previous release dagster/dagster.v16 with chart dagster@1.13.19 succeeded
- **Kustomization flux-system/calico** since 2026-09-23T02:56:27Z: GlobalNetworkPolicy/deny-direct-ai-vendor-egress dry-run failed: no matches for kind "GlobalNetworkPolicy" in version "projectcalico.org/v3" 
- **Kustomization flux-system/commerce** since 2026-09-23T02:53:10Z: health check failed after 15m0.28627039s: timeout waiting for: [HelmRelease/commerce/lago status: 'InProgress']
- **Kustomization flux-system/crossplane** since 2026-09-23T02:56:52Z: health check failed after 31.657507ms: failed early due to stalled resources: [HelmRelease/crossplane-system/crossplane status: 'Failed']
- **Kustomization flux-system/crossplane-providerconfig** since 2026-09-16T11:53:07Z: dependency 'flux-system/crossplane-providers' is not ready
- **Kustomization flux-system/crossplane-providers** since 2026-09-16T11:53:06Z: dependency 'flux-system/crossplane' is not ready
- **Kustomization flux-system/crossplane-storage-capability** since 2026-09-16T11:53:07Z: dependency 'flux-system/crossplane-providerconfig' is not ready
- **Kustomization flux-system/dagster** since 2026-09-23T02:58:25Z: health check failed after 43.263155ms: failed early due to stalled resources: [HelmRelease/dagster/dagster status: 'Failed']
- **Kustomization flux-system/epistemic-fabric** since 2026-09-23T02:58:10Z: health check failed after 377.064576ms: failed early due to stalled resources: [Deployment/epistemic-fabric/epistemic-ingest-github status: 'Failed']
- **Kustomization flux-system/hermes-agent** since 2026-09-23T02:59:39Z: health check failed after 1m36.320169235s: failed early due to stalled resources: [Deployment/hermes-agent/hermes-agent-gateway status: 'Failed']
- **Kustomization flux-system/idp-agent** since 2026-09-23T02:57:43Z: Service/idp-agent/idp-agent-redis dry-run failed: admission webhook "validate.kyverno.svc-fail" denied the request:   resource Service/idp-agent/idp-agent-redis was blocked due to the following policies   require-catalogue-entity:   service-names-its-entity: 'validation error: Service idp-agent/idp-agent-redis serves a port but names no catalogue entity. Add the label backstage.io/kubernetes-id with the entity name from backstage/**/catalog-info.yaml, and a founder surface if a person opens it (docs/policy/every-interface-is-a-door.md). rule service-names-its-entity failed at path /metadata/labels/backstage.io/kubernetes-id/'  
- **Kustomization flux-system/otto-gateway** since 2026-09-23T02:58:17Z: health check failed after 9m54.878254746s: failed early due to stalled resources: [Deployment/otto-gateway/otto-gateway status: 'Failed']
- **Kustomization flux-system/otto-golden** since 2026-09-23T02:57:50Z: health check failed after 369.945258ms: failed early due to stalled resources: [Deployment/otto-golden/otto-golden status: 'Failed']
- **Kustomization flux-system/sandbox-launch** since 2026-09-23T02:59:57Z: health check failed after 60.295821ms: failed early due to stalled resources: [Job/demo-sandbox/arm-voice-bench status: 'Failed']
- **Kustomization flux-system/via-negativa** since 2026-09-23T02:58:35Z: health check failed after 560.378306ms: failed early due to stalled resources: [Deployment/via-negativa/via-negativa-rca status: 'Failed']

## Every row

| Kind | Namespace | Name | State | Applied revision | Since | Message |
|---|---|---|---|---|---|---|
| HelmRelease | commerce | lago | Not ready | 1.28.0 | 2026-09-18T21:16:37Z | Could not determine release state: unable to determine state for release with status 'uninstalling' |
| HelmRelease | crossplane-system | crossplane | Not ready | 1.15.1 | 2026-09-16T17:08:05Z | Helm upgrade failed for release crossplane-system/crossplane with chart crossplane@1.15.1: create: failed to create: admission webhook "oke-resource-leak-protec |
| HelmRelease | dagster | dagster | Not ready | 1.13.19 | 2026-09-22T05:28:31Z | Helm rollback to previous release dagster/dagster.v16 with chart dagster@1.13.19 succeeded |
| Kustomization | flux-system | calico | Not ready | main@0df0a74 | 2026-09-23T02:56:27Z | GlobalNetworkPolicy/deny-direct-ai-vendor-egress dry-run failed: no matches for kind "GlobalNetworkPolicy" in version "projectcalico.org/v3"  |
| Kustomization | flux-system | commerce | Not ready | main@abea14d | 2026-09-23T02:53:10Z | health check failed after 15m0.28627039s: timeout waiting for: [HelmRelease/commerce/lago status: 'InProgress'] |
| Kustomization | flux-system | crossplane | Not ready | main@8d685ec | 2026-09-23T02:56:52Z | health check failed after 31.657507ms: failed early due to stalled resources: [HelmRelease/crossplane-system/crossplane status: 'Failed'] |
| Kustomization | flux-system | crossplane-providerconfig | Not ready | main@8d685ec | 2026-09-16T11:53:07Z | dependency 'flux-system/crossplane-providers' is not ready |
| Kustomization | flux-system | crossplane-providers | Not ready | main@8d685ec | 2026-09-16T11:53:06Z | dependency 'flux-system/crossplane' is not ready |
| Kustomization | flux-system | crossplane-storage-capability | Not ready | main@8d685ec | 2026-09-16T11:53:07Z | dependency 'flux-system/crossplane-providerconfig' is not ready |
| Kustomization | flux-system | dagster | Not ready | main@08aa502 | 2026-09-23T02:58:25Z | health check failed after 43.263155ms: failed early due to stalled resources: [HelmRelease/dagster/dagster status: 'Failed'] |
| Kustomization | flux-system | epistemic-fabric | Not ready | main@689bcd9 | 2026-09-23T02:58:10Z | health check failed after 377.064576ms: failed early due to stalled resources: [Deployment/epistemic-fabric/epistemic-ingest-github status: 'Failed'] |
| Kustomization | flux-system | hermes-agent | Not ready | main@0df0a74 | 2026-09-23T02:59:39Z | health check failed after 1m36.320169235s: failed early due to stalled resources: [Deployment/hermes-agent/hermes-agent-gateway status: 'Failed'] |
| Kustomization | flux-system | idp-agent | Not ready | main@689bcd9 | 2026-09-23T02:57:43Z | Service/idp-agent/idp-agent-redis dry-run failed: admission webhook "validate.kyverno.svc-fail" denied the request:   resource Service/idp-agent/idp-agent-redis |
| Kustomization | flux-system | otto-gateway | Not ready | main@cd9eb71 | 2026-09-23T02:58:17Z | health check failed after 9m54.878254746s: failed early due to stalled resources: [Deployment/otto-gateway/otto-gateway status: 'Failed'] |
| Kustomization | flux-system | otto-golden | Not ready | main@cd9eb71 | 2026-09-23T02:57:50Z | health check failed after 369.945258ms: failed early due to stalled resources: [Deployment/otto-golden/otto-golden status: 'Failed'] |
| Kustomization | flux-system | sandbox-launch | Not ready | main@ac2a1b1 | 2026-09-23T02:59:57Z | health check failed after 60.295821ms: failed early due to stalled resources: [Job/demo-sandbox/arm-voice-bench status: 'Failed'] |
| Kustomization | flux-system | via-negativa | Not ready | main@689bcd9 | 2026-09-23T02:58:35Z | health check failed after 560.378306ms: failed early due to stalled resources: [Deployment/via-negativa/via-negativa-rca status: 'Failed'] |
| HelmRelease | tigera-operator | tigera-operator | Suspended | v3.32.2 | 2026-09-06T19:38:02Z |  |
| HelmRelease | cert-manager | cert-manager | Ready | v1.21.1 | 2026-09-08T11:56:22Z |  |
| HelmRelease | chaos-mesh | chaos-mesh | Ready | 2.8.4 | 2026-09-21T03:13:40Z |  |
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
| Kustomization | flux-system | agent-workforce | Ready | main@689bcd9 | 2026-09-23T02:58:26Z |  |
| Kustomization | flux-system | alerts | Ready | main@689bcd9 | 2026-09-23T02:54:30Z |  |
| Kustomization | flux-system | alerts-github | Ready | main@689bcd9 | 2026-09-23T02:56:48Z |  |
| Kustomization | flux-system | alerts-secret | Ready | main@689bcd9 | 2026-09-23T02:58:19Z |  |
| Kustomization | flux-system | autoscaler | Ready | main@689bcd9 | 2026-09-23T02:57:58Z |  |
| Kustomization | flux-system | backstage | Ready | main@689bcd9 | 2026-09-23T02:58:37Z |  |
| Kustomization | flux-system | backstage-namespace | Ready | main@689bcd9 | 2026-09-23T02:58:17Z |  |
| Kustomization | flux-system | chaos | Ready | main@689bcd9 | 2026-09-23T02:59:01Z |  |
| Kustomization | flux-system | chaos-mesh | Ready | main@689bcd9 | 2026-09-23T02:58:11Z |  |
| Kustomization | flux-system | cluster-state | Ready | main@689bcd9 | 2026-09-23T02:58:21Z |  |
| Kustomization | flux-system | commerce-data | Ready | main@689bcd9 | 2026-09-23T02:58:07Z |  |
| Kustomization | flux-system | concierge | Ready | main@689bcd9 | 2026-09-23T02:57:16Z |  |
| Kustomization | flux-system | cross-node-drill | Ready | main@689bcd9 | 2026-09-23T02:59:22Z |  |
| Kustomization | flux-system | dns | Ready | main@689bcd9 | 2026-09-23T02:56:43Z |  |
| Kustomization | flux-system | drills | Ready | main@689bcd9 | 2026-09-23T02:59:07Z |  |
| Kustomization | flux-system | edge | Ready | main@689bcd9 | 2026-09-23T02:56:26Z |  |
| Kustomization | flux-system | estate-catalog | Ready | latest@sha256:cfd0a76a2aad036d104de5fe10 | 2026-09-23T02:54:29Z |  |
| Kustomization | flux-system | estate-db | Ready | main@689bcd9 | 2026-09-23T02:58:00Z |  |
| Kustomization | flux-system | estate-db-migrate | Ready | main@689bcd9 | 2026-09-23T02:57:28Z |  |
| Kustomization | flux-system | estate-db-operator | Ready | main@689bcd9 | 2026-09-23T02:57:54Z |  |
| Kustomization | flux-system | event-bus | Ready | main@689bcd9 | 2026-09-23T02:51:32Z |  |
| Kustomization | flux-system | external-secrets | Ready | main@689bcd9 | 2026-09-23T02:58:12Z |  |
| Kustomization | flux-system | feature-register | Ready | main@689bcd9 | 2026-09-23T02:53:18Z |  |
| Kustomization | flux-system | flux-system | Ready | main@689bcd9 | 2026-09-23T02:50:51Z |  |
| Kustomization | flux-system | flux-webhook | Ready | main@689bcd9 | 2026-09-23T02:57:46Z |  |
| Kustomization | flux-system | gateway-api-crds | Ready | v1.5.1@e7677b7 | 2026-09-23T02:59:28Z |  |
| Kustomization | flux-system | github-app-creds | Ready | main@689bcd9 | 2026-09-23T02:58:19Z |  |
| Kustomization | flux-system | guacamole | Ready | main@689bcd9 | 2026-09-23T02:57:42Z |  |
| Kustomization | flux-system | gvisor-runtime | Ready | main@689bcd9 | 2026-09-23T02:54:32Z |  |
| Kustomization | flux-system | healing | Ready | main@689bcd9 | 2026-09-23T02:58:15Z |  |
| Kustomization | flux-system | healing-analyzer | Ready | main@689bcd9 | 2026-09-23T02:58:45Z |  |
| Kustomization | flux-system | healing-k8sgpt | Ready | main@689bcd9 | 2026-09-23T02:58:21Z |  |
| Kustomization | flux-system | healthchecks | Ready | main@689bcd9 | 2026-09-23T02:58:30Z |  |
| Kustomization | flux-system | hindsight | Ready | main@689bcd9 | 2026-09-23T02:58:48Z |  |
| Kustomization | flux-system | human-vault | Ready | main@689bcd9 | 2026-09-23T02:57:19Z |  |
| Kustomization | flux-system | human-vault-bridge | Ready | main@689bcd9 | 2026-09-23T02:57:27Z |  |
| Kustomization | flux-system | identity | Ready | main@689bcd9 | 2026-09-23T02:57:42Z |  |
| Kustomization | flux-system | image-automation | Ready | main@689bcd9 | 2026-09-23T02:57:02Z |  |
| Kustomization | flux-system | jit | Ready | main@689bcd9 | 2026-09-23T02:51:07Z |  |
| Kustomization | flux-system | keda | Ready | main@689bcd9 | 2026-09-23T02:59:01Z |  |
| Kustomization | flux-system | kyverno | Ready | main@689bcd9 | 2026-09-23T02:52:25Z |  |
| Kustomization | flux-system | llm | Ready | main@689bcd9 | 2026-09-23T02:58:00Z |  |
| Kustomization | flux-system | mcp | Ready | main@689bcd9 | 2026-09-23T02:57:24Z |  |
| Kustomization | flux-system | metrics-server | Ready | main@689bcd9 | 2026-09-23T02:57:09Z |  |
| Kustomization | flux-system | monitoring | Ready | main@689bcd9 | 2026-09-23T02:57:18Z |  |
| Kustomization | flux-system | monitoring-rules | Ready | main@689bcd9 | 2026-09-23T02:57:54Z |  |
| Kustomization | flux-system | nodesoftware-operator | Ready | main@689bcd9 | 2026-09-23T02:57:20Z |  |
| Kustomization | flux-system | notify | Ready | main@689bcd9 | 2026-09-23T02:58:01Z |  |
| Kustomization | flux-system | ns-fences | Ready | main@689bcd9 | 2026-09-23T02:55:14Z |  |
| Kustomization | flux-system | observability | Ready | main@689bcd9 | 2026-09-23T02:58:31Z |  |
| Kustomization | flux-system | observability-collector | Ready | main@689bcd9 | 2026-09-23T02:57:49Z |  |
| Kustomization | flux-system | otto-golden-secret | Ready | main@689bcd9 | 2026-09-23T02:57:24Z |  |
| Kustomization | flux-system | priority-classes | Ready | main@689bcd9 | 2026-09-23T02:57:05Z |  |
| Kustomization | flux-system | prospector | Ready | main@7453d76 | 2026-09-23T02:58:37Z |  |
| Kustomization | flux-system | prospector-platform | Ready | main@689bcd9 | 2026-09-23T02:58:58Z |  |
| Kustomization | flux-system | rbac | Ready | main@689bcd9 | 2026-09-23T02:58:46Z |  |
| Kustomization | flux-system | rbac-floor | Ready | main@689bcd9 | 2026-09-23T02:55:15Z |  |
| Kustomization | flux-system | rbac-identity | Ready | main@689bcd9 | 2026-09-23T02:58:03Z |  |
| Kustomization | flux-system | reloader | Ready | main@689bcd9 | 2026-09-23T02:58:05Z |  |
| Kustomization | flux-system | research-engine | Ready | main@689bcd9 | 2026-09-23T02:59:13Z |  |
| Kustomization | flux-system | robusta | Ready | main@689bcd9 | 2026-09-23T02:58:04Z |  |
| Kustomization | flux-system | router-events | Ready | main@689bcd9 | 2026-09-23T02:57:57Z |  |
| Kustomization | flux-system | sandbox-live | Ready | sandbox/launch@4830a6e | 2026-09-23T02:59:36Z |  |
| Kustomization | flux-system | scheduling | Ready | main@689bcd9 | 2026-09-23T02:56:47Z |  |
| Kustomization | flux-system | science | Ready | main@689bcd9 | 2026-09-23T02:58:48Z |  |
| Kustomization | flux-system | searxng | Ready | main@689bcd9 | 2026-09-23T02:54:39Z |  |
| Kustomization | flux-system | secret-store | Ready | main@689bcd9 | 2026-09-23T02:57:07Z |  |
| Kustomization | flux-system | spire | Ready | main@689bcd9 | 2026-09-23T02:57:06Z |  |
| Kustomization | flux-system | staging | Ready | main@689bcd9 | 2026-09-23T02:53:51Z |  |
| Kustomization | flux-system | tailscale | Ready | main@689bcd9 | 2026-09-23T02:56:27Z |  |
| Kustomization | flux-system | temporal | Ready | main@689bcd9 | 2026-09-23T02:58:52Z |  |
| Kustomization | flux-system | trivy | Ready | main@689bcd9 | 2026-09-23T02:59:45Z |  |
| Kustomization | flux-system | verification | Ready | main@689bcd9 | 2026-09-23T02:57:13Z |  |
| Kustomization | flux-system | weave-gitops | Ready | main@689bcd9 | 2026-09-23T02:58:12Z |  |
