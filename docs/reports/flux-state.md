# Flux: what is applied

Read from the cluster receipt taken at 2026-09-08T02:15:13Z. Every Kustomization and HelmRelease, with the revision Flux last applied. **Suspended** is a switch somebody turned off on purpose (temporal, commerce, commerce-data, event-bus), not a defect; **Unknown** is a row Flux has never graded.

**109 objects: 57 ready, 50 not ready, 0 unknown, 2 suspended.**

## Not ready right now

- **HelmRelease commerce/lago** since 2026-09-08T02:06:32Z: Helm install failed for release commerce/lago with chart lago@1.28.0: failed pre-install: timeout waiting for: [Job/commerce/lago-migrate-db status: 'InProgress']
- **HelmRelease observability/langfuse** since 2026-09-07T21:12:08Z: dependency 'observability/signoz' is not ready
- **HelmRelease observability/signoz** since 2026-09-08T02:05:12Z: Helm upgrade failed for release observability/signoz with chart signoz@0.138.0: timeout waiting for: [Deployment/observability/signoz-clickhouse-operator status: 'InProgress', StatefulSet/observability/signoz status: 'InProgress']
- **Kustomization flux-system/agent-workforce** since 2026-09-08T02:06:40Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/alerts-github** since 2026-09-08T02:05:49Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/autoscaler** since 2026-09-08T02:06:08Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/backstage** since 2026-09-08T02:06:00Z: dependency 'flux-system/external-secrets' is not ready
- **Kustomization flux-system/chaos** since 2026-09-08T01:49:33Z: dependency 'flux-system/observability' is not ready
- **Kustomization flux-system/chaos-mesh** since 2026-09-08T02:14:59Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/commerce** since 2026-09-08T02:05:48Z: dependency 'flux-system/commerce-data' is not ready
- **Kustomization flux-system/commerce-data** since 2026-09-08T02:05:34Z: dependency 'flux-system/external-secrets' is not ready
- **Kustomization flux-system/dagster** since 2026-09-08T02:05:24Z: dependency 'flux-system/edge' is not ready
- **Kustomization flux-system/dns** since 2026-09-08T02:14:56Z: dependency 'flux-system/edge' is not ready
- **Kustomization flux-system/edge** since 2026-09-08T02:05:24Z: PolicyException/kyverno/calico-is-the-network dry-run failed (InternalError): Internal error occurred: failed calling webhook "kyverno-svc.kyverno.svc": failed to call webhook: Post "https://kyverno-svc.kyverno.svc:443/exceptionvalidate?timeout=10s": EOF 
- **Kustomization flux-system/estate-db** since 2026-09-08T02:15:06Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/estate-db-migrate** since 2026-09-08T02:05:51Z: dependency 'flux-system/estate-db' is not ready
- **Kustomization flux-system/external-secrets** since 2026-09-08T02:05:30Z: dependency 'flux-system/edge' is not ready
- **Kustomization flux-system/flux-webhook** since 2026-09-08T02:15:05Z: dependency 'flux-system/edge' is not ready
- **Kustomization flux-system/guacamole** since 2026-09-08T02:06:15Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/gvisor-runtime** since 2026-09-08T00:53:14Z: dependency 'flux-system/nodesoftware-operator' is not ready
- **Kustomization flux-system/healing** since 2026-09-08T02:06:13Z: dependency 'flux-system/llm' is not ready
- **Kustomization flux-system/healing-analyzer** since 2026-09-08T02:06:37Z: dependency 'flux-system/healing' is not ready
- **Kustomization flux-system/healthchecks** since 2026-09-08T02:15:00Z: dependency 'flux-system/identity' is not ready
- **Kustomization flux-system/hermes-agent** since 2026-09-08T02:06:09Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/hindsight** since 2026-09-08T02:06:02Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/human-vault** since 2026-09-08T02:05:54Z: dependency 'flux-system/external-secrets' is not ready
- **Kustomization flux-system/human-vault-bridge** since 2026-09-08T02:05:28Z: dependency 'flux-system/human-vault' is not ready
- **Kustomization flux-system/identity** since 2026-09-08T02:14:59Z: dependency 'flux-system/edge' is not ready
- **Kustomization flux-system/image-automation** since 2026-09-08T02:05:42Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/llm** since 2026-09-08T02:05:24Z: dependency 'flux-system/edge' is not ready
- **Kustomization flux-system/mcp** since 2026-09-08T02:14:50Z: dependency 'flux-system/edge' is not ready
- **Kustomization flux-system/nodesoftware-operator** since 2026-09-08T02:05:44Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/notify** since 2026-09-08T02:14:59Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/observability** since 2026-09-08T02:15:08Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/observability-collector** since 2026-09-08T02:14:55Z: dependency 'flux-system/edge' is not ready
- **Kustomization flux-system/otto-gateway** since 2026-09-08T02:05:44Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/otto-golden** since 2026-09-08T02:05:51Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/otto-golden-secret** since 2026-09-08T02:05:37Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/prospector** since 2026-09-08T02:12:53Z: dependency 'flux-system/prospector-platform' is not ready
- **Kustomization flux-system/prospector-platform** since 2026-09-08T02:05:48Z: dependency 'flux-system/edge' is not ready
- **Kustomization flux-system/reloader** since 2026-09-08T02:05:51Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/research-engine** since 2026-09-08T02:06:37Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/robusta** since 2026-09-08T02:05:39Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/sandbox-launch** since 2026-09-08T02:05:22Z: dependency 'flux-system/edge' is not ready
- **Kustomization flux-system/scheduling** since 2026-09-08T02:14:59Z: dependency 'flux-system/edge' is not ready
- **Kustomization flux-system/science** since 2026-09-07T21:13:12Z: dependency 'flux-system/observability' is not ready
- **Kustomization flux-system/secret-store** since 2026-09-08T02:05:34Z: dependency 'flux-system/external-secrets' is not ready
- **Kustomization flux-system/tailscale** since 2026-09-08T02:05:41Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/verification** since 2026-09-08T02:05:47Z: dependency 'flux-system/external-secrets' is not ready
- **Kustomization flux-system/weave-gitops** since 2026-09-08T02:15:08Z: dependency 'flux-system/identity' is not ready

