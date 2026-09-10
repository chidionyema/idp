# Flux: what is applied

Read from the cluster receipt taken at 2026-09-10T11:00:21Z. Every Kustomization and HelmRelease, with the revision Flux last applied. **Suspended** is a switch somebody turned off on purpose (temporal, commerce, commerce-data, event-bus), not a defect; **Unknown** is a row Flux has never graded.

**115 objects: 62 ready, 51 not ready, 0 unknown, 2 suspended.**

## Not ready right now

- **HelmRelease commerce/lago** since 2026-09-10T10:55:54Z: Running 'install' action with timeout of 15m0s
- **Kustomization flux-system/agent-workforce** since 2026-09-10T11:00:13Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/alerts** since 2026-09-10T11:00:12Z: dependency 'flux-system/alerts-secret' is not ready
- **Kustomization flux-system/alerts-github** since 2026-09-10T10:59:35Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/alerts-secret** since 2026-09-10T10:59:35Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/autoscaler** since 2026-09-10T10:59:36Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/backstage** since 2026-09-10T11:00:13Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/chaos** since 2026-09-10T11:00:13Z: dependency 'flux-system/observability' is not ready
- **Kustomization flux-system/cluster-state** since 2026-09-10T10:59:58Z: dependency 'flux-system/external-secrets' is not ready
- **Kustomization flux-system/commerce** since 2026-09-10T10:52:28Z: Reconciliation in progress
- **Kustomization flux-system/commerce-data** since 2026-09-10T10:59:31Z: dependency 'flux-system/external-secrets' is not ready
- **Kustomization flux-system/crossplane-providerconfig** since 2026-09-10T10:59:35Z: dependency 'flux-system/crossplane-providers' is not ready
- **Kustomization flux-system/crossplane-providers** since 2026-09-10T10:59:54Z: dependency 'flux-system/crossplane' is not ready
- **Kustomization flux-system/cyrus** since 2026-09-10T11:00:13Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/dagster** since 2026-09-10T11:00:12Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/dns** since 2026-09-10T11:00:12Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/drills** since 2026-09-10T10:59:36Z: dependency 'flux-system/alerts-github' is not ready
- **Kustomization flux-system/estate-db** since 2026-09-10T10:59:35Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/estate-db-migrate** since 2026-09-10T10:59:35Z: dependency 'flux-system/estate-db' is not ready
- **Kustomization flux-system/flux-webhook** since 2026-09-10T10:59:58Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/guacamole** since 2026-09-10T10:59:36Z: dependency 'flux-system/identity' is not ready
- **Kustomization flux-system/gvisor-runtime** since 2026-09-10T11:00:10Z: dependency 'flux-system/nodesoftware-operator' is not ready
- **Kustomization flux-system/healing-analyzer** since 2026-09-10T10:59:36Z: dependency 'flux-system/healing-k8sgpt' is not ready
- **Kustomization flux-system/healing-k8sgpt** since 2026-09-10T11:00:11Z: dependency 'flux-system/llm' is not ready
- **Kustomization flux-system/healthchecks** since 2026-09-10T11:00:12Z: dependency 'flux-system/identity' is not ready
- **Kustomization flux-system/hermes-agent** since 2026-09-10T11:00:11Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/hindsight** since 2026-09-10T10:59:36Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/human-vault** since 2026-09-10T11:00:12Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/human-vault-bridge** since 2026-09-10T10:59:36Z: dependency 'flux-system/human-vault' is not ready
- **Kustomization flux-system/identity** since 2026-09-10T11:00:13Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/image-automation** since 2026-09-10T10:59:31Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/llm** since 2026-09-10T11:00:11Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/mcp** since 2026-09-10T11:00:13Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/monitoring** since 2026-09-10T11:00:13Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/monitoring-rules** since 2026-09-10T11:00:10Z: dependency 'flux-system/monitoring' is not ready
- **Kustomization flux-system/nodesoftware-operator** since 2026-09-10T11:00:11Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/notify** since 2026-09-10T11:00:10Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/observability** since 2026-09-10T11:00:12Z: dependency 'flux-system/estate-db-migrate' is not ready
- **Kustomization flux-system/otto-gateway** since 2026-09-10T11:00:12Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/otto-golden** since 2026-09-10T11:00:13Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/otto-golden-secret** since 2026-09-10T10:59:35Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/prospector** since 2026-09-10T10:59:36Z: dependency 'flux-system/prospector-platform' is not ready
- **Kustomization flux-system/prospector-platform** since 2026-09-10T11:00:06Z: dependency 'flux-system/external-secrets' is not ready
- **Kustomization flux-system/reloader** since 2026-09-10T10:59:35Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/research-engine** since 2026-09-10T10:59:35Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/robusta** since 2026-09-10T10:59:34Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/science** since 2026-09-10T11:00:10Z: dependency 'flux-system/observability' is not ready
- **Kustomization flux-system/secret-store** since 2026-09-10T10:59:31Z: dependency 'flux-system/external-secrets' is not ready
- **Kustomization flux-system/tailscale** since 2026-09-10T10:59:36Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/verification** since 2026-09-10T11:00:11Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/weave-gitops** since 2026-09-10T10:59:36Z: dependency 'flux-system/identity' is not ready

