# Flux: what is applied

Read from the cluster receipt taken at 2026-09-14T17:30:28Z. Every Kustomization and HelmRelease, with the revision Flux last applied. **Suspended** is a switch somebody turned off on purpose (temporal, commerce, commerce-data, event-bus), not a defect; **Unknown** is a row Flux has never graded.

**116 objects: 66 ready, 48 not ready, 0 unknown, 2 suspended.**

## Not ready right now

- **HelmRelease commerce/lago** since 2026-09-14T13:45:55Z: Helm install failed for release commerce/lago with chart lago@1.28.0: failed early due to stalled resources: [Deployment/commerce/lago-worker status: 'Failed']
- **Kustomization flux-system/agent-workforce** since 2026-09-14T17:04:37Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/alerts** since 2026-09-14T17:14:17Z: dependency 'flux-system/alerts-secret' is not ready
- **Kustomization flux-system/alerts-github** since 2026-09-14T17:04:03Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/alerts-secret** since 2026-09-14T17:04:49Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/autoscaler** since 2026-09-14T17:04:46Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/backstage** since 2026-09-14T17:13:21Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/chaos** since 2026-09-14T17:05:00Z: dependency 'flux-system/observability' is not ready
- **Kustomization flux-system/commerce** since 2026-09-14T16:54:23Z: dependency 'flux-system/commerce-data' is not ready
- **Kustomization flux-system/commerce-data** since 2026-09-14T17:03:23Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/concierge** since 2026-09-14T17:04:05Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/dagster** since 2026-09-14T17:05:02Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/dns** since 2026-09-14T17:24:26Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/drills** since 2026-09-14T17:04:55Z: dependency 'flux-system/alerts-github' is not ready
- **Kustomization flux-system/estate-db** since 2026-09-14T17:23:35Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/estate-db-migrate** since 2026-09-14T16:55:42Z: dependency 'flux-system/estate-db' is not ready
- **Kustomization flux-system/flux-webhook** since 2026-09-14T17:04:47Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/guacamole** since 2026-09-14T17:05:17Z: dependency 'flux-system/identity' is not ready
- **Kustomization flux-system/gvisor-runtime** since 2026-09-14T16:35:10Z: dependency 'flux-system/nodesoftware-operator' is not ready
- **Kustomization flux-system/healing-analyzer** since 2026-09-14T17:05:15Z: dependency 'flux-system/healing-k8sgpt' is not ready
- **Kustomization flux-system/healing-k8sgpt** since 2026-09-14T17:05:07Z: dependency 'flux-system/llm' is not ready
- **Kustomization flux-system/healthchecks** since 2026-09-14T17:05:25Z: dependency 'flux-system/identity' is not ready
- **Kustomization flux-system/hermes-agent** since 2026-09-14T17:07:16Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/hindsight** since 2026-09-14T17:04:59Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/human-vault** since 2026-09-14T17:04:26Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/human-vault-bridge** since 2026-09-14T17:13:55Z: dependency 'flux-system/human-vault' is not ready
- **Kustomization flux-system/identity** since 2026-09-14T17:24:27Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/image-automation** since 2026-09-14T17:04:02Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/jit** since 2026-09-14T17:23:12Z: ExternalSecret/jit/jit-broker dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-secrets.io": failed to call webhook: Post "https://external-secrets-webhook.external-secrets.svc:443/validate-external-secrets-io-v1-externalsecret?timeout=5s": context deadline exceeded 
- **Kustomization flux-system/llm** since 2026-09-14T17:04:39Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/mcp** since 2026-09-14T17:15:37Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/monitoring** since 2026-09-14T17:24:27Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/monitoring-rules** since 2026-09-14T17:03:57Z: dependency 'flux-system/monitoring' is not ready
- **Kustomization flux-system/nodesoftware-operator** since 2026-09-14T17:03:38Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/notify** since 2026-09-14T17:04:34Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/observability** since 2026-09-14T17:04:55Z: dependency 'flux-system/estate-db-migrate' is not ready
- **Kustomization flux-system/otto-gateway** since 2026-09-14T17:05:16Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/otto-golden** since 2026-09-14T17:05:00Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/otto-golden-secret** since 2026-09-14T17:05:24Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/reloader** since 2026-09-14T17:04:04Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/research-engine** since 2026-09-14T17:03:08Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/robusta** since 2026-09-14T17:04:17Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/router-events** since 2026-09-14T17:05:17Z: dependency 'flux-system/llm' is not ready
- **Kustomization flux-system/science** since 2026-09-14T17:14:05Z: dependency 'flux-system/observability' is not ready
- **Kustomization flux-system/secret-store** since 2026-09-14T17:23:26Z: ClusterSecretStore/estate-vault dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.clustersecretstore.external-secrets.io": failed to call webhook: Post "https://external-secrets-webhook.external-secrets.svc:443/validate-external-secrets-io-v1-clustersecretstore?timeout=5s": context deadline exceeded 
- **Kustomization flux-system/tailscale** since 2026-09-14T17:04:02Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/verification** since 2026-09-14T17:24:25Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/weave-gitops** since 2026-09-14T17:14:50Z: dependency 'flux-system/identity' is not ready

