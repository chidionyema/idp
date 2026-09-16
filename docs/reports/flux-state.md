# Flux: what is applied

Read from the cluster receipt taken at 2026-09-16T13:45:22Z. Every Kustomization and HelmRelease, with the revision Flux last applied. **Suspended** is a switch somebody turned off on purpose (temporal, commerce, commerce-data, event-bus), not a defect; **Unknown** is a row Flux has never graded.

**119 objects: 97 ready, 21 not ready, 0 unknown, 1 suspended.**

## Not ready right now

- **HelmRelease commerce/lago** since 2026-09-16T13:42:32Z: Running 'install' action with timeout of 20m0s
- **HelmRelease crossplane-system/crossplane** since 2026-09-16T13:30:57Z: Helm upgrade failed for release crossplane-system/crossplane with chart crossplane@1.15.1: create: failed to create: admission webhook "oke-resource-leak-protection.oke.com" denied the request: OKE resource leak protection rejected the request. Cluster has 2650 secrets and the limit is 2000. See https://docs.oracle.com/iaas/Content/ContEng/Tasks/contengprotectingclustersfromresourceleaks.htm for details.
- **Kustomization flux-system/agent-workforce** since 2026-09-16T13:41:29Z: dependency 'flux-system/alerts-github' is not ready
- **Kustomization flux-system/alerts-github** since 2026-09-16T13:42:03Z: ExternalSecret/flux-system/github-app dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-secrets.io": failed to call webhook: Post "https://external-secrets-webhook.external-secrets.svc:443/validate-external-secrets-io-v1-externalsecret?timeout=15s": context deadline exceeded 
- **Kustomization flux-system/backstage** since 2026-09-16T13:42:27Z: dependency 'flux-system/alerts-github' is not ready
- **Kustomization flux-system/chaos** since 2026-09-16T13:42:38Z: dependency 'flux-system/backstage' is not ready
- **Kustomization flux-system/commerce** since 2026-09-16T13:42:30Z: Reconciliation in progress
- **Kustomization flux-system/crossplane** since 2026-09-16T13:41:13Z: Reconciliation in progress
- **Kustomization flux-system/crossplane-providerconfig** since 2026-09-16T11:53:07Z: dependency 'flux-system/crossplane-providers' is not ready
- **Kustomization flux-system/crossplane-providers** since 2026-09-16T11:53:06Z: dependency 'flux-system/crossplane' is not ready
- **Kustomization flux-system/crossplane-storage-capability** since 2026-09-16T11:53:07Z: dependency 'flux-system/crossplane-providerconfig' is not ready
- **Kustomization flux-system/drills** since 2026-09-16T13:40:30Z: dependency 'flux-system/alerts-github' is not ready
- **Kustomization flux-system/epistemic-fabric** since 2026-09-16T13:41:49Z: dependency 'flux-system/alerts-github' is not ready
- **Kustomization flux-system/guacamole** since 2026-09-16T13:40:54Z: dependency 'flux-system/identity' is not ready
- **Kustomization flux-system/healthchecks** since 2026-09-16T13:40:54Z: dependency 'flux-system/identity' is not ready
- **Kustomization flux-system/hermes-agent** since 2026-09-16T13:41:49Z: dependency 'flux-system/alerts-github' is not ready
- **Kustomization flux-system/identity** since 2026-09-16T13:41:48Z: ExternalSecret/identity/oauth2-proxy dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-secrets.io": failed to call webhook: Post "https://external-secrets-webhook.external-secrets.svc:443/validate-external-secrets-io-v1-externalsecret?timeout=15s": context deadline exceeded 
- **Kustomization flux-system/mcp** since 2026-09-16T13:41:49Z: dependency 'flux-system/alerts-github' is not ready
- **Kustomization flux-system/otto-gateway** since 2026-09-16T13:41:52Z: dependency 'flux-system/alerts-github' is not ready
- **Kustomization flux-system/via-negativa** since 2026-09-16T13:42:35Z: health check failed after 366.280294ms: failed early due to stalled resources: [Deployment/via-negativa/via-negativa-rca status: 'Failed']
- **Kustomization flux-system/weave-gitops** since 2026-09-16T13:40:29Z: dependency 'flux-system/identity' is not ready

## Every row

