# Flux: what is applied

Read from the cluster receipt taken at 2026-09-12T22:00:23Z. Every Kustomization and HelmRelease, with the revision Flux last applied. **Suspended** is a switch somebody turned off on purpose (temporal, commerce, commerce-data, event-bus), not a defect; **Unknown** is a row Flux has never graded.

**119 objects: 109 ready, 8 not ready, 0 unknown, 2 suspended.**

## Not ready right now

- **HelmRelease commerce/lago** since 2026-09-12T21:53:41Z: Running 'install' action with timeout of 15m0s
- **Kustomization flux-system/chaos** since 2026-09-12T21:57:57Z: dependency 'flux-system/observability' is not ready
- **Kustomization flux-system/commerce** since 2026-09-12T21:48:17Z: Reconciliation in progress
- **Kustomization flux-system/cyrus** since 2026-09-12T21:59:05Z: Reconciliation in progress
- **Kustomization flux-system/guacamole** since 2026-09-12T21:58:38Z: dependency 'flux-system/tailscale' is not ready
- **Kustomization flux-system/observability** since 2026-09-12T21:58:52Z: ExternalSecret/observability/aevum-evidence dry-run failed: no matches for kind "ExternalSecret" in version "external-secrets.io/v1beta1" 
- **Kustomization flux-system/science** since 2026-09-12T20:50:49Z: dependency 'flux-system/observability' is not ready
- **Kustomization flux-system/tailscale** since 2026-09-12T21:58:54Z: Reconciliation in progress

## Every row

