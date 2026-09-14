# Flux: what is applied

Read from the cluster receipt taken at 2026-09-14T02:00:21Z. Every Kustomization and HelmRelease, with the revision Flux last applied. **Suspended** is a switch somebody turned off on purpose (temporal, commerce, commerce-data, event-bus), not a defect; **Unknown** is a row Flux has never graded.

**116 objects: 99 ready, 15 not ready, 0 unknown, 2 suspended.**

## Not ready right now

- **HelmRelease commerce/lago** since 2026-09-13T20:26:28Z: Helm install failed for release commerce/lago with chart lago@1.28.0: failed early due to stalled resources: [Deployment/commerce/lago-payment-worker status: 'Failed']
- **Kustomization flux-system/backstage** since 2026-09-14T01:58:21Z: Reconciliation in progress
- **Kustomization flux-system/chaos** since 2026-09-14T01:52:33Z: dependency 'flux-system/observability' is not ready
- **Kustomization flux-system/cluster-state** since 2026-09-14T01:57:46Z: ExternalSecret/backstage/rotation-canary dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-secrets.io": failed to call webhook: Post "https://external-secrets-webhook.external-secrets.svc:443/validate-external-secrets-io-v1-externalsecret?timeout=5s": context deadline exceeded 
- **Kustomization flux-system/commerce** since 2026-09-14T01:58:13Z: health check failed after 41.801219ms: failed early due to stalled resources: [HelmRelease/commerce/lago status: 'Failed']
- **Kustomization flux-system/guacamole** since 2026-09-14T01:52:18Z: dependency 'flux-system/identity' is not ready
- **Kustomization flux-system/gvisor-runtime** since 2026-09-14T01:39:50Z: dependency 'flux-system/nodesoftware-operator' is not ready
- **Kustomization flux-system/healthchecks** since 2026-09-14T01:52:49Z: dependency 'flux-system/identity' is not ready
- **Kustomization flux-system/identity** since 2026-09-14T01:57:47Z: ExternalSecret/identity/oauth2-proxy dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-secrets.io": failed to call webhook: Post "https://external-secrets-webhook.external-secrets.svc:443/validate-external-secrets-io-v1-externalsecret?timeout=5s": context deadline exceeded 
- **Kustomization flux-system/jit** since 2026-09-14T01:57:07Z: ExternalSecret/jit/jit-broker dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-secrets.io": failed to call webhook: Post "https://external-secrets-webhook.external-secrets.svc:443/validate-external-secrets-io-v1-externalsecret?timeout=5s": context deadline exceeded 
- **Kustomization flux-system/nodesoftware-operator** since 2026-09-14T01:58:21Z: dependency 'flux-system/rbac-identity' is not ready
- **Kustomization flux-system/observability** since 2026-09-14T01:52:19Z: ExternalSecret/observability/aevum-evidence dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-secrets.io": failed to call webhook: Post "https://external-secrets-webhook.external-secrets.svc:443/validate-external-secrets-io-v1-externalsecret?timeout=5s": context deadline exceeded 
- **Kustomization flux-system/rbac-identity** since 2026-09-14T01:57:59Z: ExternalSecret/flux-system/bridge-identity dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-secrets.io": failed to call webhook: Post "https://external-secrets-webhook.external-secrets.svc:443/validate-external-secrets-io-v1-externalsecret?timeout=5s": context deadline exceeded 
- **Kustomization flux-system/science** since 2026-09-14T01:53:40Z: dependency 'flux-system/observability' is not ready
- **Kustomization flux-system/weave-gitops** since 2026-09-14T01:59:04Z: dependency 'flux-system/identity' is not ready

## Every row

