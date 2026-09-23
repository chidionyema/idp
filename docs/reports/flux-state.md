# Flux: what is applied

Read from the cluster receipt taken at 2026-09-23T02:15:48Z. Every Kustomization and HelmRelease, with the revision Flux last applied. **Suspended** is a switch somebody turned off on purpose (temporal, commerce, commerce-data, event-bus), not a defect; **Unknown** is a row Flux has never graded.

**121 objects: 102 ready, 18 not ready, 0 unknown, 1 suspended.**

## Not ready right now

- **HelmRelease commerce/lago** since 2026-09-18T21:16:37Z: Could not determine release state: unable to determine state for release with status 'uninstalling'
- **HelmRelease crossplane-system/crossplane** since 2026-09-16T17:08:05Z: Helm upgrade failed for release crossplane-system/crossplane with chart crossplane@1.15.1: create: failed to create: admission webhook "oke-resource-leak-protection.oke.com" denied the request: OKE resource leak protection rejected the request. Cluster has 2650 secrets and the limit is 2000. See https://docs.oracle.com/iaas/Content/ContEng/Tasks/contengprotectingclustersfromresourceleaks.htm for details.
- **HelmRelease dagster/dagster** since 2026-09-22T05:28:31Z: Helm rollback to previous release dagster/dagster.v16 with chart dagster@1.13.19 succeeded
- **Kustomization flux-system/calico** since 2026-09-23T02:06:20Z: GlobalNetworkPolicy/deny-direct-ai-vendor-egress dry-run failed: no matches for kind "GlobalNetworkPolicy" in version "projectcalico.org/v3" 
- **Kustomization flux-system/commerce** since 2026-09-23T02:09:06Z: Reconciliation in progress
- **Kustomization flux-system/crossplane** since 2026-09-23T02:06:45Z: health check failed after 66.390568ms: failed early due to stalled resources: [HelmRelease/crossplane-system/crossplane status: 'Failed']
- **Kustomization flux-system/crossplane-providerconfig** since 2026-09-16T11:53:07Z: dependency 'flux-system/crossplane-providers' is not ready
- **Kustomization flux-system/crossplane-providers** since 2026-09-16T11:53:06Z: dependency 'flux-system/crossplane' is not ready
- **Kustomization flux-system/crossplane-storage-capability** since 2026-09-16T11:53:07Z: dependency 'flux-system/crossplane-providerconfig' is not ready
- **Kustomization flux-system/dagster** since 2026-09-23T02:07:17Z: health check failed after 41.711857ms: failed early due to stalled resources: [HelmRelease/dagster/dagster status: 'Failed']
- **Kustomization flux-system/epistemic-fabric** since 2026-09-23T02:09:55Z: health check failed after 199.210144ms: failed early due to stalled resources: [Deployment/epistemic-fabric/epistemic-ingest-github status: 'Failed']
- **Kustomization flux-system/estate-db** since 2026-09-23T02:15:10Z: Reconciliation in progress
- **Kustomization flux-system/hermes-agent** since 2026-09-23T02:14:30Z: health check failed after 7m2.289597754s: failed early due to stalled resources: [Deployment/hermes-agent/hermes-agent-gateway status: 'Failed']
- **Kustomization flux-system/idp-agent** since 2026-09-23T02:07:02Z: Deployment/idp-agent/idp-engine dry-run failed: admission webhook "validate.kyverno.svc-fail" denied the request:   resource Deployment/idp-agent/idp-engine was blocked due to the following policies   disallow-latest-tag:   autogen-require-image-tag: 'validation failure: validation error: An image tag is required. rule autogen-require-image-tag failed at path /image/' require-pod-probes:   autogen-validate-probes: 'validation failure: Liveness, readiness, or startup probes are required for all containers.'  
- **Kustomization flux-system/otto-gateway** since 2026-09-23T02:13:17Z: health check failed after 5m40.982331729s: failed early due to stalled resources: [Deployment/otto-gateway/otto-gateway status: 'Failed']
- **Kustomization flux-system/otto-golden** since 2026-09-23T02:07:01Z: health check failed after 582.692988ms: failed early due to stalled resources: [Deployment/otto-golden/otto-golden status: 'Failed']
- **Kustomization flux-system/sandbox-launch** since 2026-09-23T02:15:06Z: health check failed after 102.203881ms: failed early due to stalled resources: [Job/demo-sandbox/arm-voice-bench status: 'Failed']
- **Kustomization flux-system/via-negativa** since 2026-09-23T02:07:51Z: health check failed after 602.382845ms: failed early due to stalled resources: [Deployment/via-negativa/via-negativa-rca status: 'Failed']