| Kind | Namespace | Name | State | Applied revision | Since | Message |
|---|---|---|---|---|---|---|
| HelmRelease | commerce | lago | Not ready | 1.28.0 | 2026-09-16T13:42:32Z | Running 'install' action with timeout of 20m0s |
| HelmRelease | crossplane-system | crossplane | Not ready | 1.15.1 | 2026-09-16T13:30:57Z | Helm upgrade failed for release crossplane-system/crossplane with chart crossplane@1.15.1: create: failed to create: admission webhook "oke-resource-leak-protec |
| Kustomization | flux-system | agent-workforce | Not ready | main@79f78a1 | 2026-09-16T13:41:29Z | dependency 'flux-system/alerts-github' is not ready |
| Kustomization | flux-system | alerts-github | Not ready | main@afe1ca0 | 2026-09-16T13:42:03Z | ExternalSecret/flux-system/github-app dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-secrets. |
| Kustomization | flux-system | backstage | Not ready | main@79f78a1 | 2026-09-16T13:42:27Z | dependency 'flux-system/alerts-github' is not ready |
| Kustomization | flux-system | chaos | Not ready | main@79f78a1 | 2026-09-16T13:42:38Z | dependency 'flux-system/backstage' is not ready |
| Kustomization | flux-system | commerce | Not ready | main@abea14d | 2026-09-16T13:42:30Z | Reconciliation in progress |
| Kustomization | flux-system | crossplane | Not ready | main@8d685ec | 2026-09-16T13:41:13Z | Reconciliation in progress |
| Kustomization | flux-system | crossplane-providerconfig | Not ready | main@8d685ec | 2026-09-16T11:53:07Z | dependency 'flux-system/crossplane-providers' is not ready |
| Kustomization | flux-system | crossplane-providers | Not ready | main@8d685ec | 2026-09-16T11:53:06Z | dependency 'flux-system/crossplane' is not ready |
| Kustomization | flux-system | crossplane-storage-capability | Not ready | main@8d685ec | 2026-09-16T11:53:07Z | dependency 'flux-system/crossplane-providerconfig' is not ready |
| Kustomization | flux-system | drills | Not ready | main@afe1ca0 | 2026-09-16T13:40:30Z | dependency 'flux-system/alerts-github' is not ready |
| Kustomization | flux-system | epistemic-fabric | Not ready | main@afe1ca0 | 2026-09-16T13:41:49Z | dependency 'flux-system/alerts-github' is not ready |
| Kustomization | flux-system | guacamole | Not ready | main@b9c7cf4 | 2026-09-16T13:40:54Z | dependency 'flux-system/identity' is not ready |
| Kustomization | flux-system | healthchecks | Not ready | main@b9c7cf4 | 2026-09-16T13:40:54Z | dependency 'flux-system/identity' is not ready |
| Kustomization | flux-system | hermes-agent | Not ready | main@79f78a1 | 2026-09-16T13:41:49Z | dependency 'flux-system/alerts-github' is not ready |
| Kustomization | flux-system | identity | Not ready | main@afe1ca0 | 2026-09-16T13:41:48Z | ExternalSecret/identity/oauth2-proxy dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-secrets.i |
| Kustomization | flux-system | mcp | Not ready | main@afe1ca0 | 2026-09-16T13:41:49Z | dependency 'flux-system/alerts-github' is not ready |
| Kustomization | flux-system | otto-gateway | Not ready | main@afe1ca0 | 2026-09-16T13:41:52Z | dependency 'flux-system/alerts-github' is not ready |
| Kustomization | flux-system | via-negativa | Not ready | main@320c45c | 2026-09-16T13:42:35Z | health check failed after 366.280294ms: failed early due to stalled resources: [Deployment/via-negativa/via-negativa-rca status: 'Failed'] |
| Kustomization | flux-system | weave-gitops | Not ready | main@afe1ca0 | 2026-09-16T13:40:29Z | dependency 'flux-system/identity' is not ready |
| HelmRelease | tigera-operator | tigera-operator | Suspended | v3.32.2 | 2026-09-06T19:38:02Z |  |
| HelmRelease | cert-manager | cert-manager | Ready | v1.21.1 | 2026-09-08T11:56:22Z |  |
| HelmRelease | chaos-mesh | chaos-mesh | Ready | 2.8.4 | 2026-09-15T14:48:03Z |  |
| HelmRelease | dagster | dagster | Ready | 1.13.19 | 2026-09-12T12:32:50Z |  |
| HelmRelease | edge | external-dns | Ready | 1.21.1 | 2026-09-06T19:33:35Z |  |
| HelmRelease | edge | traefik | Ready | 41.3.0 | 2026-09-06T19:35:13Z |  |
| HelmRelease | estate-db | cloudnative-pg | Ready | 0.29.0 | 2026-09-06T19:45:25Z |  |
| HelmRelease | event-bus | nats | Ready | 2.14.6 | 2026-09-06T19:39:37Z |  |
| HelmRelease | external-secrets | external-secrets | Ready | 2.9.0 | 2026-09-14T20:24:54Z |  |
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
| HelmRelease | temporal | temporal | Ready | 1.6.0 | 2026-09-15T14:03:10Z |  |
| HelmRelease | trivy-system | trivy-operator | Ready | 0.36.0 | 2026-09-06T20:26:45Z |  |
| HelmRelease | weave-gitops | weave-gitops | Ready | 4.0.36 | 2026-09-06T20:26:45Z |  |
| Kustomization | flux-system | alerts | Ready | main@320c45c | 2026-09-16T13:41:37Z |  |
| Kustomization | flux-system | alerts-secret | Ready | main@320c45c | 2026-09-16T13:41:33Z |  |
| Kustomization | flux-system | autoscaler | Ready | main@320c45c | 2026-09-16T13:41:38Z |  |
| Kustomization | flux-system | backstage-namespace | Ready | main@320c45c | 2026-09-16T13:40:32Z |  |
| Kustomization | flux-system | calico | Ready | main@320c45c | 2026-09-16T13:40:33Z |  |
| Kustomization | flux-system | chaos-mesh | Ready | main@320c45c | 2026-09-16T13:41:09Z |  |
| Kustomization | flux-system | cluster-state | Ready | main@320c45c | 2026-09-16T13:41:46Z |  |
| Kustomization | flux-system | commerce-data | Ready | main@320c45c | 2026-09-16T13:42:02Z |  |
| Kustomization | flux-system | concierge | Ready | main@320c45c | 2026-09-16T13:41:35Z |  |
| Kustomization | flux-system | cross-node-drill | Ready | main@320c45c | 2026-09-16T13:40:41Z |  |
| Kustomization | flux-system | dagster | Ready | main@320c45c | 2026-09-16T13:42:03Z |  |
| Kustomization | flux-system | dns | Ready | main@320c45c | 2026-09-16T13:41:55Z |  |
| Kustomization | flux-system | edge | Ready | main@320c45c | 2026-09-16T13:40:55Z |  |
| Kustomization | flux-system | estate-catalog | Ready | latest@sha256:779d68f6c22944615c802cd380 | 2026-09-16T13:39:00Z |  |
| Kustomization | flux-system | estate-db | Ready | main@320c45c | 2026-09-16T13:41:42Z |  |
| Kustomization | flux-system | estate-db-migrate | Ready | main@320c45c | 2026-09-16T13:42:00Z |  |
| Kustomization | flux-system | estate-db-operator | Ready | main@320c45c | 2026-09-16T13:40:42Z |  |
| Kustomization | flux-system | event-bus | Ready | main@320c45c | 2026-09-16T13:41:13Z |  |
| Kustomization | flux-system | external-secrets | Ready | main@320c45c | 2026-09-16T13:41:20Z |  |
| Kustomization | flux-system | feature-register | Ready | main@320c45c | 2026-09-16T13:40:51Z |  |
| Kustomization | flux-system | flux-system | Ready | main@320c45c | 2026-09-16T13:40:38Z |  |
| Kustomization | flux-system | flux-webhook | Ready | main@320c45c | 2026-09-16T13:41:47Z |  |
| Kustomization | flux-system | gateway-api-crds | Ready | v1.5.1@e7677b7 | 2026-09-16T13:40:44Z |  |
| Kustomization | flux-system | gvisor-runtime | Ready | main@320c45c | 2026-09-16T13:42:12Z |  |
| Kustomization | flux-system | healing | Ready | main@320c45c | 2026-09-16T13:41:28Z |  |
| Kustomization | flux-system | healing-analyzer | Ready | main@320c45c | 2026-09-16T13:43:02Z |  |
| Kustomization | flux-system | healing-k8sgpt | Ready | main@320c45c | 2026-09-16T13:42:33Z |  |
| Kustomization | flux-system | hindsight | Ready | main@320c45c | 2026-09-16T13:42:38Z |  |
| Kustomization | flux-system | human-vault | Ready | main@320c45c | 2026-09-16T13:41:49Z |  |
| Kustomization | flux-system | human-vault-bridge | Ready | main@320c45c | 2026-09-16T13:41:51Z |  |
| Kustomization | flux-system | image-automation | Ready | main@320c45c | 2026-09-16T13:41:44Z |  |
| Kustomization | flux-system | jit | Ready | main@320c45c | 2026-09-16T13:40:54Z |  |
| Kustomization | flux-system | keda | Ready | main@320c45c | 2026-09-16T13:41:56Z |  |
| Kustomization | flux-system | kyverno | Ready | main@320c45c | 2026-09-16T13:40:46Z |  |
| Kustomization | flux-system | llm | Ready | main@320c45c | 2026-09-16T13:42:06Z |  |
| Kustomization | flux-system | metrics-server | Ready | main@320c45c | 2026-09-16T13:41:34Z |  |
| Kustomization | flux-system | monitoring | Ready | main@320c45c | 2026-09-16T13:41:58Z |  |
| Kustomization | flux-system | monitoring-rules | Ready | main@320c45c | 2026-09-16T13:42:24Z |  |
| Kustomization | flux-system | nodesoftware-operator | Ready | main@320c45c | 2026-09-16T13:41:57Z |  |
| Kustomization | flux-system | notify | Ready | main@320c45c | 2026-09-16T13:41:39Z |  |
| Kustomization | flux-system | ns-fences | Ready | main@320c45c | 2026-09-16T13:40:45Z |  |
| Kustomization | flux-system | observability | Ready | main@320c45c | 2026-09-16T13:42:09Z |  |
| Kustomization | flux-system | observability-collector | Ready | main@320c45c | 2026-09-16T13:41:53Z |  |
| Kustomization | flux-system | otto-golden | Ready | main@320c45c | 2026-09-16T13:42:08Z |  |
| Kustomization | flux-system | otto-golden-secret | Ready | main@320c45c | 2026-09-16T13:41:45Z |  |
| Kustomization | flux-system | priority-classes | Ready | main@320c45c | 2026-09-16T13:40:52Z |  |
| Kustomization | flux-system | prospector | Ready | main@7453d76 | 2026-09-16T13:37:19Z |  |
| Kustomization | flux-system | prospector-platform | Ready | main@320c45c | 2026-09-16T13:41:41Z |  |
| Kustomization | flux-system | rbac | Ready | main@320c45c | 2026-09-16T13:41:16Z |  |
| Kustomization | flux-system | rbac-floor | Ready | main@320c45c | 2026-09-16T13:40:39Z |  |
| Kustomization | flux-system | rbac-identity | Ready | main@320c45c | 2026-09-16T13:40:50Z |  |
| Kustomization | flux-system | reloader | Ready | main@320c45c | 2026-09-16T13:41:30Z |  |
| Kustomization | flux-system | research-engine | Ready | main@320c45c | 2026-09-16T13:42:38Z |  |
| Kustomization | flux-system | robusta | Ready | main@320c45c | 2026-09-16T13:41:36Z |  |
| Kustomization | flux-system | router-events | Ready | main@320c45c | 2026-09-16T13:42:34Z |  |
| Kustomization | flux-system | sandbox-launch | Ready | main@320c45c | 2026-09-16T13:41:25Z |  |
| Kustomization | flux-system | sandbox-live | Ready | sandbox/launch@4830a6e | 2026-09-16T13:44:23Z |  |
| Kustomization | flux-system | scheduling | Ready | main@320c45c | 2026-09-16T13:41:04Z |  |
| Kustomization | flux-system | science | Ready | main@320c45c | 2026-09-16T13:42:32Z |  |
| Kustomization | flux-system | searxng | Ready | main@320c45c | 2026-09-16T13:40:48Z |  |
| Kustomization | flux-system | secret-store | Ready | main@320c45c | 2026-09-16T13:41:25Z |  |
| Kustomization | flux-system | spire | Ready | main@320c45c | 2026-09-16T13:41:27Z |  |
| Kustomization | flux-system | staging | Ready | main@320c45c | 2026-09-16T13:40:50Z |  |
| Kustomization | flux-system | tailscale | Ready | main@320c45c | 2026-09-16T13:41:32Z |  |
| Kustomization | flux-system | temporal | Ready | main@320c45c | 2026-09-16T13:42:05Z |  |
| Kustomization | flux-system | trivy | Ready | main@320c45c | 2026-09-16T13:40:47Z |  |
| Kustomization | flux-system | verification | Ready | main@320c45c | 2026-09-16T13:41:52Z |  |
