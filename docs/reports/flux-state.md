# Flux: what is applied

Read from the cluster receipt taken at 2026-09-14T16:45:18Z. Every Kustomization and HelmRelease, with the revision Flux last applied. **Suspended** is a switch somebody turned off on purpose (temporal, commerce, commerce-data, event-bus), not a defect; **Unknown** is a row Flux has never graded.

**116 objects: 103 ready, 11 not ready, 0 unknown, 2 suspended.**

## Not ready right now

- **HelmRelease commerce/lago** since 2026-09-14T13:45:55Z: Helm install failed for release commerce/lago with chart lago@1.28.0: failed early due to stalled resources: [Deployment/commerce/lago-worker status: 'Failed']
- **Kustomization flux-system/commerce** since 2026-09-14T16:44:23Z: health check failed after 83.651642ms: failed early due to stalled resources: [HelmRelease/commerce/lago status: 'Failed']
- **Kustomization flux-system/estate-db-migrate** since 2026-09-14T16:45:11Z: Reconciliation in progress
- **Kustomization flux-system/gvisor-runtime** since 2026-09-14T16:35:10Z: dependency 'flux-system/nodesoftware-operator' is not ready
- **Kustomization flux-system/human-vault** since 2026-09-14T16:44:13Z: ClusterSecretStore/human-vault dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.clustersecretstore.external-secrets.io": failed to call webhook: Post "https://external-secrets-webhook.external-secrets.svc:443/validate-external-secrets-io-v1-clustersecretstore?timeout=5s": context deadline exceeded 
- **Kustomization flux-system/human-vault-bridge** since 2026-09-14T16:43:46Z: ExternalSecret/concierge/human-twilio dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-secrets.io": failed to call webhook: Post "https://external-secrets-webhook.external-secrets.svc:443/validate-external-secrets-io-v1-externalsecret?timeout=5s": context deadline exceeded 
- **Kustomization flux-system/mcp** since 2026-09-14T16:44:35Z: health check failed after 10m0.044050379s: timeout waiting for: [Deployment/mcp/estate-mcp status: 'InProgress']
- **Kustomization flux-system/nodesoftware-operator** since 2026-09-14T16:34:02Z: dependency 'flux-system/rbac-identity' is not ready
- **Kustomization flux-system/otto-golden** since 2026-09-14T16:45:10Z: Reconciliation in progress
- **Kustomization flux-system/rbac** since 2026-09-14T16:42:01Z: dependency 'flux-system/rbac-identity' is not ready
- **Kustomization flux-system/rbac-identity** since 2026-09-14T16:42:40Z: ExternalSecret/flux-system/bridge-identity dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-secrets.io": failed to call webhook: Post "https://external-secrets-webhook.external-secrets.svc:443/validate-external-secrets-io-v1-externalsecret?timeout=5s": context deadline exceeded 

## Every row

