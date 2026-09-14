# Flux: what is applied

Read from the cluster receipt taken at 2026-09-14T19:45:21Z. Every Kustomization and HelmRelease, with the revision Flux last applied. **Suspended** is a switch somebody turned off on purpose (temporal, commerce, commerce-data, event-bus), not a defect; **Unknown** is a row Flux has never graded.

**116 objects: 109 ready, 5 not ready, 0 unknown, 2 suspended.**

## Not ready right now

- **HelmRelease commerce/lago** since 2026-09-14T19:36:15Z: Running 'install' action with timeout of 15m0s
- **Kustomization flux-system/autoscaler** since 2026-09-14T19:45:12Z: ExternalSecret/kube-system/oke-autoscaler dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-secrets.io": failed to call webhook: Post "https://external-secrets-webhook.external-secrets.svc:443/validate-external-secrets-io-v1-externalsecret?timeout=5s": context deadline exceeded 
- **Kustomization flux-system/commerce** since 2026-09-14T19:36:13Z: Reconciliation in progress
- **Kustomization flux-system/mcp** since 2026-09-14T19:35:56Z: Reconciliation in progress
- **Kustomization flux-system/prospector-platform** since 2026-09-14T19:45:14Z: ExternalSecret/prospector/prospector-engine-env dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-secrets.io": failed to call webhook: Post "https://external-secrets-webhook.external-secrets.svc:443/validate-external-secrets-io-v1-externalsecret?timeout=5s": context deadline exceeded 

## Every row

