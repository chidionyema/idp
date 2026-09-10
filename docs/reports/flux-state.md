# Flux: what is applied

Read from the cluster receipt taken at 2026-09-10T09:30:23Z. Every Kustomization and HelmRelease, with the revision Flux last applied. **Suspended** is a switch somebody turned off on purpose (temporal, commerce, commerce-data, event-bus), not a defect; **Unknown** is a row Flux has never graded.

**114 objects: 106 ready, 6 not ready, 0 unknown, 2 suspended.**

## Not ready right now

- **HelmRelease commerce/lago** since 2026-09-10T09:29:30Z: Running 'install' action with timeout of 15m0s
- **Kustomization flux-system/commerce** since 2026-09-10T09:19:41Z: Reconciliation in progress
- **Kustomization flux-system/cyrus** since 2026-09-10T09:25:20Z: Reconciliation in progress
- **Kustomization flux-system/guacamole** since 2026-09-10T09:25:37Z: dependency 'flux-system/tailscale' is not ready
- **Kustomization flux-system/otto-gateway** since 2026-09-10T09:26:27Z: health check failed after 1.56999041s: failed early due to stalled resources: [Deployment/otto-gateway/otto-gateway status: 'Failed']
- **Kustomization flux-system/tailscale** since 2026-09-10T09:25:18Z: Reconciliation in progress

## Every row

