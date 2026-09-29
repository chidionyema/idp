# Flux: what is applied

Read from the cluster receipt taken at 2026-09-29T02:45:14Z. Every Kustomization and HelmRelease, with the revision Flux last applied. **Suspended** is a switch somebody turned off on purpose (temporal, commerce, commerce-data, event-bus), not a defect; **Unknown** is a row Flux has never graded.

**61 objects: 46 ready, 13 not ready, 0 unknown, 2 suspended.**

## Not ready right now

- **HelmRelease commerce/lago** since 2026-09-26T09:48:22Z: Could not determine release state: unable to determine state for release with status 'uninstalling'
- **HelmRelease coroot/coroot** since 2026-09-26T19:29:36Z: Helm install failed for release coroot/coroot with chart coroot@0.22.0: timeout waiting for: [StatefulSet/coroot/coroot-clickhouse-shard0 status: 'InProgress', PersistentVolumeClaim/coroot/coroot-data status: 'InProgress', Deployment/coroot/coroot-prometheus-server status: 'InProgress', PersistentVolumeClaim/coroot/coroot-prometheus-server status: 'InProgress', Deployment/coroot/coroot status: 'InProgress']
- **HelmRelease crossplane-system/crossplane** since 2026-09-26T19:28:07Z: Helm rollback to previous release crossplane-system/crossplane.v12 with chart crossplane@2.4.0 succeeded
- **HelmRelease dagster/dagster** since 2026-09-29T01:20:33Z: Helm rollback to previous release dagster/dagster.v242 with chart dagster@1.13.19 succeeded
- **HelmRelease flux-system/vendor-bridge** since 2026-09-29T02:43:14Z: Helm upgrade failed for release flux-system/vendor-bridge with chart vendor-bridge@0.1.0+fce3d2ba7d1d: timeout waiting for: [PushSecret/dagster/seed-gemini-api-key status: 'InProgress', PushSecret/dagster/seed-groq-api-key-3 status: 'InProgress', PushSecret/dagster/seed-nvidia-api-key status: 'InProgress', PushSecret/hermes-agent/seed-telegram-hermes-bot-token status: 'InProgress', PushSecret/llm/seed-minimax-api-key status: 'InProgress', PushSecret/llm/seed-moonshot-api-key status: 'InProgress', PushSecret/llm/seed-nvidia-api-key status: 'InProgress', ExternalSecret/notify/human-apprise-teleg ... : 'InProgress', ExternalSecret/dagster/human-typesafe status: 'InProgress', PushSecret/concierge/seed-concierge-card-key status: 'InProgress', PushSecret/dagster/seed-exa-api-key status: 'InProgress', PushSecret/dagster/seed-sambanova-api-key-3 status: 'InProgress', PushSecret/llm/seed-cerebras-api-key-3 status: 'InProgress', PushSecret/dagster/seed-openrouter-api-key status: 'InProgress', PushSecret/dagster/seed-sambanova-api-key status: 'InProgress', PushSecret/dagster/seed-typesafe-api-key status: 'InProgress', PushSecret/llm/seed-cerebras-api-key-2 status: 'InProgress', PushSecret/concierge/seed-twilio-whatsapp-number status: 'InProgress', PushSecret/dagster/seed-cerebras-api-key-2 status: 'InProgress', PushSecret/prospector/seed-minimax-api-key status: 'InProgress', PushSecret/concierge/seed-twilio-auth-token status: 'InProgress', PushSecret/llm/seed-cohere-api-key status: 'InProgress', ExternalSecret/mcp/human-typesafe status: 'InProgress', PushSecret/dagster/seed-cerebras-api-key-3 status: 'InProgress', PushSecret/dagster/seed-minimax-api-key status: 'InProgress', PushSecret/dagster/seed-moonshot-api-key status: 'InProgress', PushSecret/dagster/seed-cohere-api-key status: 'InProgress', PushSecret/dagster/seed-cursor-api-key status: 'InProgress', PushSecret/dagster/seed-sambanova-api-key-2 status: 'InProgress', PushSecret/llm/seed-sambanova-api-key-3 status: 'InProgress']
- **HelmRelease hindsight/hindsight** since 2026-09-28T23:21:41Z: Helm rollback to previous release hindsight/hindsight.v83 with chart hindsight@0.9.2 failed: release hindsight failed: failed early due to stalled resources: [Deployment/hindsight/hindsight-api status: 'Failed']
- **HelmRelease observability/langfuse** since 2026-09-25T10:40:26Z: dependency 'observability/signoz' is not ready
- **HelmRelease spire-mgmt/spire** since 2026-09-26T20:11:52Z: Helm upgrade failed for release spire-mgmt/spire with chart spire@0.30.1: timeout waiting for: [DaemonSet/spire-mgmt/spire-agent status: 'InProgress', Deployment/spire-mgmt/spire-spiffe-oidc-discovery-provider status: 'InProgress']
- **Kustomization flux-system/hindsight** since 2026-09-29T02:43:56Z: health check failed after 2m0.02530298s: timeout waiting for: [HelmRelease/hindsight/hindsight status: 'InProgress']
- **Kustomization flux-system/mcp** since 2026-09-29T02:40:23Z: health check failed after 2.029497771s: failed early due to stalled resources: [Deployment/mcp/estate-mcp status: 'Failed']
- **Kustomization flux-system/otto-gateway** since 2026-09-29T02:40:44Z: health check failed after 89.999818ms: failed early due to stalled resources: [Deployment/otto-gateway/otto-gateway status: 'Failed']
- **Kustomization flux-system/otto-golden** since 2026-09-29T02:41:57Z: health check failed after 496.304793ms: failed early due to stalled resources: [Deployment/otto-golden/otto-golden status: 'Failed']
- **Kustomization flux-system/voice-router** since 2026-09-29T02:44:04Z: health check failed after 5m0.027991175s: timeout waiting for: [Deployment/voice-router/voice-router-director status: 'InProgress', ExternalSecret/voice-router/newsroom-llm status: 'InProgress']

