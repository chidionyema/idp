# Flux: what is applied

Read from the cluster receipt taken at 2026-09-10T20:15:13Z. Every Kustomization and HelmRelease, with the revision Flux last applied. **Suspended** is a switch somebody turned off on purpose (temporal, commerce, commerce-data, event-bus), not a defect; **Unknown** is a row Flux has never graded.

**115 objects: 108 ready, 5 not ready, 0 unknown, 2 suspended.**

## Not ready right now

- **HelmRelease commerce/lago** since 2026-09-10T20:03:16Z: Running 'install' action with timeout of 15m0s
- **Kustomization flux-system/commerce** since 2026-09-10T20:03:14Z: Reconciliation in progress
- **Kustomization flux-system/cyrus** since 2026-09-10T20:13:01Z: health check failed after 10m0.027632627s: timeout waiting for: [ExternalSecret/cyrus/cyrus-linear-oauth status: 'InProgress']
- **Kustomization flux-system/guacamole** since 2026-09-10T20:03:47Z: dependency 'flux-system/tailscale' is not ready
- **Kustomization flux-system/tailscale** since 2026-09-10T20:12:43Z: health check failed after 10m0.0576997s: timeout waiting for: [Deployment/tailscale/tailscale-operator status: 'NotFound']

## Every row