| Kind | Namespace | Name | State | Applied revision | Since | Message |
|---|---|---|---|---|---|---|
| HelmRelease | commerce | lago | Not ready | 1.28.0 | 2026-09-14T13:45:55Z | Helm install failed for release commerce/lago with chart lago@1.28.0: failed early due to stalled resources: [Deployment/commerce/lago-worker status: 'Failed'] |
| Kustomization | flux-system | commerce | Not ready | main@abea14d | 2026-09-14T16:44:23Z | health check failed after 83.651642ms: failed early due to stalled resources: [HelmRelease/commerce/lago status: 'Failed'] |
| Kustomization | flux-system | estate-db-migrate | Not ready | main@f80322a | 2026-09-14T16:45:11Z | Reconciliation in progress |
| Kustomization | flux-system | gvisor-runtime | Not ready | main@f80322a | 2026-09-14T16:35:10Z | dependency 'flux-system/nodesoftware-operator' is not ready |
| Kustomization | flux-system | human-vault | Not ready | main@f80322a | 2026-09-14T16:44:13Z | ClusterSecretStore/human-vault dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.clustersecretstore.external-secrets.io" |
| Kustomization | flux-system | human-vault-bridge | Not ready | main@f80322a | 2026-09-14T16:43:46Z | ExternalSecret/concierge/human-twilio dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-secrets. |
| Kustomization | flux-system | mcp | Not ready | main@6558812 | 2026-09-14T16:44:35Z | health check failed after 10m0.044050379s: timeout waiting for: [Deployment/mcp/estate-mcp status: 'InProgress'] |
| Kustomization | flux-system | nodesoftware-operator | Not ready | main@f80322a | 2026-09-14T16:34:02Z | dependency 'flux-system/rbac-identity' is not ready |
| Kustomization | flux-system | otto-golden | Not ready | main@f80322a | 2026-09-14T16:45:10Z | Reconciliation in progress |
| Kustomization | flux-system | rbac | Not ready | main@f80322a | 2026-09-14T16:42:01Z | dependency 'flux-system/rbac-identity' is not ready |
| Kustomization | flux-system | rbac-identity | Not ready | main@f80322a | 2026-09-14T16:42:40Z | ExternalSecret/flux-system/bridge-identity dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-sec |
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
| Kustomization | flux-system | agent-workforce | Ready | main@f80322a | 2026-09-14T16:44:34Z |  |
| Kustomization | flux-system | alerts | Ready | main@f80322a | 2026-09-14T16:44:47Z |  |
| Kustomization | flux-system | alerts-github | Ready | main@f80322a | 2026-09-14T16:43:53Z |  |
| Kustomization | flux-system | alerts-secret | Ready | main@f80322a | 2026-09-14T16:44:23Z |  |
| Kustomization | flux-system | autoscaler | Ready | main@f80322a | 2026-09-14T16:34:56Z |  |
| Kustomization | flux-system | backstage | Ready | main@f80322a | 2026-09-14T16:45:06Z |  |
| Kustomization | flux-system | backstage-namespace | Ready | main@f80322a | 2026-09-14T16:42:54Z |  |
| Kustomization | flux-system | calico | Ready | main@f80322a | 2026-09-14T16:42:41Z |  |
| Kustomization | flux-system | chaos | Ready | main@f80322a | 2026-09-14T16:44:51Z |  |
| Kustomization | flux-system | chaos-mesh | Ready | main@f80322a | 2026-09-14T16:44:04Z |  |
| Kustomization | flux-system | cluster-state | Ready | main@f80322a | 2026-09-14T16:44:45Z |  |
| Kustomization | flux-system | commerce-data | Ready | main@f80322a | 2026-09-14T16:43:57Z |  |
| Kustomization | flux-system | concierge | Ready | main@f80322a | 2026-09-14T16:44:02Z |  |
| Kustomization | flux-system | cross-node-drill | Ready | main@f80322a | 2026-09-14T16:42:35Z |  |
| Kustomization | flux-system | crossplane | Ready | main@f80322a | 2026-09-14T16:43:39Z |  |
| Kustomization | flux-system | crossplane-providerconfig | Ready | main@f80322a | 2026-09-14T16:43:13Z |  |
| Kustomization | flux-system | crossplane-providers | Ready | main@f80322a | 2026-09-14T16:43:55Z |  |
| Kustomization | flux-system | dagster | Ready | main@f80322a | 2026-09-14T16:44:33Z |  |
| Kustomization | flux-system | dns | Ready | main@f80322a | 2026-09-14T16:44:48Z |  |
| Kustomization | flux-system | drills | Ready | main@f80322a | 2026-09-14T16:44:52Z |  |
| Kustomization | flux-system | edge | Ready | main@f80322a | 2026-09-14T16:43:53Z |  |
| Kustomization | flux-system | estate-catalog | Ready | latest@sha256:c7d6047f10973294dd3de3b9ac | 2026-09-14T16:40:23Z |  |
| Kustomization | flux-system | estate-db | Ready | main@f80322a | 2026-09-14T16:43:31Z |  |
| Kustomization | flux-system | estate-db-operator | Ready | main@f80322a | 2026-09-14T16:42:14Z |  |
| Kustomization | flux-system | event-bus | Ready | main@f80322a | 2026-09-14T16:43:27Z |  |
| Kustomization | flux-system | external-secrets | Ready | main@f80322a | 2026-09-14T16:43:23Z |  |
| Kustomization | flux-system | feature-register | Ready | main@f80322a | 2026-09-14T16:42:48Z |  |
| Kustomization | flux-system | flux-system | Ready | main@f80322a | 2026-09-14T16:43:13Z |  |
| Kustomization | flux-system | flux-webhook | Ready | main@f80322a | 2026-09-14T16:44:19Z |  |
| Kustomization | flux-system | gateway-api-crds | Ready | v1.5.1@e7677b7 | 2026-09-14T16:42:46Z |  |
| Kustomization | flux-system | guacamole | Ready | main@f80322a | 2026-09-14T16:44:41Z |  |
| Kustomization | flux-system | healing | Ready | main@f80322a | 2026-09-14T16:45:04Z |  |
| Kustomization | flux-system | healing-analyzer | Ready | main@f80322a | 2026-09-14T16:35:25Z |  |
| Kustomization | flux-system | healing-k8sgpt | Ready | main@f80322a | 2026-09-14T16:35:03Z |  |
| Kustomization | flux-system | healthchecks | Ready | main@f80322a | 2026-09-14T16:44:42Z |  |
| Kustomization | flux-system | hermes-agent | Ready | main@f80322a | 2026-09-14T16:37:29Z |  |
| Kustomization | flux-system | hindsight | Ready | main@f80322a | 2026-09-14T16:44:55Z |  |
| Kustomization | flux-system | identity | Ready | main@f80322a | 2026-09-14T16:44:33Z |  |
| Kustomization | flux-system | image-automation | Ready | main@f80322a | 2026-09-14T16:43:59Z |  |
| Kustomization | flux-system | jit | Ready | main@f80322a | 2026-09-14T16:43:19Z |  |
| Kustomization | flux-system | keda | Ready | main@f80322a | 2026-09-14T16:43:59Z |  |
| Kustomization | flux-system | kyverno | Ready | main@f80322a | 2026-09-14T16:42:57Z |  |
| Kustomization | flux-system | llm | Ready | main@f80322a | 2026-09-14T16:44:09Z |  |
| Kustomization | flux-system | metrics-server | Ready | main@f80322a | 2026-09-14T16:42:50Z |  |
| Kustomization | flux-system | monitoring | Ready | main@f80322a | 2026-09-14T16:43:12Z |  |
| Kustomization | flux-system | monitoring-rules | Ready | main@f80322a | 2026-09-14T16:43:51Z |  |
| Kustomization | flux-system | notify | Ready | main@f80322a | 2026-09-14T16:44:34Z |  |
| Kustomization | flux-system | ns-fences | Ready | main@f80322a | 2026-09-14T16:44:11Z |  |
| Kustomization | flux-system | observability | Ready | main@f80322a | 2026-09-14T16:44:27Z |  |
| Kustomization | flux-system | observability-collector | Ready | main@f80322a | 2026-09-14T16:43:35Z |  |
| Kustomization | flux-system | otto-gateway | Ready | main@f80322a | 2026-09-14T16:45:07Z |  |
| Kustomization | flux-system | otto-golden-secret | Ready | main@f80322a | 2026-09-14T16:44:23Z |  |
| Kustomization | flux-system | priority-classes | Ready | main@f80322a | 2026-09-14T16:43:08Z |  |
| Kustomization | flux-system | prospector | Ready | main@7453d76 | 2026-09-14T16:42:02Z |  |
| Kustomization | flux-system | prospector-platform | Ready | main@f80322a | 2026-09-14T16:44:20Z |  |
| Kustomization | flux-system | rbac-floor | Ready | main@f80322a | 2026-09-14T16:42:20Z |  |
| Kustomization | flux-system | reloader | Ready | main@f80322a | 2026-09-14T16:43:52Z |  |
| Kustomization | flux-system | research-engine | Ready | main@f80322a | 2026-09-14T16:44:18Z |  |
| Kustomization | flux-system | robusta | Ready | main@f80322a | 2026-09-14T16:43:44Z |  |
| Kustomization | flux-system | router-events | Ready | main@f80322a | 2026-09-14T16:45:10Z |  |
| Kustomization | flux-system | sandbox-launch | Ready | main@f80322a | 2026-09-14T16:43:39Z |  |
| Kustomization | flux-system | sandbox-live | Ready | sandbox/launch@4830a6e | 2026-09-14T16:44:55Z |  |
| Kustomization | flux-system | scheduling | Ready | main@f80322a | 2026-09-14T16:44:18Z |  |
| Kustomization | flux-system | science | Ready | main@f80322a | 2026-09-14T16:44:41Z |  |
| Kustomization | flux-system | searxng | Ready | main@f80322a | 2026-09-14T16:42:47Z |  |
| Kustomization | flux-system | secret-store | Ready | main@f80322a | 2026-09-14T16:42:46Z |  |
| Kustomization | flux-system | spire | Ready | main@f80322a | 2026-09-14T16:43:54Z |  |
| Kustomization | flux-system | staging | Ready | main@f80322a | 2026-09-14T16:43:32Z |  |
| Kustomization | flux-system | tailscale | Ready | main@f80322a | 2026-09-14T16:44:25Z |  |
| Kustomization | flux-system | trivy | Ready | main@f80322a | 2026-09-14T16:42:19Z |  |
| Kustomization | flux-system | verification | Ready | main@f80322a | 2026-09-14T16:44:05Z |  |
| Kustomization | flux-system | weave-gitops | Ready | main@f80322a | 2026-09-14T16:44:54Z |  |
