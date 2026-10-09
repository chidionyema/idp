# Flux: what is applied

Read from the cluster receipt taken at 2026-10-09T05:45:13Z. Every Kustomization and HelmRelease, with the revision Flux last applied. **Suspended** is a switch somebody turned off on purpose (temporal, commerce, commerce-data, event-bus), not a defect; **Unknown** is a row Flux has never graded.

**71 objects: 36 ready, 32 not ready, 0 unknown, 3 suspended.**

## Not ready right now

- **HelmRelease commerce/lago** since 2026-09-26T09:48:22Z: Could not determine release state: unable to determine state for release with status 'uninstalling'
- **HelmRelease coroot/coroot** since 2026-09-29T06:30:04Z: Helm upgrade failed for release coroot/coroot with chart coroot@0.22.0: failed early due to stalled resources: [Deployment/coroot/coroot-prometheus-server status: 'Failed']
- **HelmRelease crossplane-system/crossplane** since 2026-09-29T07:14:14Z: Helm rollback to previous release crossplane-system/crossplane.v28 with chart crossplane@2.4.0 succeeded
- **HelmRelease dagster/dagster** since 2026-09-29T06:21:51Z: Helm rollback to previous release dagster/dagster.v250 with chart dagster@1.13.19 succeeded
- **HelmRelease observability/langfuse** since 2026-09-25T10:40:26Z: dependency 'observability/signoz' is not ready
- **HelmRelease spire-mgmt/spire** since 2026-09-26T20:11:52Z: Helm upgrade failed for release spire-mgmt/spire with chart spire@0.30.1: timeout waiting for: [DaemonSet/spire-mgmt/spire-agent status: 'InProgress', Deployment/spire-mgmt/spire-spiffe-oidc-discovery-provider status: 'InProgress']
- **Kustomization flux-system/agent-workforce** since 2026-10-09T05:44:27Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/backstage** since 2026-10-09T05:44:26Z: dependency 'flux-system/external-secrets' revision is not up to date
- **Kustomization flux-system/epistemic-fabric** since 2026-10-09T05:44:26Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/estate-db** since 2026-10-09T05:44:26Z: dependency 'flux-system/estate-db-operator' revision is not up to date
- **Kustomization flux-system/estate-db-migrate** since 2026-10-09T05:44:26Z: dependency 'flux-system/estate-db' is not ready
- **Kustomization flux-system/estate-db-operator** since 2026-10-09T05:44:56Z: Reconciliation in progress
- **Kustomization flux-system/event-bus** since 2026-10-09T05:44:25Z: dependency 'flux-system/priority-classes' is not ready
- **Kustomization flux-system/flannel** since 2026-10-09T05:44:59Z: Reconciliation in progress
- **Kustomization flux-system/github-app-creds** since 2026-10-09T05:44:26Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/hermes-agent** since 2026-10-09T05:44:27Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/hindsight** since 2026-10-09T05:44:27Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/image-automation** since 2026-10-09T05:44:26Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/jit** since 2026-10-09T05:44:26Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/llm** since 2026-10-09T05:44:26Z: dependency 'flux-system/estate-db-migrate' revision is not up to date
- **Kustomization flux-system/mcp** since 2026-10-09T05:44:26Z: dependency 'flux-system/edge' revision is not up to date
- **Kustomization flux-system/monitoring-rules** since 2026-10-09T05:44:52Z: Reconciliation in progress
- **Kustomization flux-system/otto-gateway** since 2026-10-09T05:44:26Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/otto-golden** since 2026-10-09T05:44:27Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/otto-golden-secret** since 2026-10-09T05:44:25Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/quad-ledger** since 2026-10-09T05:44:26Z: dependency 'flux-system/estate-db' is not ready
- **Kustomization flux-system/research-engine** since 2026-10-09T05:44:27Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/secret-store** since 2026-10-09T05:44:22Z: dependency 'flux-system/external-secrets' revision is not up to date
- **Kustomization flux-system/tailscale** since 2026-10-09T05:44:26Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/temporal** since 2026-10-09T05:44:27Z: dependency 'flux-system/edge' revision is not up to date
- **Kustomization flux-system/unified-memory** since 2026-10-09T05:44:27Z: dependency 'flux-system/estate-db' is not ready
- **Kustomization flux-system/voice-router** since 2026-10-09T05:44:56Z: Reconciliation in progress

