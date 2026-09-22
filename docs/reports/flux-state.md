# Flux: what is applied

Read from the cluster receipt taken at 2026-09-22T07:15:57Z. Every Kustomization and HelmRelease, with the revision Flux last applied. **Suspended** is a switch somebody turned off on purpose (temporal, commerce, commerce-data, event-bus), not a defect; **Unknown** is a row Flux has never graded.

**121 objects: 99 ready, 21 not ready, 0 unknown, 1 suspended.**

## Not ready right now

- **HelmRelease commerce/lago** since 2026-09-18T21:16:37Z: Could not determine release state: unable to determine state for release with status 'uninstalling'
- **HelmRelease crossplane-system/crossplane** since 2026-09-16T17:08:05Z: Helm upgrade failed for release crossplane-system/crossplane with chart crossplane@1.15.1: create: failed to create: admission webhook "oke-resource-leak-protection.oke.com" denied the request: OKE resource leak protection rejected the request. Cluster has 2650 secrets and the limit is 2000. See https://docs.oracle.com/iaas/Content/ContEng/Tasks/contengprotectingclustersfromresourceleaks.htm for details.
- **HelmRelease dagster/dagster** since 2026-09-22T05:28:31Z: Helm rollback to previous release dagster/dagster.v16 with chart dagster@1.13.19 succeeded
- **Kustomization flux-system/agent-workforce** since 2026-09-22T07:15:18Z: Reconciliation in progress
- **Kustomization flux-system/calico** since 2026-09-22T07:13:34Z: GlobalNetworkPolicy/deny-direct-ai-vendor-egress dry-run failed: no matches for kind "GlobalNetworkPolicy" in version "projectcalico.org/v3" 
- **Kustomization flux-system/commerce** since 2026-09-22T07:10:20Z: Reconciliation in progress
- **Kustomization flux-system/crossplane** since 2026-09-22T07:14:39Z: health check failed after 60.510745ms: failed early due to stalled resources: [HelmRelease/crossplane-system/crossplane status: 'Failed']
- **Kustomization flux-system/crossplane-providerconfig** since 2026-09-16T11:53:07Z: dependency 'flux-system/crossplane-providers' is not ready
- **Kustomization flux-system/crossplane-providers** since 2026-09-16T11:53:06Z: dependency 'flux-system/crossplane' is not ready
- **Kustomization flux-system/crossplane-storage-capability** since 2026-09-16T11:53:07Z: dependency 'flux-system/crossplane-providerconfig' is not ready
- **Kustomization flux-system/dagster** since 2026-09-22T07:14:58Z: health check failed after 46.379389ms: failed early due to stalled resources: [HelmRelease/dagster/dagster status: 'Failed']
- **Kustomization flux-system/epistemic-fabric** since 2026-09-22T07:14:52Z: health check failed after 95.207165ms: failed early due to stalled resources: [Deployment/epistemic-fabric/epistemic-ingest-github status: 'Failed']
- **Kustomization flux-system/healthchecks** since 2026-09-22T07:15:16Z: Reconciliation in progress
- **Kustomization flux-system/hermes-agent** since 2026-09-22T07:05:19Z: health check failed after 4.49864123s: failed early due to stalled resources: [Deployment/hermes-agent/hermes-agent-gateway status: 'Failed']
- **Kustomization flux-system/idp-agent** since 2026-09-22T07:14:57Z: dependency 'flux-system/github-app-creds' is not ready
- **Kustomization flux-system/otto-gateway** since 2026-09-22T07:05:26Z: health check failed after 3.580734193s: failed early due to stalled resources: [Deployment/otto-gateway/otto-gateway status: 'Failed']
- **Kustomization flux-system/otto-golden** since 2026-09-22T07:15:11Z: health check failed after 776.286604ms: failed early due to stalled resources: [Deployment/otto-golden/otto-golden status: 'Failed']
- **Kustomization flux-system/research-engine** since 2026-09-22T07:15:18Z: Reconciliation in progress
- **Kustomization flux-system/router-events** since 2026-09-22T07:15:15Z: dependency 'flux-system/llm' is not ready
- **Kustomization flux-system/sandbox-launch** since 2026-09-22T07:14:20Z: health check failed after 204.713887ms: failed early due to stalled resources: [Job/demo-sandbox/arm-voice-bench status: 'Failed']
- **Kustomization flux-system/via-negativa** since 2026-09-22T07:05:29Z: health check failed after 457.728905ms: failed early due to stalled resources: [Deployment/via-negativa/via-negativa-rca status: 'Failed']

## Every row

