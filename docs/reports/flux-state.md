# Flux: what is applied

Read from the cluster receipt taken at 2026-09-08T08:00:13Z. Every Kustomization and HelmRelease, with the revision Flux last applied. **Suspended** is a switch somebody turned off on purpose (temporal, commerce, commerce-data, event-bus), not a defect; **Unknown** is a row Flux has never graded.

**112 objects: 56 ready, 54 not ready, 0 unknown, 2 suspended.**

## Not ready right now

- **HelmRelease commerce/lago** since 2026-09-08T07:47:52Z: Running 'install' action with timeout of 15m0s
- **HelmRelease observability/langfuse** since 2026-09-07T21:12:08Z: dependency 'observability/signoz' is not ready
- **HelmRelease observability/signoz** since 2026-09-08T06:48:35Z: Helm rollback to previous release observability/signoz.v58 with chart signoz@0.138.0 failed: release signoz failed: timeout waiting for: [Deployment/observability/signoz-clickhouse-operator status: 'InProgress']
- **Kustomization flux-system/agent-workforce** since 2026-09-08T07:58:52Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/alerts** since 2026-09-08T07:58:02Z: dependency 'flux-system/alerts-secret' is not ready
- **Kustomization flux-system/alerts-github** since 2026-09-08T07:57:28Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/alerts-secret** since 2026-09-08T07:57:44Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/backstage** since 2026-09-08T07:58:48Z: dependency 'flux-system/external-secrets' is not ready
- **Kustomization flux-system/chaos** since 2026-09-08T07:47:21Z: dependency 'flux-system/observability' is not ready
- **Kustomization flux-system/cluster-state** since 2026-09-08T07:57:22Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/commerce** since 2026-09-08T07:48:21Z: Reconciliation in progress
- **Kustomization flux-system/commerce-data** since 2026-09-08T07:57:58Z: dependency 'flux-system/external-secrets' is not ready
- **Kustomization flux-system/crossplane-providers** since 2026-09-08T07:57:19Z: ProviderConfig/default dry-run failed: no matches for kind "ProviderConfig" in version "oci.upbound.io/v1beta1" 
- **Kustomization flux-system/cyrus** since 2026-09-08T07:58:03Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/dagster** since 2026-09-08T07:58:20Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/dns** since 2026-09-08T07:57:37Z: dependency 'flux-system/edge' is not ready
- **Kustomization flux-system/drills** since 2026-09-08T07:58:18Z: dependency 'flux-system/alerts-github' is not ready
- **Kustomization flux-system/edge** since 2026-09-08T07:56:55Z: PolicyException/kyverno/catalogue-entity-operator-children dry-run failed (InternalError): Internal error occurred: failed calling webhook "kyverno-svc.kyverno.svc": failed to call webhook: Post "https://kyverno-svc.kyverno.svc:443/exceptionvalidate?timeout=10s": EOF 
- **Kustomization flux-system/estate-db** since 2026-09-08T07:57:40Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/estate-db-migrate** since 2026-09-08T07:57:50Z: dependency 'flux-system/estate-db' is not ready
- **Kustomization flux-system/external-secrets** since 2026-09-08T07:57:03Z: dependency 'flux-system/edge' is not ready
- **Kustomization flux-system/flux-webhook** since 2026-09-08T07:57:20Z: dependency 'flux-system/edge' is not ready
- **Kustomization flux-system/guacamole** since 2026-09-08T07:58:38Z: dependency 'flux-system/identity' is not ready
- **Kustomization flux-system/gvisor-runtime** since 2026-09-08T00:53:14Z: dependency 'flux-system/nodesoftware-operator' is not ready
- **Kustomization flux-system/healing** since 2026-09-08T07:57:58Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/healing-analyzer** since 2026-09-08T07:58:37Z: dependency 'flux-system/healing' is not ready
- **Kustomization flux-system/healthchecks** since 2026-09-08T07:58:45Z: dependency 'flux-system/identity' is not ready
- **Kustomization flux-system/hermes-agent** since 2026-09-08T07:58:08Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/hindsight** since 2026-09-08T07:58:12Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/human-vault** since 2026-09-08T07:57:28Z: dependency 'flux-system/external-secrets' is not ready
- **Kustomization flux-system/human-vault-bridge** since 2026-09-08T07:57:56Z: dependency 'flux-system/human-vault' is not ready
- **Kustomization flux-system/identity** since 2026-09-08T07:58:09Z: dependency 'flux-system/edge' is not ready
- **Kustomization flux-system/image-automation** since 2026-09-08T07:58:04Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/keda** since 2026-09-08T07:57:12Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/llm** since 2026-09-08T07:58:31Z: dependency 'flux-system/edge' is not ready
- **Kustomization flux-system/mcp** since 2026-09-08T07:57:57Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/monitoring** since 2026-09-08T07:57:42Z: dependency 'flux-system/edge' is not ready
- **Kustomization flux-system/monitoring-rules** since 2026-09-08T07:58:13Z: dependency 'flux-system/monitoring' is not ready
- **Kustomization flux-system/nodesoftware-operator** since 2026-09-08T07:57:53Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/notify** since 2026-09-08T07:57:32Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/observability** since 2026-09-08T08:00:06Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/observability-collector** since 2026-09-08T07:57:33Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/otto-gateway** since 2026-09-08T07:57:52Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/otto-golden** since 2026-09-08T07:57:38Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/otto-golden-secret** since 2026-09-08T07:58:03Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/prospector-platform** since 2026-09-08T07:57:38Z: dependency 'flux-system/edge' is not ready
- **Kustomization flux-system/reloader** since 2026-09-08T07:58:11Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/research-engine** since 2026-09-08T07:58:49Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/scheduling** since 2026-09-08T07:57:07Z: dependency 'flux-system/edge' is not ready
- **Kustomization flux-system/science** since 2026-09-07T21:13:12Z: dependency 'flux-system/observability' is not ready
- **Kustomization flux-system/secret-store** since 2026-09-08T07:57:21Z: dependency 'flux-system/external-secrets' is not ready
- **Kustomization flux-system/tailscale** since 2026-09-08T07:57:29Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/verification** since 2026-09-08T07:57:52Z: dependency 'flux-system/external-secrets' is not ready
- **Kustomization flux-system/weave-gitops** since 2026-09-08T07:58:26Z: dependency 'flux-system/identity' is not ready