| Kind | Namespace | Name | State | Applied revision | Since | Message |
|---|---|---|---|---|---|---|
| HelmRelease | commerce | lago | Not ready | 1.28.0 | 2026-09-12T21:53:41Z | Running 'install' action with timeout of 15m0s |
| Kustomization | flux-system | chaos | Not ready | main@abea14d | 2026-09-12T21:57:57Z | dependency 'flux-system/observability' is not ready |
| Kustomization | flux-system | commerce | Not ready | main@abea14d | 2026-09-12T21:48:17Z | Reconciliation in progress |
| Kustomization | flux-system | cyrus | Not ready | main@17a5ceb | 2026-09-12T21:59:05Z | Reconciliation in progress |
| Kustomization | flux-system | guacamole | Not ready | main@5b6aeea | 2026-09-12T21:58:38Z | dependency 'flux-system/tailscale' is not ready |
| Kustomization | flux-system | observability | Not ready | main@a1442d8 | 2026-09-12T21:58:52Z | ExternalSecret/observability/aevum-evidence dry-run failed: no matches for kind "ExternalSecret" in version "external-secrets.io/v1beta1"  |
| Kustomization | flux-system | science | Not ready | main@a1442d8 | 2026-09-12T20:50:49Z | dependency 'flux-system/observability' is not ready |
| Kustomization | flux-system | tailscale | Not ready | main@d3ab8a2 | 2026-09-12T21:58:54Z | Reconciliation in progress |
| HelmRelease | tigera-operator | tigera-operator | Suspended | v3.32.2 | 2026-09-06T19:38:02Z |  |
| Kustomization | flux-system | temporal | Suspended | main@1b323ac | 2026-09-08T20:23:54Z |  |
| HelmRelease | cert-manager | cert-manager | Ready | v1.21.1 | 2026-09-08T11:56:22Z |  |
| HelmRelease | chaos-mesh | chaos-mesh | Ready | 2.8.4 | 2026-09-08T09:36:49Z |  |
| HelmRelease | crossplane-system | crossplane | Ready | 2.4.0 | 2026-09-08T07:05:25Z |  |
| HelmRelease | dagster | dagster | Ready | 1.13.19 | 2026-09-12T12:32:50Z |  |
| HelmRelease | demo-sandbox | demo-sandbox | Ready | 0.36.1 | 2026-09-12T20:08:12Z |  |
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
| Kustomization | flux-system | agent-workforce | Ready | main@ec26c37 | 2026-09-12T21:58:44Z |  |
| Kustomization | flux-system | alerts | Ready | main@ec26c37 | 2026-09-12T21:57:57Z |  |
| Kustomization | flux-system | alerts-github | Ready | main@ec26c37 | 2026-09-12T21:57:56Z |  |
| Kustomization | flux-system | alerts-secret | Ready | main@ec26c37 | 2026-09-12T21:57:44Z |  |
| Kustomization | flux-system | autoscaler | Ready | main@ec26c37 | 2026-09-12T21:57:47Z |  |
| Kustomization | flux-system | backstage | Ready | main@ec26c37 | 2026-09-12T21:58:50Z |  |
| Kustomization | flux-system | backstage-namespace | Ready | main@ec26c37 | 2026-09-12T21:56:41Z |  |
| Kustomization | flux-system | calico | Ready | main@ec26c37 | 2026-09-12T21:56:39Z |  |
| Kustomization | flux-system | chaos-mesh | Ready | main@ec26c37 | 2026-09-12T21:57:53Z |  |
| Kustomization | flux-system | cluster-state | Ready | main@ec26c37 | 2026-09-12T21:58:09Z |  |
| Kustomization | flux-system | commerce-data | Ready | main@ec26c37 | 2026-09-12T21:58:27Z |  |
| Kustomization | flux-system | concierge | Ready | main@ec26c37 | 2026-09-12T21:57:50Z |  |
| Kustomization | flux-system | cross-node-drill | Ready | main@ec26c37 | 2026-09-12T21:56:37Z |  |
| Kustomization | flux-system | crossplane | Ready | main@ec26c37 | 2026-09-12T21:57:49Z |  |
| Kustomization | flux-system | crossplane-providerconfig | Ready | main@ec26c37 | 2026-09-12T21:58:24Z |  |
| Kustomization | flux-system | crossplane-providers | Ready | main@ec26c37 | 2026-09-12T21:58:08Z |  |
| Kustomization | flux-system | dagster | Ready | main@ec26c37 | 2026-09-12T21:58:35Z |  |
| Kustomization | flux-system | demo-sandbox | Ready | main@ec26c37 | 2026-09-12T21:56:30Z |  |
| Kustomization | flux-system | dns | Ready | main@ec26c37 | 2026-09-12T21:58:14Z |  |
| Kustomization | flux-system | drills | Ready | main@ec26c37 | 2026-09-12T21:58:37Z |  |
| Kustomization | flux-system | edge | Ready | main@ec26c37 | 2026-09-12T21:57:11Z |  |
| Kustomization | flux-system | estate-catalog | Ready | latest@sha256:876d6e5f03c9e7f33c089c6fa1 | 2026-09-12T22:00:16Z |  |
| Kustomization | flux-system | estate-db | Ready | main@ec26c37 | 2026-09-12T21:57:52Z |  |
| Kustomization | flux-system | estate-db-migrate | Ready | main@ec26c37 | 2026-09-12T21:58:26Z |  |
| Kustomization | flux-system | estate-db-operator | Ready | main@ec26c37 | 2026-09-12T21:56:37Z |  |
| Kustomization | flux-system | event-bus | Ready | main@ec26c37 | 2026-09-12T21:57:12Z |  |
| Kustomization | flux-system | external-secrets | Ready | main@ec26c37 | 2026-09-12T21:57:35Z |  |
| Kustomization | flux-system | feature-register | Ready | main@ec26c37 | 2026-09-12T21:56:44Z |  |
| Kustomization | flux-system | flux-system | Ready | main@ec26c37 | 2026-09-12T21:56:34Z |  |
| Kustomization | flux-system | flux-webhook | Ready | main@ec26c37 | 2026-09-12T21:58:16Z |  |
| Kustomization | flux-system | gateway-api-crds | Ready | v1.5.1@e7677b7 | 2026-09-12T21:56:47Z |  |
| Kustomization | flux-system | gvisor-runtime | Ready | main@ec26c37 | 2026-09-12T21:58:36Z |  |
| Kustomization | flux-system | healing | Ready | main@ec26c37 | 2026-09-12T21:57:40Z |  |
| Kustomization | flux-system | healing-analyzer | Ready | main@ec26c37 | 2026-09-12T21:58:45Z |  |
| Kustomization | flux-system | healing-k8sgpt | Ready | main@ec26c37 | 2026-09-12T21:58:42Z |  |
| Kustomization | flux-system | healthchecks | Ready | main@ec26c37 | 2026-09-12T21:58:56Z |  |
| Kustomization | flux-system | hermes-agent | Ready | main@ec26c37 | 2026-09-12T21:58:31Z |  |
| Kustomization | flux-system | hindsight | Ready | main@ec26c37 | 2026-09-12T21:58:39Z |  |
| Kustomization | flux-system | human-vault | Ready | main@ec26c37 | 2026-09-12T21:57:55Z |  |
| Kustomization | flux-system | human-vault-bridge | Ready | main@ec26c37 | 2026-09-12T21:58:15Z |  |
| Kustomization | flux-system | identity | Ready | main@ec26c37 | 2026-09-12T21:58:06Z |  |
| Kustomization | flux-system | image-automation | Ready | main@ec26c37 | 2026-09-12T21:57:54Z |  |
| Kustomization | flux-system | jit | Ready | main@ec26c37 | 2026-09-12T21:56:50Z |  |
| Kustomization | flux-system | keda | Ready | main@ec26c37 | 2026-09-12T21:57:46Z |  |
| Kustomization | flux-system | kyverno | Ready | main@ec26c37 | 2026-09-12T21:56:35Z |  |
| Kustomization | flux-system | llm | Ready | main@ec26c37 | 2026-09-12T21:58:34Z |  |
| Kustomization | flux-system | mcp | Ready | main@ec26c37 | 2026-09-12T21:57:59Z |  |
| Kustomization | flux-system | metrics-server | Ready | main@ec26c37 | 2026-09-12T21:58:11Z |  |
| Kustomization | flux-system | monitoring | Ready | main@ec26c37 | 2026-09-12T21:58:23Z |  |
| Kustomization | flux-system | monitoring-rules | Ready | main@ec26c37 | 2026-09-12T21:58:28Z |  |
| Kustomization | flux-system | nodesoftware-operator | Ready | main@ec26c37 | 2026-09-12T21:58:20Z |  |
| Kustomization | flux-system | notify | Ready | main@ec26c37 | 2026-09-12T21:58:12Z |  |
| Kustomization | flux-system | ns-fences | Ready | main@ec26c37 | 2026-09-12T21:57:03Z |  |
| Kustomization | flux-system | observability-collector | Ready | main@ec26c37 | 2026-09-12T21:58:05Z |  |
| Kustomization | flux-system | otto-gateway | Ready | main@ec26c37 | 2026-09-12T21:58:03Z |  |
| Kustomization | flux-system | otto-golden | Ready | main@ec26c37 | 2026-09-12T21:58:22Z |  |
| Kustomization | flux-system | otto-golden-secret | Ready | main@ec26c37 | 2026-09-12T21:57:45Z |  |
| Kustomization | flux-system | priority-classes | Ready | main@ec26c37 | 2026-09-12T21:57:04Z |  |
| Kustomization | flux-system | prospector | Ready | main@7453d76 | 2026-09-12T21:50:34Z |  |
| Kustomization | flux-system | prospector-platform | Ready | main@ec26c37 | 2026-09-12T21:57:38Z |  |
| Kustomization | flux-system | rbac | Ready | main@ec26c37 | 2026-09-12T21:57:08Z |  |
| Kustomization | flux-system | rbac-floor | Ready | main@ec26c37 | 2026-09-12T21:56:38Z |  |
| Kustomization | flux-system | rbac-identity | Ready | main@ec26c37 | 2026-09-12T21:56:40Z |  |
| Kustomization | flux-system | reloader | Ready | main@ec26c37 | 2026-09-12T21:57:42Z |  |
| Kustomization | flux-system | research-engine | Ready | main@ec26c37 | 2026-09-12T21:58:41Z |  |
| Kustomization | flux-system | robusta | Ready | main@ec26c37 | 2026-09-12T21:57:48Z |  |
| Kustomization | flux-system | router-events | Ready | main@ec26c37 | 2026-09-12T21:58:47Z |  |
| Kustomization | flux-system | sandbox-launch | Ready | main@ec26c37 | 2026-09-12T21:57:39Z |  |
| Kustomization | flux-system | sandbox-live | Ready | sandbox/launch@90b8450 | 2026-09-12T21:59:35Z |  |
| Kustomization | flux-system | scheduling | Ready | main@ec26c37 | 2026-09-12T21:57:36Z |  |
| Kustomization | flux-system | searxng | Ready | main@ec26c37 | 2026-09-12T21:56:48Z |  |
| Kustomization | flux-system | secret-store | Ready | main@ec26c37 | 2026-09-12T21:57:41Z |  |
| Kustomization | flux-system | spire | Ready | main@ec26c37 | 2026-09-12T21:58:10Z |  |
| Kustomization | flux-system | staging | Ready | main@ec26c37 | 2026-09-12T21:56:43Z |  |
| Kustomization | flux-system | trivy | Ready | main@ec26c37 | 2026-09-12T21:56:31Z |  |
| Kustomization | flux-system | verification | Ready | main@ec26c37 | 2026-09-12T21:58:17Z |  |
| Kustomization | flux-system | weave-gitops | Ready | main@ec26c37 | 2026-09-12T21:58:32Z |  |