## Every row

| Kind | Namespace | Name | State | Applied revision | Since | Message |
|---|---|---|---|---|---|---|
| HelmRelease | commerce | lago | Not ready | 1.28.0 | 2026-09-26T09:48:22Z | Could not determine release state: unable to determine state for release with status 'uninstalling' |
| HelmRelease | coroot | coroot | Not ready | 0.22.0 | 2026-09-26T19:29:36Z | Helm install failed for release coroot/coroot with chart coroot@0.22.0: timeout waiting for: [StatefulSet/coroot/coroot-clickhouse-shard0 status: 'InProgress',  |
| HelmRelease | crossplane-system | crossplane | Not ready | 1.15.1 | 2026-09-26T19:28:07Z | Helm rollback to previous release crossplane-system/crossplane.v12 with chart crossplane@2.4.0 succeeded |
| HelmRelease | dagster | dagster | Not ready | 1.13.19 | 2026-09-29T01:20:33Z | Helm rollback to previous release dagster/dagster.v242 with chart dagster@1.13.19 succeeded |
| HelmRelease | flux-system | vendor-bridge | Not ready | 0.1.0+fce3d2ba7d1d | 2026-09-29T02:43:14Z | Helm upgrade failed for release flux-system/vendor-bridge with chart vendor-bridge@0.1.0+fce3d2ba7d1d: timeout waiting for: [PushSecret/dagster/seed-gemini-api- |
| HelmRelease | hindsight | hindsight | Not ready | 0.9.2 | 2026-09-28T23:21:41Z | Helm rollback to previous release hindsight/hindsight.v83 with chart hindsight@0.9.2 failed: release hindsight failed: failed early due to stalled resources: [D |
| HelmRelease | observability | langfuse | Not ready | 2.0.2 | 2026-09-25T10:40:26Z | dependency 'observability/signoz' is not ready |
| HelmRelease | spire-mgmt | spire | Not ready | 0.30.1 | 2026-09-26T20:11:52Z | Helm upgrade failed for release spire-mgmt/spire with chart spire@0.30.1: timeout waiting for: [DaemonSet/spire-mgmt/spire-agent status: 'InProgress', Deploymen |
| Kustomization | flux-system | hindsight | Not ready | main@fce3d2b | 2026-09-29T02:43:56Z | health check failed after 2m0.02530298s: timeout waiting for: [HelmRelease/hindsight/hindsight status: 'InProgress'] |
| Kustomization | flux-system | mcp | Not ready | main@fce3d2b | 2026-09-29T02:40:23Z | health check failed after 2.029497771s: failed early due to stalled resources: [Deployment/mcp/estate-mcp status: 'Failed'] |
| Kustomization | flux-system | otto-gateway | Not ready | main@fce3d2b | 2026-09-29T02:40:44Z | health check failed after 89.999818ms: failed early due to stalled resources: [Deployment/otto-gateway/otto-gateway status: 'Failed'] |
| Kustomization | flux-system | otto-golden | Not ready | main@fce3d2b | 2026-09-29T02:41:57Z | health check failed after 496.304793ms: failed early due to stalled resources: [Deployment/otto-golden/otto-golden status: 'Failed'] |
| Kustomization | flux-system | voice-router | Not ready | main@fce3d2b | 2026-09-29T02:44:04Z | health check failed after 5m0.027991175s: timeout waiting for: [Deployment/voice-router/voice-router-director status: 'InProgress', ExternalSecret/voice-router/ |
| HelmRelease | observability | signoz | Suspended | 0.138.0 | 2026-09-26T16:24:12Z |  |
| HelmRelease | tigera-operator | tigera-operator | Suspended | v3.32.2 | 2026-09-06T19:38:02Z |  |
| HelmRelease | cert-manager | cert-manager | Ready | v1.21.1 | 2026-09-27T17:04:43Z |  |
| HelmRelease | edge | external-dns | Ready | 1.21.1 | 2026-09-26T10:39:02Z |  |
| HelmRelease | edge | traefik | Ready | 41.3.0 | 2026-09-26T09:48:30Z |  |
| HelmRelease | estate-db | cloudnative-pg | Ready | 0.29.0 | 2026-09-26T10:01:26Z |  |
| HelmRelease | event-bus | nats | Ready | 2.14.6 | 2026-09-26T09:48:21Z |  |
| HelmRelease | external-secrets | external-secrets | Ready | 2.9.0 | 2026-09-27T17:09:36Z |  |
| HelmRelease | healing | descheduler | Ready | 0.36.0 | 2026-09-26T09:48:21Z |  |
| HelmRelease | healing | k8sgpt-operator | Ready | 0.2.29 | 2026-09-26T09:48:26Z |  |
| HelmRelease | identity | oauth2-proxy | Ready | 10.7.0 | 2026-09-29T00:03:03Z |  |
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
| Kustomization | flux-system | backstage | Ready | main@fce3d2b | 2026-09-29T02:40:21Z |  |
| Kustomization | flux-system | backstage-namespace | Ready | main@fce3d2b | 2026-09-29T02:38:13Z |  |
| Kustomization | flux-system | dns | Ready | main@fce3d2b | 2026-09-29T02:38:27Z |  |
| Kustomization | flux-system | edge | Ready | main@fce3d2b | 2026-09-29T02:38:44Z |  |
| Kustomization | flux-system | epistemic-fabric | Ready | main@fce3d2b | 2026-09-29T02:40:10Z |  |
| Kustomization | flux-system | estate-db | Ready | main@fce3d2b | 2026-09-29T02:40:08Z |  |
| Kustomization | flux-system | estate-db-migrate | Ready | main@fce3d2b | 2026-09-29T02:40:43Z |  |
| Kustomization | flux-system | estate-db-operator | Ready | main@fce3d2b | 2026-09-29T02:38:27Z |  |
| Kustomization | flux-system | event-bus | Ready | main@fce3d2b | 2026-09-29T02:38:34Z |  |
| Kustomization | flux-system | external-secrets | Ready | main@fce3d2b | 2026-09-29T02:38:56Z |  |
| Kustomization | flux-system | flannel | Ready | main@fce3d2b | 2026-09-29T02:38:41Z |  |
| Kustomization | flux-system | flux-system | Ready | main@fce3d2b | 2026-09-29T02:38:50Z |  |
| Kustomization | flux-system | gateway-api-crds | Ready | v1.5.1@e7677b7 | 2026-09-29T02:39:33Z |  |
| Kustomization | flux-system | github-app-creds | Ready | main@fce3d2b | 2026-09-29T02:40:07Z |  |
| Kustomization | flux-system | hermes-agent | Ready | main@fce3d2b | 2026-09-29T02:42:00Z |  |
| Kustomization | flux-system | kyverno | Ready | main@fce3d2b | 2026-09-29T02:38:19Z |  |
| Kustomization | flux-system | llm | Ready | main@fce3d2b | 2026-09-29T02:41:14Z |  |
| Kustomization | flux-system | monitoring | Ready | main@fce3d2b | 2026-09-29T02:38:22Z |  |
| Kustomization | flux-system | monitoring-rules | Ready | main@fce3d2b | 2026-09-29T02:38:34Z |  |
| Kustomization | flux-system | ns-fences | Ready | main@fce3d2b | 2026-09-29T02:39:08Z |  |
| Kustomization | flux-system | otto-golden-secret | Ready | main@fce3d2b | 2026-09-29T02:40:31Z |  |
| Kustomization | flux-system | priority-classes | Ready | main@fce3d2b | 2026-09-29T02:38:12Z |  |
| Kustomization | flux-system | secret-store | Ready | main@fce3d2b | 2026-09-29T02:39:29Z |  |
| Kustomization | flux-system | tailscale | Ready | main@fce3d2b | 2026-09-29T02:40:27Z |  |
| Kustomization | flux-system | unified-memory | Ready | main@fce3d2b | 2026-09-29T02:40:40Z |  |