| Kind | Namespace | Name | State | Applied revision | Since | Message |
|---|---|---|---|---|---|---|
| HelmRelease | commerce | lago | Not ready | 1.28.0 | 2026-09-10T20:03:16Z | Running 'install' action with timeout of 15m0s |
| Kustomization | flux-system | commerce | Not ready | main@f4a7b87 | 2026-09-10T20:03:14Z | Reconciliation in progress |
| Kustomization | flux-system | cyrus | Not ready | main@17a5ceb | 2026-09-10T20:13:01Z | health check failed after 10m0.027632627s: timeout waiting for: [ExternalSecret/cyrus/cyrus-linear-oauth status: 'InProgress'] |
| Kustomization | flux-system | guacamole | Not ready | main@5b6aeea | 2026-09-10T20:03:47Z | dependency 'flux-system/tailscale' is not ready |
| Kustomization | flux-system | tailscale | Not ready | main@d3ab8a2 | 2026-09-10T20:12:43Z | health check failed after 10m0.0576997s: timeout waiting for: [Deployment/tailscale/tailscale-operator status: 'NotFound'] |
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
| Kustomization | flux-system | agent-workforce | Ready | main@f4a7b87 | 2026-09-10T20:13:48Z |  |
| Kustomization | flux-system | alerts | Ready | main@f4a7b87 | 2026-09-10T20:14:01Z |  |
| Kustomization | flux-system | alerts-github | Ready | main@f4a7b87 | 2026-09-10T20:12:32Z |  |
| Kustomization | flux-system | alerts-secret | Ready | main@f4a7b87 | 2026-09-10T20:13:19Z |  |
| Kustomization | flux-system | autoscaler | Ready | main@f4a7b87 | 2026-09-10T20:12:36Z |  |
| Kustomization | flux-system | backstage | Ready | main@f4a7b87 | 2026-09-10T20:14:09Z |  |
| Kustomization | flux-system | backstage-namespace | Ready | main@f4a7b87 | 2026-09-10T20:11:25Z |  |
| Kustomization | flux-system | calico | Ready | main@f4a7b87 | 2026-09-10T20:11:42Z |  |
| Kustomization | flux-system | chaos | Ready | main@f4a7b87 | 2026-09-10T20:13:23Z |  |
| Kustomization | flux-system | chaos-mesh | Ready | main@f4a7b87 | 2026-09-10T20:12:52Z |  |
| Kustomization | flux-system | cluster-state | Ready | main@f4a7b87 | 2026-09-10T20:12:53Z |  |
| Kustomization | flux-system | commerce-data | Ready | main@f4a7b87 | 2026-09-10T20:13:33Z |  |
| Kustomization | flux-system | cross-node-drill | Ready | main@f4a7b87 | 2026-09-10T20:11:57Z |  |
| Kustomization | flux-system | crossplane | Ready | main@f4a7b87 | 2026-09-10T20:13:07Z |  |
| Kustomization | flux-system | crossplane-providerconfig | Ready | main@f4a7b87 | 2026-09-10T20:13:56Z |  |
| Kustomization | flux-system | crossplane-providers | Ready | main@f4a7b87 | 2026-09-10T20:13:21Z |  |
| Kustomization | flux-system | dagster | Ready | main@f4a7b87 | 2026-09-10T20:13:28Z |  |
| Kustomization | flux-system | dns | Ready | main@f4a7b87 | 2026-09-10T20:12:31Z |  |
| Kustomization | flux-system | drills | Ready | main@f4a7b87 | 2026-09-10T20:12:41Z |  |
| Kustomization | flux-system | edge | Ready | main@f4a7b87 | 2026-09-10T20:12:48Z |  |
| Kustomization | flux-system | estate-catalog | Ready | latest@sha256:656bb0bc0c36d78005c2f983cd | 2026-09-10T20:06:22Z |  |
| Kustomization | flux-system | estate-db | Ready | main@f4a7b87 | 2026-09-10T20:12:33Z |  |
| Kustomization | flux-system | estate-db-migrate | Ready | main@f4a7b87 | 2026-09-10T20:13:52Z |  |
| Kustomization | flux-system | estate-db-operator | Ready | main@f4a7b87 | 2026-09-10T20:11:46Z |  |
| Kustomization | flux-system | event-bus | Ready | main@f4a7b87 | 2026-09-10T20:11:37Z |  |
| Kustomization | flux-system | external-secrets | Ready | main@f4a7b87 | 2026-09-10T20:12:23Z |  |
| Kustomization | flux-system | feature-register | Ready | main@f4a7b87 | 2026-09-10T20:12:28Z |  |
| Kustomization | flux-system | flux-system | Ready | main@f4a7b87 | 2026-09-10T20:11:40Z |  |
| Kustomization | flux-system | flux-webhook | Ready | main@f4a7b87 | 2026-09-10T20:13:12Z |  |
| Kustomization | flux-system | gateway-api-crds | Ready | v1.5.1@e7677b7 | 2026-09-10T20:11:30Z |  |
| Kustomization | flux-system | gvisor-runtime | Ready | main@f4a7b87 | 2026-09-10T20:14:13Z |  |
| Kustomization | flux-system | healing | Ready | main@f4a7b87 | 2026-09-10T20:12:52Z |  |
| Kustomization | flux-system | healing-analyzer | Ready | main@f4a7b87 | 2026-09-10T20:13:29Z |  |
| Kustomization | flux-system | healing-k8sgpt | Ready | main@f4a7b87 | 2026-09-10T20:13:56Z |  |
| Kustomization | flux-system | healthchecks | Ready | main@f4a7b87 | 2026-09-10T20:13:43Z |  |
| Kustomization | flux-system | hermes-agent | Ready | main@f4a7b87 | 2026-09-10T20:13:48Z |  |
| Kustomization | flux-system | hindsight | Ready | main@f4a7b87 | 2026-09-10T20:14:08Z |  |
| Kustomization | flux-system | human-vault | Ready | main@f4a7b87 | 2026-09-10T20:12:37Z |  |
| Kustomization | flux-system | human-vault-bridge | Ready | main@f4a7b87 | 2026-09-10T20:13:44Z |  |
| Kustomization | flux-system | identity | Ready | main@f4a7b87 | 2026-09-10T20:13:07Z |  |
| Kustomization | flux-system | image-automation | Ready | main@f4a7b87 | 2026-09-10T20:12:39Z |  |
| Kustomization | flux-system | jit | Ready | main@f4a7b87 | 2026-09-10T20:11:33Z |  |
| Kustomization | flux-system | keda | Ready | main@f4a7b87 | 2026-09-10T20:12:29Z |  |
| Kustomization | flux-system | kyverno | Ready | main@f4a7b87 | 2026-09-10T20:11:21Z |  |
| Kustomization | flux-system | llm | Ready | main@f4a7b87 | 2026-09-10T20:13:46Z |  |
| Kustomization | flux-system | mcp | Ready | main@f4a7b87 | 2026-09-10T20:12:57Z |  |
| Kustomization | flux-system | metrics-server | Ready | main@f4a7b87 | 2026-09-10T20:12:46Z |  |
| Kustomization | flux-system | monitoring | Ready | main@f4a7b87 | 2026-09-10T20:13:11Z |  |
| Kustomization | flux-system | monitoring-rules | Ready | main@f4a7b87 | 2026-09-10T20:13:02Z |  |
| Kustomization | flux-system | nodesoftware-operator | Ready | main@f4a7b87 | 2026-09-10T20:13:08Z |  |
| Kustomization | flux-system | notify | Ready | main@f4a7b87 | 2026-09-10T20:12:44Z |  |
| Kustomization | flux-system | ns-fences | Ready | main@f4a7b87 | 2026-09-10T20:12:21Z |  |
| Kustomization | flux-system | observability | Ready | main@f4a7b87 | 2026-09-10T20:13:11Z |  |
| Kustomization | flux-system | observability-collector | Ready | main@f4a7b87 | 2026-09-10T20:12:34Z |  |
| Kustomization | flux-system | otto-gateway | Ready | main@f4a7b87 | 2026-09-10T20:12:57Z |  |
| Kustomization | flux-system | otto-golden | Ready | main@f4a7b87 | 2026-09-10T20:13:31Z |  |
| Kustomization | flux-system | otto-golden-secret | Ready | main@f4a7b87 | 2026-09-10T20:13:13Z |  |
| Kustomization | flux-system | priority-classes | Ready | main@f4a7b87 | 2026-09-10T20:12:26Z |  |
| Kustomization | flux-system | prospector | Ready | main@7453d76 | 2026-09-10T20:07:20Z |  |
| Kustomization | flux-system | prospector-platform | Ready | main@f4a7b87 | 2026-09-10T20:12:59Z |  |
| Kustomization | flux-system | rbac | Ready | main@f4a7b87 | 2026-09-10T20:11:52Z |  |
| Kustomization | flux-system | rbac-floor | Ready | main@f4a7b87 | 2026-09-10T20:11:24Z |  |
| Kustomization | flux-system | rbac-identity | Ready | main@f4a7b87 | 2026-09-10T20:11:53Z |  |
| Kustomization | flux-system | reloader | Ready | main@f4a7b87 | 2026-09-10T20:12:25Z |  |
| Kustomization | flux-system | research-engine | Ready | main@f4a7b87 | 2026-09-10T20:13:49Z |  |
| Kustomization | flux-system | robusta | Ready | main@f4a7b87 | 2026-09-10T20:12:42Z |  |
| Kustomization | flux-system | sandbox-launch | Ready | main@f4a7b87 | 2026-09-10T20:12:27Z |  |
| Kustomization | flux-system | sandbox-live | Ready | sandbox/launch@0086dc1 | 2026-09-10T20:14:48Z |  |
| Kustomization | flux-system | scheduling | Ready | main@f4a7b87 | 2026-09-10T20:11:59Z |  |
| Kustomization | flux-system | science | Ready | main@f4a7b87 | 2026-09-10T20:13:39Z |  |
| Kustomization | flux-system | searxng | Ready | main@f4a7b87 | 2026-09-10T20:11:36Z |  |
| Kustomization | flux-system | secret-store | Ready | main@f4a7b87 | 2026-09-10T20:12:24Z |  |
| Kustomization | flux-system | spire | Ready | main@f4a7b87 | 2026-09-10T20:12:30Z |  |
| Kustomization | flux-system | staging | Ready | main@f4a7b87 | 2026-09-10T20:11:16Z |  |
| Kustomization | flux-system | trivy | Ready | main@f4a7b87 | 2026-09-10T20:11:43Z |  |
| Kustomization | flux-system | verification | Ready | main@f4a7b87 | 2026-09-10T20:13:02Z |  |
| Kustomization | flux-system | weave-gitops | Ready | main@f4a7b87 | 2026-09-10T20:13:21Z |  |
