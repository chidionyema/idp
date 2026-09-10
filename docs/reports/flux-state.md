# Flux: what is applied

Read from the cluster receipt taken at 2026-09-10T12:45:44Z. Every Kustomization and HelmRelease, with the revision Flux last applied. **Suspended** is a switch somebody turned off on purpose (temporal, commerce, commerce-data, event-bus), not a defect; **Unknown** is a row Flux has never graded.

**115 objects: 108 ready, 5 not ready, 0 unknown, 2 suspended.**

## Not ready right now

- **HelmRelease commerce/lago** since 2026-09-10T12:37:41Z: Running 'install' action with timeout of 15m0s
- **Kustomization flux-system/commerce** since 2026-09-10T12:37:40Z: Reconciliation in progress
- **Kustomization flux-system/cyrus** since 2026-09-10T12:41:13Z: Reconciliation in progress
- **Kustomization flux-system/guacamole** since 2026-09-10T12:39:08Z: dependency 'flux-system/tailscale' is not ready
- **Kustomization flux-system/tailscale** since 2026-09-10T12:41:11Z: Reconciliation in progress

## Every row

| Kind | Namespace | Name | State | Applied revision | Since | Message |
|---|---|---|---|---|---|---|
| HelmRelease | commerce | lago | Not ready | 1.28.0 | 2026-09-10T12:37:41Z | Running 'install' action with timeout of 15m0s |
| Kustomization | flux-system | commerce | Not ready | main@9326ab0 | 2026-09-10T12:37:40Z | Reconciliation in progress |
| Kustomization | flux-system | cyrus | Not ready | main@17a5ceb | 2026-09-10T12:41:13Z | Reconciliation in progress |
| Kustomization | flux-system | guacamole | Not ready | main@5b6aeea | 2026-09-10T12:39:08Z | dependency 'flux-system/tailscale' is not ready |
| Kustomization | flux-system | tailscale | Not ready | main@d3ab8a2 | 2026-09-10T12:41:11Z | Reconciliation in progress |
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
| Kustomization | flux-system | agent-workforce | Ready | main@9326ab0 | 2026-09-10T12:36:18Z |  |
| Kustomization | flux-system | alerts | Ready | main@9326ab0 | 2026-09-10T12:39:02Z |  |
| Kustomization | flux-system | alerts-github | Ready | main@9326ab0 | 2026-09-10T12:35:44Z |  |
| Kustomization | flux-system | alerts-secret | Ready | main@9326ab0 | 2026-09-10T12:38:58Z |  |
| Kustomization | flux-system | autoscaler | Ready | main@9326ab0 | 2026-09-10T12:35:49Z |  |
| Kustomization | flux-system | backstage | Ready | main@9326ab0 | 2026-09-10T12:36:24Z |  |
| Kustomization | flux-system | backstage-namespace | Ready | main@9326ab0 | 2026-09-10T12:44:48Z |  |
| Kustomization | flux-system | calico | Ready | main@9326ab0 | 2026-09-10T12:45:05Z |  |
| Kustomization | flux-system | chaos | Ready | main@9326ab0 | 2026-09-10T12:39:08Z |  |
| Kustomization | flux-system | chaos-mesh | Ready | main@9326ab0 | 2026-09-10T12:35:36Z |  |
| Kustomization | flux-system | cluster-state | Ready | main@9326ab0 | 2026-09-10T12:35:39Z |  |
| Kustomization | flux-system | commerce-data | Ready | main@9326ab0 | 2026-09-10T12:36:05Z |  |
| Kustomization | flux-system | cross-node-drill | Ready | main@9326ab0 | 2026-09-10T12:44:49Z |  |
| Kustomization | flux-system | crossplane | Ready | main@9326ab0 | 2026-09-10T12:35:52Z |  |
| Kustomization | flux-system | crossplane-providerconfig | Ready | main@9326ab0 | 2026-09-10T12:39:04Z |  |
| Kustomization | flux-system | crossplane-providers | Ready | main@9326ab0 | 2026-09-10T12:35:59Z |  |
| Kustomization | flux-system | dagster | Ready | main@9326ab0 | 2026-09-10T12:36:14Z |  |
| Kustomization | flux-system | dns | Ready | main@9326ab0 | 2026-09-10T12:35:37Z |  |
| Kustomization | flux-system | drills | Ready | main@9326ab0 | 2026-09-10T12:35:51Z |  |
| Kustomization | flux-system | edge | Ready | main@9326ab0 | 2026-09-10T12:35:27Z |  |
| Kustomization | flux-system | estate-catalog | Ready | latest@sha256:8ab0d9286bc2769859d864f54d | 2026-09-10T12:39:42Z |  |
| Kustomization | flux-system | estate-db | Ready | main@9326ab0 | 2026-09-10T12:35:47Z |  |
| Kustomization | flux-system | estate-db-migrate | Ready | main@9326ab0 | 2026-09-10T12:36:03Z |  |
| Kustomization | flux-system | estate-db-operator | Ready | main@9326ab0 | 2026-09-10T12:45:04Z |  |
| Kustomization | flux-system | event-bus | Ready | main@9326ab0 | 2026-09-10T12:35:06Z |  |
| Kustomization | flux-system | external-secrets | Ready | main@9326ab0 | 2026-09-10T12:35:28Z |  |
| Kustomization | flux-system | feature-register | Ready | main@9326ab0 | 2026-09-10T12:44:37Z |  |
| Kustomization | flux-system | flux-system | Ready | main@9326ab0 | 2026-09-10T12:34:51Z |  |
| Kustomization | flux-system | flux-webhook | Ready | main@9326ab0 | 2026-09-10T12:35:40Z |  |
| Kustomization | flux-system | gateway-api-crds | Ready | v1.5.1@e7677b7 | 2026-09-10T12:35:03Z |  |
| Kustomization | flux-system | gvisor-runtime | Ready | main@9326ab0 | 2026-09-10T12:36:27Z |  |
| Kustomization | flux-system | healing | Ready | main@9326ab0 | 2026-09-10T12:35:53Z |  |
| Kustomization | flux-system | healing-analyzer | Ready | main@9326ab0 | 2026-09-10T12:39:06Z |  |
| Kustomization | flux-system | healing-k8sgpt | Ready | main@9326ab0 | 2026-09-10T12:36:15Z |  |
| Kustomization | flux-system | healthchecks | Ready | main@9326ab0 | 2026-09-10T12:36:09Z |  |
| Kustomization | flux-system | hermes-agent | Ready | main@9326ab0 | 2026-09-10T12:35:56Z |  |
| Kustomization | flux-system | hindsight | Ready | main@9326ab0 | 2026-09-10T12:36:25Z |  |
| Kustomization | flux-system | human-vault | Ready | main@9326ab0 | 2026-09-10T12:38:59Z |  |
| Kustomization | flux-system | human-vault-bridge | Ready | main@9326ab0 | 2026-09-10T12:39:01Z |  |
| Kustomization | flux-system | identity | Ready | main@9326ab0 | 2026-09-10T12:35:43Z |  |
| Kustomization | flux-system | image-automation | Ready | main@9326ab0 | 2026-09-10T12:36:04Z |  |
| Kustomization | flux-system | jit | Ready | main@9326ab0 | 2026-09-10T12:35:05Z |  |
| Kustomization | flux-system | keda | Ready | main@9326ab0 | 2026-09-10T12:35:58Z |  |
| Kustomization | flux-system | kyverno | Ready | main@9326ab0 | 2026-09-10T12:34:54Z |  |
| Kustomization | flux-system | llm | Ready | main@9326ab0 | 2026-09-10T12:36:07Z |  |
| Kustomization | flux-system | mcp | Ready | main@9326ab0 | 2026-09-10T12:36:13Z |  |
| Kustomization | flux-system | metrics-server | Ready | main@9326ab0 | 2026-09-10T12:35:54Z |  |
| Kustomization | flux-system | monitoring | Ready | main@9326ab0 | 2026-09-10T12:38:57Z |  |
| Kustomization | flux-system | monitoring-rules | Ready | main@9326ab0 | 2026-09-10T12:39:05Z |  |
| Kustomization | flux-system | nodesoftware-operator | Ready | main@9326ab0 | 2026-09-10T12:36:17Z |  |
| Kustomization | flux-system | notify | Ready | main@9326ab0 | 2026-09-10T12:35:57Z |  |
| Kustomization | flux-system | ns-fences | Ready | main@9326ab0 | 2026-09-10T12:35:23Z |  |
| Kustomization | flux-system | observability | Ready | main@9326ab0 | 2026-09-10T12:36:21Z |  |
| Kustomization | flux-system | observability-collector | Ready | main@9326ab0 | 2026-09-10T12:35:34Z |  |
| Kustomization | flux-system | otto-gateway | Ready | main@9326ab0 | 2026-09-10T12:38:54Z |  |
| Kustomization | flux-system | otto-golden | Ready | main@9326ab0 | 2026-09-10T12:36:01Z |  |
| Kustomization | flux-system | otto-golden-secret | Ready | main@9326ab0 | 2026-09-10T12:35:41Z |  |
| Kustomization | flux-system | priority-classes | Ready | main@9326ab0 | 2026-09-10T12:34:56Z |  |
| Kustomization | flux-system | prospector | Ready | main@7453d76 | 2026-09-10T12:44:19Z |  |
| Kustomization | flux-system | prospector-platform | Ready | main@9326ab0 | 2026-09-10T12:35:33Z |  |
| Kustomization | flux-system | rbac | Ready | main@9326ab0 | 2026-09-10T12:35:24Z |  |
| Kustomization | flux-system | rbac-floor | Ready | main@9326ab0 | 2026-09-10T12:45:02Z |  |
| Kustomization | flux-system | rbac-identity | Ready | main@9326ab0 | 2026-09-10T12:34:59Z |  |
| Kustomization | flux-system | reloader | Ready | main@9326ab0 | 2026-09-10T12:38:55Z |  |
| Kustomization | flux-system | research-engine | Ready | main@9326ab0 | 2026-09-10T12:36:26Z |  |
| Kustomization | flux-system | robusta | Ready | main@9326ab0 | 2026-09-10T12:38:56Z |  |
| Kustomization | flux-system | sandbox-launch | Ready | main@9326ab0 | 2026-09-10T12:35:31Z |  |
| Kustomization | flux-system | sandbox-live | Ready | sandbox/launch@5844e79 | 2026-09-10T12:45:09Z |  |
| Kustomization | flux-system | scheduling | Ready | main@9326ab0 | 2026-09-10T12:35:29Z |  |
| Kustomization | flux-system | science | Ready | main@9326ab0 | 2026-09-10T12:36:28Z |  |
| Kustomization | flux-system | searxng | Ready | main@9326ab0 | 2026-09-10T12:44:58Z |  |
| Kustomization | flux-system | secret-store | Ready | main@9326ab0 | 2026-09-10T12:35:32Z |  |
| Kustomization | flux-system | spire | Ready | main@9326ab0 | 2026-09-10T12:35:45Z |  |
| Kustomization | flux-system | staging | Ready | main@9326ab0 | 2026-09-10T12:44:21Z |  |
| Kustomization | flux-system | trivy | Ready | main@9326ab0 | 2026-09-10T12:34:57Z |  |
| Kustomization | flux-system | verification | Ready | main@9326ab0 | 2026-09-10T12:35:35Z |  |
| Kustomization | flux-system | weave-gitops | Ready | main@9326ab0 | 2026-09-10T12:35:50Z |  |