| Kind | Namespace | Name | State | Applied revision | Since | Message |
|---|---|---|---|---|---|---|
| HelmRelease | commerce | lago | Not ready | 1.28.0 | 2026-09-18T21:16:37Z | Could not determine release state: unable to determine state for release with status 'uninstalling' |
| HelmRelease | crossplane-system | crossplane | Not ready | 1.15.1 | 2026-09-16T17:08:05Z | Helm upgrade failed for release crossplane-system/crossplane with chart crossplane@1.15.1: create: failed to create: admission webhook "oke-resource-leak-protec |
| HelmRelease | dagster | dagster | Not ready | 1.13.19 | 2026-09-22T05:28:31Z | Helm rollback to previous release dagster/dagster.v16 with chart dagster@1.13.19 succeeded |
| Kustomization | flux-system | agent-workforce | Not ready | main@ba8d1c0 | 2026-09-22T07:15:18Z | Reconciliation in progress |
| Kustomization | flux-system | calico | Not ready | main@0df0a74 | 2026-09-22T07:13:34Z | GlobalNetworkPolicy/deny-direct-ai-vendor-egress dry-run failed: no matches for kind "GlobalNetworkPolicy" in version "projectcalico.org/v3"  |
| Kustomization | flux-system | commerce | Not ready | main@abea14d | 2026-09-22T07:10:20Z | Reconciliation in progress |
| Kustomization | flux-system | crossplane | Not ready | main@8d685ec | 2026-09-22T07:14:39Z | health check failed after 60.510745ms: failed early due to stalled resources: [HelmRelease/crossplane-system/crossplane status: 'Failed'] |
| Kustomization | flux-system | crossplane-providerconfig | Not ready | main@8d685ec | 2026-09-16T11:53:07Z | dependency 'flux-system/crossplane-providers' is not ready |
| Kustomization | flux-system | crossplane-providers | Not ready | main@8d685ec | 2026-09-16T11:53:06Z | dependency 'flux-system/crossplane' is not ready |
| Kustomization | flux-system | crossplane-storage-capability | Not ready | main@8d685ec | 2026-09-16T11:53:07Z | dependency 'flux-system/crossplane-providerconfig' is not ready |
| Kustomization | flux-system | dagster | Not ready | main@08aa502 | 2026-09-22T07:14:58Z | health check failed after 46.379389ms: failed early due to stalled resources: [HelmRelease/dagster/dagster status: 'Failed'] |
| Kustomization | flux-system | epistemic-fabric | Not ready | main@ba8d1c0 | 2026-09-22T07:14:52Z | health check failed after 95.207165ms: failed early due to stalled resources: [Deployment/epistemic-fabric/epistemic-ingest-github status: 'Failed'] |
| Kustomization | flux-system | healthchecks | Not ready | main@ba8d1c0 | 2026-09-22T07:15:16Z | Reconciliation in progress |
| Kustomization | flux-system | hermes-agent | Not ready | main@0df0a74 | 2026-09-22T07:05:19Z | health check failed after 4.49864123s: failed early due to stalled resources: [Deployment/hermes-agent/hermes-agent-gateway status: 'Failed'] |
| Kustomization | flux-system | idp-agent | Not ready | main@ba8d1c0 | 2026-09-22T07:14:57Z | dependency 'flux-system/github-app-creds' is not ready |
| Kustomization | flux-system | otto-gateway | Not ready | main@cd9eb71 | 2026-09-22T07:05:26Z | health check failed after 3.580734193s: failed early due to stalled resources: [Deployment/otto-gateway/otto-gateway status: 'Failed'] |
| Kustomization | flux-system | otto-golden | Not ready | main@cd9eb71 | 2026-09-22T07:15:11Z | health check failed after 776.286604ms: failed early due to stalled resources: [Deployment/otto-golden/otto-golden status: 'Failed'] |
| Kustomization | flux-system | research-engine | Not ready | main@ba8d1c0 | 2026-09-22T07:15:18Z | Reconciliation in progress |
| Kustomization | flux-system | router-events | Not ready | main@ba8d1c0 | 2026-09-22T07:15:15Z | dependency 'flux-system/llm' is not ready |
| Kustomization | flux-system | sandbox-launch | Not ready | main@ac2a1b1 | 2026-09-22T07:14:20Z | health check failed after 204.713887ms: failed early due to stalled resources: [Job/demo-sandbox/arm-voice-bench status: 'Failed'] |
| Kustomization | flux-system | via-negativa | Not ready | main@ba8d1c0 | 2026-09-22T07:05:29Z | health check failed after 457.728905ms: failed early due to stalled resources: [Deployment/via-negativa/via-negativa-rca status: 'Failed'] |
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
| Kustomization | flux-system | alerts | Ready | main@ba8d1c0 | 2026-09-22T07:15:12Z |  |
| Kustomization | flux-system | alerts-github | Ready | main@ba8d1c0 | 2026-09-22T07:05:13Z |  |
| Kustomization | flux-system | alerts-secret | Ready | main@ba8d1c0 | 2026-09-22T07:14:21Z |  |
| Kustomization | flux-system | autoscaler | Ready | main@ba8d1c0 | 2026-09-22T07:14:21Z |  |
| Kustomization | flux-system | backstage | Ready | main@ba8d1c0 | 2026-09-22T07:07:17Z |  |
| Kustomization | flux-system | backstage-namespace | Ready | main@ba8d1c0 | 2026-09-22T07:13:33Z |  |
| Kustomization | flux-system | chaos | Ready | main@ba8d1c0 | 2026-09-22T07:07:21Z |  |
| Kustomization | flux-system | chaos-mesh | Ready | main@ba8d1c0 | 2026-09-22T07:13:56Z |  |
| Kustomization | flux-system | cluster-state | Ready | main@ba8d1c0 | 2026-09-22T07:14:49Z |  |
| Kustomization | flux-system | commerce-data | Ready | main@ba8d1c0 | 2026-09-22T07:14:40Z |  |
| Kustomization | flux-system | concierge | Ready | main@ba8d1c0 | 2026-09-22T07:14:40Z |  |
| Kustomization | flux-system | cross-node-drill | Ready | main@ba8d1c0 | 2026-09-22T07:13:33Z |  |
| Kustomization | flux-system | dns | Ready | main@ba8d1c0 | 2026-09-22T07:14:49Z |  |
| Kustomization | flux-system | drills | Ready | main@ba8d1c0 | 2026-09-22T07:14:43Z |  |
| Kustomization | flux-system | edge | Ready | main@ba8d1c0 | 2026-09-22T07:13:23Z |  |
| Kustomization | flux-system | estate-catalog | Ready | latest@sha256:0f6d86e05a270e05959490c3a3 | 2026-09-22T07:06:36Z |  |
| Kustomization | flux-system | estate-db | Ready | main@ba8d1c0 | 2026-09-22T07:14:43Z |  |
| Kustomization | flux-system | estate-db-migrate | Ready | main@ba8d1c0 | 2026-09-22T07:14:37Z |  |
| Kustomization | flux-system | estate-db-operator | Ready | main@ba8d1c0 | 2026-09-22T07:13:19Z |  |
| Kustomization | flux-system | event-bus | Ready | main@ba8d1c0 | 2026-09-22T07:13:34Z |  |
| Kustomization | flux-system | external-secrets | Ready | main@ba8d1c0 | 2026-09-22T07:14:12Z |  |
| Kustomization | flux-system | feature-register | Ready | main@ba8d1c0 | 2026-09-22T07:13:31Z |  |
| Kustomization | flux-system | flux-system | Ready | main@ba8d1c0 | 2026-09-22T07:14:00Z |  |
| Kustomization | flux-system | flux-webhook | Ready | main@ba8d1c0 | 2026-09-22T07:14:34Z |  |
| Kustomization | flux-system | gateway-api-crds | Ready | v1.5.1@e7677b7 | 2026-09-22T07:13:25Z |  |
| Kustomization | flux-system | github-app-creds | Ready | main@ba8d1c0 | 2026-09-22T07:14:58Z |  |
| Kustomization | flux-system | guacamole | Ready | main@ba8d1c0 | 2026-09-22T07:05:19Z |  |
| Kustomization | flux-system | gvisor-runtime | Ready | main@ba8d1c0 | 2026-09-22T07:14:54Z |  |
| Kustomization | flux-system | healing | Ready | main@ba8d1c0 | 2026-09-22T07:13:49Z |  |
| Kustomization | flux-system | healing-analyzer | Ready | main@ba8d1c0 | 2026-09-22T07:15:16Z |  |
| Kustomization | flux-system | healing-k8sgpt | Ready | main@ba8d1c0 | 2026-09-22T07:05:23Z |  |
| Kustomization | flux-system | hindsight | Ready | main@ba8d1c0 | 2026-09-22T07:15:04Z |  |
| Kustomization | flux-system | human-vault | Ready | main@ba8d1c0 | 2026-09-22T07:14:45Z |  |
| Kustomization | flux-system | human-vault-bridge | Ready | main@ba8d1c0 | 2026-09-22T07:14:45Z |  |
| Kustomization | flux-system | identity | Ready | main@ba8d1c0 | 2026-09-22T07:14:27Z |  |
| Kustomization | flux-system | image-automation | Ready | main@ba8d1c0 | 2026-09-22T07:14:00Z |  |
| Kustomization | flux-system | jit | Ready | main@ba8d1c0 | 2026-09-22T07:13:51Z |  |
| Kustomization | flux-system | keda | Ready | main@ba8d1c0 | 2026-09-22T07:14:29Z |  |
| Kustomization | flux-system | kyverno | Ready | main@ba8d1c0 | 2026-09-22T07:13:05Z |  |
| Kustomization | flux-system | llm | Ready | main@ba8d1c0 | 2026-09-22T07:15:18Z |  |
| Kustomization | flux-system | mcp | Ready | main@ba8d1c0 | 2026-09-22T07:15:13Z |  |
| Kustomization | flux-system | metrics-server | Ready | main@ba8d1c0 | 2026-09-22T07:14:28Z |  |
| Kustomization | flux-system | monitoring | Ready | main@ba8d1c0 | 2026-09-22T07:14:13Z |  |
| Kustomization | flux-system | monitoring-rules | Ready | main@ba8d1c0 | 2026-09-22T07:15:18Z |  |
| Kustomization | flux-system | nodesoftware-operator | Ready | main@ba8d1c0 | 2026-09-22T07:15:00Z |  |
| Kustomization | flux-system | notify | Ready | main@ba8d1c0 | 2026-09-22T07:13:56Z |  |
| Kustomization | flux-system | ns-fences | Ready | main@ba8d1c0 | 2026-09-22T07:14:35Z |  |
| Kustomization | flux-system | observability | Ready | main@ba8d1c0 | 2026-09-22T07:15:15Z |  |
| Kustomization | flux-system | observability-collector | Ready | main@ba8d1c0 | 2026-09-22T07:14:48Z |  |
| Kustomization | flux-system | otto-golden-secret | Ready | main@ba8d1c0 | 2026-09-22T07:14:30Z |  |
| Kustomization | flux-system | priority-classes | Ready | main@ba8d1c0 | 2026-09-22T07:13:46Z |  |
| Kustomization | flux-system | prospector | Ready | main@7453d76 | 2026-09-22T07:08:35Z |  |
| Kustomization | flux-system | prospector-platform | Ready | main@ba8d1c0 | 2026-09-22T07:15:03Z |  |
| Kustomization | flux-system | rbac | Ready | main@ba8d1c0 | 2026-09-22T07:13:37Z |  |
| Kustomization | flux-system | rbac-floor | Ready | main@ba8d1c0 | 2026-09-22T07:13:58Z |  |
| Kustomization | flux-system | rbac-identity | Ready | main@ba8d1c0 | 2026-09-22T07:13:12Z |  |
| Kustomization | flux-system | reloader | Ready | main@ba8d1c0 | 2026-09-22T07:14:13Z |  |
| Kustomization | flux-system | robusta | Ready | main@ba8d1c0 | 2026-09-22T07:14:33Z |  |
| Kustomization | flux-system | sandbox-live | Ready | sandbox/launch@4830a6e | 2026-09-22T07:14:52Z |  |
| Kustomization | flux-system | scheduling | Ready | main@ba8d1c0 | 2026-09-22T07:13:53Z |  |
| Kustomization | flux-system | science | Ready | main@ba8d1c0 | 2026-09-22T07:05:40Z |  |
| Kustomization | flux-system | searxng | Ready | main@ba8d1c0 | 2026-09-22T07:13:37Z |  |
| Kustomization | flux-system | secret-store | Ready | main@ba8d1c0 | 2026-09-22T07:13:47Z |  |
| Kustomization | flux-system | spire | Ready | main@ba8d1c0 | 2026-09-22T07:13:49Z |  |
| Kustomization | flux-system | staging | Ready | main@ba8d1c0 | 2026-09-22T07:13:40Z |  |
| Kustomization | flux-system | tailscale | Ready | main@ba8d1c0 | 2026-09-22T07:14:16Z |  |
| Kustomization | flux-system | temporal | Ready | main@ba8d1c0 | 2026-09-22T07:14:54Z |  |
| Kustomization | flux-system | trivy | Ready | main@ba8d1c0 | 2026-09-22T07:13:49Z |  |
| Kustomization | flux-system | verification | Ready | main@ba8d1c0 | 2026-09-22T07:14:33Z |  |
| Kustomization | flux-system | weave-gitops | Ready | main@ba8d1c0 | 2026-09-22T07:14:15Z |  |
