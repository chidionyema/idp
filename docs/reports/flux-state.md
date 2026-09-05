# Flux: what is applied

Read from the cluster receipt taken at 2026-09-05T02:00:10Z. Every Kustomization and HelmRelease, with the revision Flux last applied. **Suspended** is a switch somebody turned off on purpose (temporal, commerce, commerce-data, event-bus), not a defect; **Unknown** is a row Flux has never graded.

**97 objects: 87 ready, 7 not ready, 0 unknown, 3 suspended.**

## Not ready right now

- **HelmRelease tigera-operator/tigera-operator** since 2026-09-05T01:47:30Z: Helm install failed for release tigera-operator/tigera-operator with chart tigera-operator@v3.32.2: unable to build kubernetes objects from release manifest: [resource mapping not found for name: "default" namespace: "" from "": no matches for kind "APIServer" in version "operator.tigera.io/v1" ensure CRDs are installed first, resource mapping not found for name: "default" namespace: "" from "": no matches for kind "Goldmane" in version "operator.tigera.io/v1" ensure CRDs are installed first, resource mapping not found for name: "default" namespace: "" from "": no matches for kind "Installation" in version "operator.tigera.io/v1" ensure CRDs are installed first, resource mapping not found for name: "default" namespace: "" from "": no matches for kind "Whisker" in version "operator.tigera.io/v1" ensure CRDs are installed first]
- **Kustomization flux-system/agent-workforce** since 2026-09-05T01:50:38Z: Reconciliation in progress
- **Kustomization flux-system/image-automation** since 2026-09-05T01:57:56Z: Reconciliation in progress
- **Kustomization flux-system/notify** since 2026-09-05T01:57:57Z: Reconciliation in progress
- **Kustomization flux-system/prospector** since 2026-09-05T02:00:02Z: Reconciliation in progress
- **Kustomization flux-system/rbac** since 2026-09-04T22:11:22Z: dependency 'flux-system/rbac-identity' is not ready
- **Kustomization flux-system/rbac-identity** since 2026-09-05T01:57:23Z: health check failed after 5m0.018705188s: timeout waiting for: [ExternalSecret/flux-system/bridge-identity status: 'InProgress']

## Every row