## Every row

| Kind | Namespace | Name | State | Applied revision | Since | Message |
|---|---|---|---|---|---|---|
| HelmRelease | commerce | lago | Not ready | 1.28.0 | 2026-09-10T10:55:54Z | Running 'install' action with timeout of 15m0s |
| Kustomization | flux-system | agent-workforce | Not ready | main@d6a9ed6 | 2026-09-10T11:00:13Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | alerts | Not ready | main@d6a9ed6 | 2026-09-10T11:00:12Z | dependency 'flux-system/alerts-secret' is not ready |
| Kustomization | flux-system | alerts-github | Not ready | main@d6a9ed6 | 2026-09-10T10:59:35Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | alerts-secret | Not ready | main@d6a9ed6 | 2026-09-10T10:59:35Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | autoscaler | Not ready | main@d6a9ed6 | 2026-09-10T10:59:36Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | backstage | Not ready | main@d6a9ed6 | 2026-09-10T11:00:13Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | chaos | Not ready | main@d6a9ed6 | 2026-09-10T11:00:13Z | dependency 'flux-system/observability' is not ready |
| Kustomization | flux-system | cluster-state | Not ready | main@d6a9ed6 | 2026-09-10T10:59:58Z | dependency 'flux-system/external-secrets' is not ready |
| Kustomization | flux-system | commerce | Not ready | main@d6a9ed6 | 2026-09-10T10:52:28Z | Reconciliation in progress |
| Kustomization | flux-system | commerce-data | Not ready | main@d6a9ed6 | 2026-09-10T10:59:31Z | dependency 'flux-system/external-secrets' is not ready |
| Kustomization | flux-system | crossplane-providerconfig | Not ready | main@d6a9ed6 | 2026-09-10T10:59:35Z | dependency 'flux-system/crossplane-providers' is not ready |
| Kustomization | flux-system | crossplane-providers | Not ready | main@d6a9ed6 | 2026-09-10T10:59:54Z | dependency 'flux-system/crossplane' is not ready |
| Kustomization | flux-system | cyrus | Not ready | main@17a5ceb | 2026-09-10T11:00:13Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | dagster | Not ready | main@d6a9ed6 | 2026-09-10T11:00:12Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | dns | Not ready | main@d6a9ed6 | 2026-09-10T11:00:12Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | drills | Not ready | main@d6a9ed6 | 2026-09-10T10:59:36Z | dependency 'flux-system/alerts-github' is not ready |
| Kustomization | flux-system | estate-db | Not ready | main@d6a9ed6 | 2026-09-10T10:59:35Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | estate-db-migrate | Not ready | main@d6a9ed6 | 2026-09-10T10:59:35Z | dependency 'flux-system/estate-db' is not ready |
| Kustomization | flux-system | flux-webhook | Not ready | main@d6a9ed6 | 2026-09-10T10:59:58Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | guacamole | Not ready | main@5b6aeea | 2026-09-10T10:59:36Z | dependency 'flux-system/identity' is not ready |
| Kustomization | flux-system | gvisor-runtime | Not ready | main@d6a9ed6 | 2026-09-10T11:00:10Z | dependency 'flux-system/nodesoftware-operator' is not ready |
| Kustomization | flux-system | healing-analyzer | Not ready | main@d6a9ed6 | 2026-09-10T10:59:36Z | dependency 'flux-system/healing-k8sgpt' is not ready |
| Kustomization | flux-system | healing-k8sgpt | Not ready | main@d6a9ed6 | 2026-09-10T11:00:11Z | dependency 'flux-system/llm' is not ready |
| Kustomization | flux-system | healthchecks | Not ready | main@d6a9ed6 | 2026-09-10T11:00:12Z | dependency 'flux-system/identity' is not ready |
| Kustomization | flux-system | hermes-agent | Not ready | main@d6a9ed6 | 2026-09-10T11:00:11Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | hindsight | Not ready | main@d6a9ed6 | 2026-09-10T10:59:36Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | human-vault | Not ready | main@d6a9ed6 | 2026-09-10T11:00:12Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | human-vault-bridge | Not ready | main@d6a9ed6 | 2026-09-10T10:59:36Z | dependency 'flux-system/human-vault' is not ready |
| Kustomization | flux-system | identity | Not ready | main@d6a9ed6 | 2026-09-10T11:00:13Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | image-automation | Not ready | main@d6a9ed6 | 2026-09-10T10:59:31Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | llm | Not ready | main@d6a9ed6 | 2026-09-10T11:00:11Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | mcp | Not ready | main@d6a9ed6 | 2026-09-10T11:00:13Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | monitoring | Not ready | main@d6a9ed6 | 2026-09-10T11:00:13Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | monitoring-rules | Not ready | main@d6a9ed6 | 2026-09-10T11:00:10Z | dependency 'flux-system/monitoring' is not ready |
| Kustomization | flux-system | nodesoftware-operator | Not ready | main@d6a9ed6 | 2026-09-10T11:00:11Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | notify | Not ready | main@d6a9ed6 | 2026-09-10T11:00:10Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | observability | Not ready | main@d6a9ed6 | 2026-09-10T11:00:12Z | dependency 'flux-system/estate-db-migrate' is not ready |
| Kustomization | flux-system | otto-gateway | Not ready | main@d6a9ed6 | 2026-09-10T11:00:12Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | otto-golden | Not ready | main@d6a9ed6 | 2026-09-10T11:00:13Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | otto-golden-secret | Not ready | main@d6a9ed6 | 2026-09-10T10:59:35Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | prospector | Not ready | main@7453d76 | 2026-09-10T10:59:36Z | dependency 'flux-system/prospector-platform' is not ready |
| Kustomization | flux-system | prospector-platform | Not ready | main@d6a9ed6 | 2026-09-10T11:00:06Z | dependency 'flux-system/external-secrets' is not ready |
| Kustomization | flux-system | reloader | Not ready | main@d6a9ed6 | 2026-09-10T10:59:35Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | research-engine | Not ready | main@d6a9ed6 | 2026-09-10T10:59:35Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | robusta | Not ready | main@d6a9ed6 | 2026-09-10T10:59:34Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | science | Not ready | main@d6a9ed6 | 2026-09-10T11:00:10Z | dependency 'flux-system/observability' is not ready |
| Kustomization | flux-system | secret-store | Not ready | main@d6a9ed6 | 2026-09-10T10:59:31Z | dependency 'flux-system/external-secrets' is not ready |
| Kustomization | flux-system | tailscale | Not ready | main@d3ab8a2 | 2026-09-10T10:59:36Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | verification | Not ready | main@d6a9ed6 | 2026-09-10T11:00:11Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | weave-gitops | Not ready | main@d6a9ed6 | 2026-09-10T10:59:36Z | dependency 'flux-system/identity' is not ready |
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
| Kustomization | flux-system | backstage-namespace | Ready | main@9a46d93 | 2026-09-10T10:58:57Z |  |
| Kustomization | flux-system | calico | Ready | main@9a46d93 | 2026-09-10T10:59:29Z |  |
| Kustomization | flux-system | chaos-mesh | Ready | main@9a46d93 | 2026-09-10T10:59:59Z |  |
| Kustomization | flux-system | cross-node-drill | Ready | main@9a46d93 | 2026-09-10T10:59:15Z |  |
| Kustomization | flux-system | crossplane | Ready | main@9a46d93 | 2026-09-10T11:00:10Z |  |
| Kustomization | flux-system | edge | Ready | main@9a46d93 | 2026-09-10T10:59:41Z |  |
| Kustomization | flux-system | estate-catalog | Ready | latest@sha256:8ab0d9286bc2769859d864f54d | 2026-09-10T10:58:24Z |  |
| Kustomization | flux-system | estate-db-operator | Ready | main@9a46d93 | 2026-09-10T10:59:18Z |  |
| Kustomization | flux-system | event-bus | Ready | main@9a46d93 | 2026-09-10T10:59:31Z |  |
| Kustomization | flux-system | external-secrets | Ready | main@9a46d93 | 2026-09-10T11:00:09Z |  |
| Kustomization | flux-system | feature-register | Ready | main@9a46d93 | 2026-09-10T10:59:32Z |  |
| Kustomization | flux-system | flux-system | Ready | main@9a46d93 | 2026-09-10T10:59:27Z |  |
| Kustomization | flux-system | gateway-api-crds | Ready | v1.5.1@e7677b7 | 2026-09-10T10:59:24Z |  |
| Kustomization | flux-system | healing | Ready | main@9a46d93 | 2026-09-10T11:00:06Z |  |
| Kustomization | flux-system | jit | Ready | main@9a46d93 | 2026-09-10T10:59:36Z |  |
| Kustomization | flux-system | keda | Ready | main@9a46d93 | 2026-09-10T11:00:13Z |  |
| Kustomization | flux-system | kyverno | Ready | main@9a46d93 | 2026-09-10T10:59:17Z |  |
| Kustomization | flux-system | metrics-server | Ready | main@9a46d93 | 2026-09-10T11:00:12Z |  |
| Kustomization | flux-system | ns-fences | Ready | main@9a46d93 | 2026-09-10T10:59:13Z |  |
| Kustomization | flux-system | observability-collector | Ready | main@9a46d93 | 2026-09-10T11:00:05Z |  |
| Kustomization | flux-system | priority-classes | Ready | main@9a46d93 | 2026-09-10T10:59:19Z |  |
| Kustomization | flux-system | rbac | Ready | main@9a46d93 | 2026-09-10T10:59:30Z |  |
| Kustomization | flux-system | rbac-floor | Ready | main@9a46d93 | 2026-09-10T10:59:20Z |  |
| Kustomization | flux-system | rbac-identity | Ready | main@9a46d93 | 2026-09-10T10:59:21Z |  |
| Kustomization | flux-system | sandbox-launch | Ready | main@9a46d93 | 2026-09-10T11:00:10Z |  |
| Kustomization | flux-system | sandbox-live | Ready | sandbox/launch@5844e79 | 2026-09-10T10:59:38Z |  |
| Kustomization | flux-system | scheduling | Ready | main@9a46d93 | 2026-09-10T10:59:52Z |  |
| Kustomization | flux-system | searxng | Ready | main@9a46d93 | 2026-09-10T10:59:28Z |  |
| Kustomization | flux-system | spire | Ready | main@9a46d93 | 2026-09-10T11:00:06Z |  |
| Kustomization | flux-system | staging | Ready | main@9a46d93 | 2026-09-10T10:59:38Z |  |
| Kustomization | flux-system | trivy | Ready | main@9a46d93 | 2026-09-10T10:58:56Z |  |
