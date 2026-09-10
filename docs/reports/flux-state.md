# Flux: what is applied

Read from the cluster receipt taken at 2026-09-10T12:30:15Z. Every Kustomization and HelmRelease, with the revision Flux last applied. **Suspended** is a switch somebody turned off on purpose (temporal, commerce, commerce-data, event-bus), not a defect; **Unknown** is a row Flux has never graded.

**115 objects: 53 ready, 60 not ready, 0 unknown, 2 suspended.**

## Not ready right now

- **HelmRelease commerce/lago** since 2026-09-10T12:22:40Z: Running 'install' action with timeout of 15m0s
- **Kustomization flux-system/agent-workforce** since 2026-09-10T12:29:42Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/alerts** since 2026-09-10T12:29:40Z: dependency 'flux-system/alerts-secret' is not ready
- **Kustomization flux-system/alerts-github** since 2026-09-10T12:29:40Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/alerts-secret** since 2026-09-10T12:29:40Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/autoscaler** since 2026-09-10T12:29:40Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/backstage** since 2026-09-10T12:29:41Z: dependency 'flux-system/external-secrets' is not ready
- **Kustomization flux-system/chaos** since 2026-09-10T12:29:42Z: dependency 'flux-system/chaos-mesh' is not ready
- **Kustomization flux-system/chaos-mesh** since 2026-09-10T12:29:40Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/cluster-state** since 2026-09-10T12:29:40Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/commerce** since 2026-09-10T12:22:39Z: Reconciliation in progress
- **Kustomization flux-system/commerce-data** since 2026-09-10T12:29:41Z: dependency 'flux-system/external-secrets' is not ready
- **Kustomization flux-system/crossplane** since 2026-09-10T12:29:41Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/crossplane-providerconfig** since 2026-09-10T12:29:41Z: dependency 'flux-system/crossplane-providers' is not ready
- **Kustomization flux-system/crossplane-providers** since 2026-09-10T12:29:41Z: dependency 'flux-system/crossplane' is not ready
- **Kustomization flux-system/cyrus** since 2026-09-10T12:29:46Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/dagster** since 2026-09-10T12:29:41Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/dns** since 2026-09-10T12:29:40Z: dependency 'flux-system/edge' is not ready
- **Kustomization flux-system/drills** since 2026-09-10T12:29:40Z: dependency 'flux-system/alerts-github' is not ready
- **Kustomization flux-system/estate-db** since 2026-09-10T12:29:40Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/estate-db-migrate** since 2026-09-10T12:29:41Z: dependency 'flux-system/estate-db' is not ready
- **Kustomization flux-system/external-secrets** since 2026-09-10T12:30:09Z: Reconciliation in progress
- **Kustomization flux-system/flux-webhook** since 2026-09-10T12:29:40Z: dependency 'flux-system/edge' is not ready
- **Kustomization flux-system/guacamole** since 2026-09-10T12:29:42Z: dependency 'flux-system/identity' is not ready
- **Kustomization flux-system/gvisor-runtime** since 2026-09-10T12:29:42Z: dependency 'flux-system/nodesoftware-operator' is not ready
- **Kustomization flux-system/healing** since 2026-09-10T12:29:41Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/healing-analyzer** since 2026-09-10T12:29:41Z: dependency 'flux-system/healing-k8sgpt' is not ready
- **Kustomization flux-system/healing-k8sgpt** since 2026-09-10T12:29:41Z: dependency 'flux-system/healing' is not ready
- **Kustomization flux-system/healthchecks** since 2026-09-10T12:29:41Z: dependency 'flux-system/identity' is not ready
- **Kustomization flux-system/hermes-agent** since 2026-09-10T12:29:41Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/hindsight** since 2026-09-10T12:29:42Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/human-vault** since 2026-09-10T12:29:40Z: dependency 'flux-system/external-secrets' is not ready
- **Kustomization flux-system/human-vault-bridge** since 2026-09-10T12:29:40Z: dependency 'flux-system/human-vault' is not ready
- **Kustomization flux-system/identity** since 2026-09-10T12:29:40Z: dependency 'flux-system/edge' is not ready
- **Kustomization flux-system/image-automation** since 2026-09-10T12:29:41Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/keda** since 2026-09-10T12:29:41Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/llm** since 2026-09-10T12:29:41Z: dependency 'flux-system/edge' is not ready
- **Kustomization flux-system/mcp** since 2026-09-10T12:29:41Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/metrics-server** since 2026-09-10T12:29:41Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/monitoring** since 2026-09-10T12:29:40Z: dependency 'flux-system/edge' is not ready
- **Kustomization flux-system/monitoring-rules** since 2026-09-10T12:29:41Z: dependency 'flux-system/monitoring' is not ready
- **Kustomization flux-system/nodesoftware-operator** since 2026-09-10T12:29:41Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/notify** since 2026-09-10T12:29:41Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/observability** since 2026-09-10T12:29:41Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/observability-collector** since 2026-09-10T12:29:40Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/otto-gateway** since 2026-09-10T12:29:42Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/otto-golden** since 2026-09-10T12:29:41Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/otto-golden-secret** since 2026-09-10T12:29:40Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/prospector-platform** since 2026-09-10T12:29:39Z: dependency 'flux-system/edge' is not ready
- **Kustomization flux-system/reloader** since 2026-09-10T12:29:39Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/research-engine** since 2026-09-10T12:29:42Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/robusta** since 2026-09-10T12:29:39Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/sandbox-launch** since 2026-09-10T12:30:09Z: Reconciliation in progress
- **Kustomization flux-system/scheduling** since 2026-09-10T12:30:09Z: Reconciliation in progress
- **Kustomization flux-system/science** since 2026-09-10T12:29:42Z: dependency 'flux-system/observability' is not ready
- **Kustomization flux-system/secret-store** since 2026-09-10T12:29:39Z: dependency 'flux-system/external-secrets' is not ready
- **Kustomization flux-system/spire** since 2026-09-10T12:29:40Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/tailscale** since 2026-09-10T12:29:42Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/verification** since 2026-09-10T12:29:40Z: dependency 'flux-system/external-secrets' is not ready
- **Kustomization flux-system/weave-gitops** since 2026-09-10T12:29:40Z: dependency 'flux-system/identity' is not ready

