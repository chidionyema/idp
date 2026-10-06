# Flux: what is applied

Read from the cluster receipt taken at 2026-10-06T03:00:14Z. Every Kustomization and HelmRelease, with the revision Flux last applied. **Suspended** is a switch somebody turned off on purpose (temporal, commerce, commerce-data, event-bus), not a defect; **Unknown** is a row Flux has never graded.

**71 objects: 50 ready, 18 not ready, 0 unknown, 3 suspended.**

## Not ready right now

- **HelmRelease commerce/lago** since 2026-09-26T09:48:22Z: Could not determine release state: unable to determine state for release with status 'uninstalling'
- **HelmRelease coroot/coroot** since 2026-09-29T06:30:04Z: Helm upgrade failed for release coroot/coroot with chart coroot@0.22.0: failed early due to stalled resources: [Deployment/coroot/coroot-prometheus-server status: 'Failed']
- **HelmRelease crossplane-system/crossplane** since 2026-09-29T07:14:14Z: Helm rollback to previous release crossplane-system/crossplane.v28 with chart crossplane@2.4.0 succeeded
- **HelmRelease dagster/dagster** since 2026-09-29T06:21:51Z: Helm rollback to previous release dagster/dagster.v250 with chart dagster@1.13.19 succeeded
- **HelmRelease observability/langfuse** since 2026-09-25T10:40:26Z: dependency 'observability/signoz' is not ready
- **HelmRelease spire-mgmt/spire** since 2026-09-26T20:11:52Z: Helm upgrade failed for release spire-mgmt/spire with chart spire@0.30.1: timeout waiting for: [DaemonSet/spire-mgmt/spire-agent status: 'InProgress', Deployment/spire-mgmt/spire-spiffe-oidc-discovery-provider status: 'InProgress']
- **Kustomization flux-system/agent-workforce** since 2026-10-06T02:55:28Z: dependency 'flux-system/llm' is not ready
- **Kustomization flux-system/estate-db-migrate** since 2026-10-06T02:57:45Z: ExternalSecret/temporal/estate-db-role-temporal dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-secrets.io": failed to call webhook: Post "https://external-secrets-webhook.external-secrets.svc:443/validate-external-secrets-io-v1-externalsecret?timeout=15s": EOF 
- **Kustomization flux-system/flux-system** since 2026-10-06T03:00:05Z: Reconciliation in progress
- **Kustomization flux-system/hermes-agent** since 2026-10-06T02:56:14Z: dependency 'flux-system/llm' is not ready
- **Kustomization flux-system/hindsight** since 2026-10-06T02:55:53Z: dependency 'flux-system/llm' is not ready
- **Kustomization flux-system/jit** since 2026-10-06T02:56:36Z: health check failed after 202.090446ms: failed early due to stalled resources: [Deployment/jit/jit-broker status: 'Failed']
- **Kustomization flux-system/llm** since 2026-10-06T02:55:23Z: dependency 'flux-system/estate-db-migrate' is not ready
- **Kustomization flux-system/otto-gateway** since 2026-10-06T02:58:02Z: health check failed after 245.597953ms: failed early due to stalled resources: [Deployment/otto-gateway/otto-gateway status: 'Failed']
- **Kustomization flux-system/otto-golden** since 2026-10-06T02:59:34Z: dependency 'flux-system/llm' is not ready
- **Kustomization flux-system/quad-ledger** since 2026-10-06T02:58:21Z: health check failed after 86.878052ms: failed early due to stalled resources: [Deployment/quad/quad-ledger status: 'Failed']
- **Kustomization flux-system/research-engine** since 2026-10-06T02:55:30Z: dependency 'flux-system/llm' is not ready
- **Kustomization flux-system/temporal** since 2026-10-06T02:59:34Z: dependency 'flux-system/estate-db-migrate' is not ready

## Every row