| Kind | Namespace | Name | State | Applied revision | Since | Message |
|---|---|---|---|---|---|---|
| HelmRelease | tigera-operator | tigera-operator | Not ready | v3.32.2 | 2026-09-05T01:47:30Z | Helm install failed for release tigera-operator/tigera-operator with chart tigera-operator@v3.32.2: unable to build kubernetes objects from release manifest: [r |
| Kustomization | flux-system | agent-workforce | Not ready | main@aa9a27c | 2026-09-05T01:50:38Z | Reconciliation in progress |
| Kustomization | flux-system | image-automation | Not ready | main@190b364 | 2026-09-05T01:57:56Z | Reconciliation in progress |
| Kustomization | flux-system | notify | Not ready | main@1c82c5a | 2026-09-05T01:57:57Z | Reconciliation in progress |
| Kustomization | flux-system | prospector | Not ready | main@6c20302 | 2026-09-05T02:00:02Z | Reconciliation in progress |
| Kustomization | flux-system | rbac | Not ready | main@4167db0 | 2026-09-04T22:11:22Z | dependency 'flux-system/rbac-identity' is not ready |
| Kustomization | flux-system | rbac-identity | Not ready | main@4167db0 | 2026-09-05T01:57:23Z | health check failed after 5m0.018705188s: timeout waiting for: [ExternalSecret/flux-system/bridge-identity status: 'InProgress'] |
| Kustomization | flux-system | commerce | Suspended |  |  |  |
| Kustomization | flux-system | commerce-data | Suspended |  |  |  |
| Kustomization | flux-system | temporal | Suspended | main@1b323ac | 2026-08-30T05:54:22Z |  |
| HelmRelease | cert-manager | cert-manager | Ready | v1.21.1 | 2026-08-31T07:10:44Z |  |
| HelmRelease | chaos-mesh | chaos-mesh | Ready | 2.8.4 | 2026-08-31T07:12:00Z |  |
| HelmRelease | dagster | dagster | Ready | 1.13.19 | 2026-09-04T18:15:02Z |  |
| HelmRelease | edge | external-dns | Ready | 1.21.1 | 2026-08-31T07:11:28Z |  |
| HelmRelease | edge | traefik | Ready | 41.3.0 | 2026-08-31T07:10:46Z |  |
| HelmRelease | estate-db | cloudnative-pg | Ready | 0.29.0 | 2026-09-04T13:28:55Z |  |
| HelmRelease | event-bus | nats | Ready | 2.14.6 | 2026-09-04T12:12:19Z |  |
| HelmRelease | external-secrets | external-secrets | Ready | 2.9.0 | 2026-09-02T11:40:21Z |  |
| HelmRelease | healing | descheduler | Ready | 0.36.0 | 2026-08-31T07:11:29Z |  |
| HelmRelease | healing | k8sgpt-operator | Ready | 0.2.29 | 2026-08-31T07:11:29Z |  |
| HelmRelease | hindsight | hindsight | Ready | 0.9.2 | 2026-09-04T23:34:42Z |  |
| HelmRelease | identity | oauth2-proxy | Ready | 10.7.0 | 2026-08-29T07:33:02Z |  |
| HelmRelease | keda | keda | Ready | 2.20.2 | 2026-08-31T07:14:43Z |  |
| HelmRelease | keda | keda-add-ons-http | Ready | 0.15.0 | 2026-08-31T07:14:44Z |  |
| HelmRelease | kyverno | kyverno | Ready | 3.9.0 | 2026-09-04T11:31:56Z |  |
| HelmRelease | metrics-server | metrics-server | Ready | 3.14.0 | 2026-08-31T07:11:28Z |  |
| HelmRelease | monitoring | blackbox | Ready | 11.17.2 | 2026-08-31T07:12:07Z |  |
| HelmRelease | monitoring | kube-prometheus-stack | Ready | 88.6.0 | 2026-08-31T07:12:05Z |  |
| HelmRelease | observability | langfuse | Ready | 2.0.2 | 2026-09-04T18:18:00Z |  |
| HelmRelease | observability | signoz | Ready | 0.138.0 | 2026-08-31T07:12:44Z |  |
| HelmRelease | observability | superset | Ready | 0.22.4 | 2026-09-04T18:34:35Z |  |
| HelmRelease | observability-agent | k8s-infra | Ready | 0.17.0 | 2026-09-03T15:19:29Z |  |
| HelmRelease | reloader | reloader | Ready | 2.2.16 | 2026-08-31T07:11:24Z |  |
| HelmRelease | robusta | robusta | Ready | 0.48.0 | 2026-08-31T07:12:01Z |  |
| HelmRelease | spire-mgmt | spire | Ready | 0.30.1 | 2026-08-31T07:12:31Z |  |
| HelmRelease | spire-mgmt | spire-crds | Ready | 0.6.1 | 2026-08-31T07:12:02Z |  |
| HelmRelease | tailscale | tailscale-operator | Ready | 1.102.3 | 2026-09-02T16:32:30Z |  |
| HelmRelease | temporal | temporal | Ready | 1.6.0 | 2026-08-29T19:01:39Z |  |
| HelmRelease | weave-gitops | weave-gitops | Ready | 4.0.36 | 2026-09-04T08:56:00Z |  |
| Kustomization | flux-system | alerts | Ready | main@1c82c5a | 2026-09-05T01:51:57Z |  |
| Kustomization | flux-system | alerts-github | Ready | main@1c82c5a | 2026-09-05T01:52:04Z |  |
| Kustomization | flux-system | alerts-secret | Ready | main@1c82c5a | 2026-09-05T01:51:53Z |  |
| Kustomization | flux-system | autoscaler | Ready | main@1c82c5a | 2026-09-05T01:51:52Z |  |
| Kustomization | flux-system | backstage | Ready | main@1c82c5a | 2026-09-05T01:52:17Z |  |
| Kustomization | flux-system | backstage-namespace | Ready | main@1c82c5a | 2026-09-05T01:51:32Z |  |
| Kustomization | flux-system | calico | Ready | main@1c82c5a | 2026-09-05T01:51:39Z |  |
| Kustomization | flux-system | chaos | Ready | main@1c82c5a | 2026-09-05T01:52:23Z |  |
| Kustomization | flux-system | chaos-mesh | Ready | main@1c82c5a | 2026-09-05T01:51:46Z |  |
| Kustomization | flux-system | cluster-state | Ready | main@1c82c5a | 2026-09-05T01:52:03Z |  |
| Kustomization | flux-system | dagster | Ready | main@1c82c5a | 2026-09-05T01:52:12Z |  |
| Kustomization | flux-system | dns | Ready | main@1c82c5a | 2026-09-05T01:51:49Z |  |
| Kustomization | flux-system | drills | Ready | main@1c82c5a | 2026-09-05T01:52:06Z |  |
| Kustomization | flux-system | edge | Ready | main@1c82c5a | 2026-09-05T01:51:43Z |  |
| Kustomization | flux-system | estate-catalog | Ready | latest@sha256:30ab8d57b68029b271650cfad8 | 2026-09-05T01:50:18Z |  |
| Kustomization | flux-system | estate-db | Ready | main@1c82c5a | 2026-09-05T01:52:04Z |  |
| Kustomization | flux-system | estate-db-migrate | Ready | main@1c82c5a | 2026-09-05T01:52:10Z |  |
| Kustomization | flux-system | estate-db-operator | Ready | main@1c82c5a | 2026-09-05T01:51:33Z |  |
| Kustomization | flux-system | event-bus | Ready | main@1c82c5a | 2026-09-05T01:51:38Z |  |
| Kustomization | flux-system | external-secrets | Ready | main@1c82c5a | 2026-09-05T01:51:44Z |  |
| Kustomization | flux-system | flux-system | Ready | main@1c82c5a | 2026-09-05T01:51:35Z |  |
| Kustomization | flux-system | flux-webhook | Ready | main@1c82c5a | 2026-09-05T01:51:58Z |  |
| Kustomization | flux-system | gateway-api-crds | Ready | v1.5.1@e7677b7 | 2026-09-05T01:51:38Z |  |
| Kustomization | flux-system | guacamole | Ready | main@1c82c5a | 2026-09-05T01:52:13Z |  |
| Kustomization | flux-system | healing | Ready | main@1c82c5a | 2026-09-05T01:52:20Z |  |
| Kustomization | flux-system | healing-analyzer | Ready | main@1c82c5a | 2026-09-05T01:52:22Z |  |
| Kustomization | flux-system | healthchecks | Ready | main@1c82c5a | 2026-09-05T01:52:12Z |  |
| Kustomization | flux-system | hermes-agent | Ready | main@1c82c5a | 2026-09-05T01:52:09Z |  |
| Kustomization | flux-system | hindsight | Ready | main@1c82c5a | 2026-09-05T01:52:18Z |  |
| Kustomization | flux-system | human-vault | Ready | main@1c82c5a | 2026-09-05T01:51:54Z |  |
| Kustomization | flux-system | identity | Ready | main@1c82c5a | 2026-09-05T01:51:53Z |  |
| Kustomization | flux-system | keda | Ready | main@1c82c5a | 2026-09-05T01:52:02Z |  |
| Kustomization | flux-system | kyverno | Ready | main@1c82c5a | 2026-09-05T01:51:36Z |  |
| Kustomization | flux-system | llm | Ready | main@1c82c5a | 2026-09-05T01:52:18Z |  |
| Kustomization | flux-system | mcp | Ready | main@1c82c5a | 2026-09-05T01:52:08Z |  |
| Kustomization | flux-system | metrics-server | Ready | main@1c82c5a | 2026-09-05T01:51:47Z |  |
| Kustomization | flux-system | monitoring | Ready | main@1c82c5a | 2026-09-05T01:51:55Z |  |
| Kustomization | flux-system | monitoring-rules | Ready | main@1c82c5a | 2026-09-05T01:51:58Z |  |
| Kustomization | flux-system | ns-fences | Ready | main@1c82c5a | 2026-09-05T01:51:41Z |  |
| Kustomization | flux-system | observability | Ready | main@1c82c5a | 2026-09-05T01:52:22Z |  |
| Kustomization | flux-system | observability-collector | Ready | main@1c82c5a | 2026-09-05T01:51:48Z |  |
| Kustomization | flux-system | otto-gateway | Ready | main@1c82c5a | 2026-09-05T01:52:15Z |  |
| Kustomization | flux-system | otto-golden | Ready | main@1c82c5a | 2026-09-05T01:52:01Z |  |
| Kustomization | flux-system | otto-golden-secret | Ready | main@1c82c5a | 2026-09-05T01:51:56Z |  |
| Kustomization | flux-system | priority-classes | Ready | main@1c82c5a | 2026-09-05T01:51:31Z |  |
| Kustomization | flux-system | prospector-platform | Ready | main@1c82c5a | 2026-09-05T01:51:46Z |  |
| Kustomization | flux-system | reloader | Ready | main@1c82c5a | 2026-09-05T01:51:51Z |  |
| Kustomization | flux-system | research-engine | Ready | main@1c82c5a | 2026-09-05T01:52:19Z |  |
| Kustomization | flux-system | robusta | Ready | main@1c82c5a | 2026-09-05T01:52:05Z |  |
| Kustomization | flux-system | scheduling | Ready | main@1c82c5a | 2026-09-05T01:51:45Z |  |
| Kustomization | flux-system | science | Ready | main@1c82c5a | 2026-09-05T01:57:24Z |  |
| Kustomization | flux-system | searxng | Ready | main@1c82c5a | 2026-09-05T01:51:39Z |  |
| Kustomization | flux-system | secret-store | Ready | main@1c82c5a | 2026-09-05T01:51:49Z |  |
| Kustomization | flux-system | spire | Ready | main@1c82c5a | 2026-09-05T01:51:48Z |  |
| Kustomization | flux-system | staging | Ready | main@1c82c5a | 2026-09-05T01:51:35Z |  |
| Kustomization | flux-system | tailscale | Ready | main@1c82c5a | 2026-09-05T01:51:50Z |  |
| Kustomization | flux-system | verification | Ready | main@1c82c5a | 2026-09-05T01:51:56Z |  |
| Kustomization | flux-system | weave-gitops | Ready | main@1c82c5a | 2026-09-05T01:51:59Z |  |
