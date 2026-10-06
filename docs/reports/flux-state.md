# Flux: what is applied

Read from the cluster receipt taken at 2026-10-06T21:15:13Z. Every Kustomization and HelmRelease, with the revision Flux last applied. **Suspended** is a switch somebody turned off on purpose (temporal, commerce, commerce-data, event-bus), not a defect; **Unknown** is a row Flux has never graded.

**71 objects: 58 ready, 10 not ready, 0 unknown, 3 suspended.**

## Not ready right now

- **HelmRelease commerce/lago** since 2026-09-26T09:48:22Z: Could not determine release state: unable to determine state for release with status 'uninstalling'
- **HelmRelease coroot/coroot** since 2026-09-29T06:30:04Z: Helm upgrade failed for release coroot/coroot with chart coroot@0.22.0: failed early due to stalled resources: [Deployment/coroot/coroot-prometheus-server status: 'Failed']
- **HelmRelease crossplane-system/crossplane** since 2026-09-29T07:14:14Z: Helm rollback to previous release crossplane-system/crossplane.v28 with chart crossplane@2.4.0 succeeded
- **HelmRelease dagster/dagster** since 2026-09-29T06:21:51Z: Helm rollback to previous release dagster/dagster.v250 with chart dagster@1.13.19 succeeded
- **HelmRelease observability/langfuse** since 2026-09-25T10:40:26Z: dependency 'observability/signoz' is not ready
- **HelmRelease spire-mgmt/spire** since 2026-09-26T20:11:52Z: Helm upgrade failed for release spire-mgmt/spire with chart spire@0.30.1: timeout waiting for: [DaemonSet/spire-mgmt/spire-agent status: 'InProgress', Deployment/spire-mgmt/spire-spiffe-oidc-discovery-provider status: 'InProgress']
- **Kustomization flux-system/agent-workforce** since 2026-10-06T21:10:27Z: post build failed for 'GithubAccessToken.v1alpha1.generators.external-secrets.io/agent-workforce-github': envsubst error: variable substitution failed: variable not set (strict mode): "githubAppIDQuoted"
- **Kustomization flux-system/jit** since 2026-10-06T21:08:56Z: health check failed after 804.286749ms: failed early due to stalled resources: [Deployment/jit/jit-broker status: 'Failed']
- **Kustomization flux-system/otto-gateway** since 2026-10-06T21:12:44Z: health check failed after 850.040967ms: failed early due to stalled resources: [Deployment/otto-gateway/otto-gateway status: 'Failed']
- **Kustomization flux-system/quad-ledger** since 2026-10-06T21:09:31Z: health check failed after 68.12376ms: failed early due to stalled resources: [Deployment/quad/quad-ledger status: 'Failed']

## Every row