| Kind | Namespace | Name | State | Applied revision | Since | Message |
|---|---|---|---|---|---|---|
| HelmRelease | commerce | lago | Not ready | 1.28.0 | 2026-09-13T20:26:28Z | Helm install failed for release commerce/lago with chart lago@1.28.0: failed early due to stalled resources: [Deployment/commerce/lago-payment-worker status: 'F |
| Kustomization | flux-system | backstage | Not ready | main@4d95760 | 2026-09-14T01:58:21Z | Reconciliation in progress |
| Kustomization | flux-system | chaos | Not ready | main@4d95760 | 2026-09-14T01:52:33Z | dependency 'flux-system/observability' is not ready |
| Kustomization | flux-system | cluster-state | Not ready | main@4d95760 | 2026-09-14T01:57:46Z | ExternalSecret/backstage/rotation-canary dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-secre |
| Kustomization | flux-system | commerce | Not ready | main@abea14d | 2026-09-14T01:58:13Z | health check failed after 41.801219ms: failed early due to stalled resources: [HelmRelease/commerce/lago status: 'Failed'] |
| Kustomization | flux-system | guacamole | Not ready | main@4d95760 | 2026-09-14T01:52:18Z | dependency 'flux-system/identity' is not ready |
| Kustomization | flux-system | gvisor-runtime | Not ready | main@4d95760 | 2026-09-14T01:39:50Z | dependency 'flux-system/nodesoftware-operator' is not ready |
| Kustomization | flux-system | healthchecks | Not ready | main@4d95760 | 2026-09-14T01:52:49Z | dependency 'flux-system/identity' is not ready |
| Kustomization | flux-system | identity | Not ready | main@4d95760 | 2026-09-14T01:57:47Z | ExternalSecret/identity/oauth2-proxy dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-secrets.i |
| Kustomization | flux-system | jit | Not ready | main@4d95760 | 2026-09-14T01:57:07Z | ExternalSecret/jit/jit-broker dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-secrets.io": fai |
| Kustomization | flux-system | nodesoftware-operator | Not ready | main@4d95760 | 2026-09-14T01:58:21Z | dependency 'flux-system/rbac-identity' is not ready |
| Kustomization | flux-system | observability | Not ready | main@4d95760 | 2026-09-14T01:52:19Z | ExternalSecret/observability/aevum-evidence dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-se |
| Kustomization | flux-system | rbac-identity | Not ready | main@4d95760 | 2026-09-14T01:57:59Z | ExternalSecret/flux-system/bridge-identity dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-sec |
| Kustomization | flux-system | science | Not ready | main@4d95760 | 2026-09-14T01:53:40Z | dependency 'flux-system/observability' is not ready |
| Kustomization | flux-system | weave-gitops | Not ready | main@4d95760 | 2026-09-14T01:59:04Z | dependency 'flux-system/identity' is not ready |
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
| Kustomization | flux-system | agent-workforce | Ready | main@4d95760 | 2026-09-14T01:58:29Z |  |
| Kustomization | flux-system | alerts | Ready | main@4d95760 | 2026-09-14T01:58:04Z |  |
| Kustomization | flux-system | alerts-github | Ready | main@4d95760 | 2026-09-14T01:58:07Z |  |
| Kustomization | flux-system | alerts-secret | Ready | main@4d95760 | 2026-09-14T01:57:49Z |  |
| Kustomization | flux-system | autoscaler | Ready | main@4d95760 | 2026-09-14T01:58:09Z |  |
| Kustomization | flux-system | backstage-namespace | Ready | main@4d95760 | 2026-09-14T01:57:36Z |  |
| Kustomization | flux-system | calico | Ready | main@4d95760 | 2026-09-14T01:57:12Z |  |
| Kustomization | flux-system | chaos-mesh | Ready | main@4d95760 | 2026-09-14T01:58:22Z |  |
| Kustomization | flux-system | commerce-data | Ready | main@4d95760 | 2026-09-14T01:58:10Z |  |
| Kustomization | flux-system | concierge | Ready | main@4d95760 | 2026-09-14T01:57:58Z |  |
| Kustomization | flux-system | cross-node-drill | Ready | main@4d95760 | 2026-09-14T01:57:19Z |  |
| Kustomization | flux-system | crossplane | Ready | main@4d95760 | 2026-09-14T01:57:52Z |  |
| Kustomization | flux-system | crossplane-providerconfig | Ready | main@4d95760 | 2026-09-14T01:52:25Z |  |
| Kustomization | flux-system | crossplane-providers | Ready | main@4d95760 | 2026-09-14T01:50:54Z |  |
| Kustomization | flux-system | dagster | Ready | main@4d95760 | 2026-09-14T01:58:12Z |  |
| Kustomization | flux-system | dns | Ready | main@4d95760 | 2026-09-14T01:57:58Z |  |
| Kustomization | flux-system | drills | Ready | main@4d95760 | 2026-09-14T02:00:15Z |  |
| Kustomization | flux-system | edge | Ready | main@4d95760 | 2026-09-14T01:59:29Z |  |
| Kustomization | flux-system | estate-catalog | Ready | latest@sha256:565c8ab5a2b63e1b878d5d81f4 | 2026-09-14T01:53:38Z |  |
| Kustomization | flux-system | estate-db | Ready | main@4d95760 | 2026-09-14T01:57:46Z |  |
| Kustomization | flux-system | estate-db-migrate | Ready | main@4d95760 | 2026-09-14T01:58:01Z |  |
| Kustomization | flux-system | estate-db-operator | Ready | main@4d95760 | 2026-09-14T01:59:39Z |  |
| Kustomization | flux-system | event-bus | Ready | main@4d95760 | 2026-09-14T01:57:08Z |  |
| Kustomization | flux-system | external-secrets | Ready | main@4d95760 | 2026-09-14T01:56:57Z |  |
| Kustomization | flux-system | feature-register | Ready | main@4d95760 | 2026-09-14T01:55:21Z |  |
| Kustomization | flux-system | flux-system | Ready | main@4d95760 | 2026-09-14T01:57:32Z |  |
| Kustomization | flux-system | flux-webhook | Ready | main@4d95760 | 2026-09-14T01:58:05Z |  |
| Kustomization | flux-system | gateway-api-crds | Ready | v1.5.1@e7677b7 | 2026-09-14T01:56:26Z |  |
| Kustomization | flux-system | healing | Ready | main@4d95760 | 2026-09-14T01:56:10Z |  |
| Kustomization | flux-system | healing-analyzer | Ready | main@4d95760 | 2026-09-14T01:50:09Z |  |
| Kustomization | flux-system | healing-k8sgpt | Ready | main@4d95760 | 2026-09-14T01:58:52Z |  |
| Kustomization | flux-system | hermes-agent | Ready | main@4d95760 | 2026-09-14T01:58:24Z |  |
| Kustomization | flux-system | hindsight | Ready | main@4d95760 | 2026-09-14T01:58:49Z |  |
| Kustomization | flux-system | human-vault | Ready | main@4d95760 | 2026-09-14T01:58:05Z |  |
| Kustomization | flux-system | human-vault-bridge | Ready | main@4d95760 | 2026-09-14T01:58:34Z |  |
| Kustomization | flux-system | image-automation | Ready | main@4d95760 | 2026-09-14T01:57:54Z |  |
| Kustomization | flux-system | keda | Ready | main@4d95760 | 2026-09-14T01:59:35Z |  |
| Kustomization | flux-system | kyverno | Ready | main@4d95760 | 2026-09-14T01:58:02Z |  |
| Kustomization | flux-system | llm | Ready | main@4d95760 | 2026-09-14T01:58:22Z |  |
| Kustomization | flux-system | mcp | Ready | main@4d95760 | 2026-09-14T01:58:38Z |  |
| Kustomization | flux-system | metrics-server | Ready | main@4d95760 | 2026-09-14T01:59:13Z |  |
| Kustomization | flux-system | monitoring | Ready | main@4d95760 | 2026-09-14T01:57:43Z |  |
| Kustomization | flux-system | monitoring-rules | Ready | main@4d95760 | 2026-09-14T01:57:57Z |  |
| Kustomization | flux-system | notify | Ready | main@4d95760 | 2026-09-14T01:57:54Z |  |
| Kustomization | flux-system | ns-fences | Ready | main@4d95760 | 2026-09-14T01:53:56Z |  |
| Kustomization | flux-system | observability-collector | Ready | main@4d95760 | 2026-09-14T02:00:11Z |  |
| Kustomization | flux-system | otto-gateway | Ready | main@4d95760 | 2026-09-14T01:58:19Z |  |
| Kustomization | flux-system | otto-golden | Ready | main@4d95760 | 2026-09-14T01:57:47Z |  |
| Kustomization | flux-system | otto-golden-secret | Ready | main@4d95760 | 2026-09-14T01:57:44Z |  |
| Kustomization | flux-system | priority-classes | Ready | main@4d95760 | 2026-09-14T01:56:00Z |  |
| Kustomization | flux-system | prospector | Ready | main@7453d76 | 2026-09-14T01:53:35Z |  |
| Kustomization | flux-system | prospector-platform | Ready | main@4d95760 | 2026-09-14T01:52:49Z |  |
| Kustomization | flux-system | rbac | Ready | main@4d95760 | 2026-09-14T01:57:36Z |  |
| Kustomization | flux-system | rbac-floor | Ready | main@4d95760 | 2026-09-14T01:56:49Z |  |
| Kustomization | flux-system | reloader | Ready | main@4d95760 | 2026-09-14T01:57:56Z |  |
| Kustomization | flux-system | research-engine | Ready | main@4d95760 | 2026-09-14T01:58:34Z |  |
| Kustomization | flux-system | robusta | Ready | main@4d95760 | 2026-09-14T01:57:49Z |  |
| Kustomization | flux-system | router-events | Ready | main@4d95760 | 2026-09-14T01:58:29Z |  |
| Kustomization | flux-system | sandbox-launch | Ready | main@4d95760 | 2026-09-14T01:55:45Z |  |
| Kustomization | flux-system | sandbox-live | Ready | sandbox/launch@4830a6e | 2026-09-14T02:00:03Z |  |
| Kustomization | flux-system | scheduling | Ready | main@4d95760 | 2026-09-14T01:58:06Z |  |
| Kustomization | flux-system | searxng | Ready | main@4d95760 | 2026-09-14T01:59:13Z |  |
| Kustomization | flux-system | secret-store | Ready | main@4d95760 | 2026-09-14T01:57:39Z |  |
| Kustomization | flux-system | spire | Ready | main@4d95760 | 2026-09-14T01:50:11Z |  |
| Kustomization | flux-system | staging | Ready | main@4d95760 | 2026-09-14T01:56:49Z |  |
| Kustomization | flux-system | tailscale | Ready | main@4d95760 | 2026-09-14T01:57:53Z |  |
| Kustomization | flux-system | trivy | Ready | main@4d95760 | 2026-09-14T01:56:06Z |  |
| Kustomization | flux-system | verification | Ready | main@4d95760 | 2026-09-14T01:57:47Z |  |
