# Flux: what is applied

Read from the cluster receipt taken at 2026-09-09T02:00:15Z. Every Kustomization and HelmRelease, with the revision Flux last applied. **Suspended** is a switch somebody turned off on purpose (temporal, commerce, commerce-data, event-bus), not a defect; **Unknown** is a row Flux has never graded.

**114 objects: 84 ready, 28 not ready, 0 unknown, 2 suspended.**

## Not ready right now

- **HelmRelease commerce/lago** since 2026-09-09T01:51:57Z: Running 'install' action with timeout of 15m0s
- **Kustomization flux-system/agent-workforce** since 2026-09-09T01:56:13Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/chaos** since 2026-09-09T01:56:13Z: dependency 'flux-system/chaos-mesh' is not ready
- **Kustomization flux-system/chaos-mesh** since 2026-09-09T01:56:13Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/cluster-state** since 2026-09-09T01:56:13Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/commerce** since 2026-09-09T01:51:56Z: Reconciliation in progress
- **Kustomization flux-system/crossplane** since 2026-09-09T01:56:13Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/crossplane-providerconfig** since 2026-09-09T01:56:13Z: dependency 'flux-system/crossplane-providers' is not ready
- **Kustomization flux-system/crossplane-providers** since 2026-09-09T01:56:13Z: dependency 'flux-system/crossplane' is not ready
- **Kustomization flux-system/cyrus** since 2026-09-09T01:56:13Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/dagster** since 2026-09-09T01:56:13Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/gvisor-runtime** since 2026-09-09T01:56:13Z: dependency 'flux-system/nodesoftware-operator' is not ready
- **Kustomization flux-system/healing** since 2026-09-09T01:56:13Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/healing-analyzer** since 2026-09-09T01:56:13Z: dependency 'flux-system/healing-k8sgpt' is not ready
- **Kustomization flux-system/healing-k8sgpt** since 2026-09-09T01:56:13Z: dependency 'flux-system/healing' is not ready
- **Kustomization flux-system/hermes-agent** since 2026-09-09T01:56:13Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/keda** since 2026-09-09T01:56:13Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/mcp** since 2026-09-09T01:56:13Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/metrics-server** since 2026-09-09T01:56:13Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/nodesoftware-operator** since 2026-09-09T01:56:13Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/notify** since 2026-09-09T01:56:13Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/observability** since 2026-09-09T01:56:13Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/observability-collector** since 2026-09-09T01:56:13Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/otto-gateway** since 2026-09-09T01:56:13Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/otto-golden** since 2026-09-09T01:56:13Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/scheduling** since 2026-09-09T01:56:43Z: Reconciliation in progress
- **Kustomization flux-system/science** since 2026-09-09T01:56:13Z: dependency 'flux-system/observability' is not ready
- **Kustomization flux-system/spire** since 2026-09-09T01:56:13Z: dependency 'flux-system/scheduling' is not ready

## Every row

