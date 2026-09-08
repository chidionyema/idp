# Flux: what is applied

Read from the cluster receipt taken at 2026-09-08T14:00:15Z. Every Kustomization and HelmRelease, with the revision Flux last applied. **Suspended** is a switch somebody turned off on purpose (temporal, commerce, commerce-data, event-bus), not a defect; **Unknown** is a row Flux has never graded.

**114 objects: 101 ready, 11 not ready, 0 unknown, 2 suspended.**

## Not ready right now

- **HelmRelease commerce/lago** since 2026-09-08T13:47:26Z: Running 'install' action with timeout of 15m0s
- **HelmRelease hindsight/hindsight** since 2026-09-08T13:38:26Z: Helm rollback to previous release hindsight/hindsight.v51 with chart hindsight@0.9.2 failed: release hindsight failed: failed early due to stalled resources: [Deployment/hindsight/hindsight-api status: 'Failed']
- **Kustomization flux-system/chaos** since 2026-09-08T13:59:38Z: dependency 'flux-system/backstage' is not ready
- **Kustomization flux-system/commerce** since 2026-09-08T13:45:38Z: Reconciliation in progress
- **Kustomization flux-system/gvisor-runtime** since 2026-09-08T10:27:58Z: dependency 'flux-system/nodesoftware-operator' is not ready
- **Kustomization flux-system/healing-analyzer** since 2026-09-08T13:57:47Z: dependency 'flux-system/healing-k8sgpt' is not ready
- **Kustomization flux-system/healing-k8sgpt** since 2026-09-08T13:58:18Z: dependency 'flux-system/llm' is not ready
- **Kustomization flux-system/hindsight** since 2026-09-08T13:59:44Z: Reconciliation in progress
- **Kustomization flux-system/nodesoftware-operator** since 2026-09-08T13:59:02Z: Reconciliation in progress
- **Kustomization flux-system/otto-gateway** since 2026-09-08T13:58:58Z: health check failed after 570.067003ms: failed early due to stalled resources: [Job/otto-gateway/otto-memory-store-6 status: 'Failed']
- **Kustomization flux-system/prospector** since 2026-09-08T13:51:04Z: Reconciliation in progress

## Every row