## Every row

| Kind | Namespace | Name | State | Applied revision | Since | Message |
|---|---|---|---|---|---|---|
| HelmRelease | commerce | lago | Not ready | 1.28.0 | 2026-09-18T21:16:37Z | Could not determine release state: unable to determine state for release with status 'uninstalling' |
| HelmRelease | crossplane-system | crossplane | Not ready | 1.15.1 | 2026-09-16T17:08:05Z | Helm upgrade failed for release crossplane-system/crossplane with chart crossplane@1.15.1: create: failed to create: admission webhook "oke-resource-leak-protec |
| HelmRelease | dagster | dagster | Not ready | 1.13.19 | 2026-09-22T05:28:31Z | Helm rollback to previous release dagster/dagster.v16 with chart dagster@1.13.19 succeeded |
| Kustomization | flux-system | calico | Not ready | main@0df0a74 | 2026-09-23T02:06:20Z | GlobalNetworkPolicy/deny-direct-ai-vendor-egress dry-run failed: no matches for kind "GlobalNetworkPolicy" in version "projectcalico.org/v3"  |
| Kustomization | flux-system | commerce | Not ready | main@abea14d | 2026-09-23T02:09:06Z | Reconciliation in progress |
| Kustomization | flux-system | crossplane | Not ready | main@8d685ec | 2026-09-23T02:06:45Z | health check failed after 66.390568ms: failed early due to stalled resources: [HelmRelease/crossplane-system/crossplane status: 'Failed'] |
| Kustomization | flux-system | crossplane-providerconfig | Not ready | main@8d685ec | 2026-09-16T11:53:07Z | dependency 'flux-system/crossplane-providers' is not ready |
| Kustomization | flux-system | crossplane-providers | Not ready | main@8d685ec | 2026-09-16T11:53:06Z | dependency 'flux-system/crossplane' is not ready |
| Kustomization | flux-system | crossplane-storage-capability | Not ready | main@8d685ec | 2026-09-16T11:53:07Z | dependency 'flux-system/crossplane-providerconfig' is not ready |
| Kustomization | flux-system | dagster | Not ready | main@08aa502 | 2026-09-23T02:07:17Z | health check failed after 41.711857ms: failed early due to stalled resources: [HelmRelease/dagster/dagster status: 'Failed'] |
| Kustomization | flux-system | epistemic-fabric | Not ready | main@689bcd9 | 2026-09-23T02:09:55Z | health check failed after 199.210144ms: failed early due to stalled resources: [Deployment/epistemic-fabric/epistemic-ingest-github status: 'Failed'] |
| Kustomization | flux-system | estate-db | Not ready | main@689bcd9 | 2026-09-23T02:15:10Z | Reconciliation in progress |
| Kustomization | flux-system | hermes-agent | Not ready | main@0df0a74 | 2026-09-23T02:14:30Z | health check failed after 7m2.289597754s: failed early due to stalled resources: [Deployment/hermes-agent/hermes-agent-gateway status: 'Failed'] |
| Kustomization | flux-system | idp-agent | Not ready | main@689bcd9 | 2026-09-23T02:07:02Z | Deployment/idp-agent/idp-engine dry-run failed: admission webhook "validate.kyverno.svc-fail" denied the request:   resource Deployment/idp-agent/idp-engine was |
| Kustomization | flux-system | otto-gateway | Not ready | main@cd9eb71 | 2026-09-23T02:13:17Z | health check failed after 5m40.982331729s: failed early due to stalled resources: [Deployment/otto-gateway/otto-gateway status: 'Failed'] |
| Kustomization | flux-system | otto-golden | Not ready | main@cd9eb71 | 2026-09-23T02:07:01Z | health check failed after 582.692988ms: failed early due to stalled resources: [Deployment/otto-golden/otto-golden status: 'Failed'] |
| Kustomization | flux-system | sandbox-launch | Not ready | main@ac2a1b1 | 2026-09-23T02:15:06Z | health check failed after 102.203881ms: failed early due to stalled resources: [Job/demo-sandbox/arm-voice-bench status: 'Failed'] |
| Kustomization | flux-system | via-negativa | Not ready | main@689bcd9 | 2026-09-23T02:07:51Z | health check failed after 602.382845ms: failed early due to stalled resources: [Deployment/via-negativa/via-negativa-rca status: 'Failed'] |
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
| Kustomization | flux-system | agent-workforce | Ready | main@689bcd9 | 2026-09-23T02:07:59Z |  |
| Kustomization | flux-system | alerts | Ready | main@689bcd9 | 2026-09-23T02:13:48Z |  |
| Kustomization | flux-system | alerts-github | Ready | main@689bcd9 | 2026-09-23T02:08:28Z |  |
| Kustomization | flux-system | alerts-secret | Ready | main@689bcd9 | 2026-09-23T02:06:10Z |  |
| Kustomization | flux-system | autoscaler | Ready | main@689bcd9 | 2026-09-23T02:13:26Z |  |
| Kustomization | flux-system | backstage | Ready | main@689bcd9 | 2026-09-23T02:07:24Z |  |
| Kustomization | flux-system | backstage-namespace | Ready | main@689bcd9 | 2026-09-23T02:08:20Z |  |
| Kustomization | flux-system | chaos | Ready | main@689bcd9 | 2026-09-23T02:09:09Z |  |
| Kustomization | flux-system | chaos-mesh | Ready | main@689bcd9 | 2026-09-23T02:07:20Z |  |
| Kustomization | flux-system | cluster-state | Ready | main@689bcd9 | 2026-09-23T02:06:59Z |  |
| Kustomization | flux-system | commerce-data | Ready | main@689bcd9 | 2026-09-23T02:07:22Z |  |
| Kustomization | flux-system | concierge | Ready | main@689bcd9 | 2026-09-23T02:08:46Z |  |
| Kustomization | flux-system | cross-node-drill | Ready | main@689bcd9 | 2026-09-23T02:09:44Z |  |
| Kustomization | flux-system | dns | Ready | main@689bcd9 | 2026-09-23T02:06:21Z |  |
| Kustomization | flux-system | drills | Ready | main@689bcd9 | 2026-09-23T02:09:22Z |  |
| Kustomization | flux-system | edge | Ready | main@689bcd9 | 2026-09-23T02:06:33Z |  |
| Kustomization | flux-system | estate-catalog | Ready | latest@sha256:cfd0a76a2aad036d104de5fe10 | 2026-09-23T02:14:13Z |  |
| Kustomization | flux-system | estate-db-migrate | Ready | main@689bcd9 | 2026-09-23T02:06:18Z |  |
| Kustomization | flux-system | estate-db-operator | Ready | main@689bcd9 | 2026-09-23T02:07:47Z |  |
| Kustomization | flux-system | event-bus | Ready | main@689bcd9 | 2026-09-23T02:10:59Z |  |
| Kustomization | flux-system | external-secrets | Ready | main@689bcd9 | 2026-09-23T02:06:48Z |  |
| Kustomization | flux-system | feature-register | Ready | main@689bcd9 | 2026-09-23T02:12:38Z |  |
| Kustomization | flux-system | flux-system | Ready | main@689bcd9 | 2026-09-23T02:09:37Z |  |
| Kustomization | flux-system | flux-webhook | Ready | main@689bcd9 | 2026-09-23T02:06:45Z |  |
| Kustomization | flux-system | gateway-api-crds | Ready | v1.5.1@e7677b7 | 2026-09-23T02:08:53Z |  |
| Kustomization | flux-system | github-app-creds | Ready | main@689bcd9 | 2026-09-23T02:09:31Z |  |
| Kustomization | flux-system | guacamole | Ready | main@689bcd9 | 2026-09-23T02:08:27Z |  |
| Kustomization | flux-system | gvisor-runtime | Ready | main@689bcd9 | 2026-09-23T02:14:17Z |  |
| Kustomization | flux-system | healing | Ready | main@689bcd9 | 2026-09-23T02:07:46Z |  |
| Kustomization | flux-system | healing-analyzer | Ready | main@689bcd9 | 2026-09-23T02:08:01Z |  |
| Kustomization | flux-system | healing-k8sgpt | Ready | main@689bcd9 | 2026-09-23T02:07:59Z |  |
| Kustomization | flux-system | healthchecks | Ready | main@689bcd9 | 2026-09-23T02:07:58Z |  |
| Kustomization | flux-system | hindsight | Ready | main@689bcd9 | 2026-09-23T02:07:51Z |  |
| Kustomization | flux-system | human-vault | Ready | main@689bcd9 | 2026-09-23T02:08:21Z |  |
| Kustomization | flux-system | human-vault-bridge | Ready | main@689bcd9 | 2026-09-23T02:11:38Z |  |
| Kustomization | flux-system | identity | Ready | main@689bcd9 | 2026-09-23T02:06:18Z |  |
| Kustomization | flux-system | image-automation | Ready | main@689bcd9 | 2026-09-23T02:08:59Z |  |
| Kustomization | flux-system | jit | Ready | main@689bcd9 | 2026-09-23T02:10:35Z |  |
| Kustomization | flux-system | keda | Ready | main@689bcd9 | 2026-09-23T02:09:27Z |  |
| Kustomization | flux-system | kyverno | Ready | main@689bcd9 | 2026-09-23T02:12:47Z |  |
| Kustomization | flux-system | llm | Ready | main@689bcd9 | 2026-09-23T02:07:37Z |  |
| Kustomization | flux-system | mcp | Ready | main@689bcd9 | 2026-09-23T02:06:51Z |  |
| Kustomization | flux-system | metrics-server | Ready | main@689bcd9 | 2026-09-23T02:07:14Z |  |
| Kustomization | flux-system | monitoring | Ready | main@689bcd9 | 2026-09-23T02:07:55Z |  |
| Kustomization | flux-system | monitoring-rules | Ready | main@689bcd9 | 2026-09-23T02:09:30Z |  |
| Kustomization | flux-system | nodesoftware-operator | Ready | main@689bcd9 | 2026-09-23T02:06:56Z |  |
| Kustomization | flux-system | notify | Ready | main@689bcd9 | 2026-09-23T02:06:58Z |  |
| Kustomization | flux-system | ns-fences | Ready | main@689bcd9 | 2026-09-23T02:14:15Z |  |
| Kustomization | flux-system | observability | Ready | main@689bcd9 | 2026-09-23T02:07:46Z |  |
| Kustomization | flux-system | observability-collector | Ready | main@689bcd9 | 2026-09-23T02:07:20Z |  |
| Kustomization | flux-system | otto-golden-secret | Ready | main@689bcd9 | 2026-09-23T02:12:51Z |  |
| Kustomization | flux-system | priority-classes | Ready | main@689bcd9 | 2026-09-23T02:07:54Z |  |
| Kustomization | flux-system | prospector | Ready | main@7453d76 | 2026-09-23T02:08:54Z |  |
| Kustomization | flux-system | prospector-platform | Ready | main@689bcd9 | 2026-09-23T02:08:09Z |  |
| Kustomization | flux-system | rbac | Ready | main@689bcd9 | 2026-09-23T02:08:33Z |  |
| Kustomization | flux-system | rbac-floor | Ready | main@689bcd9 | 2026-09-23T02:14:14Z |  |
| Kustomization | flux-system | rbac-identity | Ready | main@689bcd9 | 2026-09-23T02:07:34Z |  |
| Kustomization | flux-system | reloader | Ready | main@689bcd9 | 2026-09-23T02:05:11Z |  |
| Kustomization | flux-system | research-engine | Ready | main@689bcd9 | 2026-09-23T02:07:25Z |  |
| Kustomization | flux-system | robusta | Ready | main@689bcd9 | 2026-09-23T02:12:25Z |  |
| Kustomization | flux-system | router-events | Ready | main@689bcd9 | 2026-09-23T02:06:53Z |  |
| Kustomization | flux-system | sandbox-live | Ready | sandbox/launch@4830a6e | 2026-09-23T02:14:39Z |  |
| Kustomization | flux-system | scheduling | Ready | main@689bcd9 | 2026-09-23T02:05:53Z |  |
| Kustomization | flux-system | science | Ready | main@689bcd9 | 2026-09-23T02:09:38Z |  |
| Kustomization | flux-system | searxng | Ready | main@689bcd9 | 2026-09-23T02:14:18Z |  |
| Kustomization | flux-system | secret-store | Ready | main@689bcd9 | 2026-09-23T02:07:56Z |  |
| Kustomization | flux-system | spire | Ready | main@689bcd9 | 2026-09-23T02:07:16Z |  |
| Kustomization | flux-system | staging | Ready | main@689bcd9 | 2026-09-23T02:14:12Z |  |
| Kustomization | flux-system | tailscale | Ready | main@689bcd9 | 2026-09-23T02:09:21Z |  |
| Kustomization | flux-system | temporal | Ready | main@689bcd9 | 2026-09-23T02:07:06Z |  |
| Kustomization | flux-system | trivy | Ready | main@689bcd9 | 2026-09-23T02:09:40Z |  |
| Kustomization | flux-system | verification | Ready | main@689bcd9 | 2026-09-23T02:07:18Z |  |
| Kustomization | flux-system | weave-gitops | Ready | main@689bcd9 | 2026-09-23T02:06:54Z |  |