## Every row

| Kind | Namespace | Name | State | Applied revision | Since | Message |
|---|---|---|---|---|---|---|
| HelmRelease | commerce | lago | Not ready | 1.28.0 | 2026-09-10T12:22:40Z | Running 'install' action with timeout of 15m0s |
| Kustomization | flux-system | agent-workforce | Not ready | main@b88fff0 | 2026-09-10T12:29:42Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | alerts | Not ready | main@b88fff0 | 2026-09-10T12:29:40Z | dependency 'flux-system/alerts-secret' is not ready |
| Kustomization | flux-system | alerts-github | Not ready | main@b88fff0 | 2026-09-10T12:29:40Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | alerts-secret | Not ready | main@b88fff0 | 2026-09-10T12:29:40Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | autoscaler | Not ready | main@b88fff0 | 2026-09-10T12:29:40Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | backstage | Not ready | main@b88fff0 | 2026-09-10T12:29:41Z | dependency 'flux-system/external-secrets' is not ready |
| Kustomization | flux-system | chaos | Not ready | main@b88fff0 | 2026-09-10T12:29:42Z | dependency 'flux-system/chaos-mesh' is not ready |
| Kustomization | flux-system | chaos-mesh | Not ready | main@b88fff0 | 2026-09-10T12:29:40Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | cluster-state | Not ready | main@b88fff0 | 2026-09-10T12:29:40Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | commerce | Not ready | main@2b48589 | 2026-09-10T12:22:39Z | Reconciliation in progress |
| Kustomization | flux-system | commerce-data | Not ready | main@b88fff0 | 2026-09-10T12:29:41Z | dependency 'flux-system/external-secrets' is not ready |
| Kustomization | flux-system | crossplane | Not ready | main@b88fff0 | 2026-09-10T12:29:41Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | crossplane-providerconfig | Not ready | main@b88fff0 | 2026-09-10T12:29:41Z | dependency 'flux-system/crossplane-providers' is not ready |
| Kustomization | flux-system | crossplane-providers | Not ready | main@b88fff0 | 2026-09-10T12:29:41Z | dependency 'flux-system/crossplane' is not ready |
| Kustomization | flux-system | cyrus | Not ready | main@17a5ceb | 2026-09-10T12:29:46Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | dagster | Not ready | main@b88fff0 | 2026-09-10T12:29:41Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | dns | Not ready | main@b88fff0 | 2026-09-10T12:29:40Z | dependency 'flux-system/edge' is not ready |
| Kustomization | flux-system | drills | Not ready | main@b88fff0 | 2026-09-10T12:29:40Z | dependency 'flux-system/alerts-github' is not ready |
| Kustomization | flux-system | estate-db | Not ready | main@b88fff0 | 2026-09-10T12:29:40Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | estate-db-migrate | Not ready | main@b88fff0 | 2026-09-10T12:29:41Z | dependency 'flux-system/estate-db' is not ready |
| Kustomization | flux-system | external-secrets | Not ready | main@b88fff0 | 2026-09-10T12:30:09Z | Reconciliation in progress |
| Kustomization | flux-system | flux-webhook | Not ready | main@b88fff0 | 2026-09-10T12:29:40Z | dependency 'flux-system/edge' is not ready |
| Kustomization | flux-system | guacamole | Not ready | main@5b6aeea | 2026-09-10T12:29:42Z | dependency 'flux-system/identity' is not ready |
| Kustomization | flux-system | gvisor-runtime | Not ready | main@b88fff0 | 2026-09-10T12:29:42Z | dependency 'flux-system/nodesoftware-operator' is not ready |
| Kustomization | flux-system | healing | Not ready | main@b88fff0 | 2026-09-10T12:29:41Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | healing-analyzer | Not ready | main@b88fff0 | 2026-09-10T12:29:41Z | dependency 'flux-system/healing-k8sgpt' is not ready |
| Kustomization | flux-system | healing-k8sgpt | Not ready | main@b88fff0 | 2026-09-10T12:29:41Z | dependency 'flux-system/healing' is not ready |
| Kustomization | flux-system | healthchecks | Not ready | main@b88fff0 | 2026-09-10T12:29:41Z | dependency 'flux-system/identity' is not ready |
| Kustomization | flux-system | hermes-agent | Not ready | main@b88fff0 | 2026-09-10T12:29:41Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | hindsight | Not ready | main@b88fff0 | 2026-09-10T12:29:42Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | human-vault | Not ready | main@b88fff0 | 2026-09-10T12:29:40Z | dependency 'flux-system/external-secrets' is not ready |
| Kustomization | flux-system | human-vault-bridge | Not ready | main@b88fff0 | 2026-09-10T12:29:40Z | dependency 'flux-system/human-vault' is not ready |
| Kustomization | flux-system | identity | Not ready | main@b88fff0 | 2026-09-10T12:29:40Z | dependency 'flux-system/edge' is not ready |
| Kustomization | flux-system | image-automation | Not ready | main@b88fff0 | 2026-09-10T12:29:41Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | keda | Not ready | main@b88fff0 | 2026-09-10T12:29:41Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | llm | Not ready | main@b88fff0 | 2026-09-10T12:29:41Z | dependency 'flux-system/edge' is not ready |
| Kustomization | flux-system | mcp | Not ready | main@b88fff0 | 2026-09-10T12:29:41Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | metrics-server | Not ready | main@b88fff0 | 2026-09-10T12:29:41Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | monitoring | Not ready | main@b88fff0 | 2026-09-10T12:29:40Z | dependency 'flux-system/edge' is not ready |
| Kustomization | flux-system | monitoring-rules | Not ready | main@b88fff0 | 2026-09-10T12:29:41Z | dependency 'flux-system/monitoring' is not ready |
| Kustomization | flux-system | nodesoftware-operator | Not ready | main@b88fff0 | 2026-09-10T12:29:41Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | notify | Not ready | main@b88fff0 | 2026-09-10T12:29:41Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | observability | Not ready | main@b88fff0 | 2026-09-10T12:29:41Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | observability-collector | Not ready | main@b88fff0 | 2026-09-10T12:29:40Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | otto-gateway | Not ready | main@b88fff0 | 2026-09-10T12:29:42Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | otto-golden | Not ready | main@b88fff0 | 2026-09-10T12:29:41Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | otto-golden-secret | Not ready | main@b88fff0 | 2026-09-10T12:29:40Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | prospector-platform | Not ready | main@b88fff0 | 2026-09-10T12:29:39Z | dependency 'flux-system/edge' is not ready |
| Kustomization | flux-system | reloader | Not ready | main@b88fff0 | 2026-09-10T12:29:39Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | research-engine | Not ready | main@b88fff0 | 2026-09-10T12:29:42Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | robusta | Not ready | main@b88fff0 | 2026-09-10T12:29:39Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | sandbox-launch | Not ready | main@b88fff0 | 2026-09-10T12:30:09Z | Reconciliation in progress |
| Kustomization | flux-system | scheduling | Not ready | main@b88fff0 | 2026-09-10T12:30:09Z | Reconciliation in progress |
| Kustomization | flux-system | science | Not ready | main@b88fff0 | 2026-09-10T12:29:42Z | dependency 'flux-system/observability' is not ready |
| Kustomization | flux-system | secret-store | Not ready | main@b88fff0 | 2026-09-10T12:29:39Z | dependency 'flux-system/external-secrets' is not ready |
| Kustomization | flux-system | spire | Not ready | main@b88fff0 | 2026-09-10T12:29:40Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | tailscale | Not ready | main@d3ab8a2 | 2026-09-10T12:29:42Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | verification | Not ready | main@b88fff0 | 2026-09-10T12:29:40Z | dependency 'flux-system/external-secrets' is not ready |
| Kustomization | flux-system | weave-gitops | Not ready | main@b88fff0 | 2026-09-10T12:29:40Z | dependency 'flux-system/identity' is not ready |
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
| Kustomization | flux-system | backstage-namespace | Ready | main@8730193 | 2026-09-10T12:29:14Z |  |
| Kustomization | flux-system | calico | Ready | main@8730193 | 2026-09-10T12:29:02Z |  |
| Kustomization | flux-system | cross-node-drill | Ready | main@8730193 | 2026-09-10T12:29:12Z |  |
| Kustomization | flux-system | edge | Ready | main@8730193 | 2026-09-10T12:29:47Z |  |
| Kustomization | flux-system | estate-catalog | Ready | latest@sha256:8ab0d9286bc2769859d864f54d | 2026-09-10T12:29:43Z |  |
| Kustomization | flux-system | estate-db-operator | Ready | main@8730193 | 2026-09-10T12:29:17Z |  |
| Kustomization | flux-system | event-bus | Ready | main@8730193 | 2026-09-10T12:29:43Z |  |
| Kustomization | flux-system | feature-register | Ready | main@8730193 | 2026-09-10T12:29:19Z |  |
| Kustomization | flux-system | flux-system | Ready | main@8730193 | 2026-09-10T12:29:11Z |  |
| Kustomization | flux-system | gateway-api-crds | Ready | v1.5.1@e7677b7 | 2026-09-10T12:29:22Z |  |
| Kustomization | flux-system | jit | Ready | main@8730193 | 2026-09-10T12:29:25Z |  |
| Kustomization | flux-system | kyverno | Ready | main@8730193 | 2026-09-10T12:29:13Z |  |
| Kustomization | flux-system | ns-fences | Ready | main@8730193 | 2026-09-10T12:29:38Z |  |
| Kustomization | flux-system | priority-classes | Ready | main@8730193 | 2026-09-10T12:29:15Z |  |
| Kustomization | flux-system | prospector | Ready | main@7453d76 | 2026-09-10T12:22:57Z |  |
| Kustomization | flux-system | rbac | Ready | main@8730193 | 2026-09-10T12:29:39Z |  |
| Kustomization | flux-system | rbac-floor | Ready | main@8730193 | 2026-09-10T12:29:06Z |  |
| Kustomization | flux-system | rbac-identity | Ready | main@8730193 | 2026-09-10T12:29:19Z |  |
| Kustomization | flux-system | sandbox-live | Ready | sandbox/launch@5844e79 | 2026-09-10T12:29:57Z |  |
| Kustomization | flux-system | searxng | Ready | main@8730193 | 2026-09-10T12:29:07Z |  |
| Kustomization | flux-system | staging | Ready | main@8730193 | 2026-09-10T12:29:04Z |  |
| Kustomization | flux-system | trivy | Ready | main@8730193 | 2026-09-10T12:29:17Z |  |
