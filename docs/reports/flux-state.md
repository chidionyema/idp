# Flux: what is applied

Read from the cluster receipt taken at 2026-09-12T17:00:18Z. Every Kustomization and HelmRelease, with the revision Flux last applied. **Suspended** is a switch somebody turned off on purpose (temporal, commerce, commerce-data, event-bus), not a defect; **Unknown** is a row Flux has never graded.

**117 objects: 109 ready, 6 not ready, 0 unknown, 2 suspended.**

## Not ready right now

- **HelmRelease commerce/lago** since 2026-09-12T16:58:30Z: Helm install failed for release commerce/lago with chart lago@1.28.0: failed early due to stalled resources: [Deployment/commerce/lago-api status: 'Failed']
- **Kustomization flux-system/chaos** since 2026-09-12T16:59:58Z: Workflow/observability/langfuse-alert-drill-first-run dry-run failed (InternalError): Internal error occurred: failed calling webhook "mworkflow.kb.io": failed to call webhook: Post "https://chaos-mesh-controller-manager.chaos-mesh.svc:443/mutate-chaos-mesh-org-v1alpha1-workflow?timeout=5s": EOF 
- **Kustomization flux-system/commerce** since 2026-09-12T16:46:32Z: Reconciliation in progress
- **Kustomization flux-system/cyrus** since 2026-09-12T16:59:16Z: Reconciliation in progress
- **Kustomization flux-system/guacamole** since 2026-09-12T16:59:59Z: dependency 'flux-system/tailscale' is not ready
- **Kustomization flux-system/tailscale** since 2026-09-12T16:59:15Z: Reconciliation in progress

## Every row