## Every row

| Kind | Namespace | Name | State | Applied revision | Since | Message |
|---|---|---|---|---|---|---|
| HelmRelease | commerce | lago | Not ready | 1.28.0 | 2026-09-14T13:45:55Z | Helm install failed for release commerce/lago with chart lago@1.28.0: failed early due to stalled resources: [Deployment/commerce/lago-worker status: 'Failed'] |
| Kustomization | flux-system | agent-workforce | Not ready | main@f80322a | 2026-09-14T17:04:37Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | alerts | Not ready | main@f80322a | 2026-09-14T17:14:17Z | dependency 'flux-system/alerts-secret' is not ready |
| Kustomization | flux-system | alerts-github | Not ready | main@f80322a | 2026-09-14T17:04:03Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | alerts-secret | Not ready | main@f80322a | 2026-09-14T17:04:49Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | autoscaler | Not ready | main@f80322a | 2026-09-14T17:04:46Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | backstage | Not ready | main@f80322a | 2026-09-14T17:13:21Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | chaos | Not ready | main@f80322a | 2026-09-14T17:05:00Z | dependency 'flux-system/observability' is not ready |
| Kustomization | flux-system | commerce | Not ready | main@abea14d | 2026-09-14T16:54:23Z | dependency 'flux-system/commerce-data' is not ready |
| Kustomization | flux-system | commerce-data | Not ready | main@f80322a | 2026-09-14T17:03:23Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | concierge | Not ready | main@f80322a | 2026-09-14T17:04:05Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | dagster | Not ready | main@f80322a | 2026-09-14T17:05:02Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | dns | Not ready | main@f80322a | 2026-09-14T17:24:26Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | drills | Not ready | main@f80322a | 2026-09-14T17:04:55Z | dependency 'flux-system/alerts-github' is not ready |
| Kustomization | flux-system | estate-db | Not ready | main@f80322a | 2026-09-14T17:23:35Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | estate-db-migrate | Not ready | main@f80322a | 2026-09-14T16:55:42Z | dependency 'flux-system/estate-db' is not ready |
| Kustomization | flux-system | flux-webhook | Not ready | main@f80322a | 2026-09-14T17:04:47Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | guacamole | Not ready | main@f80322a | 2026-09-14T17:05:17Z | dependency 'flux-system/identity' is not ready |
| Kustomization | flux-system | gvisor-runtime | Not ready | main@f80322a | 2026-09-14T16:35:10Z | dependency 'flux-system/nodesoftware-operator' is not ready |
| Kustomization | flux-system | healing-analyzer | Not ready | main@f80322a | 2026-09-14T17:05:15Z | dependency 'flux-system/healing-k8sgpt' is not ready |
| Kustomization | flux-system | healing-k8sgpt | Not ready | main@f80322a | 2026-09-14T17:05:07Z | dependency 'flux-system/llm' is not ready |
| Kustomization | flux-system | healthchecks | Not ready | main@f80322a | 2026-09-14T17:05:25Z | dependency 'flux-system/identity' is not ready |
| Kustomization | flux-system | hermes-agent | Not ready | main@f80322a | 2026-09-14T17:07:16Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | hindsight | Not ready | main@f80322a | 2026-09-14T17:04:59Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | human-vault | Not ready | main@f80322a | 2026-09-14T17:04:26Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | human-vault-bridge | Not ready | main@f80322a | 2026-09-14T17:13:55Z | dependency 'flux-system/human-vault' is not ready |
| Kustomization | flux-system | identity | Not ready | main@f80322a | 2026-09-14T17:24:27Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | image-automation | Not ready | main@f80322a | 2026-09-14T17:04:02Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | jit | Not ready | main@f80322a | 2026-09-14T17:23:12Z | ExternalSecret/jit/jit-broker dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-secrets.io": fai |
| Kustomization | flux-system | llm | Not ready | main@f80322a | 2026-09-14T17:04:39Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | mcp | Not ready | main@6558812 | 2026-09-14T17:15:37Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | monitoring | Not ready | main@f80322a | 2026-09-14T17:24:27Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | monitoring-rules | Not ready | main@f80322a | 2026-09-14T17:03:57Z | dependency 'flux-system/monitoring' is not ready |
| Kustomization | flux-system | nodesoftware-operator | Not ready | main@f80322a | 2026-09-14T17:03:38Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | notify | Not ready | main@f80322a | 2026-09-14T17:04:34Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | observability | Not ready | main@f80322a | 2026-09-14T17:04:55Z | dependency 'flux-system/estate-db-migrate' is not ready |
| Kustomization | flux-system | otto-gateway | Not ready | main@f80322a | 2026-09-14T17:05:16Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | otto-golden | Not ready | main@f80322a | 2026-09-14T17:05:00Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | otto-golden-secret | Not ready | main@f80322a | 2026-09-14T17:05:24Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | reloader | Not ready | main@f80322a | 2026-09-14T17:04:04Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | research-engine | Not ready | main@f80322a | 2026-09-14T17:03:08Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | robusta | Not ready | main@f80322a | 2026-09-14T17:04:17Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | router-events | Not ready | main@f80322a | 2026-09-14T17:05:17Z | dependency 'flux-system/llm' is not ready |
| Kustomization | flux-system | science | Not ready | main@f80322a | 2026-09-14T17:14:05Z | dependency 'flux-system/observability' is not ready |
| Kustomization | flux-system | secret-store | Not ready | main@f80322a | 2026-09-14T17:23:26Z | ClusterSecretStore/estate-vault dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.clustersecretstore.external-secrets.io |
| Kustomization | flux-system | tailscale | Not ready | main@f80322a | 2026-09-14T17:04:02Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | verification | Not ready | main@f80322a | 2026-09-14T17:24:25Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | weave-gitops | Not ready | main@f80322a | 2026-09-14T17:14:50Z | dependency 'flux-system/identity' is not ready |
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
| Kustomization | flux-system | backstage-namespace | Ready | main@f80322a | 2026-09-14T17:23:01Z |  |
| Kustomization | flux-system | calico | Ready | main@f80322a | 2026-09-14T17:22:10Z |  |
| Kustomization | flux-system | chaos-mesh | Ready | main@f80322a | 2026-09-14T17:24:17Z |  |
| Kustomization | flux-system | cluster-state | Ready | main@f80322a | 2026-09-14T17:24:59Z |  |
| Kustomization | flux-system | cross-node-drill | Ready | main@f80322a | 2026-09-14T17:22:12Z |  |
| Kustomization | flux-system | crossplane | Ready | main@f80322a | 2026-09-14T17:23:38Z |  |
| Kustomization | flux-system | crossplane-providerconfig | Ready | main@f80322a | 2026-09-14T17:22:54Z |  |
| Kustomization | flux-system | crossplane-providers | Ready | main@f80322a | 2026-09-14T17:24:10Z |  |
| Kustomization | flux-system | edge | Ready | main@f80322a | 2026-09-14T17:24:00Z |  |
| Kustomization | flux-system | estate-catalog | Ready | latest@sha256:c7d6047f10973294dd3de3b9ac | 2026-09-14T17:21:13Z |  |
| Kustomization | flux-system | estate-db-operator | Ready | main@f80322a | 2026-09-14T17:23:06Z |  |
| Kustomization | flux-system | event-bus | Ready | main@f80322a | 2026-09-14T17:24:17Z |  |
| Kustomization | flux-system | external-secrets | Ready | main@f80322a | 2026-09-14T17:23:56Z |  |
| Kustomization | flux-system | feature-register | Ready | main@f80322a | 2026-09-14T17:22:57Z |  |
| Kustomization | flux-system | flux-system | Ready | main@f80322a | 2026-09-14T17:22:28Z |  |
| Kustomization | flux-system | gateway-api-crds | Ready | v1.5.1@e7677b7 | 2026-09-14T17:23:42Z |  |
| Kustomization | flux-system | healing | Ready | main@f80322a | 2026-09-14T17:26:11Z |  |
| Kustomization | flux-system | keda | Ready | main@f80322a | 2026-09-14T17:24:47Z |  |
| Kustomization | flux-system | kyverno | Ready | main@f80322a | 2026-09-14T17:21:45Z |  |
| Kustomization | flux-system | metrics-server | Ready | main@f80322a | 2026-09-14T17:22:57Z |  |
| Kustomization | flux-system | ns-fences | Ready | main@f80322a | 2026-09-14T17:25:41Z |  |
| Kustomization | flux-system | observability-collector | Ready | main@f80322a | 2026-09-14T17:24:01Z |  |
| Kustomization | flux-system | priority-classes | Ready | main@f80322a | 2026-09-14T17:22:54Z |  |
| Kustomization | flux-system | prospector | Ready | main@7453d76 | 2026-09-14T17:22:34Z |  |
| Kustomization | flux-system | prospector-platform | Ready | main@f80322a | 2026-09-14T17:26:07Z |  |
| Kustomization | flux-system | rbac | Ready | main@f80322a | 2026-09-14T17:23:08Z |  |
| Kustomization | flux-system | rbac-floor | Ready | main@f80322a | 2026-09-14T17:22:14Z |  |
| Kustomization | flux-system | rbac-identity | Ready | main@f80322a | 2026-09-14T17:23:00Z |  |
| Kustomization | flux-system | sandbox-launch | Ready | main@f80322a | 2026-09-14T17:25:10Z |  |
| Kustomization | flux-system | sandbox-live | Ready | sandbox/launch@4830a6e | 2026-09-14T17:29:24Z |  |
| Kustomization | flux-system | scheduling | Ready | main@f80322a | 2026-09-14T17:25:16Z |  |
| Kustomization | flux-system | searxng | Ready | main@f80322a | 2026-09-14T17:22:47Z |  |
| Kustomization | flux-system | spire | Ready | main@f80322a | 2026-09-14T17:23:16Z |  |
| Kustomization | flux-system | staging | Ready | main@f80322a | 2026-09-14T17:23:06Z |  |
| Kustomization | flux-system | trivy | Ready | main@f80322a | 2026-09-14T17:21:32Z |  |
