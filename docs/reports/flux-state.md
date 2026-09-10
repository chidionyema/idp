# Flux: what is applied

Read from the cluster receipt taken at 2026-09-10T09:15:13Z. Every Kustomization and HelmRelease, with the revision Flux last applied. **Suspended** is a switch somebody turned off on purpose (temporal, commerce, commerce-data, event-bus), not a defect; **Unknown** is a row Flux has never graded.

**114 objects: 86 ready, 26 not ready, 0 unknown, 2 suspended.**

## Not ready right now

- **HelmRelease commerce/lago** since 2026-09-10T09:04:41Z: Running 'upgrade' action with timeout of 15m0s
- **Kustomization flux-system/agent-workforce** since 2026-09-10T09:11:58Z: dependency 'flux-system/llm' is not ready
- **Kustomization flux-system/backstage** since 2026-09-10T09:11:58Z: dependency 'flux-system/estate-db-migrate' is not ready
- **Kustomization flux-system/chaos** since 2026-09-10T09:11:11Z: dependency 'flux-system/chaos-mesh' is not ready
- **Kustomization flux-system/commerce** since 2026-09-10T09:04:40Z: Reconciliation in progress
- **Kustomization flux-system/cyrus** since 2026-09-10T09:11:58Z: Reconciliation in progress
- **Kustomization flux-system/dagster** since 2026-09-10T09:11:58Z: dependency 'flux-system/estate-db-migrate' is not ready
- **Kustomization flux-system/estate-db-migrate** since 2026-09-10T09:11:11Z: dependency 'flux-system/estate-db' is not ready
- **Kustomization flux-system/guacamole** since 2026-09-10T09:11:53Z: dependency 'flux-system/tailscale' is not ready
- **Kustomization flux-system/healing** since 2026-09-10T09:11:02Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/healing-analyzer** since 2026-09-10T09:11:07Z: dependency 'flux-system/healing-k8sgpt' is not ready
- **Kustomization flux-system/healing-k8sgpt** since 2026-09-10T09:11:11Z: dependency 'flux-system/healing' is not ready
- **Kustomization flux-system/healthchecks** since 2026-09-10T09:11:58Z: dependency 'flux-system/estate-db-migrate' is not ready
- **Kustomization flux-system/hermes-agent** since 2026-09-10T09:11:36Z: dependency 'flux-system/alerts-github' is not ready
- **Kustomization flux-system/hindsight** since 2026-09-10T09:11:58Z: dependency 'flux-system/llm' is not ready
- **Kustomization flux-system/keda** since 2026-09-10T09:11:02Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/llm** since 2026-09-10T09:11:58Z: dependency 'flux-system/estate-db-migrate' is not ready
- **Kustomization flux-system/metrics-server** since 2026-09-10T09:11:02Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/notify** since 2026-09-10T09:11:33Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/observability** since 2026-09-10T09:11:58Z: dependency 'flux-system/observability-collector' is not ready
- **Kustomization flux-system/observability-collector** since 2026-09-10T09:15:09Z: Reconciliation in progress
- **Kustomization flux-system/otto-gateway** since 2026-09-10T09:15:07Z: health check failed after 1.72506263s: failed early due to stalled resources: [Deployment/otto-gateway/otto-gateway status: 'Failed']
- **Kustomization flux-system/research-engine** since 2026-09-10T09:11:58Z: dependency 'flux-system/llm' is not ready
- **Kustomization flux-system/science** since 2026-09-10T09:10:41Z: dependency 'flux-system/observability' is not ready
- **Kustomization flux-system/tailscale** since 2026-09-10T09:11:54Z: Reconciliation in progress
- **Kustomization flux-system/weave-gitops** since 2026-09-10T09:11:47Z: dependency 'flux-system/identity' is not ready

## Every row