| Kind | Namespace | Name | State | Applied revision | Since | Message |
|---|---|---|---|---|---|---|
| HelmRelease | commerce | lago | Not ready | 1.28.0 | 2026-09-26T09:48:22Z | Could not determine release state: unable to determine state for release with status 'uninstalling' |
| HelmRelease | coroot | coroot | Not ready | 0.22.0 | 2026-09-29T06:30:04Z | Helm upgrade failed for release coroot/coroot with chart coroot@0.22.0: failed early due to stalled resources: [Deployment/coroot/coroot-prometheus-server statu |
| HelmRelease | crossplane-system | crossplane | Not ready | 1.15.1 | 2026-09-29T07:14:14Z | Helm rollback to previous release crossplane-system/crossplane.v28 with chart crossplane@2.4.0 succeeded |
| HelmRelease | dagster | dagster | Not ready | 1.13.19 | 2026-09-29T06:21:51Z | Helm rollback to previous release dagster/dagster.v250 with chart dagster@1.13.19 succeeded |
| HelmRelease | observability | langfuse | Not ready | 2.0.2 | 2026-09-25T10:40:26Z | dependency 'observability/signoz' is not ready |
| HelmRelease | spire-mgmt | spire | Not ready | 0.30.1 | 2026-09-26T20:11:52Z | Helm upgrade failed for release spire-mgmt/spire with chart spire@0.30.1: timeout waiting for: [DaemonSet/spire-mgmt/spire-agent status: 'InProgress', Deploymen |
| Kustomization | flux-system | agent-workforce | Not ready | main@840d3f0 | 2026-10-06T21:10:27Z | post build failed for 'GithubAccessToken.v1alpha1.generators.external-secrets.io/agent-workforce-github': envsubst error: variable substitution failed: variable |
| Kustomization | flux-system | jit | Not ready | main@840d3f0 | 2026-10-06T21:08:56Z | health check failed after 804.286749ms: failed early due to stalled resources: [Deployment/jit/jit-broker status: 'Failed'] |
| Kustomization | flux-system | otto-gateway | Not ready | main@32e71ec | 2026-10-06T21:12:44Z | health check failed after 850.040967ms: failed early due to stalled resources: [Deployment/otto-gateway/otto-gateway status: 'Failed'] |
| Kustomization | flux-system | quad-ledger | Not ready | main@840d3f0 | 2026-10-06T21:09:31Z | health check failed after 68.12376ms: failed early due to stalled resources: [Deployment/quad/quad-ledger status: 'Failed'] |
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
| Kustomization | flux-system | backstage | Ready | main@840d3f0 | 2026-10-06T21:09:23Z |  |
| Kustomization | flux-system | backstage-namespace | Ready | main@840d3f0 | 2026-10-06T21:14:08Z |  |
| Kustomization | flux-system | dns | Ready | main@840d3f0 | 2026-10-06T21:05:41Z |  |
| Kustomization | flux-system | edge | Ready | main@840d3f0 | 2026-10-06T21:06:38Z |  |
| Kustomization | flux-system | epistemic-fabric | Ready | main@840d3f0 | 2026-10-06T21:09:23Z |  |
| Kustomization | flux-system | estate-db | Ready | main@840d3f0 | 2026-10-06T21:07:39Z |  |
| Kustomization | flux-system | estate-db-migrate | Ready | main@840d3f0 | 2026-10-06T21:09:31Z |  |
| Kustomization | flux-system | estate-db-operator | Ready | main@840d3f0 | 2026-10-06T21:06:48Z |  |
| Kustomization | flux-system | event-bus | Ready | main@840d3f0 | 2026-10-06T21:08:06Z |  |
| Kustomization | flux-system | external-secrets | Ready | main@840d3f0 | 2026-10-06T21:08:39Z |  |
| Kustomization | flux-system | flannel | Ready | main@840d3f0 | 2026-10-06T21:06:03Z |  |
| Kustomization | flux-system | flux-system | Ready | main@840d3f0 | 2026-10-06T21:06:56Z |  |
| Kustomization | flux-system | gateway-api-crds | Ready | v1.5.1@e7677b7 | 2026-10-06T21:06:17Z |  |
| Kustomization | flux-system | github-app-creds | Ready | main@840d3f0 | 2026-10-06T21:09:11Z |  |
| Kustomization | flux-system | hermes-agent | Ready | main@840d3f0 | 2026-10-06T21:12:39Z |  |
| Kustomization | flux-system | hindsight | Ready | main@840d3f0 | 2026-10-06T21:10:34Z |  |
| Kustomization | flux-system | image-automation | Ready | main@840d3f0 | 2026-10-06T21:09:08Z |  |
| Kustomization | flux-system | kyverno | Ready | main@840d3f0 | 2026-10-06T21:14:13Z |  |
| Kustomization | flux-system | llm | Ready | main@840d3f0 | 2026-10-06T21:08:29Z |  |
| Kustomization | flux-system | mcp | Ready | main@840d3f0 | 2026-10-06T21:10:03Z |  |
| Kustomization | flux-system | monitoring | Ready | main@840d3f0 | 2026-10-06T21:06:27Z |  |
| Kustomization | flux-system | monitoring-rules | Ready | main@840d3f0 | 2026-10-06T21:08:00Z |  |
| Kustomization | flux-system | ns-fences | Ready | main@840d3f0 | 2026-10-06T21:08:48Z |  |
| Kustomization | flux-system | otto-golden | Ready | main@840d3f0 | 2026-10-06T21:10:26Z |  |
| Kustomization | flux-system | otto-golden-secret | Ready | main@840d3f0 | 2026-10-06T21:08:00Z |  |
| Kustomization | flux-system | priority-classes | Ready | main@840d3f0 | 2026-10-06T21:06:37Z |  |
| Kustomization | flux-system | quad-ledger-exception | Ready | main@840d3f0 | 2026-10-06T21:07:21Z |  |
| Kustomization | flux-system | reloader | Ready | main@840d3f0 | 2026-10-06T21:06:27Z |  |
| Kustomization | flux-system | research-engine | Ready | main@840d3f0 | 2026-10-06T21:09:41Z |  |
| Kustomization | flux-system | searxng | Ready | main@840d3f0 | 2026-10-06T21:06:03Z |  |
| Kustomization | flux-system | secret-store | Ready | main@840d3f0 | 2026-10-06T21:06:14Z |  |
| Kustomization | flux-system | tailscale | Ready | main@840d3f0 | 2026-10-06T21:07:16Z |  |
| Kustomization | flux-system | temporal | Ready | main@840d3f0 | 2026-10-06T21:10:23Z |  |
| Kustomization | flux-system | unified-memory | Ready | main@840d3f0 | 2026-10-06T21:09:06Z |  |
| Kustomization | flux-system | voice-router | Ready | main@840d3f0 | 2026-10-06T21:06:48Z |  |