| Kind | Namespace | Name | State | Applied revision | Since | Message |
|---|---|---|---|---|---|---|
| HelmRelease | commerce | lago | Not ready | 1.28.0 | 2026-09-09T01:51:57Z | Running 'install' action with timeout of 15m0s |
| Kustomization | flux-system | agent-workforce | Not ready | main@934ba08 | 2026-09-09T01:56:13Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | chaos | Not ready | main@934ba08 | 2026-09-09T01:56:13Z | dependency 'flux-system/chaos-mesh' is not ready |
| Kustomization | flux-system | chaos-mesh | Not ready | main@934ba08 | 2026-09-09T01:56:13Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | cluster-state | Not ready | main@934ba08 | 2026-09-09T01:56:13Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | commerce | Not ready | main@934ba08 | 2026-09-09T01:51:56Z | Reconciliation in progress |
| Kustomization | flux-system | crossplane | Not ready | main@934ba08 | 2026-09-09T01:56:13Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | crossplane-providerconfig | Not ready | main@934ba08 | 2026-09-09T01:56:13Z | dependency 'flux-system/crossplane-providers' is not ready |
| Kustomization | flux-system | crossplane-providers | Not ready | main@934ba08 | 2026-09-09T01:56:13Z | dependency 'flux-system/crossplane' is not ready |
| Kustomization | flux-system | cyrus | Not ready | main@934ba08 | 2026-09-09T01:56:13Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | dagster | Not ready | main@934ba08 | 2026-09-09T01:56:13Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | gvisor-runtime | Not ready | main@934ba08 | 2026-09-09T01:56:13Z | dependency 'flux-system/nodesoftware-operator' is not ready |
| Kustomization | flux-system | healing | Not ready | main@934ba08 | 2026-09-09T01:56:13Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | healing-analyzer | Not ready | main@934ba08 | 2026-09-09T01:56:13Z | dependency 'flux-system/healing-k8sgpt' is not ready |
| Kustomization | flux-system | healing-k8sgpt | Not ready | main@934ba08 | 2026-09-09T01:56:13Z | dependency 'flux-system/healing' is not ready |
| Kustomization | flux-system | hermes-agent | Not ready | main@934ba08 | 2026-09-09T01:56:13Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | keda | Not ready | main@934ba08 | 2026-09-09T01:56:13Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | mcp | Not ready | main@934ba08 | 2026-09-09T01:56:13Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | metrics-server | Not ready | main@934ba08 | 2026-09-09T01:56:13Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | nodesoftware-operator | Not ready | main@934ba08 | 2026-09-09T01:56:13Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | notify | Not ready | main@934ba08 | 2026-09-09T01:56:13Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | observability | Not ready | main@934ba08 | 2026-09-09T01:56:13Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | observability-collector | Not ready | main@934ba08 | 2026-09-09T01:56:13Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | otto-gateway | Not ready | main@934ba08 | 2026-09-09T01:56:13Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | otto-golden | Not ready | main@934ba08 | 2026-09-09T01:56:13Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | scheduling | Not ready | main@934ba08 | 2026-09-09T01:56:43Z | Reconciliation in progress |
| Kustomization | flux-system | science | Not ready | main@934ba08 | 2026-09-09T01:56:13Z | dependency 'flux-system/observability' is not ready |
| Kustomization | flux-system | spire | Not ready | main@934ba08 | 2026-09-09T01:56:13Z | dependency 'flux-system/scheduling' is not ready |
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
| HelmRelease | observability-agent | k8s-infra | Ready | 0.17.0 | 2026-09-08T11:24:56Z |  |
| HelmRelease | reloader | reloader | Ready | 2.2.16 | 2026-09-06T19:33:25Z |  |
| HelmRelease | robusta | robusta | Ready | 0.48.0 | 2026-09-06T20:26:45Z |  |
| HelmRelease | spire-mgmt | spire | Ready | 0.30.1 | 2026-09-08T09:39:33Z |  |
| HelmRelease | spire-mgmt | spire-crds | Ready | 0.6.1 | 2026-09-06T20:26:47Z |  |
| HelmRelease | tailscale | tailscale-operator | Ready | 1.102.3 | 2026-09-06T19:33:35Z |  |
| HelmRelease | temporal | temporal | Ready | 1.6.0 | 2026-09-08T23:12:29Z |  |
| HelmRelease | trivy-system | trivy-operator | Ready | 0.36.0 | 2026-09-06T20:26:45Z |  |
| HelmRelease | weave-gitops | weave-gitops | Ready | 4.0.36 | 2026-09-06T20:26:45Z |  |
| Kustomization | flux-system | alerts | Ready | main@1feda76 | 2026-09-09T01:57:23Z |  |
| Kustomization | flux-system | alerts-github | Ready | main@1feda76 | 2026-09-09T01:57:18Z |  |
| Kustomization | flux-system | alerts-secret | Ready | main@1feda76 | 2026-09-09T01:57:21Z |  |
| Kustomization | flux-system | autoscaler | Ready | main@1feda76 | 2026-09-09T01:57:15Z |  |
| Kustomization | flux-system | backstage | Ready | main@1feda76 | 2026-09-09T01:57:59Z |  |
| Kustomization | flux-system | backstage-namespace | Ready | main@1feda76 | 2026-09-09T01:56:03Z |  |
| Kustomization | flux-system | calico | Ready | main@1feda76 | 2026-09-09T01:56:06Z |  |
| Kustomization | flux-system | commerce-data | Ready | main@1feda76 | 2026-09-09T01:57:23Z |  |
| Kustomization | flux-system | dns | Ready | main@1feda76 | 2026-09-09T01:57:15Z |  |
| Kustomization | flux-system | drills | Ready | main@1feda76 | 2026-09-09T01:57:22Z |  |
| Kustomization | flux-system | edge | Ready | main@1feda76 | 2026-09-09T01:56:34Z |  |
| Kustomization | flux-system | estate-catalog | Ready | latest@sha256:4b475563ce7c5f1a14e99025ee | 2026-09-09T01:53:10Z |  |
| Kustomization | flux-system | estate-db | Ready | main@1feda76 | 2026-09-09T01:57:20Z |  |
| Kustomization | flux-system | estate-db-migrate | Ready | main@1feda76 | 2026-09-09T01:57:32Z |  |
| Kustomization | flux-system | estate-db-operator | Ready | main@1feda76 | 2026-09-09T01:56:06Z |  |
| Kustomization | flux-system | event-bus | Ready | main@1feda76 | 2026-09-09T01:56:10Z |  |
| Kustomization | flux-system | external-secrets | Ready | main@1feda76 | 2026-09-09T01:56:43Z |  |
| Kustomization | flux-system | feature-register | Ready | main@1feda76 | 2026-09-09T01:56:08Z |  |
| Kustomization | flux-system | flux-system | Ready | main@1feda76 | 2026-09-09T01:56:11Z |  |
| Kustomization | flux-system | flux-webhook | Ready | main@1feda76 | 2026-09-09T01:57:16Z |  |
| Kustomization | flux-system | gateway-api-crds | Ready | v1.5.1@e7677b7 | 2026-09-09T01:56:07Z |  |
| Kustomization | flux-system | guacamole | Ready | main@1feda76 | 2026-09-09T01:57:55Z |  |
| Kustomization | flux-system | healthchecks | Ready | main@1feda76 | 2026-09-09T01:57:56Z |  |
| Kustomization | flux-system | hindsight | Ready | main@1feda76 | 2026-09-09T01:58:27Z |  |
| Kustomization | flux-system | human-vault | Ready | main@1feda76 | 2026-09-09T01:57:17Z |  |
| Kustomization | flux-system | human-vault-bridge | Ready | main@1feda76 | 2026-09-09T01:57:22Z |  |
| Kustomization | flux-system | identity | Ready | main@1feda76 | 2026-09-09T01:57:17Z |  |
| Kustomization | flux-system | image-automation | Ready | main@1feda76 | 2026-09-09T01:57:26Z |  |
| Kustomization | flux-system | jit | Ready | main@1feda76 | 2026-09-09T01:56:13Z |  |
| Kustomization | flux-system | kyverno | Ready | main@1feda76 | 2026-09-09T01:56:02Z |  |
| Kustomization | flux-system | llm | Ready | main@1feda76 | 2026-09-09T01:57:58Z |  |
| Kustomization | flux-system | monitoring | Ready | main@1feda76 | 2026-09-09T01:57:18Z |  |
| Kustomization | flux-system | monitoring-rules | Ready | main@1feda76 | 2026-09-09T01:57:21Z |  |
| Kustomization | flux-system | ns-fences | Ready | main@1feda76 | 2026-09-09T01:56:23Z |  |
| Kustomization | flux-system | otto-golden-secret | Ready | main@1feda76 | 2026-09-09T01:57:20Z |  |
| Kustomization | flux-system | priority-classes | Ready | main@1feda76 | 2026-09-09T01:56:04Z |  |
| Kustomization | flux-system | prospector | Ready | main@7453d76 | 2026-09-09T01:53:18Z |  |
| Kustomization | flux-system | prospector-platform | Ready | main@1feda76 | 2026-09-09T01:57:13Z |  |
| Kustomization | flux-system | rbac | Ready | main@1feda76 | 2026-09-09T01:56:09Z |  |
| Kustomization | flux-system | rbac-floor | Ready | main@1feda76 | 2026-09-09T01:56:02Z |  |
| Kustomization | flux-system | rbac-identity | Ready | main@1feda76 | 2026-09-09T01:56:02Z |  |
| Kustomization | flux-system | reloader | Ready | main@1feda76 | 2026-09-09T01:57:19Z |  |
| Kustomization | flux-system | research-engine | Ready | main@1feda76 | 2026-09-09T01:58:27Z |  |
| Kustomization | flux-system | robusta | Ready | main@1feda76 | 2026-09-09T01:57:13Z |  |
| Kustomization | flux-system | sandbox-launch | Ready | main@1feda76 | 2026-09-09T01:56:43Z |  |
| Kustomization | flux-system | sandbox-live | Ready | sandbox/launch@1f051da | 2026-09-09T02:00:04Z |  |
| Kustomization | flux-system | searxng | Ready | main@1feda76 | 2026-09-09T01:56:05Z |  |
| Kustomization | flux-system | secret-store | Ready | main@1feda76 | 2026-09-09T01:57:01Z |  |
| Kustomization | flux-system | staging | Ready | main@1feda76 | 2026-09-09T01:56:05Z |  |
| Kustomization | flux-system | tailscale | Ready | main@1feda76 | 2026-09-09T01:57:16Z |  |
| Kustomization | flux-system | trivy | Ready | main@1feda76 | 2026-09-09T01:56:08Z |  |
| Kustomization | flux-system | verification | Ready | main@1feda76 | 2026-09-09T01:57:14Z |  |
| Kustomization | flux-system | weave-gitops | Ready | main@1feda76 | 2026-09-09T01:57:24Z |  |