| Kind | Namespace | Name | State | Applied revision | Since | Message |
|---|---|---|---|---|---|---|
| HelmRelease | commerce | lago | Not ready | 1.28.0 | 2026-09-10T09:04:41Z | Running 'upgrade' action with timeout of 15m0s |
| Kustomization | flux-system | agent-workforce | Not ready | main@54b4a64 | 2026-09-10T09:11:58Z | dependency 'flux-system/llm' is not ready |
| Kustomization | flux-system | backstage | Not ready | main@54b4a64 | 2026-09-10T09:11:58Z | dependency 'flux-system/estate-db-migrate' is not ready |
| Kustomization | flux-system | chaos | Not ready | main@54b4a64 | 2026-09-10T09:11:11Z | dependency 'flux-system/chaos-mesh' is not ready |
| Kustomization | flux-system | commerce | Not ready | main@54b4a64 | 2026-09-10T09:04:40Z | Reconciliation in progress |
| Kustomization | flux-system | cyrus | Not ready | main@17a5ceb | 2026-09-10T09:11:58Z | Reconciliation in progress |
| Kustomization | flux-system | dagster | Not ready | main@54b4a64 | 2026-09-10T09:11:58Z | dependency 'flux-system/estate-db-migrate' is not ready |
| Kustomization | flux-system | estate-db-migrate | Not ready | main@54b4a64 | 2026-09-10T09:11:11Z | dependency 'flux-system/estate-db' is not ready |
| Kustomization | flux-system | guacamole | Not ready | main@5b6aeea | 2026-09-10T09:11:53Z | dependency 'flux-system/tailscale' is not ready |
| Kustomization | flux-system | healing | Not ready | main@54b4a64 | 2026-09-10T09:11:02Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | healing-analyzer | Not ready | main@54b4a64 | 2026-09-10T09:11:07Z | dependency 'flux-system/healing-k8sgpt' is not ready |
| Kustomization | flux-system | healing-k8sgpt | Not ready | main@54b4a64 | 2026-09-10T09:11:11Z | dependency 'flux-system/healing' is not ready |
| Kustomization | flux-system | healthchecks | Not ready | main@54b4a64 | 2026-09-10T09:11:58Z | dependency 'flux-system/estate-db-migrate' is not ready |
| Kustomization | flux-system | hermes-agent | Not ready | main@54b4a64 | 2026-09-10T09:11:36Z | dependency 'flux-system/alerts-github' is not ready |
| Kustomization | flux-system | hindsight | Not ready | main@54b4a64 | 2026-09-10T09:11:58Z | dependency 'flux-system/llm' is not ready |
| Kustomization | flux-system | keda | Not ready | main@54b4a64 | 2026-09-10T09:11:02Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | llm | Not ready | main@54b4a64 | 2026-09-10T09:11:58Z | dependency 'flux-system/estate-db-migrate' is not ready |
| Kustomization | flux-system | metrics-server | Not ready | main@54b4a64 | 2026-09-10T09:11:02Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | notify | Not ready | main@54b4a64 | 2026-09-10T09:11:33Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | observability | Not ready | main@54b4a64 | 2026-09-10T09:11:58Z | dependency 'flux-system/observability-collector' is not ready |
| Kustomization | flux-system | observability-collector | Not ready | main@54b4a64 | 2026-09-10T09:15:09Z | Reconciliation in progress |
| Kustomization | flux-system | otto-gateway | Not ready | main@bb83118 | 2026-09-10T09:15:07Z | health check failed after 1.72506263s: failed early due to stalled resources: [Deployment/otto-gateway/otto-gateway status: 'Failed'] |
| Kustomization | flux-system | research-engine | Not ready | main@54b4a64 | 2026-09-10T09:11:58Z | dependency 'flux-system/llm' is not ready |
| Kustomization | flux-system | science | Not ready | main@54b4a64 | 2026-09-10T09:10:41Z | dependency 'flux-system/observability' is not ready |
| Kustomization | flux-system | tailscale | Not ready | main@d3ab8a2 | 2026-09-10T09:11:54Z | Reconciliation in progress |
| Kustomization | flux-system | weave-gitops | Not ready | main@54b4a64 | 2026-09-10T09:11:47Z | dependency 'flux-system/identity' is not ready |
| HelmRelease | tigera-operator | tigera-operator | Suspended | v3.32.2 | 2026-09-06T19:38:02Z |  |
| Kustomization | flux-system | temporal | Suspended | main@1b323ac | 2026-09-08T20:23:54Z |  |
| HelmRelease | cert-manager | cert-manager | Ready | v1.21.1 | 2026-09-08T11:56:22Z |  |
| HelmRelease | chaos-mesh | chaos-mesh | Ready | 2.8.4 | 2026-09-08T09:36:49Z |  |
| HelmRelease | crossplane-system | crossplane | Ready | 2.4.0 | 2026-09-08T07:05:25Z |  |
| HelmRelease | dagster | dagster | Ready | 1.13.19 | 2026-09-08T06:32:55Z |  |
| HelmRelease | edge | external-dns | Ready | 1.21.1 | 2026-09-06T19:33:35Z |  |
| HelmRelease | edge | traefik | Ready | 41.3.0 | 2026-09-06T19:35:13Z |  |
| HelmRelease | estate-db | cloudnative-pg | Ready | 0.29.0 | 2026-09-06T19:45:25Z |  |
| HelmRelease | event-bus | nats | Ready | 2.14.6 | 2026-09-06T19:39:37Z |  |
| HelmRelease | external-secrets | external-secrets | Ready | 2.9.0 | 2026-09-08T11:57:40Z |  |
| HelmRelease | healing | descheduler | Ready | 0.36.0 | 2026-09-08T10:45:39Z |  |
| HelmRelease | healing | k8sgpt-operator | Ready | 0.2.29 | 2026-09-08T12:01:53Z |  |
| HelmRelease | hindsight | hindsight | Ready | 0.9.2 | 2026-09-08T18:46:49Z |  |
| HelmRelease | identity | oauth2-proxy | Ready | 10.7.0 | 2026-09-08T10:18:34Z |  |
| HelmRelease | keda | keda | Ready | 2.20.2 | 2026-09-08T10:19:32Z |  |
| HelmRelease | keda | keda-add-ons-http | Ready | 0.15.0 | 2026-09-08T10:20:22Z |  |
| HelmRelease | kyverno | kyverno | Ready | 3.9.0 | 2026-09-08T10:19:02Z |  |
| HelmRelease | metrics-server | metrics-server | Ready | 3.14.0 | 2026-09-06T19:34:02Z |  |
| HelmRelease | monitoring | blackbox | Ready | 11.17.2 | 2026-09-06T19:47:10Z |  |
| HelmRelease | monitoring | kube-prometheus-stack | Ready | 88.6.0 | 2026-09-06T20:26:45Z |  |
| HelmRelease | observability | langfuse | Ready | 2.0.2 | 2026-09-08T08:30:33Z |  |
| HelmRelease | observability | signoz | Ready | 0.138.0 | 2026-09-08T12:05:11Z |  |
| HelmRelease | observability | superset | Ready | 0.22.4 | 2026-09-06T19:46:05Z |  |
| HelmRelease | observability-agent | k8s-infra | Ready | 0.17.0 | 2026-09-09T14:28:44Z |  |
| HelmRelease | reloader | reloader | Ready | 2.2.16 | 2026-09-06T19:33:25Z |  |
| HelmRelease | robusta | robusta | Ready | 0.48.0 | 2026-09-06T20:26:45Z |  |
| HelmRelease | spire-mgmt | spire | Ready | 0.30.1 | 2026-09-08T09:39:33Z |  |
| HelmRelease | spire-mgmt | spire-crds | Ready | 0.6.1 | 2026-09-06T20:26:47Z |  |
| HelmRelease | tailscale | tailscale-operator | Ready | 1.102.3 | 2026-09-06T19:33:35Z |  |
| HelmRelease | temporal | temporal | Ready | 1.6.0 | 2026-09-08T23:12:29Z |  |
| HelmRelease | trivy-system | trivy-operator | Ready | 0.36.0 | 2026-09-06T20:26:45Z |  |
| HelmRelease | weave-gitops | weave-gitops | Ready | 4.0.36 | 2026-09-06T20:26:45Z |  |
| Kustomization | flux-system | alerts | Ready | main@a347384 | 2026-09-10T09:11:45Z |  |
| Kustomization | flux-system | alerts-github | Ready | main@a347384 | 2026-09-10T09:11:42Z |  |
| Kustomization | flux-system | alerts-secret | Ready | main@a347384 | 2026-09-10T09:11:35Z |  |
| Kustomization | flux-system | autoscaler | Ready | main@a347384 | 2026-09-10T09:11:38Z |  |
| Kustomization | flux-system | backstage-namespace | Ready | main@a347384 | 2026-09-10T09:10:53Z |  |
| Kustomization | flux-system | calico | Ready | main@a347384 | 2026-09-10T09:10:56Z |  |
| Kustomization | flux-system | chaos-mesh | Ready | main@a347384 | 2026-09-10T09:15:08Z |  |
| Kustomization | flux-system | cluster-state | Ready | main@a347384 | 2026-09-10T09:11:51Z |  |
| Kustomization | flux-system | commerce-data | Ready | main@a347384 | 2026-09-10T09:11:58Z |  |
| Kustomization | flux-system | crossplane | Ready | main@a347384 | 2026-09-10T09:11:41Z |  |
| Kustomization | flux-system | crossplane-providerconfig | Ready | main@a347384 | 2026-09-10T09:11:53Z |  |
| Kustomization | flux-system | crossplane-providers | Ready | main@a347384 | 2026-09-10T09:11:44Z |  |
| Kustomization | flux-system | dns | Ready | main@a347384 | 2026-09-10T09:11:39Z |  |
| Kustomization | flux-system | drills | Ready | main@a347384 | 2026-09-10T09:11:46Z |  |
| Kustomization | flux-system | edge | Ready | main@a347384 | 2026-09-10T09:11:06Z |  |
| Kustomization | flux-system | estate-catalog | Ready | latest@sha256:8ab0d9286bc2769859d864f54d | 2026-09-10T09:09:01Z |  |
| Kustomization | flux-system | estate-db | Ready | main@a347384 | 2026-09-10T09:11:57Z |  |
| Kustomization | flux-system | estate-db-operator | Ready | main@a347384 | 2026-09-10T09:10:43Z |  |
| Kustomization | flux-system | event-bus | Ready | main@a347384 | 2026-09-10T09:10:52Z |  |
| Kustomization | flux-system | external-secrets | Ready | main@a347384 | 2026-09-10T09:11:09Z |  |
| Kustomization | flux-system | feature-register | Ready | main@a347384 | 2026-09-10T09:10:57Z |  |
| Kustomization | flux-system | flux-system | Ready | main@a347384 | 2026-09-10T09:11:02Z |  |
| Kustomization | flux-system | flux-webhook | Ready | main@a347384 | 2026-09-10T09:11:33Z |  |
| Kustomization | flux-system | gateway-api-crds | Ready | v1.5.1@e7677b7 | 2026-09-10T09:10:46Z |  |
| Kustomization | flux-system | gvisor-runtime | Ready | main@a347384 | 2026-09-10T09:11:47Z |  |
| Kustomization | flux-system | human-vault | Ready | main@a347384 | 2026-09-10T09:11:53Z |  |
| Kustomization | flux-system | human-vault-bridge | Ready | main@a347384 | 2026-09-10T09:11:55Z |  |
| Kustomization | flux-system | identity | Ready | main@a347384 | 2026-09-10T09:11:49Z |  |
| Kustomization | flux-system | image-automation | Ready | main@a347384 | 2026-09-10T09:11:39Z |  |
| Kustomization | flux-system | jit | Ready | main@a347384 | 2026-09-10T09:10:54Z |  |
| Kustomization | flux-system | kyverno | Ready | main@a347384 | 2026-09-10T09:10:48Z |  |
| Kustomization | flux-system | mcp | Ready | main@a347384 | 2026-09-10T09:11:51Z |  |
| Kustomization | flux-system | monitoring | Ready | main@a347384 | 2026-09-10T09:11:48Z |  |
| Kustomization | flux-system | monitoring-rules | Ready | main@a347384 | 2026-09-10T09:11:54Z |  |
| Kustomization | flux-system | nodesoftware-operator | Ready | main@a347384 | 2026-09-10T09:11:43Z |  |
| Kustomization | flux-system | ns-fences | Ready | main@a347384 | 2026-09-10T09:11:14Z |  |
| Kustomization | flux-system | otto-golden | Ready | main@a347384 | 2026-09-10T09:11:47Z |  |
| Kustomization | flux-system | otto-golden-secret | Ready | main@a347384 | 2026-09-10T09:11:33Z |  |
| Kustomization | flux-system | priority-classes | Ready | main@a347384 | 2026-09-10T09:10:47Z |  |
| Kustomization | flux-system | prospector | Ready | main@7453d76 | 2026-09-10T09:04:37Z |  |
| Kustomization | flux-system | prospector-platform | Ready | main@a347384 | 2026-09-10T09:11:30Z |  |
| Kustomization | flux-system | rbac | Ready | main@a347384 | 2026-09-10T09:10:50Z |  |
| Kustomization | flux-system | rbac-floor | Ready | main@a347384 | 2026-09-10T09:10:49Z |  |
| Kustomization | flux-system | rbac-identity | Ready | main@a347384 | 2026-09-10T09:10:43Z |  |
| Kustomization | flux-system | reloader | Ready | main@a347384 | 2026-09-10T09:11:41Z |  |
| Kustomization | flux-system | robusta | Ready | main@a347384 | 2026-09-10T09:11:44Z |  |
| Kustomization | flux-system | sandbox-launch | Ready | main@a347384 | 2026-09-10T09:11:25Z |  |
| Kustomization | flux-system | sandbox-live | Ready | sandbox/launch@5844e79 | 2026-09-10T09:11:10Z |  |
| Kustomization | flux-system | scheduling | Ready | main@a347384 | 2026-09-10T09:11:35Z |  |
| Kustomization | flux-system | searxng | Ready | main@a347384 | 2026-09-10T09:10:50Z |  |
| Kustomization | flux-system | secret-store | Ready | main@a347384 | 2026-09-10T09:11:29Z |  |
| Kustomization | flux-system | spire | Ready | main@a347384 | 2026-09-10T09:11:38Z |  |
| Kustomization | flux-system | staging | Ready | main@a347384 | 2026-09-10T09:10:45Z |  |
| Kustomization | flux-system | trivy | Ready | main@a347384 | 2026-09-10T09:10:58Z |  |
| Kustomization | flux-system | verification | Ready | main@a347384 | 2026-09-10T09:11:50Z |  |