## Every row

| Kind | Namespace | Name | State | Applied revision | Since | Message |
|---|---|---|---|---|---|---|
| HelmRelease | commerce | lago | Not ready | 1.28.0 | 2026-09-08T02:06:32Z | Helm install failed for release commerce/lago with chart lago@1.28.0: failed pre-install: timeout waiting for: [Job/commerce/lago-migrate-db status: 'InProgress |
| HelmRelease | observability | langfuse | Not ready | 2.0.2 | 2026-09-07T21:12:08Z | dependency 'observability/signoz' is not ready |
| HelmRelease | observability | signoz | Not ready | 0.138.0 | 2026-09-08T02:05:12Z | Helm upgrade failed for release observability/signoz with chart signoz@0.138.0: timeout waiting for: [Deployment/observability/signoz-clickhouse-operator status |
| Kustomization | flux-system | agent-workforce | Not ready | main@6d84a86 | 2026-09-08T02:06:40Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | alerts-github | Not ready | main@6d84a86 | 2026-09-08T02:05:49Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | autoscaler | Not ready | main@6d84a86 | 2026-09-08T02:06:08Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | backstage | Not ready | main@6d84a86 | 2026-09-08T02:06:00Z | dependency 'flux-system/external-secrets' is not ready |
| Kustomization | flux-system | chaos | Not ready | main@a38150d | 2026-09-08T01:49:33Z | dependency 'flux-system/observability' is not ready |
| Kustomization | flux-system | chaos-mesh | Not ready | main@6d84a86 | 2026-09-08T02:14:59Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | commerce | Not ready | main@ec2e05f | 2026-09-08T02:05:48Z | dependency 'flux-system/commerce-data' is not ready |
| Kustomization | flux-system | commerce-data | Not ready | main@6d84a86 | 2026-09-08T02:05:34Z | dependency 'flux-system/external-secrets' is not ready |
| Kustomization | flux-system | dagster | Not ready | main@6d84a86 | 2026-09-08T02:05:24Z | dependency 'flux-system/edge' is not ready |
| Kustomization | flux-system | dns | Not ready | main@6d84a86 | 2026-09-08T02:14:56Z | dependency 'flux-system/edge' is not ready |
| Kustomization | flux-system | edge | Not ready | main@6d84a86 | 2026-09-08T02:05:24Z | PolicyException/kyverno/calico-is-the-network dry-run failed (InternalError): Internal error occurred: failed calling webhook "kyverno-svc.kyverno.svc": failed  |
| Kustomization | flux-system | estate-db | Not ready | main@6d84a86 | 2026-09-08T02:15:06Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | estate-db-migrate | Not ready | main@6d84a86 | 2026-09-08T02:05:51Z | dependency 'flux-system/estate-db' is not ready |
| Kustomization | flux-system | external-secrets | Not ready | main@6d84a86 | 2026-09-08T02:05:30Z | dependency 'flux-system/edge' is not ready |
| Kustomization | flux-system | flux-webhook | Not ready | main@6d84a86 | 2026-09-08T02:15:05Z | dependency 'flux-system/edge' is not ready |
| Kustomization | flux-system | guacamole | Not ready | main@6d84a86 | 2026-09-08T02:06:15Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | gvisor-runtime | Not ready | main@8e1bade | 2026-09-08T00:53:14Z | dependency 'flux-system/nodesoftware-operator' is not ready |
| Kustomization | flux-system | healing | Not ready | main@6d84a86 | 2026-09-08T02:06:13Z | dependency 'flux-system/llm' is not ready |
| Kustomization | flux-system | healing-analyzer | Not ready | main@6d84a86 | 2026-09-08T02:06:37Z | dependency 'flux-system/healing' is not ready |
| Kustomization | flux-system | healthchecks | Not ready | main@6d84a86 | 2026-09-08T02:15:00Z | dependency 'flux-system/identity' is not ready |
| Kustomization | flux-system | hermes-agent | Not ready | main@6d84a86 | 2026-09-08T02:06:09Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | hindsight | Not ready | main@6d84a86 | 2026-09-08T02:06:02Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | human-vault | Not ready | main@6d84a86 | 2026-09-08T02:05:54Z | dependency 'flux-system/external-secrets' is not ready |
| Kustomization | flux-system | human-vault-bridge | Not ready | main@6d84a86 | 2026-09-08T02:05:28Z | dependency 'flux-system/human-vault' is not ready |
| Kustomization | flux-system | identity | Not ready | main@6d84a86 | 2026-09-08T02:14:59Z | dependency 'flux-system/edge' is not ready |
| Kustomization | flux-system | image-automation | Not ready | main@6d84a86 | 2026-09-08T02:05:42Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | llm | Not ready | main@6d84a86 | 2026-09-08T02:05:24Z | dependency 'flux-system/edge' is not ready |
| Kustomization | flux-system | mcp | Not ready | main@6d84a86 | 2026-09-08T02:14:50Z | dependency 'flux-system/edge' is not ready |
| Kustomization | flux-system | nodesoftware-operator | Not ready | main@8e1bade | 2026-09-08T02:05:44Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | notify | Not ready | main@6d84a86 | 2026-09-08T02:14:59Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | observability | Not ready | main@a38150d | 2026-09-08T02:15:08Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | observability-collector | Not ready | main@6d84a86 | 2026-09-08T02:14:55Z | dependency 'flux-system/edge' is not ready |
| Kustomization | flux-system | otto-gateway | Not ready | main@7dd9f6e | 2026-09-08T02:05:44Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | otto-golden | Not ready | main@6d84a86 | 2026-09-08T02:05:51Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | otto-golden-secret | Not ready | main@6d84a86 | 2026-09-08T02:05:37Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | prospector | Not ready | main@7453d76 | 2026-09-08T02:12:53Z | dependency 'flux-system/prospector-platform' is not ready |
| Kustomization | flux-system | prospector-platform | Not ready | main@6d84a86 | 2026-09-08T02:05:48Z | dependency 'flux-system/edge' is not ready |
| Kustomization | flux-system | reloader | Not ready | main@6d84a86 | 2026-09-08T02:05:51Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | research-engine | Not ready | main@6d84a86 | 2026-09-08T02:06:37Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | robusta | Not ready | main@6d84a86 | 2026-09-08T02:05:39Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | sandbox-launch | Not ready | main@6d84a86 | 2026-09-08T02:05:22Z | dependency 'flux-system/edge' is not ready |
| Kustomization | flux-system | scheduling | Not ready | main@6d84a86 | 2026-09-08T02:14:59Z | dependency 'flux-system/edge' is not ready |
| Kustomization | flux-system | science | Not ready | main@a38150d | 2026-09-07T21:13:12Z | dependency 'flux-system/observability' is not ready |
| Kustomization | flux-system | secret-store | Not ready | main@6d84a86 | 2026-09-08T02:05:34Z | dependency 'flux-system/external-secrets' is not ready |
| Kustomization | flux-system | tailscale | Not ready | main@6d84a86 | 2026-09-08T02:05:41Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | verification | Not ready | main@6d84a86 | 2026-09-08T02:05:47Z | dependency 'flux-system/external-secrets' is not ready |
| Kustomization | flux-system | weave-gitops | Not ready | main@6d84a86 | 2026-09-08T02:15:08Z | dependency 'flux-system/identity' is not ready |
| HelmRelease | tigera-operator | tigera-operator | Suspended | v3.32.2 | 2026-09-06T19:38:02Z |  |
| Kustomization | flux-system | temporal | Suspended | main@1b323ac | 2026-08-30T05:54:22Z |  |
| HelmRelease | cert-manager | cert-manager | Ready | v1.21.1 | 2026-09-06T19:34:17Z |  |
| HelmRelease | chaos-mesh | chaos-mesh | Ready | 2.8.4 | 2026-09-06T19:34:33Z |  |
| HelmRelease | dagster | dagster | Ready | 1.13.19 | 2026-09-08T00:49:13Z |  |
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
| HelmRelease | observability-agent | k8s-infra | Ready | 0.17.0 | 2026-09-06T19:34:33Z |  |
| HelmRelease | reloader | reloader | Ready | 2.2.16 | 2026-09-06T19:33:25Z |  |
| HelmRelease | robusta | robusta | Ready | 0.48.0 | 2026-09-06T20:26:45Z |  |
| HelmRelease | spire-mgmt | spire | Ready | 0.30.1 | 2026-09-06T20:27:16Z |  |
| HelmRelease | spire-mgmt | spire-crds | Ready | 0.6.1 | 2026-09-06T20:26:47Z |  |
| HelmRelease | tailscale | tailscale-operator | Ready | 1.102.3 | 2026-09-06T19:33:35Z |  |
| HelmRelease | temporal | temporal | Ready | 1.6.0 | 2026-09-06T19:33:25Z |  |
| HelmRelease | trivy-system | trivy-operator | Ready | 0.36.0 | 2026-09-06T20:26:45Z |  |
| HelmRelease | weave-gitops | weave-gitops | Ready | 4.0.36 | 2026-09-06T20:26:45Z |  |
| Kustomization | flux-system | alerts | Ready | main@6d84a86 | 2026-09-08T02:05:37Z |  |
| Kustomization | flux-system | alerts-secret | Ready | main@6d84a86 | 2026-09-08T02:05:08Z |  |
| Kustomization | flux-system | backstage-namespace | Ready | main@6d84a86 | 2026-09-08T02:14:30Z |  |
| Kustomization | flux-system | calico | Ready | main@6d84a86 | 2026-09-08T02:14:34Z |  |
| Kustomization | flux-system | cluster-state | Ready | main@6d84a86 | 2026-09-08T02:05:20Z |  |
| Kustomization | flux-system | cyrus | Ready | main@6d84a86 | 2026-09-08T02:05:14Z |  |
| Kustomization | flux-system | drills | Ready | main@6d84a86 | 2026-09-08T02:05:37Z |  |
| Kustomization | flux-system | estate-catalog | Ready | latest@sha256:67bb6c94dadcb443d1b4ca9bda | 2026-09-08T02:08:58Z |  |
| Kustomization | flux-system | estate-db-operator | Ready | main@6d84a86 | 2026-09-08T02:05:20Z |  |
| Kustomization | flux-system | event-bus | Ready | main@6d84a86 | 2026-09-08T02:14:39Z |  |
| Kustomization | flux-system | feature-register | Ready | main@6d84a86 | 2026-09-08T02:05:25Z |  |
| Kustomization | flux-system | flux-system | Ready | main@6d84a86 | 2026-09-08T02:04:55Z |  |
| Kustomization | flux-system | gateway-api-crds | Ready | v1.5.1@e7677b7 | 2026-09-08T02:14:47Z |  |
| Kustomization | flux-system | jit | Ready | main@6d84a86 | 2026-09-08T02:04:57Z |  |
| Kustomization | flux-system | keda | Ready | main@6d84a86 | 2026-09-08T02:05:26Z |  |
| Kustomization | flux-system | kyverno | Ready | main@6d84a86 | 2026-09-08T02:05:38Z |  |
| Kustomization | flux-system | metrics-server | Ready | main@6d84a86 | 2026-09-08T02:05:51Z |  |
| Kustomization | flux-system | monitoring | Ready | main@6d84a86 | 2026-09-08T02:05:18Z |  |
| Kustomization | flux-system | monitoring-rules | Ready | main@6d84a86 | 2026-09-08T02:05:29Z |  |
| Kustomization | flux-system | ns-fences | Ready | main@6d84a86 | 2026-09-08T02:15:03Z |  |
| Kustomization | flux-system | priority-classes | Ready | main@6d84a86 | 2026-09-08T02:14:10Z |  |
| Kustomization | flux-system | rbac | Ready | main@6d84a86 | 2026-09-08T02:05:33Z |  |
| Kustomization | flux-system | rbac-floor | Ready | main@6d84a86 | 2026-09-08T02:05:02Z |  |
| Kustomization | flux-system | rbac-identity | Ready | main@6d84a86 | 2026-09-08T02:14:37Z |  |
| Kustomization | flux-system | sandbox-live | Ready | sandbox/launch@929c1d7 | 2026-09-08T02:14:55Z |  |
| Kustomization | flux-system | searxng | Ready | main@6d84a86 | 2026-09-08T02:14:35Z |  |
| Kustomization | flux-system | spire | Ready | main@6d84a86 | 2026-09-08T02:05:54Z |  |
| Kustomization | flux-system | staging | Ready | main@6d84a86 | 2026-09-08T02:05:32Z |  |
| Kustomization | flux-system | trivy | Ready | main@6d84a86 | 2026-09-08T02:05:40Z |  |
