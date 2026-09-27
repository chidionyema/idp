# Flux: what is applied

Read from the cluster receipt taken at 2026-09-27T13:00:58Z. Every Kustomization and HelmRelease, with the revision Flux last applied. **Suspended** is a switch somebody turned off on purpose (temporal, commerce, commerce-data, event-bus), not a defect; **Unknown** is a row Flux has never graded.

**41 objects: 31 ready, 8 not ready, 0 unknown, 2 suspended.**

## Not ready right now

- **HelmRelease commerce/lago** since 2026-09-26T09:48:22Z: Could not determine release state: unable to determine state for release with status 'uninstalling'
- **HelmRelease coroot/coroot** since 2026-09-26T19:29:36Z: Helm install failed for release coroot/coroot with chart coroot@0.22.0: timeout waiting for: [StatefulSet/coroot/coroot-clickhouse-shard0 status: 'InProgress', PersistentVolumeClaim/coroot/coroot-data status: 'InProgress', Deployment/coroot/coroot-prometheus-server status: 'InProgress', PersistentVolumeClaim/coroot/coroot-prometheus-server status: 'InProgress', Deployment/coroot/coroot status: 'InProgress']
- **HelmRelease crossplane-system/crossplane** since 2026-09-26T19:28:07Z: Helm rollback to previous release crossplane-system/crossplane.v12 with chart crossplane@2.4.0 succeeded
- **HelmRelease dagster/dagster** since 2026-09-26T19:04:24Z: Helm rollback to previous release dagster/dagster.v18 with chart dagster@1.13.19 failed: release dagster failed: failed early due to stalled resources: [Deployment/dagster/dagster-dagster-user-deployments-estate-scheduler status: 'Failed']
- **HelmRelease observability/langfuse** since 2026-09-25T10:40:26Z: dependency 'observability/signoz' is not ready
- **HelmRelease spire-mgmt/spire** since 2026-09-26T20:11:52Z: Helm upgrade failed for release spire-mgmt/spire with chart spire@0.30.1: timeout waiting for: [DaemonSet/spire-mgmt/spire-agent status: 'InProgress', Deployment/spire-mgmt/spire-spiffe-oidc-discovery-provider status: 'InProgress']
- **Kustomization flux-system/external-secrets** since 2026-09-27T13:00:43Z: Certificate/external-secrets/human-vault-ca dry-run failed (InternalError): Internal error occurred: failed calling webhook "webhook.cert-manager.io": failed to call webhook: Post "https://cert-manager-webhook.cert-manager.svc:443/validate?timeout=30s": read tcp 168.254.5.2:49412->168.254.5.1:33711: read: connection reset by peer 
- **Kustomization flux-system/secret-store** since 2026-09-26T19:59:30Z: dependency 'flux-system/external-secrets' is not ready

## Every row