| Kind | Namespace | Name | State | Applied revision | Since | Message |
|---|---|---|---|---|---|---|
| HelmRelease | commerce | lago | Not ready | 1.28.0 | 2026-09-12T16:58:30Z | Helm install failed for release commerce/lago with chart lago@1.28.0: failed early due to stalled resources: [Deployment/commerce/lago-api status: 'Failed'] |
| Kustomization | flux-system | chaos | Not ready | main@abea14d | 2026-09-12T16:59:58Z | Workflow/observability/langfuse-alert-drill-first-run dry-run failed (InternalError): Internal error occurred: failed calling webhook "mworkflow.kb.io": failed  |
| Kustomization | flux-system | commerce | Not ready | main@abea14d | 2026-09-12T16:46:32Z | Reconciliation in progress |
| Kustomization | flux-system | cyrus | Not ready | main@17a5ceb | 2026-09-12T16:59:16Z | Reconciliation in progress |
| Kustomization | flux-system | guacamole | Not ready | main@5b6aeea | 2026-09-12T16:59:59Z | dependency 'flux-system/tailscale' is not ready |
| Kustomization | flux-system | tailscale | Not ready | main@d3ab8a2 | 2026-09-12T16:59:15Z | Reconciliation in progress |
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
| Kustomization | flux-system | agent-workforce | Ready | main@b08d18b | 2026-09-12T16:59:41Z |  |
| Kustomization | flux-system | alerts | Ready | main@b08d18b | 2026-09-12T16:59:33Z |  |
| Kustomization | flux-system | alerts-github | Ready | main@b08d18b | 2026-09-12T16:59:13Z |  |
| Kustomization | flux-system | alerts-secret | Ready | main@b08d18b | 2026-09-12T16:59:18Z |  |
| Kustomization | flux-system | autoscaler | Ready | main@b08d18b | 2026-09-12T16:59:02Z |  |
| Kustomization | flux-system | backstage | Ready | main@b08d18b | 2026-09-12T16:59:46Z |  |
| Kustomization | flux-system | backstage-namespace | Ready | main@b08d18b | 2026-09-12T16:57:49Z |  |
| Kustomization | flux-system | calico | Ready | main@b08d18b | 2026-09-12T16:58:18Z |  |
| Kustomization | flux-system | chaos-mesh | Ready | main@b08d18b | 2026-09-12T16:59:12Z |  |
| Kustomization | flux-system | cluster-state | Ready | main@b08d18b | 2026-09-12T16:59:52Z |  |
| Kustomization | flux-system | commerce-data | Ready | main@b08d18b | 2026-09-12T16:59:11Z |  |
| Kustomization | flux-system | concierge | Ready | main@b08d18b | 2026-09-12T16:58:58Z |  |
| Kustomization | flux-system | cross-node-drill | Ready | main@b08d18b | 2026-09-12T16:57:52Z |  |
| Kustomization | flux-system | crossplane | Ready | main@b08d18b | 2026-09-12T16:58:53Z |  |
| Kustomization | flux-system | crossplane-providerconfig | Ready | main@b08d18b | 2026-09-12T16:59:37Z |  |
| Kustomization | flux-system | crossplane-providers | Ready | main@b08d18b | 2026-09-12T16:59:21Z |  |
| Kustomization | flux-system | dagster | Ready | main@b08d18b | 2026-09-12T16:59:56Z |  |
| Kustomization | flux-system | dns | Ready | main@b08d18b | 2026-09-12T16:58:56Z |  |
| Kustomization | flux-system | drills | Ready | main@b08d18b | 2026-09-12T16:59:36Z |  |
| Kustomization | flux-system | edge | Ready | main@b08d18b | 2026-09-12T16:58:33Z |  |
| Kustomization | flux-system | estate-catalog | Ready | latest@sha256:667515359df3fe606417ffe52b | 2026-09-12T17:00:09Z |  |
| Kustomization | flux-system | estate-db | Ready | main@b08d18b | 2026-09-12T16:59:00Z |  |
| Kustomization | flux-system | estate-db-migrate | Ready | main@b08d18b | 2026-09-12T16:59:10Z |  |
| Kustomization | flux-system | estate-db-operator | Ready | main@b08d18b | 2026-09-12T16:57:48Z |  |
| Kustomization | flux-system | event-bus | Ready | main@b08d18b | 2026-09-12T16:57:54Z |  |
| Kustomization | flux-system | external-secrets | Ready | main@b08d18b | 2026-09-12T16:58:45Z |  |
| Kustomization | flux-system | feature-register | Ready | main@b08d18b | 2026-09-12T16:57:50Z |  |
| Kustomization | flux-system | flux-system | Ready | main@b08d18b | 2026-09-12T16:57:47Z |  |
| Kustomization | flux-system | flux-webhook | Ready | main@b08d18b | 2026-09-12T16:59:53Z |  |
| Kustomization | flux-system | gateway-api-crds | Ready | v1.5.1@e7677b7 | 2026-09-12T16:58:21Z |  |
| Kustomization | flux-system | gvisor-runtime | Ready | main@b08d18b | 2026-09-12T16:59:22Z |  |
| Kustomization | flux-system | healing | Ready | main@b08d18b | 2026-09-12T16:58:52Z |  |
| Kustomization | flux-system | healing-analyzer | Ready | main@b08d18b | 2026-09-12T16:59:44Z |  |
| Kustomization | flux-system | healing-k8sgpt | Ready | main@b08d18b | 2026-09-12T16:59:42Z |  |
| Kustomization | flux-system | healthchecks | Ready | main@b08d18b | 2026-09-12T16:59:32Z |  |
| Kustomization | flux-system | hermes-agent | Ready | main@b08d18b | 2026-09-12T16:59:50Z |  |
| Kustomization | flux-system | hindsight | Ready | main@b08d18b | 2026-09-12T16:59:38Z |  |
| Kustomization | flux-system | human-vault | Ready | main@b08d18b | 2026-09-12T16:59:02Z |  |
| Kustomization | flux-system | human-vault-bridge | Ready | main@b08d18b | 2026-09-12T16:59:07Z |  |
| Kustomization | flux-system | identity | Ready | main@b08d18b | 2026-09-12T16:59:08Z |  |
| Kustomization | flux-system | image-automation | Ready | main@b08d18b | 2026-09-12T16:58:55Z |  |
| Kustomization | flux-system | jit | Ready | main@b08d18b | 2026-09-12T16:57:57Z |  |
| Kustomization | flux-system | keda | Ready | main@b08d18b | 2026-09-12T16:59:49Z |  |
| Kustomization | flux-system | kyverno | Ready | main@b08d18b | 2026-09-12T16:58:19Z |  |
| Kustomization | flux-system | llm | Ready | main@b08d18b | 2026-09-12T16:59:31Z |  |
| Kustomization | flux-system | mcp | Ready | main@b08d18b | 2026-09-12T16:59:25Z |  |
| Kustomization | flux-system | metrics-server | Ready | main@b08d18b | 2026-09-12T16:58:49Z |  |
| Kustomization | flux-system | monitoring | Ready | main@b08d18b | 2026-09-12T16:59:19Z |  |
| Kustomization | flux-system | monitoring-rules | Ready | main@b08d18b | 2026-09-12T16:59:35Z |  |
| Kustomization | flux-system | nodesoftware-operator | Ready | main@b08d18b | 2026-09-12T16:59:16Z |  |
| Kustomization | flux-system | notify | Ready | main@b08d18b | 2026-09-12T16:59:06Z |  |
| Kustomization | flux-system | ns-fences | Ready | main@b08d18b | 2026-09-12T16:58:13Z |  |
| Kustomization | flux-system | observability | Ready | main@b08d18b | 2026-09-12T16:59:55Z |  |
| Kustomization | flux-system | observability-collector | Ready | main@b08d18b | 2026-09-12T16:59:47Z |  |
| Kustomization | flux-system | otto-gateway | Ready | main@b08d18b | 2026-09-12T16:59:29Z |  |
| Kustomization | flux-system | otto-golden | Ready | main@b08d18b | 2026-09-12T16:59:05Z |  |
| Kustomization | flux-system | otto-golden-secret | Ready | main@b08d18b | 2026-09-12T16:58:54Z |  |
| Kustomization | flux-system | priority-classes | Ready | main@b08d18b | 2026-09-12T16:57:49Z |  |
| Kustomization | flux-system | prospector | Ready | main@7453d76 | 2026-09-12T17:00:05Z |  |
| Kustomization | flux-system | prospector-platform | Ready | main@b08d18b | 2026-09-12T16:58:57Z |  |
| Kustomization | flux-system | rbac | Ready | main@b08d18b | 2026-09-12T16:57:58Z |  |
| Kustomization | flux-system | rbac-floor | Ready | main@b08d18b | 2026-09-12T16:57:42Z |  |
| Kustomization | flux-system | rbac-identity | Ready | main@b08d18b | 2026-09-12T16:57:55Z |  |
| Kustomization | flux-system | reloader | Ready | main@b08d18b | 2026-09-12T16:59:20Z |  |
| Kustomization | flux-system | research-engine | Ready | main@b08d18b | 2026-09-12T16:59:43Z |  |
| Kustomization | flux-system | robusta | Ready | main@b08d18b | 2026-09-12T16:58:59Z |  |
| Kustomization | flux-system | router-events | Ready | main@b08d18b | 2026-09-12T16:59:39Z |  |
| Kustomization | flux-system | sandbox-launch | Ready | main@b08d18b | 2026-09-12T16:58:48Z |  |
| Kustomization | flux-system | sandbox-live | Ready | sandbox/launch@0086dc1 | 2026-09-12T16:59:59Z |  |
| Kustomization | flux-system | scheduling | Ready | main@b08d18b | 2026-09-12T16:58:47Z |  |
| Kustomization | flux-system | science | Ready | main@b08d18b | 2026-09-12T16:59:57Z |  |
| Kustomization | flux-system | searxng | Ready | main@b08d18b | 2026-09-12T16:58:23Z |  |
| Kustomization | flux-system | secret-store | Ready | main@b08d18b | 2026-09-12T16:58:51Z |  |
| Kustomization | flux-system | spire | Ready | main@b08d18b | 2026-09-12T16:58:50Z |  |
| Kustomization | flux-system | staging | Ready | main@b08d18b | 2026-09-12T16:57:43Z |  |
| Kustomization | flux-system | trivy | Ready | main@b08d18b | 2026-09-12T16:57:53Z |  |
| Kustomization | flux-system | verification | Ready | main@b08d18b | 2026-09-12T16:59:14Z |  |
| Kustomization | flux-system | weave-gitops | Ready | main@b08d18b | 2026-09-12T16:59:26Z |  |