## Every row

| Kind | Namespace | Name | State | Applied revision | Since | Message |
|---|---|---|---|---|---|---|
| HelmRelease | commerce | lago | Not ready | 1.28.0 | 2026-09-26T09:48:22Z | Could not determine release state: unable to determine state for release with status 'uninstalling' |
| HelmRelease | coroot | coroot | Not ready | 0.22.0 | 2026-09-29T06:30:04Z | Helm upgrade failed for release coroot/coroot with chart coroot@0.22.0: failed early due to stalled resources: [Deployment/coroot/coroot-prometheus-server statu |
| HelmRelease | crossplane-system | crossplane | Not ready | 1.15.1 | 2026-09-29T07:14:14Z | Helm rollback to previous release crossplane-system/crossplane.v28 with chart crossplane@2.4.0 succeeded |
| HelmRelease | dagster | dagster | Not ready | 1.13.19 | 2026-09-29T06:21:51Z | Helm rollback to previous release dagster/dagster.v250 with chart dagster@1.13.19 succeeded |
| HelmRelease | observability | langfuse | Not ready | 2.0.2 | 2026-09-25T10:40:26Z | dependency 'observability/signoz' is not ready |
| HelmRelease | spire-mgmt | spire | Not ready | 0.30.1 | 2026-09-26T20:11:52Z | Helm upgrade failed for release spire-mgmt/spire with chart spire@0.30.1: timeout waiting for: [DaemonSet/spire-mgmt/spire-agent status: 'InProgress', Deploymen |
| Kustomization | flux-system | agent-workforce | Not ready | main@7500cb1 | 2026-10-09T05:44:27Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | backstage | Not ready | main@7500cb1 | 2026-10-09T05:44:26Z | dependency 'flux-system/external-secrets' revision is not up to date |
| Kustomization | flux-system | epistemic-fabric | Not ready | main@7500cb1 | 2026-10-09T05:44:26Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | estate-db | Not ready | main@7500cb1 | 2026-10-09T05:44:26Z | dependency 'flux-system/estate-db-operator' revision is not up to date |
| Kustomization | flux-system | estate-db-migrate | Not ready | main@7500cb1 | 2026-10-09T05:44:26Z | dependency 'flux-system/estate-db' is not ready |
| Kustomization | flux-system | estate-db-operator | Not ready | main@7500cb1 | 2026-10-09T05:44:56Z | Reconciliation in progress |
| Kustomization | flux-system | event-bus | Not ready | main@7500cb1 | 2026-10-09T05:44:25Z | dependency 'flux-system/priority-classes' is not ready |
| Kustomization | flux-system | flannel | Not ready | main@7500cb1 | 2026-10-09T05:44:59Z | Reconciliation in progress |
| Kustomization | flux-system | github-app-creds | Not ready | main@7500cb1 | 2026-10-09T05:44:26Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | hermes-agent | Not ready | main@7500cb1 | 2026-10-09T05:44:27Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | hindsight | Not ready | main@7500cb1 | 2026-10-09T05:44:27Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | image-automation | Not ready | main@7500cb1 | 2026-10-09T05:44:26Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | jit | Not ready | main@7500cb1 | 2026-10-09T05:44:26Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | llm | Not ready | main@7500cb1 | 2026-10-09T05:44:26Z | dependency 'flux-system/estate-db-migrate' revision is not up to date |
| Kustomization | flux-system | mcp | Not ready | main@7500cb1 | 2026-10-09T05:44:26Z | dependency 'flux-system/edge' revision is not up to date |
| Kustomization | flux-system | monitoring-rules | Not ready | main@7500cb1 | 2026-10-09T05:44:52Z | Reconciliation in progress |
| Kustomization | flux-system | otto-gateway | Not ready | main@7500cb1 | 2026-10-09T05:44:26Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | otto-golden | Not ready | main@7500cb1 | 2026-10-09T05:44:27Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | otto-golden-secret | Not ready | main@7500cb1 | 2026-10-09T05:44:25Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | quad-ledger | Not ready | main@7500cb1 | 2026-10-09T05:44:26Z | dependency 'flux-system/estate-db' is not ready |
| Kustomization | flux-system | research-engine | Not ready | main@7500cb1 | 2026-10-09T05:44:27Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | secret-store | Not ready | main@7500cb1 | 2026-10-09T05:44:22Z | dependency 'flux-system/external-secrets' revision is not up to date |
| Kustomization | flux-system | tailscale | Not ready | main@7500cb1 | 2026-10-09T05:44:26Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | temporal | Not ready | main@7500cb1 | 2026-10-09T05:44:27Z | dependency 'flux-system/edge' revision is not up to date |
| Kustomization | flux-system | unified-memory | Not ready | main@7500cb1 | 2026-10-09T05:44:27Z | dependency 'flux-system/estate-db' is not ready |
| Kustomization | flux-system | voice-router | Not ready | main@7500cb1 | 2026-10-09T05:44:56Z | Reconciliation in progress |
| HelmRelease | flux-system | vendor-bridge | Suspended | 0.1.0+991920d87ecd | 2026-10-03T13:56:39Z |  |
| HelmRelease | observability | signoz | Suspended | 0.138.0 | 2026-09-26T16:24:12Z |  |
| HelmRelease | tigera-operator | tigera-operator | Suspended | v3.32.2 | 2026-09-06T19:38:02Z |  |
| HelmRelease | cert-manager | cert-manager | Ready | v1.21.1 | 2026-09-30T23:26:48Z |  |
| HelmRelease | edge | external-dns | Ready | 1.21.1 | 2026-09-26T10:39:02Z |  |
| HelmRelease | edge | traefik | Ready | 41.3.0 | 2026-09-26T09:48:30Z |  |
| HelmRelease | estate-db | cloudnative-pg | Ready | 0.29.0 | 2026-09-26T10:01:26Z |  |
| HelmRelease | event-bus | nats | Ready | 2.14.6 | 2026-10-07T19:34:40Z |  |
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
| Kustomization | flux-system | backstage-namespace | Ready | main@0711374 | 2026-10-09T05:44:22Z |  |
| Kustomization | flux-system | dns | Ready | main@0711374 | 2026-10-09T05:44:59Z |  |
| Kustomization | flux-system | edge | Ready | main@7500cb1 | 2026-10-09T05:43:25Z |  |
| Kustomization | flux-system | external-secrets | Ready | main@7500cb1 | 2026-10-09T05:43:47Z |  |
| Kustomization | flux-system | flux-system | Ready | main@0711374 | 2026-10-09T05:44:25Z |  |
| Kustomization | flux-system | gateway-api-crds | Ready | v1.5.1@e7677b7 | 2026-10-09T05:34:06Z |  |
| Kustomization | flux-system | kyverno | Ready | main@0711374 | 2026-10-09T05:44:55Z |  |
| Kustomization | flux-system | monitoring | Ready | main@0711374 | 2026-10-09T05:44:43Z |  |
| Kustomization | flux-system | ns-fences | Ready | main@0711374 | 2026-10-09T05:44:56Z |  |
| Kustomization | flux-system | priority-classes | Ready | main@0711374 | 2026-10-09T05:44:38Z |  |
| Kustomization | flux-system | quad-ledger-exception | Ready | main@0711374 | 2026-10-09T05:44:52Z |  |
| Kustomization | flux-system | reloader | Ready | main@0711374 | 2026-10-09T05:44:23Z |  |
| Kustomization | flux-system | searxng | Ready | main@0711374 | 2026-10-09T05:44:22Z |  |
