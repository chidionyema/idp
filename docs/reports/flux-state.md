# Flux: what is applied

Read from the cluster receipt taken at 2026-09-12T17:45:14Z. Every Kustomization and HelmRelease, with the revision Flux last applied. **Suspended** is a switch somebody turned off on purpose (temporal, commerce, commerce-data, event-bus), not a defect; **Unknown** is a row Flux has never graded.

**117 objects: 109 ready, 6 not ready, 0 unknown, 2 suspended.**

## Not ready right now

- **HelmRelease commerce/lago** since 2026-09-12T17:43:30Z: Helm install failed for release commerce/lago with chart lago@1.28.0: failed early due to stalled resources: [Deployment/commerce/lago-api status: 'Failed']
- **Kustomization flux-system/chaos** since 2026-09-12T17:43:26Z: Schedule/observability/langfuse-alert-drill dry-run failed (InternalError): Internal error occurred: failed calling webhook "mschedule.kb.io": failed to call webhook: Post "https://chaos-mesh-controller-manager.chaos-mesh.svc:443/mutate-chaos-mesh-org-v1alpha1-schedule?timeout=5s": EOF 
- **Kustomization flux-system/commerce** since 2026-09-12T17:31:36Z: Reconciliation in progress
- **Kustomization flux-system/cyrus** since 2026-09-12T17:44:48Z: Reconciliation in progress
- **Kustomization flux-system/guacamole** since 2026-09-12T17:24:42Z: dependency 'flux-system/tailscale' is not ready
- **Kustomization flux-system/tailscale** since 2026-09-12T17:44:46Z: Reconciliation in progress

## Every row