| Kind | Namespace | Name | State | Applied revision | Since | Message |
|---|---|---|---|---|---|---|
| HelmRelease | commerce | lago | Not ready | 1.28.0 | 2026-09-10T09:29:30Z | Running 'install' action with timeout of 15m0s |
| Kustomization | flux-system | commerce | Not ready | main@a347384 | 2026-09-10T09:19:41Z | Reconciliation in progress |
| Kustomization | flux-system | cyrus | Not ready | main@17a5ceb | 2026-09-10T09:25:20Z | Reconciliation in progress |
| Kustomization | flux-system | guacamole | Not ready | main@5b6aeea | 2026-09-10T09:25:37Z | dependency 'flux-system/tailscale' is not ready |
| Kustomization | flux-system | otto-gateway | Not ready | main@bb83118 | 2026-09-10T09:26:27Z | health check failed after 1.56999041s: failed early due to stalled resources: [Deployment/otto-gateway/otto-gateway status: 'Failed'] |
| Kustomization | flux-system | tailscale | Not ready | main@d3ab8a2 | 2026-09-10T09:25:18Z | Reconciliation in progress |
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
| Kustomization | flux-system | agent-workforce | Ready | main@be6a4cc | 2026-09-10T09:26:31Z |  |
| Kustomization | flux-system | alerts | Ready | main@be6a4cc | 2026-09-10T09:26:38Z |  |
| Kustomization | flux-system | alerts-github | Ready | main@be6a4cc | 2026-09-10T09:26:06Z |  |
| Kustomization | flux-system | alerts-secret | Ready | main@be6a4cc | 2026-09-10T09:26:09Z |  |
| Kustomization | flux-system | autoscaler | Ready | main@be6a4cc | 2026-09-10T09:26:12Z |  |
| Kustomization | flux-system | backstage | Ready | main@be6a4cc | 2026-09-10T09:26:34Z |  |
| Kustomization | flux-system | backstage-namespace | Ready | main@be6a4cc | 2026-09-10T09:24:04Z |  |
| Kustomization | flux-system | calico | Ready | main@be6a4cc | 2026-09-10T09:24:08Z |  |
| Kustomization | flux-system | chaos | Ready | main@be6a4cc | 2026-09-10T09:26:36Z |  |
| Kustomization | flux-system | chaos-mesh | Ready | main@be6a4cc | 2026-09-10T09:25:04Z |  |
| Kustomization | flux-system | cluster-state | Ready | main@be6a4cc | 2026-09-10T09:25:18Z |  |
| Kustomization | flux-system | commerce-data | Ready | main@be6a4cc | 2026-09-10T09:25:37Z |  |
| Kustomization | flux-system | crossplane | Ready | main@be6a4cc | 2026-09-10T09:25:20Z |  |
| Kustomization | flux-system | crossplane-providerconfig | Ready | main@be6a4cc | 2026-09-10T09:26:19Z |  |
| Kustomization | flux-system | crossplane-providers | Ready | main@be6a4cc | 2026-09-10T09:26:14Z |  |
| Kustomization | flux-system | dagster | Ready | main@be6a4cc | 2026-09-10T09:25:57Z |  |
| Kustomization | flux-system | dns | Ready | main@be6a4cc | 2026-09-10T09:26:05Z |  |
| Kustomization | flux-system | drills | Ready | main@be6a4cc | 2026-09-10T09:26:10Z |  |
| Kustomization | flux-system | edge | Ready | main@be6a4cc | 2026-09-10T09:24:41Z |  |
| Kustomization | flux-system | estate-catalog | Ready | latest@sha256:8ab0d9286bc2769859d864f54d | 2026-09-10T09:29:18Z |  |
| Kustomization | flux-system | estate-db | Ready | main@be6a4cc | 2026-09-10T09:25:30Z |  |
| Kustomization | flux-system | estate-db-migrate | Ready | main@be6a4cc | 2026-09-10T09:25:49Z |  |
| Kustomization | flux-system | estate-db-operator | Ready | main@be6a4cc | 2026-09-10T09:24:11Z |  |
| Kustomization | flux-system | event-bus | Ready | main@be6a4cc | 2026-09-10T09:24:35Z |  |
| Kustomization | flux-system | external-secrets | Ready | main@be6a4cc | 2026-09-10T09:25:08Z |  |
| Kustomization | flux-system | feature-register | Ready | main@be6a4cc | 2026-09-10T09:24:32Z |  |
| Kustomization | flux-system | flux-system | Ready | main@be6a4cc | 2026-09-10T09:24:09Z |  |
| Kustomization | flux-system | flux-webhook | Ready | main@be6a4cc | 2026-09-10T09:25:20Z |  |
| Kustomization | flux-system | gateway-api-crds | Ready | v1.5.1@e7677b7 | 2026-09-10T09:24:13Z |  |
| Kustomization | flux-system | gvisor-runtime | Ready | main@be6a4cc | 2026-09-10T09:26:23Z |  |
| Kustomization | flux-system | healing | Ready | main@be6a4cc | 2026-09-10T09:25:07Z |  |
| Kustomization | flux-system | healing-analyzer | Ready | main@be6a4cc | 2026-09-10T09:26:00Z |  |
| Kustomization | flux-system | healing-k8sgpt | Ready | main@be6a4cc | 2026-09-10T09:25:59Z |  |
| Kustomization | flux-system | healthchecks | Ready | main@be6a4cc | 2026-09-10T09:25:51Z |  |
| Kustomization | flux-system | hermes-agent | Ready | main@be6a4cc | 2026-09-10T09:26:28Z |  |
| Kustomization | flux-system | hindsight | Ready | main@be6a4cc | 2026-09-10T09:26:03Z |  |
| Kustomization | flux-system | human-vault | Ready | main@be6a4cc | 2026-09-10T09:25:36Z |  |
| Kustomization | flux-system | human-vault-bridge | Ready | main@be6a4cc | 2026-09-10T09:26:13Z |  |
| Kustomization | flux-system | identity | Ready | main@be6a4cc | 2026-09-10T09:25:32Z |  |
| Kustomization | flux-system | image-automation | Ready | main@be6a4cc | 2026-09-10T09:26:08Z |  |
| Kustomization | flux-system | jit | Ready | main@be6a4cc | 2026-09-10T09:24:15Z |  |
| Kustomization | flux-system | keda | Ready | main@be6a4cc | 2026-09-10T09:25:04Z |  |
| Kustomization | flux-system | kyverno | Ready | main@be6a4cc | 2026-09-10T09:24:11Z |  |
| Kustomization | flux-system | llm | Ready | main@be6a4cc | 2026-09-10T09:25:53Z |  |
| Kustomization | flux-system | mcp | Ready | main@be6a4cc | 2026-09-10T09:26:21Z |  |
| Kustomization | flux-system | metrics-server | Ready | main@be6a4cc | 2026-09-10T09:25:07Z |  |
| Kustomization | flux-system | monitoring | Ready | main@be6a4cc | 2026-09-10T09:25:33Z |  |
| Kustomization | flux-system | monitoring-rules | Ready | main@be6a4cc | 2026-09-10T09:25:35Z |  |
| Kustomization | flux-system | nodesoftware-operator | Ready | main@be6a4cc | 2026-09-10T09:26:17Z |  |
| Kustomization | flux-system | notify | Ready | main@be6a4cc | 2026-09-10T09:25:46Z |  |
| Kustomization | flux-system | ns-fences | Ready | main@be6a4cc | 2026-09-10T09:24:26Z |  |
| Kustomization | flux-system | observability | Ready | main@be6a4cc | 2026-09-10T09:25:56Z |  |
| Kustomization | flux-system | observability-collector | Ready | main@be6a4cc | 2026-09-10T09:25:04Z |  |
| Kustomization | flux-system | otto-golden | Ready | main@be6a4cc | 2026-09-10T09:26:16Z |  |
| Kustomization | flux-system | otto-golden-secret | Ready | main@be6a4cc | 2026-09-10T09:26:11Z |  |
| Kustomization | flux-system | priority-classes | Ready | main@be6a4cc | 2026-09-10T09:24:09Z |  |
| Kustomization | flux-system | prospector | Ready | main@7453d76 | 2026-09-10T09:25:44Z |  |
| Kustomization | flux-system | prospector-platform | Ready | main@be6a4cc | 2026-09-10T09:25:18Z |  |
| Kustomization | flux-system | rbac | Ready | main@be6a4cc | 2026-09-10T09:24:35Z |  |
| Kustomization | flux-system | rbac-floor | Ready | main@be6a4cc | 2026-09-10T09:24:07Z |  |
| Kustomization | flux-system | rbac-identity | Ready | main@be6a4cc | 2026-09-10T09:24:05Z |  |
| Kustomization | flux-system | reloader | Ready | main@be6a4cc | 2026-09-10T09:25:23Z |  |
| Kustomization | flux-system | research-engine | Ready | main@be6a4cc | 2026-09-10T09:26:30Z |  |
| Kustomization | flux-system | robusta | Ready | main@be6a4cc | 2026-09-10T09:25:18Z |  |
| Kustomization | flux-system | sandbox-launch | Ready | main@be6a4cc | 2026-09-10T09:24:45Z |  |
| Kustomization | flux-system | sandbox-live | Ready | sandbox/launch@5844e79 | 2026-09-10T09:29:36Z |  |
| Kustomization | flux-system | scheduling | Ready | main@be6a4cc | 2026-09-10T09:24:45Z |  |
| Kustomization | flux-system | science | Ready | main@be6a4cc | 2026-09-10T09:26:02Z |  |
| Kustomization | flux-system | searxng | Ready | main@be6a4cc | 2026-09-10T09:24:05Z |  |
| Kustomization | flux-system | secret-store | Ready | main@be6a4cc | 2026-09-10T09:25:15Z |  |
| Kustomization | flux-system | spire | Ready | main@be6a4cc | 2026-09-10T09:25:16Z |  |
| Kustomization | flux-system | staging | Ready | main@be6a4cc | 2026-09-10T09:24:08Z |  |
| Kustomization | flux-system | trivy | Ready | main@be6a4cc | 2026-09-10T09:24:09Z |  |
| Kustomization | flux-system | verification | Ready | main@be6a4cc | 2026-09-10T09:25:24Z |  |
| Kustomization | flux-system | weave-gitops | Ready | main@be6a4cc | 2026-09-10T09:25:47Z |  |
