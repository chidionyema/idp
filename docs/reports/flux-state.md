# Flux: what is applied

Read from the cluster receipt taken at 2026-09-14T20:00:21Z. Every Kustomization and HelmRelease, with the revision Flux last applied. **Suspended** is a switch somebody turned off on purpose (temporal, commerce, commerce-data, event-bus), not a defect; **Unknown** is a row Flux has never graded.

**116 objects: 70 ready, 44 not ready, 0 unknown, 2 suspended.**

## Not ready right now

- **HelmRelease commerce/lago** since 2026-09-14T19:51:16Z: Running 'install' action with timeout of 15m0s
- **Kustomization flux-system/agent-workforce** since 2026-09-14T19:57:09Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/alerts** since 2026-09-14T19:57:18Z: dependency 'flux-system/alerts-secret' is not ready
- **Kustomization flux-system/alerts-github** since 2026-09-14T19:57:21Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/alerts-secret** since 2026-09-14T19:57:10Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/autoscaler** since 2026-09-14T19:57:23Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/backstage** since 2026-09-14T19:57:23Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/chaos** since 2026-09-14T19:58:13Z: dependency 'flux-system/observability' is not ready
- **Kustomization flux-system/commerce** since 2026-09-14T19:51:15Z: Reconciliation in progress
- **Kustomization flux-system/commerce-data** since 2026-09-14T19:57:02Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/concierge** since 2026-09-14T19:56:11Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/dagster** since 2026-09-14T19:57:22Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/dns** since 2026-09-14T19:56:42Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/drills** since 2026-09-14T19:57:40Z: dependency 'flux-system/alerts-github' is not ready
- **Kustomization flux-system/estate-db** since 2026-09-14T19:56:17Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/estate-db-migrate** since 2026-09-14T19:57:10Z: dependency 'flux-system/estate-db' is not ready
- **Kustomization flux-system/flux-webhook** since 2026-09-14T19:56:23Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/guacamole** since 2026-09-14T19:57:13Z: dependency 'flux-system/identity' is not ready
- **Kustomization flux-system/healing-k8sgpt** since 2026-09-14T19:57:47Z: dependency 'flux-system/llm' is not ready
- **Kustomization flux-system/healthchecks** since 2026-09-14T19:57:10Z: dependency 'flux-system/identity' is not ready
- **Kustomization flux-system/hermes-agent** since 2026-09-14T19:57:19Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/hindsight** since 2026-09-14T19:57:57Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/human-vault** since 2026-09-14T19:57:17Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/human-vault-bridge** since 2026-09-14T19:57:30Z: dependency 'flux-system/human-vault' is not ready
- **Kustomization flux-system/identity** since 2026-09-14T19:56:34Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/image-automation** since 2026-09-14T19:56:13Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/llm** since 2026-09-14T19:57:15Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/mcp** since 2026-09-14T19:57:12Z: health check failed after 10m0.025617077s: timeout waiting for: [Deployment/mcp/estate-mcp status: 'InProgress']
- **Kustomization flux-system/monitoring** since 2026-09-14T19:56:52Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/monitoring-rules** since 2026-09-14T19:45:40Z: dependency 'flux-system/monitoring' is not ready
- **Kustomization flux-system/nodesoftware-operator** since 2026-09-14T19:56:43Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/notify** since 2026-09-14T19:56:57Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/observability** since 2026-09-14T19:57:44Z: dependency 'flux-system/estate-db-migrate' is not ready
- **Kustomization flux-system/otto-gateway** since 2026-09-14T19:57:28Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/otto-golden** since 2026-09-14T19:57:25Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/otto-golden-secret** since 2026-09-14T19:56:56Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/reloader** since 2026-09-14T19:57:04Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/research-engine** since 2026-09-14T19:57:44Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/robusta** since 2026-09-14T19:57:04Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/router-events** since 2026-09-14T19:57:24Z: dependency 'flux-system/llm' is not ready
- **Kustomization flux-system/science** since 2026-09-14T19:57:50Z: dependency 'flux-system/observability' is not ready
- **Kustomization flux-system/secret-store** since 2026-09-14T19:56:11Z: ClusterSecretStore/estate-vault dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.clustersecretstore.external-secrets.io": failed to call webhook: Post "https://external-secrets-webhook.external-secrets.svc:443/validate-external-secrets-io-v1-clustersecretstore?timeout=5s": context deadline exceeded 
- **Kustomization flux-system/tailscale** since 2026-09-14T19:56:59Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/verification** since 2026-09-14T19:56:47Z: dependency 'flux-system/secret-store' is not ready