| Kind | Namespace | Name | State | Applied revision | Since | Message |
|---|---|---|---|---|---|---|
| HelmRelease | commerce | lago | Not ready | 1.28.0 | 2026-09-26T09:48:22Z | Could not determine release state: unable to determine state for release with status 'uninstalling' |
| HelmRelease | coroot | coroot | Not ready | 0.22.0 | 2026-09-26T19:29:36Z | Helm install failed for release coroot/coroot with chart coroot@0.22.0: timeout waiting for: [StatefulSet/coroot/coroot-clickhouse-shard0 status: 'InProgress',  |
| HelmRelease | crossplane-system | crossplane | Not ready | 1.15.1 | 2026-09-26T19:28:07Z | Helm rollback to previous release crossplane-system/crossplane.v12 with chart crossplane@2.4.0 succeeded |
| HelmRelease | dagster | dagster | Not ready | 1.13.19 | 2026-09-26T19:04:24Z | Helm rollback to previous release dagster/dagster.v18 with chart dagster@1.13.19 failed: release dagster failed: failed early due to stalled resources: [Deploym |
| HelmRelease | observability | langfuse | Not ready | 2.0.2 | 2026-09-25T10:40:26Z | dependency 'observability/signoz' is not ready |
| HelmRelease | spire-mgmt | spire | Not ready | 0.30.1 | 2026-09-26T20:11:52Z | Helm upgrade failed for release spire-mgmt/spire with chart spire@0.30.1: timeout waiting for: [DaemonSet/spire-mgmt/spire-agent status: 'InProgress', Deploymen |
| Kustomization | flux-system | external-secrets | Not ready | main@7d86661 | 2026-09-27T13:00:43Z | Certificate/external-secrets/human-vault-ca dry-run failed (InternalError): Internal error occurred: failed calling webhook "webhook.cert-manager.io": failed to |
| Kustomization | flux-system | secret-store | Not ready |  | 2026-09-26T19:59:30Z | dependency 'flux-system/external-secrets' is not ready |
| HelmRelease | observability | signoz | Suspended | 0.138.0 | 2026-09-26T16:24:12Z |  |
| HelmRelease | tigera-operator | tigera-operator | Suspended | v3.32.2 | 2026-09-06T19:38:02Z |  |
| HelmRelease | cert-manager | cert-manager | Ready | v1.21.1 | 2026-09-26T10:39:03Z |  |
| HelmRelease | edge | external-dns | Ready | 1.21.1 | 2026-09-26T10:39:02Z |  |
| HelmRelease | edge | traefik | Ready | 41.3.0 | 2026-09-26T09:48:30Z |  |
| HelmRelease | estate-db | cloudnative-pg | Ready | 0.29.0 | 2026-09-26T10:01:26Z |  |
| HelmRelease | event-bus | nats | Ready | 2.14.6 | 2026-09-26T09:48:21Z |  |
| HelmRelease | external-secrets | external-secrets | Ready | 2.9.0 | 2026-09-26T09:48:27Z |  |
| HelmRelease | flux-system | vendor-bridge | Ready | 0.1.0+7d86661394cb | 2026-09-27T12:58:04Z |  |
| HelmRelease | healing | descheduler | Ready | 0.36.0 | 2026-09-26T09:48:21Z |  |
| HelmRelease | healing | k8sgpt-operator | Ready | 0.2.29 | 2026-09-26T09:48:26Z |  |
| HelmRelease | hindsight | hindsight | Ready | 0.9.2 | 2026-09-26T09:48:29Z |  |
| HelmRelease | identity | oauth2-proxy | Ready | 10.7.0 | 2026-09-26T10:01:26Z |  |
| HelmRelease | keda | keda | Ready | 2.20.2 | 2026-09-26T10:39:03Z |  |
| HelmRelease | keda | keda-add-ons-http | Ready | 0.15.0 | 2026-09-26T10:39:31Z |  |
| HelmRelease | kyverno | kyverno | Ready | 3.9.0 | 2026-09-26T10:01:28Z |  |
| HelmRelease | metrics-server | metrics-server | Ready | 3.14.0 | 2026-09-26T09:48:29Z |  |
| HelmRelease | monitoring | blackbox | Ready | 11.17.2 | 2026-09-26T11:01:14Z |  |
| HelmRelease | monitoring | kube-prometheus-stack | Ready | 88.6.0 | 2026-09-26T10:01:27Z |  |
| HelmRelease | observability | superset | Ready | 0.22.4 | 2026-09-26T10:39:02Z |  |
| HelmRelease | spire-mgmt | spire-crds | Ready | 0.6.1 | 2026-09-26T09:48:25Z |  |
| HelmRelease | tailscale | tailscale-operator | Ready | 1.102.3 | 2026-09-26T09:48:27Z |  |
| HelmRelease | temporal | temporal | Ready | 1.6.0 | 2026-09-26T10:39:02Z |  |
| HelmRelease | trivy-system | trivy-operator | Ready | 0.36.0 | 2026-09-26T18:25:31Z |  |
| HelmRelease | weave-gitops | weave-gitops | Ready | 4.0.36 | 2026-09-26T09:48:27Z |  |
| Kustomization | flux-system | dns | Ready | main@7d86661 | 2026-09-27T12:59:48Z |  |
| Kustomization | flux-system | edge | Ready | main@7d86661 | 2026-09-27T12:59:56Z |  |
| Kustomization | flux-system | flux-system | Ready | main@7d86661 | 2026-09-27T13:00:45Z |  |
| Kustomization | flux-system | gateway-api-crds | Ready | v1.5.1@e7677b7 | 2026-09-27T13:00:07Z |  |
| Kustomization | flux-system | kyverno | Ready | main@7d86661 | 2026-09-27T12:59:26Z |  |
| Kustomization | flux-system | monitoring | Ready | main@7d86661 | 2026-09-27T13:00:04Z |  |
| Kustomization | flux-system | monitoring-rules | Ready | main@7d86661 | 2026-09-27T12:58:55Z |  |
| Kustomization | flux-system | ns-fences | Ready | main@7d86661 | 2026-09-27T13:00:46Z |  |