| Kind | Namespace | Name | State | Applied revision | Since | Message |
|---|---|---|---|---|---|---|
| HelmRelease | commerce | lago | Not ready | 1.28.0 | 2026-09-14T19:36:15Z | Running 'install' action with timeout of 15m0s |
| Kustomization | flux-system | autoscaler | Not ready | main@e497116 | 2026-09-14T19:45:12Z | ExternalSecret/kube-system/oke-autoscaler dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-secr |
| Kustomization | flux-system | commerce | Not ready | main@abea14d | 2026-09-14T19:36:13Z | Reconciliation in progress |
| Kustomization | flux-system | mcp | Not ready | main@6558812 | 2026-09-14T19:35:56Z | Reconciliation in progress |
| Kustomization | flux-system | prospector-platform | Not ready | main@e497116 | 2026-09-14T19:45:14Z | ExternalSecret/prospector/prospector-engine-env dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.externa |
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
| HelmRelease | observability-agent | k8s-infra | Ready | 0.17.0 | 2026-09-14T18:09:18Z |  |
| HelmRelease | reloader | reloader | Ready | 2.2.16 | 2026-09-06T19:33:25Z |  |
| HelmRelease | robusta | robusta | Ready | 0.48.0 | 2026-09-06T20:26:45Z |  |
| HelmRelease | spire-mgmt | spire | Ready | 0.30.1 | 2026-09-08T09:39:33Z |  |
| HelmRelease | spire-mgmt | spire-crds | Ready | 0.6.1 | 2026-09-06T20:26:47Z |  |
| HelmRelease | tailscale | tailscale-operator | Ready | 1.102.3 | 2026-09-06T19:33:35Z |  |
| HelmRelease | temporal | temporal | Ready | 1.6.0 | 2026-09-08T23:12:29Z |  |
| HelmRelease | trivy-system | trivy-operator | Ready | 0.36.0 | 2026-09-06T20:26:45Z |  |
| HelmRelease | weave-gitops | weave-gitops | Ready | 4.0.36 | 2026-09-06T20:26:45Z |  |
| Kustomization | flux-system | agent-workforce | Ready | main@e497116 | 2026-09-14T19:36:38Z |  |
| Kustomization | flux-system | alerts | Ready | main@e497116 | 2026-09-14T19:35:44Z |  |
| Kustomization | flux-system | alerts-github | Ready | main@e497116 | 2026-09-14T19:35:36Z |  |
| Kustomization | flux-system | alerts-secret | Ready | main@e497116 | 2026-09-14T19:35:30Z |  |
| Kustomization | flux-system | backstage | Ready | main@e497116 | 2026-09-14T19:36:33Z |  |
| Kustomization | flux-system | backstage-namespace | Ready | main@e497116 | 2026-09-14T19:43:51Z |  |
| Kustomization | flux-system | calico | Ready | main@e497116 | 2026-09-14T19:44:12Z |  |
| Kustomization | flux-system | chaos | Ready | main@e497116 | 2026-09-14T19:36:58Z |  |
| Kustomization | flux-system | chaos-mesh | Ready | main@e497116 | 2026-09-14T19:35:24Z |  |
| Kustomization | flux-system | cluster-state | Ready | main@e497116 | 2026-09-14T19:35:27Z |  |
| Kustomization | flux-system | commerce-data | Ready | main@e497116 | 2026-09-14T19:35:42Z |  |
| Kustomization | flux-system | concierge | Ready | main@e497116 | 2026-09-14T19:35:33Z |  |
| Kustomization | flux-system | cross-node-drill | Ready | main@e497116 | 2026-09-14T19:43:50Z |  |
| Kustomization | flux-system | crossplane | Ready | main@e497116 | 2026-09-14T19:35:26Z |  |
| Kustomization | flux-system | crossplane-providerconfig | Ready | main@e497116 | 2026-09-14T19:35:59Z |  |
| Kustomization | flux-system | crossplane-providers | Ready | main@e497116 | 2026-09-14T19:35:54Z |  |
| Kustomization | flux-system | dagster | Ready | main@e497116 | 2026-09-14T19:36:28Z |  |
| Kustomization | flux-system | dns | Ready | main@e497116 | 2026-09-14T19:35:43Z |  |
| Kustomization | flux-system | drills | Ready | main@e497116 | 2026-09-14T19:36:05Z |  |
| Kustomization | flux-system | edge | Ready | main@e497116 | 2026-09-14T19:44:52Z |  |
| Kustomization | flux-system | estate-catalog | Ready | latest@sha256:c7d6047f10973294dd3de3b9ac | 2026-09-14T19:41:15Z |  |
| Kustomization | flux-system | estate-db | Ready | main@e497116 | 2026-09-14T19:35:38Z |  |
| Kustomization | flux-system | estate-db-migrate | Ready | main@e497116 | 2026-09-14T19:36:08Z |  |
| Kustomization | flux-system | estate-db-operator | Ready | main@e497116 | 2026-09-14T19:44:41Z |  |
| Kustomization | flux-system | event-bus | Ready | main@e497116 | 2026-09-14T19:44:29Z |  |
| Kustomization | flux-system | external-secrets | Ready | main@e497116 | 2026-09-14T19:44:35Z |  |
| Kustomization | flux-system | feature-register | Ready | main@e497116 | 2026-09-14T19:44:07Z |  |
| Kustomization | flux-system | flux-system | Ready | main@e497116 | 2026-09-14T19:44:18Z |  |
| Kustomization | flux-system | flux-webhook | Ready | main@e497116 | 2026-09-14T19:35:39Z |  |
| Kustomization | flux-system | gateway-api-crds | Ready | v1.5.1@e7677b7 | 2026-09-14T19:43:54Z |  |
| Kustomization | flux-system | guacamole | Ready | main@e497116 | 2026-09-14T19:36:13Z |  |
| Kustomization | flux-system | gvisor-runtime | Ready | main@e497116 | 2026-09-14T19:36:16Z |  |
| Kustomization | flux-system | healing | Ready | main@e497116 | 2026-09-14T19:35:23Z |  |
| Kustomization | flux-system | healing-analyzer | Ready | main@e497116 | 2026-09-14T19:36:50Z |  |
| Kustomization | flux-system | healing-k8sgpt | Ready | main@e497116 | 2026-09-14T19:36:29Z |  |
| Kustomization | flux-system | healthchecks | Ready | main@e497116 | 2026-09-14T19:36:15Z |  |
| Kustomization | flux-system | hermes-agent | Ready | main@e497116 | 2026-09-14T19:37:41Z |  |
| Kustomization | flux-system | hindsight | Ready | main@e497116 | 2026-09-14T19:36:49Z |  |
| Kustomization | flux-system | human-vault | Ready | main@e497116 | 2026-09-14T19:45:13Z |  |
| Kustomization | flux-system | human-vault-bridge | Ready | main@e497116 | 2026-09-14T19:35:42Z |  |
| Kustomization | flux-system | identity | Ready | main@e497116 | 2026-09-14T19:35:41Z |  |
| Kustomization | flux-system | image-automation | Ready | main@e497116 | 2026-09-14T19:35:33Z |  |
| Kustomization | flux-system | jit | Ready | main@e497116 | 2026-09-14T19:44:18Z |  |
| Kustomization | flux-system | keda | Ready | main@e497116 | 2026-09-14T19:45:01Z |  |
| Kustomization | flux-system | kyverno | Ready | main@e497116 | 2026-09-14T19:43:53Z |  |
| Kustomization | flux-system | llm | Ready | main@e497116 | 2026-09-14T19:36:18Z |  |
| Kustomization | flux-system | metrics-server | Ready | main@e497116 | 2026-09-14T19:35:23Z |  |
| Kustomization | flux-system | monitoring | Ready | main@e497116 | 2026-09-14T19:35:39Z |  |
| Kustomization | flux-system | monitoring-rules | Ready | main@e497116 | 2026-09-14T19:36:05Z |  |
| Kustomization | flux-system | nodesoftware-operator | Ready | main@e497116 | 2026-09-14T19:35:59Z |  |
| Kustomization | flux-system | notify | Ready | main@e497116 | 2026-09-14T19:35:40Z |  |
| Kustomization | flux-system | ns-fences | Ready | main@e497116 | 2026-09-14T19:44:53Z |  |
| Kustomization | flux-system | observability | Ready | main@e497116 | 2026-09-14T19:36:36Z |  |
| Kustomization | flux-system | observability-collector | Ready | main@e497116 | 2026-09-14T19:35:26Z |  |
| Kustomization | flux-system | otto-gateway | Ready | main@e497116 | 2026-09-14T19:35:47Z |  |
| Kustomization | flux-system | otto-golden | Ready | main@e497116 | 2026-09-14T19:35:45Z |  |
| Kustomization | flux-system | otto-golden-secret | Ready | main@e497116 | 2026-09-14T19:45:14Z |  |
| Kustomization | flux-system | priority-classes | Ready | main@e497116 | 2026-09-14T19:44:32Z |  |
| Kustomization | flux-system | prospector | Ready | main@7453d76 | 2026-09-14T19:35:52Z |  |
| Kustomization | flux-system | rbac | Ready | main@e497116 | 2026-09-14T19:44:30Z |  |
| Kustomization | flux-system | rbac-floor | Ready | main@e497116 | 2026-09-14T19:44:43Z |  |
| Kustomization | flux-system | rbac-identity | Ready | main@e497116 | 2026-09-14T19:44:12Z |  |
| Kustomization | flux-system | reloader | Ready | main@e497116 | 2026-09-14T19:35:30Z |  |
| Kustomization | flux-system | research-engine | Ready | main@e497116 | 2026-09-14T19:36:47Z |  |
| Kustomization | flux-system | robusta | Ready | main@e497116 | 2026-09-14T19:35:36Z |  |
| Kustomization | flux-system | router-events | Ready | main@e497116 | 2026-09-14T19:36:44Z |  |
| Kustomization | flux-system | sandbox-launch | Ready | main@e497116 | 2026-09-14T19:44:39Z |  |
| Kustomization | flux-system | sandbox-live | Ready | sandbox/launch@4830a6e | 2026-09-14T19:45:01Z |  |
| Kustomization | flux-system | scheduling | Ready | main@e497116 | 2026-09-14T19:44:56Z |  |
| Kustomization | flux-system | science | Ready | main@e497116 | 2026-09-14T19:36:46Z |  |
| Kustomization | flux-system | searxng | Ready | main@e497116 | 2026-09-14T19:44:02Z |  |
| Kustomization | flux-system | secret-store | Ready | main@e497116 | 2026-09-14T19:35:26Z |  |
| Kustomization | flux-system | spire | Ready | main@e497116 | 2026-09-14T19:35:29Z |  |
| Kustomization | flux-system | staging | Ready | main@e497116 | 2026-09-14T19:44:06Z |  |
| Kustomization | flux-system | tailscale | Ready | main@e497116 | 2026-09-14T19:45:07Z |  |
| Kustomization | flux-system | trivy | Ready | main@e497116 | 2026-09-14T19:44:05Z |  |
| Kustomization | flux-system | verification | Ready | main@e497116 | 2026-09-14T19:35:46Z |  |
| Kustomization | flux-system | weave-gitops | Ready | main@e497116 | 2026-09-14T19:36:13Z |  |