| Kind | Namespace | Name | State | Applied revision | Since | Message |
|---|---|---|---|---|---|---|
| HelmRelease | commerce | lago | Not ready | 1.28.0 | 2026-09-12T17:43:30Z | Helm install failed for release commerce/lago with chart lago@1.28.0: failed early due to stalled resources: [Deployment/commerce/lago-api status: 'Failed'] |
| Kustomization | flux-system | chaos | Not ready | main@abea14d | 2026-09-12T17:43:26Z | Schedule/observability/langfuse-alert-drill dry-run failed (InternalError): Internal error occurred: failed calling webhook "mschedule.kb.io": failed to call we |
| Kustomization | flux-system | commerce | Not ready | main@abea14d | 2026-09-12T17:31:36Z | Reconciliation in progress |
| Kustomization | flux-system | cyrus | Not ready | main@17a5ceb | 2026-09-12T17:44:48Z | Reconciliation in progress |
| Kustomization | flux-system | guacamole | Not ready | main@5b6aeea | 2026-09-12T17:24:42Z | dependency 'flux-system/tailscale' is not ready |
| Kustomization | flux-system | tailscale | Not ready | main@d3ab8a2 | 2026-09-12T17:44:46Z | Reconciliation in progress |
| HelmRelease | tigera-operator | tigera-operator | Suspended | v3.32.2 | 2026-09-06T19:38:02Z |  |
| Kustomization | flux-system | temporal | Suspended | main@1b323ac | 2026-09-08T20:23:54Z |  |
| HelmRelease | cert-manager | cert-manager | Ready | v1.21.1 | 2026-09-08T11:56:22Z |  |
| HelmRelease | chaos-mesh | chaos-mesh | Ready | 2.8.4 | 2026-09-08T09:36:49Z |  |
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
| Kustomization | flux-system | agent-workforce | Ready | main@e4fd4d5 | 2026-09-12T17:43:22Z |  |
| Kustomization | flux-system | alerts | Ready | main@e4fd4d5 | 2026-09-12T17:42:29Z |  |
| Kustomization | flux-system | alerts-github | Ready | main@e4fd4d5 | 2026-09-12T17:42:32Z |  |
| Kustomization | flux-system | alerts-secret | Ready | main@e4fd4d5 | 2026-09-12T17:42:22Z |  |
| Kustomization | flux-system | autoscaler | Ready | main@e4fd4d5 | 2026-09-12T17:42:15Z |  |
| Kustomization | flux-system | backstage | Ready | main@e4fd4d5 | 2026-09-12T17:43:04Z |  |
| Kustomization | flux-system | backstage-namespace | Ready | main@e4fd4d5 | 2026-09-12T17:41:41Z |  |
| Kustomization | flux-system | calico | Ready | main@e4fd4d5 | 2026-09-12T17:41:40Z |  |
| Kustomization | flux-system | chaos-mesh | Ready | main@e4fd4d5 | 2026-09-12T17:42:19Z |  |
| Kustomization | flux-system | cluster-state | Ready | main@e4fd4d5 | 2026-09-12T17:42:58Z |  |
| Kustomization | flux-system | commerce-data | Ready | main@e4fd4d5 | 2026-09-12T17:42:23Z |  |
| Kustomization | flux-system | concierge | Ready | main@e4fd4d5 | 2026-09-12T17:42:11Z |  |
| Kustomization | flux-system | cross-node-drill | Ready | main@e4fd4d5 | 2026-09-12T17:41:08Z |  |
| Kustomization | flux-system | crossplane | Ready | main@e4fd4d5 | 2026-09-12T17:42:55Z |  |
| Kustomization | flux-system | crossplane-providerconfig | Ready | main@e4fd4d5 | 2026-09-12T17:43:00Z |  |
| Kustomization | flux-system | crossplane-providers | Ready | main@e4fd4d5 | 2026-09-12T17:42:59Z |  |
| Kustomization | flux-system | dagster | Ready | main@e4fd4d5 | 2026-09-12T17:43:15Z |  |
| Kustomization | flux-system | dns | Ready | main@e4fd4d5 | 2026-09-12T17:42:26Z |  |
| Kustomization | flux-system | drills | Ready | main@e4fd4d5 | 2026-09-12T17:42:47Z |  |
| Kustomization | flux-system | edge | Ready | main@e4fd4d5 | 2026-09-12T17:41:51Z |  |
| Kustomization | flux-system | estate-catalog | Ready | latest@sha256:667515359df3fe606417ffe52b | 2026-09-12T17:43:26Z |  |
| Kustomization | flux-system | estate-db | Ready | main@e4fd4d5 | 2026-09-12T17:42:12Z |  |
| Kustomization | flux-system | estate-db-migrate | Ready | main@e4fd4d5 | 2026-09-12T17:42:50Z |  |
| Kustomization | flux-system | estate-db-operator | Ready | main@e4fd4d5 | 2026-09-12T17:41:35Z |  |
| Kustomization | flux-system | event-bus | Ready | main@e4fd4d5 | 2026-09-12T17:41:58Z |  |
| Kustomization | flux-system | external-secrets | Ready | main@e4fd4d5 | 2026-09-12T17:42:00Z |  |
| Kustomization | flux-system | feature-register | Ready | main@e4fd4d5 | 2026-09-12T17:42:53Z |  |
| Kustomization | flux-system | flux-system | Ready | main@e4fd4d5 | 2026-09-12T17:41:39Z |  |
| Kustomization | flux-system | flux-webhook | Ready | main@e4fd4d5 | 2026-09-12T17:42:36Z |  |
| Kustomization | flux-system | gateway-api-crds | Ready | v1.5.1@e7677b7 | 2026-09-12T17:41:57Z |  |
| Kustomization | flux-system | gvisor-runtime | Ready | main@e4fd4d5 | 2026-09-12T17:43:09Z |  |
| Kustomization | flux-system | healing | Ready | main@e4fd4d5 | 2026-09-12T17:42:13Z |  |
| Kustomization | flux-system | healing-analyzer | Ready | main@e4fd4d5 | 2026-09-12T17:43:23Z |  |
| Kustomization | flux-system | healing-k8sgpt | Ready | main@e4fd4d5 | 2026-09-12T17:43:08Z |  |
| Kustomization | flux-system | healthchecks | Ready | main@e4fd4d5 | 2026-09-12T17:43:14Z |  |
| Kustomization | flux-system | hermes-agent | Ready | main@e4fd4d5 | 2026-09-12T17:42:39Z |  |
| Kustomization | flux-system | hindsight | Ready | main@e4fd4d5 | 2026-09-12T17:43:10Z |  |
| Kustomization | flux-system | human-vault | Ready | main@e4fd4d5 | 2026-09-12T17:42:20Z |  |
| Kustomization | flux-system | human-vault-bridge | Ready | main@e4fd4d5 | 2026-09-12T17:42:34Z |  |
| Kustomization | flux-system | identity | Ready | main@e4fd4d5 | 2026-09-12T17:42:09Z |  |
| Kustomization | flux-system | image-automation | Ready | main@e4fd4d5 | 2026-09-12T17:42:48Z |  |
| Kustomization | flux-system | jit | Ready | main@e4fd4d5 | 2026-09-12T17:42:02Z |  |
| Kustomization | flux-system | keda | Ready | main@e4fd4d5 | 2026-09-12T17:42:54Z |  |
| Kustomization | flux-system | kyverno | Ready | main@e4fd4d5 | 2026-09-12T17:41:47Z |  |
| Kustomization | flux-system | llm | Ready | main@e4fd4d5 | 2026-09-12T17:43:07Z |  |
| Kustomization | flux-system | mcp | Ready | main@e4fd4d5 | 2026-09-12T17:42:42Z |  |
| Kustomization | flux-system | metrics-server | Ready | main@e4fd4d5 | 2026-09-12T17:42:27Z |  |
| Kustomization | flux-system | monitoring | Ready | main@e4fd4d5 | 2026-09-12T17:42:25Z |  |
| Kustomization | flux-system | monitoring-rules | Ready | main@e4fd4d5 | 2026-09-12T17:42:35Z |  |
| Kustomization | flux-system | nodesoftware-operator | Ready | main@e4fd4d5 | 2026-09-12T17:43:06Z |  |
| Kustomization | flux-system | notify | Ready | main@e4fd4d5 | 2026-09-12T17:42:24Z |  |
| Kustomization | flux-system | ns-fences | Ready | main@e4fd4d5 | 2026-09-12T17:41:33Z |  |
| Kustomization | flux-system | observability | Ready | main@e4fd4d5 | 2026-09-12T17:43:18Z |  |
| Kustomization | flux-system | observability-collector | Ready | main@e4fd4d5 | 2026-09-12T17:42:56Z |  |
| Kustomization | flux-system | otto-gateway | Ready | main@e4fd4d5 | 2026-09-12T17:42:46Z |  |
| Kustomization | flux-system | otto-golden | Ready | main@e4fd4d5 | 2026-09-12T17:42:31Z |  |
| Kustomization | flux-system | otto-golden-secret | Ready | main@e4fd4d5 | 2026-09-12T17:42:06Z |  |
| Kustomization | flux-system | priority-classes | Ready | main@e4fd4d5 | 2026-09-12T17:41:46Z |  |
| Kustomization | flux-system | prospector | Ready | main@7453d76 | 2026-09-12T17:40:23Z |  |
| Kustomization | flux-system | prospector-platform | Ready | main@e4fd4d5 | 2026-09-12T17:42:18Z |  |
| Kustomization | flux-system | rbac | Ready | main@e4fd4d5 | 2026-09-12T17:42:05Z |  |
| Kustomization | flux-system | rbac-floor | Ready | main@e4fd4d5 | 2026-09-12T17:41:45Z |  |
| Kustomization | flux-system | rbac-identity | Ready | main@e4fd4d5 | 2026-09-12T17:41:42Z |  |
| Kustomization | flux-system | reloader | Ready | main@e4fd4d5 | 2026-09-12T17:42:21Z |  |
| Kustomization | flux-system | research-engine | Ready | main@e4fd4d5 | 2026-09-12T17:43:12Z |  |
| Kustomization | flux-system | robusta | Ready | main@e4fd4d5 | 2026-09-12T17:42:10Z |  |
| Kustomization | flux-system | router-events | Ready | main@e4fd4d5 | 2026-09-12T17:43:20Z |  |
| Kustomization | flux-system | sandbox-launch | Ready | main@e4fd4d5 | 2026-09-12T17:42:03Z |  |
| Kustomization | flux-system | sandbox-live | Ready | sandbox/launch@0086dc1 | 2026-09-12T17:44:26Z |  |
| Kustomization | flux-system | scheduling | Ready | main@e4fd4d5 | 2026-09-12T17:42:07Z |  |
| Kustomization | flux-system | science | Ready | main@e4fd4d5 | 2026-09-12T17:43:25Z |  |
| Kustomization | flux-system | searxng | Ready | main@e4fd4d5 | 2026-09-12T17:41:54Z |  |
| Kustomization | flux-system | secret-store | Ready | main@e4fd4d5 | 2026-09-12T17:42:04Z |  |
| Kustomization | flux-system | spire | Ready | main@e4fd4d5 | 2026-09-12T17:42:16Z |  |
| Kustomization | flux-system | staging | Ready | main@e4fd4d5 | 2026-09-12T17:41:53Z |  |
| Kustomization | flux-system | trivy | Ready | main@e4fd4d5 | 2026-09-12T17:41:43Z |  |
| Kustomization | flux-system | verification | Ready | main@e4fd4d5 | 2026-09-12T17:42:37Z |  |
| Kustomization | flux-system | weave-gitops | Ready | main@e4fd4d5 | 2026-09-12T17:42:52Z |  |
