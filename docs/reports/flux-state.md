# Flux: what is applied

Read from the cluster receipt taken at 2026-09-13T20:00:19Z. Every Kustomization and HelmRelease, with the revision Flux last applied. **Suspended** is a switch somebody turned off on purpose (temporal, commerce, commerce-data, event-bus), not a defect; **Unknown** is a row Flux has never graded.

**116 objects: 112 ready, 2 not ready, 0 unknown, 2 suspended.**

## Not ready right now

- **HelmRelease commerce/lago** since 2026-09-13T19:59:09Z: Helm install failed for release commerce/lago with chart lago@1.28.0: failed early due to stalled resources: [Deployment/commerce/lago-webhook-worker status: 'Failed']
- **Kustomization flux-system/commerce** since 2026-09-13T19:57:39Z: health check failed after 15m0.02905483s: timeout waiting for: [HelmRelease/commerce/lago status: 'InProgress']

## Every row

| Kind | Namespace | Name | State | Applied revision | Since | Message |
|---|---|---|---|---|---|---|
| HelmRelease | commerce | lago | Not ready | 1.28.0 | 2026-09-13T19:59:09Z | Helm install failed for release commerce/lago with chart lago@1.28.0: failed early due to stalled resources: [Deployment/commerce/lago-webhook-worker status: 'F |
| Kustomization | flux-system | commerce | Not ready | main@abea14d | 2026-09-13T19:57:39Z | health check failed after 15m0.02905483s: timeout waiting for: [HelmRelease/commerce/lago status: 'InProgress'] |
| HelmRelease | tigera-operator | tigera-operator | Suspended | v3.32.2 | 2026-09-06T19:38:02Z |  |
| Kustomization | flux-system | temporal | Suspended | main@1b323ac | 2026-09-08T20:23:54Z |  |
| HelmRelease | cert-manager | cert-manager | Ready | v1.21.1 | 2026-09-08T11:56:22Z |  |
| HelmRelease | chaos-mesh | chaos-mesh | Ready | 2.8.4 | 2026-09-13T04:26:37Z |  |
| HelmRelease | crossplane-system | crossplane | Ready | 2.4.0 | 2026-09-08T07:05:25Z |  |
| HelmRelease | dagster | dagster | Ready | 1.13.19 | 2026-09-12T12:32:50Z |  |
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
| HelmRelease | observability | langfuse | Ready | 2.0.2 | 2026-09-13T03:17:37Z |  |
| HelmRelease | observability | signoz | Ready | 0.138.0 | 2026-09-13T10:24:12Z |  |
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
| Kustomization | flux-system | agent-workforce | Ready | main@4503e0d | 2026-09-13T19:56:03Z |  |
| Kustomization | flux-system | alerts | Ready | main@4503e0d | 2026-09-13T19:53:25Z |  |
| Kustomization | flux-system | alerts-github | Ready | main@4503e0d | 2026-09-13T19:53:13Z |  |
| Kustomization | flux-system | alerts-secret | Ready | main@4503e0d | 2026-09-13T19:54:54Z |  |
| Kustomization | flux-system | autoscaler | Ready | main@4503e0d | 2026-09-13T19:54:52Z |  |
| Kustomization | flux-system | backstage | Ready | main@4503e0d | 2026-09-13T19:59:41Z |  |
| Kustomization | flux-system | backstage-namespace | Ready | main@4503e0d | 2026-09-13T19:52:47Z |  |
| Kustomization | flux-system | calico | Ready | main@4503e0d | 2026-09-13T19:53:41Z |  |
| Kustomization | flux-system | chaos | Ready | main@4503e0d | 2026-09-13T19:54:56Z |  |
| Kustomization | flux-system | chaos-mesh | Ready | main@4503e0d | 2026-09-13T19:53:57Z |  |
| Kustomization | flux-system | cluster-state | Ready | main@4503e0d | 2026-09-13T19:53:53Z |  |
| Kustomization | flux-system | commerce-data | Ready | main@4503e0d | 2026-09-13T19:55:28Z |  |
| Kustomization | flux-system | concierge | Ready | main@4503e0d | 2026-09-13T19:54:05Z |  |
| Kustomization | flux-system | cross-node-drill | Ready | main@4503e0d | 2026-09-13T19:53:14Z |  |
| Kustomization | flux-system | crossplane | Ready | main@4503e0d | 2026-09-13T19:54:00Z |  |
| Kustomization | flux-system | crossplane-providerconfig | Ready | main@4503e0d | 2026-09-13T19:53:59Z |  |
| Kustomization | flux-system | crossplane-providers | Ready | main@4503e0d | 2026-09-13T19:53:15Z |  |
| Kustomization | flux-system | dagster | Ready | main@4503e0d | 2026-09-13T19:55:24Z |  |
| Kustomization | flux-system | dns | Ready | main@4503e0d | 2026-09-13T19:55:06Z |  |
| Kustomization | flux-system | drills | Ready | main@4503e0d | 2026-09-13T19:54:51Z |  |
| Kustomization | flux-system | edge | Ready | main@4503e0d | 2026-09-13T19:52:53Z |  |
| Kustomization | flux-system | estate-catalog | Ready | latest@sha256:e51fbb21aa977410ca83ed8a9c | 2026-09-13T19:52:44Z |  |
| Kustomization | flux-system | estate-db | Ready | main@4503e0d | 2026-09-13T19:54:48Z |  |
| Kustomization | flux-system | estate-db-migrate | Ready | main@4503e0d | 2026-09-13T19:55:10Z |  |
| Kustomization | flux-system | estate-db-operator | Ready | main@4503e0d | 2026-09-13T19:53:33Z |  |
| Kustomization | flux-system | event-bus | Ready | main@4503e0d | 2026-09-13T19:52:05Z |  |
| Kustomization | flux-system | external-secrets | Ready | main@4503e0d | 2026-09-13T19:53:46Z |  |
| Kustomization | flux-system | feature-register | Ready | main@4503e0d | 2026-09-13T19:53:46Z |  |
| Kustomization | flux-system | flux-system | Ready | main@4503e0d | 2026-09-13T19:53:42Z |  |
| Kustomization | flux-system | flux-webhook | Ready | main@4503e0d | 2026-09-13T19:54:54Z |  |
| Kustomization | flux-system | gateway-api-crds | Ready | v1.5.1@e7677b7 | 2026-09-13T19:54:30Z |  |
| Kustomization | flux-system | guacamole | Ready | main@4503e0d | 2026-09-13T19:54:31Z |  |
| Kustomization | flux-system | gvisor-runtime | Ready | main@4503e0d | 2026-09-13T19:55:29Z |  |
| Kustomization | flux-system | healing | Ready | main@4503e0d | 2026-09-13T19:54:53Z |  |
| Kustomization | flux-system | healing-analyzer | Ready | main@4503e0d | 2026-09-13T19:56:04Z |  |
| Kustomization | flux-system | healing-k8sgpt | Ready | main@4503e0d | 2026-09-13T19:56:15Z |  |
| Kustomization | flux-system | healthchecks | Ready | main@4503e0d | 2026-09-13T19:55:20Z |  |
| Kustomization | flux-system | hermes-agent | Ready | main@4503e0d | 2026-09-13T19:56:46Z |  |
| Kustomization | flux-system | hindsight | Ready | main@4503e0d | 2026-09-13T19:54:55Z |  |
| Kustomization | flux-system | human-vault | Ready | main@4503e0d | 2026-09-13T19:53:22Z |  |
| Kustomization | flux-system | human-vault-bridge | Ready | main@4503e0d | 2026-09-13T19:54:10Z |  |
| Kustomization | flux-system | identity | Ready | main@4503e0d | 2026-09-13T19:55:33Z |  |
| Kustomization | flux-system | image-automation | Ready | main@4503e0d | 2026-09-13T19:53:55Z |  |
| Kustomization | flux-system | jit | Ready | main@4503e0d | 2026-09-13T19:52:45Z |  |
| Kustomization | flux-system | keda | Ready | main@4503e0d | 2026-09-13T19:53:25Z |  |
| Kustomization | flux-system | kyverno | Ready | main@4503e0d | 2026-09-13T19:52:29Z |  |
| Kustomization | flux-system | llm | Ready | main@4503e0d | 2026-09-13T19:55:20Z |  |
| Kustomization | flux-system | mcp | Ready | main@4503e0d | 2026-09-13T19:54:43Z |  |
| Kustomization | flux-system | metrics-server | Ready | main@4503e0d | 2026-09-13T19:54:06Z |  |
| Kustomization | flux-system | monitoring | Ready | main@4503e0d | 2026-09-13T19:55:00Z |  |
| Kustomization | flux-system | monitoring-rules | Ready | main@4503e0d | 2026-09-13T19:55:32Z |  |
| Kustomization | flux-system | nodesoftware-operator | Ready | main@4503e0d | 2026-09-13T19:56:06Z |  |
| Kustomization | flux-system | notify | Ready | main@4503e0d | 2026-09-13T19:55:33Z |  |
| Kustomization | flux-system | ns-fences | Ready | main@4503e0d | 2026-09-13T19:55:25Z |  |
| Kustomization | flux-system | observability | Ready | main@4503e0d | 2026-09-13T19:55:45Z |  |
| Kustomization | flux-system | observability-collector | Ready | main@4503e0d | 2026-09-13T19:53:10Z |  |
| Kustomization | flux-system | otto-gateway | Ready | main@4503e0d | 2026-09-13T19:54:59Z |  |
| Kustomization | flux-system | otto-golden | Ready | main@4503e0d | 2026-09-13T19:54:15Z |  |
| Kustomization | flux-system | otto-golden-secret | Ready | main@4503e0d | 2026-09-13T19:53:43Z |  |
| Kustomization | flux-system | priority-classes | Ready | main@4503e0d | 2026-09-13T19:51:44Z |  |
| Kustomization | flux-system | prospector | Ready | main@7453d76 | 2026-09-13T19:57:28Z |  |
| Kustomization | flux-system | prospector-platform | Ready | main@4503e0d | 2026-09-13T19:54:34Z |  |
| Kustomization | flux-system | rbac | Ready | main@4503e0d | 2026-09-13T19:53:52Z |  |
| Kustomization | flux-system | rbac-floor | Ready | main@4503e0d | 2026-09-13T19:52:21Z |  |
| Kustomization | flux-system | rbac-identity | Ready | main@4503e0d | 2026-09-13T19:53:22Z |  |
| Kustomization | flux-system | reloader | Ready | main@4503e0d | 2026-09-13T19:54:27Z |  |
| Kustomization | flux-system | research-engine | Ready | main@4503e0d | 2026-09-13T19:55:21Z |  |
| Kustomization | flux-system | robusta | Ready | main@4503e0d | 2026-09-13T19:55:50Z |  |
| Kustomization | flux-system | router-events | Ready | main@4503e0d | 2026-09-13T19:54:12Z |  |
| Kustomization | flux-system | sandbox-launch | Ready | main@4503e0d | 2026-09-13T19:54:39Z |  |
| Kustomization | flux-system | sandbox-live | Ready | sandbox/launch@4830a6e | 2026-09-13T19:59:41Z |  |
| Kustomization | flux-system | scheduling | Ready | main@4503e0d | 2026-09-13T19:53:33Z |  |
| Kustomization | flux-system | science | Ready | main@4503e0d | 2026-09-13T19:54:36Z |  |
| Kustomization | flux-system | searxng | Ready | main@4503e0d | 2026-09-13T19:52:41Z |  |
| Kustomization | flux-system | secret-store | Ready | main@4503e0d | 2026-09-13T19:54:57Z |  |
| Kustomization | flux-system | spire | Ready | main@4503e0d | 2026-09-13T19:53:11Z |  |
| Kustomization | flux-system | staging | Ready | main@4503e0d | 2026-09-13T19:53:16Z |  |
| Kustomization | flux-system | tailscale | Ready | main@4503e0d | 2026-09-13T19:53:36Z |  |
| Kustomization | flux-system | trivy | Ready | main@4503e0d | 2026-09-13T19:52:48Z |  |
| Kustomization | flux-system | verification | Ready | main@4503e0d | 2026-09-13T19:54:56Z |  |
| Kustomization | flux-system | weave-gitops | Ready | main@4503e0d | 2026-09-13T19:54:52Z |  |