## Every row

| Kind | Namespace | Name | State | Applied revision | Since | Message |
|---|---|---|---|---|---|---|
| HelmRelease | commerce | lago | Not ready | 1.28.0 | 2026-09-08T07:47:52Z | Running 'install' action with timeout of 15m0s |
| HelmRelease | observability | langfuse | Not ready | 2.0.2 | 2026-09-07T21:12:08Z | dependency 'observability/signoz' is not ready |
| HelmRelease | observability | signoz | Not ready | 0.138.0 | 2026-09-08T06:48:35Z | Helm rollback to previous release observability/signoz.v58 with chart signoz@0.138.0 failed: release signoz failed: timeout waiting for: [Deployment/observabili |
| Kustomization | flux-system | agent-workforce | Not ready | main@a1eedeb | 2026-09-08T07:58:52Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | alerts | Not ready | main@a1eedeb | 2026-09-08T07:58:02Z | dependency 'flux-system/alerts-secret' is not ready |
| Kustomization | flux-system | alerts-github | Not ready | main@a1eedeb | 2026-09-08T07:57:28Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | alerts-secret | Not ready | main@a1eedeb | 2026-09-08T07:57:44Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | backstage | Not ready | main@a1eedeb | 2026-09-08T07:58:48Z | dependency 'flux-system/external-secrets' is not ready |
| Kustomization | flux-system | chaos | Not ready | main@a38150d | 2026-09-08T07:47:21Z | dependency 'flux-system/observability' is not ready |
| Kustomization | flux-system | cluster-state | Not ready | main@a1eedeb | 2026-09-08T07:57:22Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | commerce | Not ready | main@a1eedeb | 2026-09-08T07:48:21Z | Reconciliation in progress |
| Kustomization | flux-system | commerce-data | Not ready | main@a1eedeb | 2026-09-08T07:57:58Z | dependency 'flux-system/external-secrets' is not ready |
| Kustomization | flux-system | crossplane-providers | Not ready | main@a1eedeb | 2026-09-08T07:57:19Z | ProviderConfig/default dry-run failed: no matches for kind "ProviderConfig" in version "oci.upbound.io/v1beta1"  |
| Kustomization | flux-system | cyrus | Not ready | main@a1eedeb | 2026-09-08T07:58:03Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | dagster | Not ready | main@a1eedeb | 2026-09-08T07:58:20Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | dns | Not ready | main@a1eedeb | 2026-09-08T07:57:37Z | dependency 'flux-system/edge' is not ready |
| Kustomization | flux-system | drills | Not ready | main@a1eedeb | 2026-09-08T07:58:18Z | dependency 'flux-system/alerts-github' is not ready |
| Kustomization | flux-system | edge | Not ready | main@a1eedeb | 2026-09-08T07:56:55Z | PolicyException/kyverno/catalogue-entity-operator-children dry-run failed (InternalError): Internal error occurred: failed calling webhook "kyverno-svc.kyverno. |
| Kustomization | flux-system | estate-db | Not ready | main@a1eedeb | 2026-09-08T07:57:40Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | estate-db-migrate | Not ready | main@a1eedeb | 2026-09-08T07:57:50Z | dependency 'flux-system/estate-db' is not ready |
| Kustomization | flux-system | external-secrets | Not ready | main@a1eedeb | 2026-09-08T07:57:03Z | dependency 'flux-system/edge' is not ready |
| Kustomization | flux-system | flux-webhook | Not ready | main@a1eedeb | 2026-09-08T07:57:20Z | dependency 'flux-system/edge' is not ready |
| Kustomization | flux-system | guacamole | Not ready | main@a1eedeb | 2026-09-08T07:58:38Z | dependency 'flux-system/identity' is not ready |
| Kustomization | flux-system | gvisor-runtime | Not ready | main@8e1bade | 2026-09-08T00:53:14Z | dependency 'flux-system/nodesoftware-operator' is not ready |
| Kustomization | flux-system | healing | Not ready | main@a1eedeb | 2026-09-08T07:57:58Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | healing-analyzer | Not ready | main@a1eedeb | 2026-09-08T07:58:37Z | dependency 'flux-system/healing' is not ready |
| Kustomization | flux-system | healthchecks | Not ready | main@a1eedeb | 2026-09-08T07:58:45Z | dependency 'flux-system/identity' is not ready |
| Kustomization | flux-system | hermes-agent | Not ready | main@a1eedeb | 2026-09-08T07:58:08Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | hindsight | Not ready | main@a1eedeb | 2026-09-08T07:58:12Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | human-vault | Not ready | main@a1eedeb | 2026-09-08T07:57:28Z | dependency 'flux-system/external-secrets' is not ready |
| Kustomization | flux-system | human-vault-bridge | Not ready | main@a1eedeb | 2026-09-08T07:57:56Z | dependency 'flux-system/human-vault' is not ready |
| Kustomization | flux-system | identity | Not ready | main@a1eedeb | 2026-09-08T07:58:09Z | dependency 'flux-system/edge' is not ready |
| Kustomization | flux-system | image-automation | Not ready | main@a1eedeb | 2026-09-08T07:58:04Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | keda | Not ready | main@a1eedeb | 2026-09-08T07:57:12Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | llm | Not ready | main@a1eedeb | 2026-09-08T07:58:31Z | dependency 'flux-system/edge' is not ready |
| Kustomization | flux-system | mcp | Not ready | main@a1eedeb | 2026-09-08T07:57:57Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | monitoring | Not ready | main@a1eedeb | 2026-09-08T07:57:42Z | dependency 'flux-system/edge' is not ready |
| Kustomization | flux-system | monitoring-rules | Not ready | main@a1eedeb | 2026-09-08T07:58:13Z | dependency 'flux-system/monitoring' is not ready |
| Kustomization | flux-system | nodesoftware-operator | Not ready | main@8e1bade | 2026-09-08T07:57:53Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | notify | Not ready | main@a1eedeb | 2026-09-08T07:57:32Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | observability | Not ready | main@a38150d | 2026-09-08T08:00:06Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | observability-collector | Not ready | main@a1eedeb | 2026-09-08T07:57:33Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | otto-gateway | Not ready | main@7dd9f6e | 2026-09-08T07:57:52Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | otto-golden | Not ready | main@a1eedeb | 2026-09-08T07:57:38Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | otto-golden-secret | Not ready | main@a1eedeb | 2026-09-08T07:58:03Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | prospector-platform | Not ready | main@a1eedeb | 2026-09-08T07:57:38Z | dependency 'flux-system/edge' is not ready |
| Kustomization | flux-system | reloader | Not ready | main@a1eedeb | 2026-09-08T07:58:11Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | research-engine | Not ready | main@a1eedeb | 2026-09-08T07:58:49Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | scheduling | Not ready | main@a1eedeb | 2026-09-08T07:57:07Z | dependency 'flux-system/edge' is not ready |
| Kustomization | flux-system | science | Not ready | main@a38150d | 2026-09-07T21:13:12Z | dependency 'flux-system/observability' is not ready |
| Kustomization | flux-system | secret-store | Not ready | main@a1eedeb | 2026-09-08T07:57:21Z | dependency 'flux-system/external-secrets' is not ready |
| Kustomization | flux-system | tailscale | Not ready | main@a1eedeb | 2026-09-08T07:57:29Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | verification | Not ready | main@a1eedeb | 2026-09-08T07:57:52Z | dependency 'flux-system/external-secrets' is not ready |
| Kustomization | flux-system | weave-gitops | Not ready | main@a1eedeb | 2026-09-08T07:58:26Z | dependency 'flux-system/identity' is not ready |
| HelmRelease | tigera-operator | tigera-operator | Suspended | v3.32.2 | 2026-09-06T19:38:02Z |  |
| Kustomization | flux-system | temporal | Suspended | main@1b323ac | 2026-08-30T05:54:22Z |  |
| HelmRelease | cert-manager | cert-manager | Ready | v1.21.1 | 2026-09-06T19:34:17Z |  |
| HelmRelease | chaos-mesh | chaos-mesh | Ready | 2.8.4 | 2026-09-06T19:34:33Z |  |
| HelmRelease | crossplane-system | crossplane | Ready | 2.4.0 | 2026-09-08T07:05:25Z |  |
| HelmRelease | dagster | dagster | Ready | 1.13.19 | 2026-09-08T06:32:55Z |  |
| HelmRelease | edge | external-dns | Ready | 1.21.1 | 2026-09-06T19:33:35Z |  |
| HelmRelease | edge | traefik | Ready | 41.3.0 | 2026-09-06T19:35:13Z |  |
| HelmRelease | estate-db | cloudnative-pg | Ready | 0.29.0 | 2026-09-06T19:45:25Z |  |
| HelmRelease | event-bus | nats | Ready | 2.14.6 | 2026-09-06T19:39:37Z |  |
| HelmRelease | external-secrets | external-secrets | Ready | 2.9.0 | 2026-09-06T19:33:05Z |  |
| HelmRelease | healing | descheduler | Ready | 0.36.0 | 2026-09-06T19:34:32Z |  |
| HelmRelease | healing | k8sgpt-operator | Ready | 0.2.29 | 2026-09-06T19:33:00Z |  |
| HelmRelease | hindsight | hindsight | Ready | 0.9.2 | 2026-09-06T20:26:45Z |  |
| HelmRelease | identity | oauth2-proxy | Ready | 10.7.0 | 2026-09-06T19:35:13Z |  |
| HelmRelease | keda | keda | Ready | 2.20.2 | 2026-09-06T19:34:17Z |  |
| HelmRelease | keda | keda-add-ons-http | Ready | 0.15.0 | 2026-09-06T19:35:13Z |  |
| HelmRelease | kyverno | kyverno | Ready | 3.9.0 | 2026-09-06T20:26:45Z |  |
| HelmRelease | metrics-server | metrics-server | Ready | 3.14.0 | 2026-09-06T19:34:02Z |  |
| HelmRelease | monitoring | blackbox | Ready | 11.17.2 | 2026-09-06T19:47:10Z |  |
| HelmRelease | monitoring | kube-prometheus-stack | Ready | 88.6.0 | 2026-09-06T20:26:45Z |  |
| HelmRelease | observability | superset | Ready | 0.22.4 | 2026-09-06T19:46:05Z |  |
| HelmRelease | observability-agent | k8s-infra | Ready | 0.17.0 | 2026-09-08T02:42:15Z |  |
| HelmRelease | reloader | reloader | Ready | 2.2.16 | 2026-09-06T19:33:25Z |  |
| HelmRelease | robusta | robusta | Ready | 0.48.0 | 2026-09-06T20:26:45Z |  |
| HelmRelease | spire-mgmt | spire | Ready | 0.30.1 | 2026-09-06T20:27:16Z |  |
| HelmRelease | spire-mgmt | spire-crds | Ready | 0.6.1 | 2026-09-06T20:26:47Z |  |
| HelmRelease | tailscale | tailscale-operator | Ready | 1.102.3 | 2026-09-06T19:33:35Z |  |
| HelmRelease | temporal | temporal | Ready | 1.6.0 | 2026-09-06T19:33:25Z |  |
| HelmRelease | trivy-system | trivy-operator | Ready | 0.36.0 | 2026-09-06T20:26:45Z |  |
| HelmRelease | weave-gitops | weave-gitops | Ready | 4.0.36 | 2026-09-06T20:26:45Z |  |
| Kustomization | flux-system | autoscaler | Ready | main@a1eedeb | 2026-09-08T07:57:19Z |  |
| Kustomization | flux-system | backstage-namespace | Ready | main@a1eedeb | 2026-09-08T07:56:43Z |  |
| Kustomization | flux-system | calico | Ready | main@a1eedeb | 2026-09-08T07:56:57Z |  |
| Kustomization | flux-system | chaos-mesh | Ready | main@a1eedeb | 2026-09-08T07:57:03Z |  |
| Kustomization | flux-system | crossplane | Ready | main@a1eedeb | 2026-09-08T07:57:02Z |  |
| Kustomization | flux-system | estate-catalog | Ready | latest@sha256:ccf2a31448be47a5023f3c1ff2 | 2026-09-08T07:51:24Z |  |
| Kustomization | flux-system | estate-db-operator | Ready | main@a1eedeb | 2026-09-08T07:56:53Z |  |
| Kustomization | flux-system | event-bus | Ready | main@a1eedeb | 2026-09-08T07:56:35Z |  |
| Kustomization | flux-system | feature-register | Ready | main@a1eedeb | 2026-09-08T07:56:55Z |  |
| Kustomization | flux-system | flux-system | Ready | main@a1eedeb | 2026-09-08T07:56:29Z |  |
| Kustomization | flux-system | gateway-api-crds | Ready | v1.5.1@e7677b7 | 2026-09-08T07:56:32Z |  |
| Kustomization | flux-system | jit | Ready | main@a1eedeb | 2026-09-08T07:56:36Z |  |
| Kustomization | flux-system | kyverno | Ready | main@a1eedeb | 2026-09-08T07:57:03Z |  |
| Kustomization | flux-system | metrics-server | Ready | main@a1eedeb | 2026-09-08T07:56:49Z |  |
| Kustomization | flux-system | ns-fences | Ready | main@a1eedeb | 2026-09-08T07:56:50Z |  |
| Kustomization | flux-system | priority-classes | Ready | main@a1eedeb | 2026-09-08T07:56:10Z |  |
| Kustomization | flux-system | prospector | Ready | main@7453d76 | 2026-09-08T07:53:12Z |  |
| Kustomization | flux-system | rbac | Ready | main@a1eedeb | 2026-09-08T07:56:35Z |  |
| Kustomization | flux-system | rbac-floor | Ready | main@a1eedeb | 2026-09-08T07:56:43Z |  |
| Kustomization | flux-system | rbac-identity | Ready | main@a1eedeb | 2026-09-08T07:56:36Z |  |
| Kustomization | flux-system | robusta | Ready | main@a1eedeb | 2026-09-08T07:57:15Z |  |
| Kustomization | flux-system | sandbox-launch | Ready | main@a1eedeb | 2026-09-08T07:56:52Z |  |
| Kustomization | flux-system | sandbox-live | Ready | sandbox/launch@929c1d7 | 2026-09-08T07:59:57Z |  |
| Kustomization | flux-system | searxng | Ready | main@a1eedeb | 2026-09-08T07:56:36Z |  |
| Kustomization | flux-system | spire | Ready | main@a1eedeb | 2026-09-08T07:56:55Z |  |
| Kustomization | flux-system | staging | Ready | main@a1eedeb | 2026-09-08T07:57:04Z |  |
| Kustomization | flux-system | trivy | Ready | main@a1eedeb | 2026-09-08T07:57:02Z |  |