| Kind | Namespace | Name | State | Applied revision | Since | Message |
|---|---|---|---|---|---|---|
| HelmRelease | commerce | lago | Not ready | 1.28.0 | 2026-09-08T13:47:26Z | Running 'install' action with timeout of 15m0s |
| HelmRelease | hindsight | hindsight | Not ready | 0.9.2 | 2026-09-08T13:38:26Z | Helm rollback to previous release hindsight/hindsight.v51 with chart hindsight@0.9.2 failed: release hindsight failed: failed early due to stalled resources: [D |
| Kustomization | flux-system | chaos | Not ready | main@38e3213 | 2026-09-08T13:59:38Z | dependency 'flux-system/backstage' is not ready |
| Kustomization | flux-system | commerce | Not ready | main@38e3213 | 2026-09-08T13:45:38Z | Reconciliation in progress |
| Kustomization | flux-system | gvisor-runtime | Not ready | main@8e1bade | 2026-09-08T10:27:58Z | dependency 'flux-system/nodesoftware-operator' is not ready |
| Kustomization | flux-system | healing-analyzer | Not ready | main@38e3213 | 2026-09-08T13:57:47Z | dependency 'flux-system/healing-k8sgpt' is not ready |
| Kustomization | flux-system | healing-k8sgpt | Not ready | main@38e3213 | 2026-09-08T13:58:18Z | dependency 'flux-system/llm' is not ready |
| Kustomization | flux-system | hindsight | Not ready | main@a295542 | 2026-09-08T13:59:44Z | Reconciliation in progress |
| Kustomization | flux-system | nodesoftware-operator | Not ready | main@8e1bade | 2026-09-08T13:59:02Z | Reconciliation in progress |
| Kustomization | flux-system | otto-gateway | Not ready | main@aa3ee81 | 2026-09-08T13:58:58Z | health check failed after 570.067003ms: failed early due to stalled resources: [Job/otto-gateway/otto-memory-store-6 status: 'Failed'] |
| Kustomization | flux-system | prospector | Not ready | main@7453d76 | 2026-09-08T13:51:04Z | Reconciliation in progress |
| HelmRelease | tigera-operator | tigera-operator | Suspended | v3.32.2 | 2026-09-06T19:38:02Z |  |
| Kustomization | flux-system | temporal | Suspended | main@1b323ac | 2026-08-30T05:54:22Z |  |
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
| HelmRelease | temporal | temporal | Ready | 1.6.0 | 2026-09-06T19:33:25Z |  |
| HelmRelease | trivy-system | trivy-operator | Ready | 0.36.0 | 2026-09-06T20:26:45Z |  |
| HelmRelease | weave-gitops | weave-gitops | Ready | 4.0.36 | 2026-09-06T20:26:45Z |  |
| Kustomization | flux-system | agent-workforce | Ready | main@44af8f3 | 2026-09-08T13:59:44Z |  |
| Kustomization | flux-system | alerts | Ready | main@44af8f3 | 2026-09-08T13:59:20Z |  |
| Kustomization | flux-system | alerts-github | Ready | main@44af8f3 | 2026-09-08T13:58:47Z |  |
| Kustomization | flux-system | alerts-secret | Ready | main@44af8f3 | 2026-09-08T13:59:00Z |  |
| Kustomization | flux-system | autoscaler | Ready | main@44af8f3 | 2026-09-08T13:58:51Z |  |
| Kustomization | flux-system | backstage | Ready | main@44af8f3 | 2026-09-08T13:59:41Z |  |
| Kustomization | flux-system | backstage-namespace | Ready | main@44af8f3 | 2026-09-08T13:57:31Z |  |
| Kustomization | flux-system | calico | Ready | main@44af8f3 | 2026-09-08T13:57:20Z |  |
| Kustomization | flux-system | chaos-mesh | Ready | main@44af8f3 | 2026-09-08T13:58:18Z |  |
| Kustomization | flux-system | cluster-state | Ready | main@44af8f3 | 2026-09-08T13:58:34Z |  |
| Kustomization | flux-system | commerce-data | Ready | main@44af8f3 | 2026-09-08T13:59:21Z |  |
| Kustomization | flux-system | crossplane | Ready | main@44af8f3 | 2026-09-08T13:58:17Z |  |
| Kustomization | flux-system | crossplane-providerconfig | Ready | main@44af8f3 | 2026-09-08T13:58:51Z |  |
| Kustomization | flux-system | crossplane-providers | Ready | main@44af8f3 | 2026-09-08T13:58:45Z |  |
| Kustomization | flux-system | cyrus | Ready | main@44af8f3 | 2026-09-08T13:59:01Z |  |
| Kustomization | flux-system | dagster | Ready | main@44af8f3 | 2026-09-08T13:59:35Z |  |
| Kustomization | flux-system | dns | Ready | main@44af8f3 | 2026-09-08T13:58:52Z |  |
| Kustomization | flux-system | drills | Ready | main@44af8f3 | 2026-09-08T13:58:50Z |  |
| Kustomization | flux-system | edge | Ready | main@44af8f3 | 2026-09-08T13:57:58Z |  |
| Kustomization | flux-system | estate-catalog | Ready | latest@sha256:89f39d6cf4bd7058d0d6021049 | 2026-09-08T13:51:03Z |  |
| Kustomization | flux-system | estate-db | Ready | main@44af8f3 | 2026-09-08T13:58:57Z |  |
| Kustomization | flux-system | estate-db-migrate | Ready | main@44af8f3 | 2026-09-08T13:59:03Z |  |
| Kustomization | flux-system | estate-db-operator | Ready | main@44af8f3 | 2026-09-08T13:57:21Z |  |
| Kustomization | flux-system | event-bus | Ready | main@44af8f3 | 2026-09-08T13:57:54Z |  |
| Kustomization | flux-system | external-secrets | Ready | main@44af8f3 | 2026-09-08T13:58:15Z |  |
| Kustomization | flux-system | feature-register | Ready | main@44af8f3 | 2026-09-08T13:58:01Z |  |
| Kustomization | flux-system | flux-system | Ready | main@44af8f3 | 2026-09-08T13:57:27Z |  |
| Kustomization | flux-system | flux-webhook | Ready | main@44af8f3 | 2026-09-08T13:58:55Z |  |
| Kustomization | flux-system | gateway-api-crds | Ready | v1.5.1@e7677b7 | 2026-09-08T13:57:32Z |  |
| Kustomization | flux-system | guacamole | Ready | main@44af8f3 | 2026-09-08T13:59:42Z |  |
| Kustomization | flux-system | healing | Ready | main@44af8f3 | 2026-09-08T13:58:17Z |  |
| Kustomization | flux-system | healthchecks | Ready | main@44af8f3 | 2026-09-08T13:59:34Z |  |
| Kustomization | flux-system | hermes-agent | Ready | main@44af8f3 | 2026-09-08T13:58:54Z |  |
| Kustomization | flux-system | human-vault | Ready | main@44af8f3 | 2026-09-08T13:58:48Z |  |
| Kustomization | flux-system | human-vault-bridge | Ready | main@44af8f3 | 2026-09-08T13:59:01Z |  |
| Kustomization | flux-system | identity | Ready | main@44af8f3 | 2026-09-08T13:58:47Z |  |
| Kustomization | flux-system | image-automation | Ready | main@44af8f3 | 2026-09-08T13:58:49Z |  |
| Kustomization | flux-system | jit | Ready | main@44af8f3 | 2026-09-08T13:57:44Z |  |
| Kustomization | flux-system | keda | Ready | main@44af8f3 | 2026-09-08T13:58:44Z |  |
| Kustomization | flux-system | kyverno | Ready | main@44af8f3 | 2026-09-08T13:57:24Z |  |
| Kustomization | flux-system | llm | Ready | main@44af8f3 | 2026-09-08T13:59:36Z |  |
| Kustomization | flux-system | mcp | Ready | main@44af8f3 | 2026-09-08T13:58:55Z |  |
| Kustomization | flux-system | metrics-server | Ready | main@44af8f3 | 2026-09-08T13:58:16Z |  |
| Kustomization | flux-system | monitoring | Ready | main@44af8f3 | 2026-09-08T13:58:59Z |  |
| Kustomization | flux-system | monitoring-rules | Ready | main@44af8f3 | 2026-09-08T13:59:02Z |  |
| Kustomization | flux-system | notify | Ready | main@44af8f3 | 2026-09-08T13:58:47Z |  |
| Kustomization | flux-system | ns-fences | Ready | main@44af8f3 | 2026-09-08T13:57:42Z |  |
| Kustomization | flux-system | observability | Ready | main@44af8f3 | 2026-09-08T13:59:32Z |  |
| Kustomization | flux-system | observability-collector | Ready | main@44af8f3 | 2026-09-08T13:58:43Z |  |
| Kustomization | flux-system | otto-golden | Ready | main@44af8f3 | 2026-09-08T13:59:30Z |  |
| Kustomization | flux-system | otto-golden-secret | Ready | main@44af8f3 | 2026-09-08T13:58:59Z |  |
| Kustomization | flux-system | priority-classes | Ready | main@44af8f3 | 2026-09-08T13:57:30Z |  |
| Kustomization | flux-system | prospector-platform | Ready | main@44af8f3 | 2026-09-08T13:58:45Z |  |
| Kustomization | flux-system | rbac | Ready | main@44af8f3 | 2026-09-08T13:57:45Z |  |
| Kustomization | flux-system | rbac-floor | Ready | main@44af8f3 | 2026-09-08T13:57:28Z |  |
| Kustomization | flux-system | rbac-identity | Ready | main@44af8f3 | 2026-09-08T13:57:22Z |  |
| Kustomization | flux-system | reloader | Ready | main@44af8f3 | 2026-09-08T13:58:51Z |  |
| Kustomization | flux-system | research-engine | Ready | main@44af8f3 | 2026-09-08T13:59:37Z |  |
| Kustomization | flux-system | robusta | Ready | main@44af8f3 | 2026-09-08T13:58:49Z |  |
| Kustomization | flux-system | sandbox-launch | Ready | main@44af8f3 | 2026-09-08T13:58:13Z |  |
| Kustomization | flux-system | sandbox-live | Ready | sandbox/launch@929c1d7 | 2026-09-08T13:59:02Z |  |
| Kustomization | flux-system | scheduling | Ready | main@44af8f3 | 2026-09-08T13:58:14Z |  |
| Kustomization | flux-system | science | Ready | main@44af8f3 | 2026-09-08T13:59:38Z |  |
| Kustomization | flux-system | searxng | Ready | main@44af8f3 | 2026-09-08T13:57:24Z |  |
| Kustomization | flux-system | secret-store | Ready | main@44af8f3 | 2026-09-08T13:58:44Z |  |
| Kustomization | flux-system | spire | Ready | main@44af8f3 | 2026-09-08T13:58:18Z |  |
| Kustomization | flux-system | staging | Ready | main@44af8f3 | 2026-09-08T13:57:29Z |  |
| Kustomization | flux-system | tailscale | Ready | main@44af8f3 | 2026-09-08T13:58:46Z |  |
| Kustomization | flux-system | trivy | Ready | main@44af8f3 | 2026-09-08T13:57:23Z |  |
| Kustomization | flux-system | verification | Ready | main@44af8f3 | 2026-09-08T13:58:50Z |  |
| Kustomization | flux-system | weave-gitops | Ready | main@44af8f3 | 2026-09-08T13:58:58Z |  |