## Every row

| Kind | Namespace | Name | State | Applied revision | Since | Message |
|---|---|---|---|---|---|---|
| HelmRelease | commerce | lago | Not ready | 1.28.0 | 2026-09-14T19:51:16Z | Running 'install' action with timeout of 15m0s |
| Kustomization | flux-system | agent-workforce | Not ready | main@ee608dd | 2026-09-14T19:57:09Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | alerts | Not ready | main@ee608dd | 2026-09-14T19:57:18Z | dependency 'flux-system/alerts-secret' is not ready |
| Kustomization | flux-system | alerts-github | Not ready | main@ee608dd | 2026-09-14T19:57:21Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | alerts-secret | Not ready | main@ee608dd | 2026-09-14T19:57:10Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | autoscaler | Not ready | main@ee608dd | 2026-09-14T19:57:23Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | backstage | Not ready | main@ee608dd | 2026-09-14T19:57:23Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | chaos | Not ready | main@e497116 | 2026-09-14T19:58:13Z | dependency 'flux-system/observability' is not ready |
| Kustomization | flux-system | commerce | Not ready | main@abea14d | 2026-09-14T19:51:15Z | Reconciliation in progress |
| Kustomization | flux-system | commerce-data | Not ready | main@ee608dd | 2026-09-14T19:57:02Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | concierge | Not ready | main@ee608dd | 2026-09-14T19:56:11Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | dagster | Not ready | main@ee608dd | 2026-09-14T19:57:22Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | dns | Not ready | main@ee608dd | 2026-09-14T19:56:42Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | drills | Not ready | main@ee608dd | 2026-09-14T19:57:40Z | dependency 'flux-system/alerts-github' is not ready |
| Kustomization | flux-system | estate-db | Not ready | main@ee608dd | 2026-09-14T19:56:17Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | estate-db-migrate | Not ready | main@ee608dd | 2026-09-14T19:57:10Z | dependency 'flux-system/estate-db' is not ready |
| Kustomization | flux-system | flux-webhook | Not ready | main@ee608dd | 2026-09-14T19:56:23Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | guacamole | Not ready | main@ee608dd | 2026-09-14T19:57:13Z | dependency 'flux-system/identity' is not ready |
| Kustomization | flux-system | healing-k8sgpt | Not ready | main@ee608dd | 2026-09-14T19:57:47Z | dependency 'flux-system/llm' is not ready |
| Kustomization | flux-system | healthchecks | Not ready | main@ee608dd | 2026-09-14T19:57:10Z | dependency 'flux-system/identity' is not ready |
| Kustomization | flux-system | hermes-agent | Not ready | main@ee608dd | 2026-09-14T19:57:19Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | hindsight | Not ready | main@ee608dd | 2026-09-14T19:57:57Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | human-vault | Not ready | main@ee608dd | 2026-09-14T19:57:17Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | human-vault-bridge | Not ready | main@ee608dd | 2026-09-14T19:57:30Z | dependency 'flux-system/human-vault' is not ready |
| Kustomization | flux-system | identity | Not ready | main@ee608dd | 2026-09-14T19:56:34Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | image-automation | Not ready | main@ee608dd | 2026-09-14T19:56:13Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | llm | Not ready | main@ee608dd | 2026-09-14T19:57:15Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | mcp | Not ready | main@6558812 | 2026-09-14T19:57:12Z | health check failed after 10m0.025617077s: timeout waiting for: [Deployment/mcp/estate-mcp status: 'InProgress'] |
| Kustomization | flux-system | monitoring | Not ready | main@e497116 | 2026-09-14T19:56:52Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | monitoring-rules | Not ready | main@e497116 | 2026-09-14T19:45:40Z | dependency 'flux-system/monitoring' is not ready |
| Kustomization | flux-system | nodesoftware-operator | Not ready | main@ee608dd | 2026-09-14T19:56:43Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | notify | Not ready | main@ee608dd | 2026-09-14T19:56:57Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | observability | Not ready | main@ee608dd | 2026-09-14T19:57:44Z | dependency 'flux-system/estate-db-migrate' is not ready |
| Kustomization | flux-system | otto-gateway | Not ready | main@e497116 | 2026-09-14T19:57:28Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | otto-golden | Not ready | main@e497116 | 2026-09-14T19:57:25Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | otto-golden-secret | Not ready | main@ee608dd | 2026-09-14T19:56:56Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | reloader | Not ready | main@ee608dd | 2026-09-14T19:57:04Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | research-engine | Not ready | main@e497116 | 2026-09-14T19:57:44Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | robusta | Not ready | main@ee608dd | 2026-09-14T19:57:04Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | router-events | Not ready | main@ee608dd | 2026-09-14T19:57:24Z | dependency 'flux-system/llm' is not ready |
| Kustomization | flux-system | science | Not ready | main@ee608dd | 2026-09-14T19:57:50Z | dependency 'flux-system/observability' is not ready |
| Kustomization | flux-system | secret-store | Not ready | main@ee608dd | 2026-09-14T19:56:11Z | ClusterSecretStore/estate-vault dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.clustersecretstore.external-secrets.io |
| Kustomization | flux-system | tailscale | Not ready | main@ee608dd | 2026-09-14T19:56:59Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | verification | Not ready | main@ee608dd | 2026-09-14T19:56:47Z | dependency 'flux-system/secret-store' is not ready |
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
| HelmRelease | observability-agent | k8s-infra | Ready | 0.17.0 | 2026-09-14T18:09:18Z |  |
| HelmRelease | reloader | reloader | Ready | 2.2.16 | 2026-09-06T19:33:25Z |  |
| HelmRelease | robusta | robusta | Ready | 0.48.0 | 2026-09-06T20:26:45Z |  |
| HelmRelease | spire-mgmt | spire | Ready | 0.30.1 | 2026-09-08T09:39:33Z |  |
| HelmRelease | spire-mgmt | spire-crds | Ready | 0.6.1 | 2026-09-06T20:26:47Z |  |
| HelmRelease | tailscale | tailscale-operator | Ready | 1.102.3 | 2026-09-06T19:33:35Z |  |
| HelmRelease | temporal | temporal | Ready | 1.6.0 | 2026-09-08T23:12:29Z |  |
| HelmRelease | trivy-system | trivy-operator | Ready | 0.36.0 | 2026-09-06T20:26:45Z |  |
| HelmRelease | weave-gitops | weave-gitops | Ready | 4.0.36 | 2026-09-06T20:26:45Z |  |
| Kustomization | flux-system | backstage-namespace | Ready | main@ee608dd | 2026-09-14T19:55:51Z |  |
| Kustomization | flux-system | calico | Ready | main@ee608dd | 2026-09-14T19:55:32Z |  |
| Kustomization | flux-system | chaos-mesh | Ready | main@ee608dd | 2026-09-14T19:56:13Z |  |
| Kustomization | flux-system | cluster-state | Ready | main@ee608dd | 2026-09-14T19:56:20Z |  |
| Kustomization | flux-system | cross-node-drill | Ready | main@ee608dd | 2026-09-14T19:56:02Z |  |
| Kustomization | flux-system | crossplane | Ready | main@ee608dd | 2026-09-14T19:56:18Z |  |
| Kustomization | flux-system | crossplane-providerconfig | Ready | main@ee608dd | 2026-09-14T19:57:17Z |  |
| Kustomization | flux-system | crossplane-providers | Ready | main@ee608dd | 2026-09-14T19:57:11Z |  |
| Kustomization | flux-system | edge | Ready | main@ee608dd | 2026-09-14T19:55:55Z |  |
| Kustomization | flux-system | estate-catalog | Ready | latest@sha256:c7d6047f10973294dd3de3b9ac | 2026-09-14T19:51:41Z |  |
| Kustomization | flux-system | estate-db-operator | Ready | main@ee608dd | 2026-09-14T19:56:26Z |  |
| Kustomization | flux-system | event-bus | Ready | main@ee608dd | 2026-09-14T19:56:10Z |  |
| Kustomization | flux-system | external-secrets | Ready | main@ee608dd | 2026-09-14T19:56:43Z |  |
| Kustomization | flux-system | feature-register | Ready | main@ee608dd | 2026-09-14T19:55:53Z |  |
| Kustomization | flux-system | flux-system | Ready | main@ee608dd | 2026-09-14T19:56:25Z |  |
| Kustomization | flux-system | gateway-api-crds | Ready | v1.5.1@e7677b7 | 2026-09-14T19:55:57Z |  |
| Kustomization | flux-system | gvisor-runtime | Ready | main@ee608dd | 2026-09-14T19:56:29Z |  |
| Kustomization | flux-system | healing | Ready | main@ee608dd | 2026-09-14T19:56:49Z |  |
| Kustomization | flux-system | healing-analyzer | Ready | main@ee608dd | 2026-09-14T19:57:22Z |  |
| Kustomization | flux-system | jit | Ready | main@ee608dd | 2026-09-14T19:56:05Z |  |
| Kustomization | flux-system | keda | Ready | main@ee608dd | 2026-09-14T19:56:59Z |  |
| Kustomization | flux-system | kyverno | Ready | main@ee608dd | 2026-09-14T19:55:24Z |  |
| Kustomization | flux-system | metrics-server | Ready | main@ee608dd | 2026-09-14T19:56:20Z |  |
| Kustomization | flux-system | ns-fences | Ready | main@ee608dd | 2026-09-14T19:56:47Z |  |
| Kustomization | flux-system | observability-collector | Ready | main@ee608dd | 2026-09-14T19:57:02Z |  |
| Kustomization | flux-system | priority-classes | Ready | main@ee608dd | 2026-09-14T19:55:41Z |  |
| Kustomization | flux-system | prospector | Ready | main@7453d76 | 2026-09-14T19:57:53Z |  |
| Kustomization | flux-system | prospector-platform | Ready | main@ee608dd | 2026-09-14T19:57:41Z |  |
| Kustomization | flux-system | rbac | Ready | main@ee608dd | 2026-09-14T19:55:41Z |  |
| Kustomization | flux-system | rbac-floor | Ready | main@ee608dd | 2026-09-14T19:56:25Z |  |
| Kustomization | flux-system | rbac-identity | Ready | main@ee608dd | 2026-09-14T19:55:56Z |  |
| Kustomization | flux-system | sandbox-launch | Ready | main@ee608dd | 2026-09-14T19:56:03Z |  |
| Kustomization | flux-system | sandbox-live | Ready | sandbox/launch@4830a6e | 2026-09-14T19:59:26Z |  |
| Kustomization | flux-system | scheduling | Ready | main@ee608dd | 2026-09-14T19:56:42Z |  |
| Kustomization | flux-system | searxng | Ready | main@ee608dd | 2026-09-14T19:56:19Z |  |
| Kustomization | flux-system | spire | Ready | main@ee608dd | 2026-09-14T19:57:05Z |  |
| Kustomization | flux-system | staging | Ready | main@ee608dd | 2026-09-14T19:56:23Z |  |
| Kustomization | flux-system | trivy | Ready | main@ee608dd | 2026-09-14T19:55:54Z |  |
| Kustomization | flux-system | weave-gitops | Ready | main@ee608dd | 2026-09-14T19:56:30Z |  |