| Kind | Namespace | Name | State | Applied revision | Since | Message |
|---|---|---|---|---|---|---|
| HelmRelease | commerce | lago | Not ready | 1.28.0 | 2026-09-26T09:48:22Z | Could not determine release state: unable to determine state for release with status 'uninstalling' |
| HelmRelease | coroot | coroot | Not ready | 0.22.0 | 2026-09-29T06:30:04Z | Helm upgrade failed for release coroot/coroot with chart coroot@0.22.0: failed early due to stalled resources: [Deployment/coroot/coroot-prometheus-server statu |
| HelmRelease | crossplane-system | crossplane | Not ready | 1.15.1 | 2026-09-29T07:14:14Z | Helm rollback to previous release crossplane-system/crossplane.v28 with chart crossplane@2.4.0 succeeded |
| HelmRelease | dagster | dagster | Not ready | 1.13.19 | 2026-09-29T06:21:51Z | Helm rollback to previous release dagster/dagster.v250 with chart dagster@1.13.19 succeeded |
| HelmRelease | observability | langfuse | Not ready | 2.0.2 | 2026-09-25T10:40:26Z | dependency 'observability/signoz' is not ready |
| HelmRelease | spire-mgmt | spire | Not ready | 0.30.1 | 2026-09-26T20:11:52Z | Helm upgrade failed for release spire-mgmt/spire with chart spire@0.30.1: timeout waiting for: [DaemonSet/spire-mgmt/spire-agent status: 'InProgress', Deploymen |
| Kustomization | flux-system | agent-workforce | Not ready | main@32e71ec | 2026-10-06T02:55:28Z | dependency 'flux-system/llm' is not ready |
| Kustomization | flux-system | estate-db-migrate | Not ready | main@32e71ec | 2026-10-06T02:57:45Z | ExternalSecret/temporal/estate-db-role-temporal dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.externa |
| Kustomization | flux-system | flux-system | Not ready | main@32e71ec | 2026-10-06T03:00:05Z | Reconciliation in progress |
| Kustomization | flux-system | hermes-agent | Not ready | main@32e71ec | 2026-10-06T02:56:14Z | dependency 'flux-system/llm' is not ready |
| Kustomization | flux-system | hindsight | Not ready | main@32e71ec | 2026-10-06T02:55:53Z | dependency 'flux-system/llm' is not ready |
| Kustomization | flux-system | jit | Not ready | main@32e71ec | 2026-10-06T02:56:36Z | health check failed after 202.090446ms: failed early due to stalled resources: [Deployment/jit/jit-broker status: 'Failed'] |
| Kustomization | flux-system | llm | Not ready | main@32e71ec | 2026-10-06T02:55:23Z | dependency 'flux-system/estate-db-migrate' is not ready |
| Kustomization | flux-system | otto-gateway | Not ready | main@32e71ec | 2026-10-06T02:58:02Z | health check failed after 245.597953ms: failed early due to stalled resources: [Deployment/otto-gateway/otto-gateway status: 'Failed'] |
| Kustomization | flux-system | otto-golden | Not ready | main@32e71ec | 2026-10-06T02:59:34Z | dependency 'flux-system/llm' is not ready |
| Kustomization | flux-system | quad-ledger | Not ready | main@32e71ec | 2026-10-06T02:58:21Z | health check failed after 86.878052ms: failed early due to stalled resources: [Deployment/quad/quad-ledger status: 'Failed'] |
| Kustomization | flux-system | research-engine | Not ready | main@32e71ec | 2026-10-06T02:55:30Z | dependency 'flux-system/llm' is not ready |
| Kustomization | flux-system | temporal | Not ready | main@32e71ec | 2026-10-06T02:59:34Z | dependency 'flux-system/estate-db-migrate' is not ready |
| HelmRelease | flux-system | vendor-bridge | Suspended | 0.1.0+991920d87ecd | 2026-10-03T13:56:39Z |  |
| HelmRelease | observability | signoz | Suspended | 0.138.0 | 2026-09-26T16:24:12Z |  |
| HelmRelease | tigera-operator | tigera-operator | Suspended | v3.32.2 | 2026-09-06T19:38:02Z |  |
| HelmRelease | cert-manager | cert-manager | Ready | v1.21.1 | 2026-09-30T23:26:48Z |  |
| HelmRelease | edge | external-dns | Ready | 1.21.1 | 2026-09-26T10:39:02Z |  |
| HelmRelease | edge | traefik | Ready | 41.3.0 | 2026-09-26T09:48:30Z |  |
| HelmRelease | estate-db | cloudnative-pg | Ready | 0.29.0 | 2026-09-26T10:01:26Z |  |
| HelmRelease | event-bus | nats | Ready | 2.14.6 | 2026-09-26T09:48:21Z |  |
| HelmRelease | external-secrets | external-secrets | Ready | 2.9.0 | 2026-09-27T17:09:36Z |  |
| HelmRelease | healing | descheduler | Ready | 0.36.0 | 2026-09-26T09:48:21Z |  |
| HelmRelease | healing | k8sgpt-operator | Ready | 0.2.29 | 2026-09-26T09:48:26Z |  |
| HelmRelease | hindsight | hindsight | Ready | 0.9.2 | 2026-09-29T03:07:48Z |  |
| HelmRelease | identity | oauth2-proxy | Ready | 10.7.0 | 2026-09-29T00:03:03Z |  |
| HelmRelease | keda | keda | Ready | 2.20.2 | 2026-09-26T10:39:03Z |  |
| HelmRelease | keda | keda-add-ons-http | Ready | 0.15.0 | 2026-09-26T10:39:31Z |  |
| HelmRelease | kyverno | kyverno | Ready | 3.9.0 | 2026-09-26T10:01:28Z |  |
| HelmRelease | metrics-server | metrics-server | Ready | 3.14.0 | 2026-09-26T09:48:29Z |  |
| HelmRelease | monitoring | blackbox | Ready | 11.17.2 | 2026-09-26T11:01:14Z |  |
| HelmRelease | monitoring | kube-prometheus-stack | Ready | 88.6.0 | 2026-09-26T10:01:27Z |  |
| HelmRelease | observability | superset | Ready | 0.22.4 | 2026-09-26T10:39:02Z |  |
| HelmRelease | reloader | reloader | Ready | 2.2.16 | 2026-10-03T14:24:32Z |  |
| HelmRelease | spire-mgmt | spire-crds | Ready | 0.6.1 | 2026-09-26T09:48:25Z |  |
| HelmRelease | tailscale | tailscale-operator | Ready | 1.102.3 | 2026-09-26T09:48:27Z |  |
| HelmRelease | temporal | temporal | Ready | 1.6.0 | 2026-09-26T10:39:02Z |  |
| HelmRelease | trivy-system | trivy-operator | Ready | 0.36.0 | 2026-09-26T18:25:31Z |  |
| HelmRelease | weave-gitops | weave-gitops | Ready | 4.0.36 | 2026-09-26T09:48:27Z |  |
| Kustomization | flux-system | backstage | Ready | main@32e71ec | 2026-10-06T02:55:56Z |  |
| Kustomization | flux-system | backstage-namespace | Ready | main@32e71ec | 2026-10-06T02:59:21Z |  |
| Kustomization | flux-system | dns | Ready | main@32e71ec | 2026-10-06T02:58:27Z |  |
| Kustomization | flux-system | edge | Ready | main@32e71ec | 2026-10-06T02:59:05Z |  |
| Kustomization | flux-system | epistemic-fabric | Ready | main@32e71ec | 2026-10-06T02:57:20Z |  |
| Kustomization | flux-system | estate-db | Ready | main@32e71ec | 2026-10-06T02:57:17Z |  |
| Kustomization | flux-system | estate-db-operator | Ready | main@32e71ec | 2026-10-06T02:51:26Z |  |
| Kustomization | flux-system | event-bus | Ready | main@32e71ec | 2026-10-06T02:58:21Z |  |
| Kustomization | flux-system | external-secrets | Ready | main@32e71ec | 2026-10-06T02:57:03Z |  |
| Kustomization | flux-system | flannel | Ready | main@32e71ec | 2026-10-06T02:58:35Z |  |
| Kustomization | flux-system | gateway-api-crds | Ready | v1.5.1@e7677b7 | 2026-10-06T02:59:30Z |  |
| Kustomization | flux-system | github-app-creds | Ready | main@32e71ec | 2026-10-06T02:56:22Z |  |
| Kustomization | flux-system | image-automation | Ready | main@32e71ec | 2026-10-06T02:55:21Z |  |
| Kustomization | flux-system | kyverno | Ready | main@32e71ec | 2026-10-06T02:58:21Z |  |
| Kustomization | flux-system | mcp | Ready | main@32e71ec | 2026-10-06T02:57:36Z |  |
| Kustomization | flux-system | monitoring | Ready | main@32e71ec | 2026-10-06T02:58:39Z |  |
| Kustomization | flux-system | monitoring-rules | Ready | main@32e71ec | 2026-10-06T02:59:04Z |  |
| Kustomization | flux-system | ns-fences | Ready | main@32e71ec | 2026-10-06T02:53:44Z |  |
| Kustomization | flux-system | otto-golden-secret | Ready | main@32e71ec | 2026-10-06T02:57:51Z |  |
| Kustomization | flux-system | priority-classes | Ready | main@32e71ec | 2026-10-06T02:53:33Z |  |
| Kustomization | flux-system | quad-ledger-exception | Ready | main@32e71ec | 2026-10-06T02:50:34Z |  |
| Kustomization | flux-system | reloader | Ready | main@32e71ec | 2026-10-06T02:50:15Z |  |
| Kustomization | flux-system | searxng | Ready | main@32e71ec | 2026-10-06T02:56:29Z |  |
| Kustomization | flux-system | secret-store | Ready | main@32e71ec | 2026-10-06T02:54:11Z |  |
| Kustomization | flux-system | tailscale | Ready | main@32e71ec | 2026-10-06T02:55:16Z |  |
| Kustomization | flux-system | unified-memory | Ready | main@32e71ec | 2026-10-06T02:58:03Z |  |
| Kustomization | flux-system | voice-router | Ready | main@32e71ec | 2026-10-06T02:55:05Z |  |
