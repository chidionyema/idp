# Flux: what is applied

Read from the cluster receipt taken at 2026-09-16T14:15:18Z. Every Kustomization and HelmRelease, with the revision Flux last applied. **Suspended** is a switch somebody turned off on purpose (temporal, commerce, commerce-data, event-bus), not a defect; **Unknown** is a row Flux has never graded.

**119 objects: 95 ready, 23 not ready, 0 unknown, 1 suspended.**

## Not ready right now

- **HelmRelease commerce/lago** since 2026-09-16T14:12:36Z: Helm install failed for release commerce/lago with chart lago@1.28.0: create: failed to create: admission webhook "oke-resource-leak-protection.oke.com" denied the request: OKE resource leak protection rejected the request. Cluster has 2650 secrets and the limit is 2000. See https://docs.oracle.com/iaas/Content/ContEng/Tasks/contengprotectingclustersfromresourceleaks.htm for details.
- **HelmRelease crossplane-system/crossplane** since 2026-09-16T13:56:01Z: Helm rollback to previous release crossplane-system/crossplane.v4 with chart crossplane@2.4.0 failed: create: failed to create: admission webhook "oke-resource-leak-protection.oke.com" denied the request: OKE resource leak protection rejected the request. Cluster has 2650 secrets and the limit is 2000. See https://docs.oracle.com/iaas/Content/ContEng/Tasks/contengprotectingclustersfromresourceleaks.htm for details.
- **Kustomization flux-system/agent-workforce** since 2026-09-16T14:11:43Z: dependency 'flux-system/alerts-github' is not ready
- **Kustomization flux-system/alerts-github** since 2026-09-16T14:11:59Z: ExternalSecret/flux-system/github-app dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-secrets.io": failed to call webhook: Post "https://external-secrets-webhook.external-secrets.svc:443/validate-external-secrets-io-v1-externalsecret?timeout=15s": context deadline exceeded 
- **Kustomization flux-system/backstage** since 2026-09-16T14:12:18Z: dependency 'flux-system/alerts-github' is not ready
- **Kustomization flux-system/chaos** since 2026-09-16T14:13:03Z: dependency 'flux-system/backstage' is not ready
- **Kustomization flux-system/commerce** since 2026-09-16T14:12:33Z: Reconciliation in progress
- **Kustomization flux-system/crossplane** since 2026-09-16T14:11:16Z: Reconciliation in progress
- **Kustomization flux-system/crossplane-providerconfig** since 2026-09-16T11:53:07Z: dependency 'flux-system/crossplane-providers' is not ready
- **Kustomization flux-system/crossplane-providers** since 2026-09-16T11:53:06Z: dependency 'flux-system/crossplane' is not ready
- **Kustomization flux-system/crossplane-storage-capability** since 2026-09-16T11:53:07Z: dependency 'flux-system/crossplane-providerconfig' is not ready
- **Kustomization flux-system/drills** since 2026-09-16T14:02:45Z: dependency 'flux-system/alerts-github' is not ready
- **Kustomization flux-system/epistemic-fabric** since 2026-09-16T14:11:14Z: dependency 'flux-system/alerts-github' is not ready
- **Kustomization flux-system/guacamole** since 2026-09-16T14:03:24Z: dependency 'flux-system/identity' is not ready
- **Kustomization flux-system/healing-analyzer** since 2026-09-16T14:02:36Z: dependency 'flux-system/healing-k8sgpt' is not ready
- **Kustomization flux-system/healing-k8sgpt** since 2026-09-16T14:12:58Z: ExternalSecret/healing/k8sgpt dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-secrets.io": failed to call webhook: Post "https://external-secrets-webhook.external-secrets.svc:443/validate-external-secrets-io-v1-externalsecret?timeout=15s": context deadline exceeded 
- **Kustomization flux-system/healthchecks** since 2026-09-16T14:03:34Z: dependency 'flux-system/identity' is not ready
- **Kustomization flux-system/hermes-agent** since 2026-09-16T14:11:43Z: dependency 'flux-system/alerts-github' is not ready
- **Kustomization flux-system/identity** since 2026-09-16T14:11:47Z: ExternalSecret/identity/oauth2-proxy dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-secrets.io": failed to call webhook: Post "https://external-secrets-webhook.external-secrets.svc:443/validate-external-secrets-io-v1-externalsecret?timeout=15s": context deadline exceeded 
- **Kustomization flux-system/mcp** since 2026-09-16T14:11:47Z: dependency 'flux-system/alerts-github' is not ready
- **Kustomization flux-system/otto-gateway** since 2026-09-16T14:11:59Z: dependency 'flux-system/alerts-github' is not ready
- **Kustomization flux-system/via-negativa** since 2026-09-16T14:13:03Z: health check failed after 411.194063ms: failed early due to stalled resources: [Deployment/via-negativa/via-negativa-rca status: 'Failed']
- **Kustomization flux-system/weave-gitops** since 2026-09-16T14:03:16Z: dependency 'flux-system/identity' is not ready

## Every row

| Kind | Namespace | Name | State | Applied revision | Since | Message |
|---|---|---|---|---|---|---|
| HelmRelease | commerce | lago | Not ready | 1.28.0 | 2026-09-16T14:12:36Z | Helm install failed for release commerce/lago with chart lago@1.28.0: create: failed to create: admission webhook "oke-resource-leak-protection.oke.com" denied  |
| HelmRelease | crossplane-system | crossplane | Not ready | 1.15.1 | 2026-09-16T13:56:01Z | Helm rollback to previous release crossplane-system/crossplane.v4 with chart crossplane@2.4.0 failed: create: failed to create: admission webhook "oke-resource- |
| Kustomization | flux-system | agent-workforce | Not ready | main@5c09168 | 2026-09-16T14:11:43Z | dependency 'flux-system/alerts-github' is not ready |
| Kustomization | flux-system | alerts-github | Not ready | main@5c09168 | 2026-09-16T14:11:59Z | ExternalSecret/flux-system/github-app dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-secrets. |
| Kustomization | flux-system | backstage | Not ready | main@79f78a1 | 2026-09-16T14:12:18Z | dependency 'flux-system/alerts-github' is not ready |
| Kustomization | flux-system | chaos | Not ready | main@79f78a1 | 2026-09-16T14:13:03Z | dependency 'flux-system/backstage' is not ready |
| Kustomization | flux-system | commerce | Not ready | main@abea14d | 2026-09-16T14:12:33Z | Reconciliation in progress |
| Kustomization | flux-system | crossplane | Not ready | main@8d685ec | 2026-09-16T14:11:16Z | Reconciliation in progress |
| Kustomization | flux-system | crossplane-providerconfig | Not ready | main@8d685ec | 2026-09-16T11:53:07Z | dependency 'flux-system/crossplane-providers' is not ready |
| Kustomization | flux-system | crossplane-providers | Not ready | main@8d685ec | 2026-09-16T11:53:06Z | dependency 'flux-system/crossplane' is not ready |
| Kustomization | flux-system | crossplane-storage-capability | Not ready | main@8d685ec | 2026-09-16T11:53:07Z | dependency 'flux-system/crossplane-providerconfig' is not ready |
| Kustomization | flux-system | drills | Not ready | main@5c09168 | 2026-09-16T14:02:45Z | dependency 'flux-system/alerts-github' is not ready |
| Kustomization | flux-system | epistemic-fabric | Not ready | main@5c09168 | 2026-09-16T14:11:14Z | dependency 'flux-system/alerts-github' is not ready |
| Kustomization | flux-system | guacamole | Not ready | main@5c09168 | 2026-09-16T14:03:24Z | dependency 'flux-system/identity' is not ready |
| Kustomization | flux-system | healing-analyzer | Not ready | main@5c09168 | 2026-09-16T14:02:36Z | dependency 'flux-system/healing-k8sgpt' is not ready |
| Kustomization | flux-system | healing-k8sgpt | Not ready | main@5c09168 | 2026-09-16T14:12:58Z | ExternalSecret/healing/k8sgpt dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-secrets.io": fai |
| Kustomization | flux-system | healthchecks | Not ready | main@5c09168 | 2026-09-16T14:03:34Z | dependency 'flux-system/identity' is not ready |
| Kustomization | flux-system | hermes-agent | Not ready | main@5c09168 | 2026-09-16T14:11:43Z | dependency 'flux-system/alerts-github' is not ready |
| Kustomization | flux-system | identity | Not ready | main@5c09168 | 2026-09-16T14:11:47Z | ExternalSecret/identity/oauth2-proxy dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-secrets.i |
| Kustomization | flux-system | mcp | Not ready | main@5c09168 | 2026-09-16T14:11:47Z | dependency 'flux-system/alerts-github' is not ready |
| Kustomization | flux-system | otto-gateway | Not ready | main@5c09168 | 2026-09-16T14:11:59Z | dependency 'flux-system/alerts-github' is not ready |
| Kustomization | flux-system | via-negativa | Not ready | main@f573545 | 2026-09-16T14:13:03Z | health check failed after 411.194063ms: failed early due to stalled resources: [Deployment/via-negativa/via-negativa-rca status: 'Failed'] |
| Kustomization | flux-system | weave-gitops | Not ready | main@5c09168 | 2026-09-16T14:03:16Z | dependency 'flux-system/identity' is not ready |
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
| Kustomization | flux-system | alerts | Ready | main@f573545 | 2026-09-16T14:12:07Z |  |
| Kustomization | flux-system | alerts-secret | Ready | main@f573545 | 2026-09-16T14:11:19Z |  |
| Kustomization | flux-system | autoscaler | Ready | main@f573545 | 2026-09-16T14:12:00Z |  |
| Kustomization | flux-system | backstage-namespace | Ready | main@f573545 | 2026-09-16T14:10:37Z |  |
| Kustomization | flux-system | calico | Ready | main@f573545 | 2026-09-16T14:10:29Z |  |
| Kustomization | flux-system | chaos-mesh | Ready | main@f573545 | 2026-09-16T14:11:14Z |  |
| Kustomization | flux-system | cluster-state | Ready | main@f573545 | 2026-09-16T14:11:21Z |  |
| Kustomization | flux-system | commerce-data | Ready | main@f573545 | 2026-09-16T14:12:08Z |  |
| Kustomization | flux-system | concierge | Ready | main@f573545 | 2026-09-16T14:12:01Z |  |
| Kustomization | flux-system | cross-node-drill | Ready | main@f573545 | 2026-09-16T14:10:35Z |  |
| Kustomization | flux-system | dagster | Ready | main@f573545 | 2026-09-16T14:12:13Z |  |
| Kustomization | flux-system | dns | Ready | main@f573545 | 2026-09-16T14:13:05Z |  |
| Kustomization | flux-system | edge | Ready | main@f573545 | 2026-09-16T14:10:49Z |  |
| Kustomization | flux-system | estate-catalog | Ready | latest@sha256:779d68f6c22944615c802cd380 | 2026-09-16T14:09:13Z |  |
| Kustomization | flux-system | estate-db | Ready | main@f573545 | 2026-09-16T14:11:21Z |  |
| Kustomization | flux-system | estate-db-migrate | Ready | main@f573545 | 2026-09-16T14:12:11Z |  |
| Kustomization | flux-system | estate-db-operator | Ready | main@f573545 | 2026-09-16T14:10:38Z |  |
| Kustomization | flux-system | event-bus | Ready | main@f573545 | 2026-09-16T14:10:51Z |  |
| Kustomization | flux-system | external-secrets | Ready | main@f573545 | 2026-09-16T14:10:51Z |  |
| Kustomization | flux-system | feature-register | Ready | main@f573545 | 2026-09-16T14:10:40Z |  |
| Kustomization | flux-system | flux-system | Ready | main@f573545 | 2026-09-16T14:10:49Z |  |
| Kustomization | flux-system | flux-webhook | Ready | main@f573545 | 2026-09-16T14:11:20Z |  |
| Kustomization | flux-system | gateway-api-crds | Ready | v1.5.1@e7677b7 | 2026-09-16T14:10:33Z |  |
| Kustomization | flux-system | gvisor-runtime | Ready | main@f573545 | 2026-09-16T14:12:38Z |  |
| Kustomization | flux-system | healing | Ready | main@f573545 | 2026-09-16T14:11:06Z |  |
| Kustomization | flux-system | hindsight | Ready | main@f573545 | 2026-09-16T14:13:02Z |  |
| Kustomization | flux-system | human-vault | Ready | main@f573545 | 2026-09-16T14:12:05Z |  |
| Kustomization | flux-system | human-vault-bridge | Ready | main@f573545 | 2026-09-16T14:12:18Z |  |
| Kustomization | flux-system | image-automation | Ready | main@f573545 | 2026-09-16T14:12:02Z |  |
| Kustomization | flux-system | jit | Ready | main@f573545 | 2026-09-16T14:11:11Z |  |
| Kustomization | flux-system | keda | Ready | main@f573545 | 2026-09-16T14:11:11Z |  |
| Kustomization | flux-system | kyverno | Ready | main@f573545 | 2026-09-16T14:10:42Z |  |
| Kustomization | flux-system | llm | Ready | main@f573545 | 2026-09-16T14:12:42Z |  |
| Kustomization | flux-system | metrics-server | Ready | main@f573545 | 2026-09-16T14:11:10Z |  |
| Kustomization | flux-system | monitoring | Ready | main@f573545 | 2026-09-16T14:11:17Z |  |
| Kustomization | flux-system | monitoring-rules | Ready | main@f573545 | 2026-09-16T14:12:04Z |  |
| Kustomization | flux-system | nodesoftware-operator | Ready | main@f573545 | 2026-09-16T14:12:08Z |  |
| Kustomization | flux-system | notify | Ready | main@f573545 | 2026-09-16T14:12:05Z |  |
| Kustomization | flux-system | ns-fences | Ready | main@f573545 | 2026-09-16T14:10:45Z |  |
| Kustomization | flux-system | observability | Ready | main@f573545 | 2026-09-16T14:12:40Z |  |
| Kustomization | flux-system | observability-collector | Ready | main@f573545 | 2026-09-16T14:11:13Z |  |
| Kustomization | flux-system | otto-golden | Ready | main@f573545 | 2026-09-16T14:12:11Z |  |
| Kustomization | flux-system | otto-golden-secret | Ready | main@f573545 | 2026-09-16T14:11:29Z |  |
| Kustomization | flux-system | priority-classes | Ready | main@f573545 | 2026-09-16T14:10:31Z |  |
| Kustomization | flux-system | prospector | Ready | main@7453d76 | 2026-09-16T14:07:26Z |  |
| Kustomization | flux-system | prospector-platform | Ready | main@f573545 | 2026-09-16T14:11:03Z |  |
| Kustomization | flux-system | rbac | Ready | main@f573545 | 2026-09-16T14:10:45Z |  |
| Kustomization | flux-system | rbac-floor | Ready | main@f573545 | 2026-09-16T14:10:43Z |  |
| Kustomization | flux-system | rbac-identity | Ready | main@f573545 | 2026-09-16T14:10:28Z |  |
| Kustomization | flux-system | reloader | Ready | main@f573545 | 2026-09-16T14:11:15Z |  |
| Kustomization | flux-system | research-engine | Ready | main@f573545 | 2026-09-16T14:13:00Z |  |
| Kustomization | flux-system | robusta | Ready | main@f573545 | 2026-09-16T14:12:06Z |  |
| Kustomization | flux-system | router-events | Ready | main@f573545 | 2026-09-16T14:13:08Z |  |
| Kustomization | flux-system | sandbox-launch | Ready | main@f573545 | 2026-09-16T14:11:31Z |  |
| Kustomization | flux-system | sandbox-live | Ready | sandbox/launch@4830a6e | 2026-09-16T14:15:10Z |  |
| Kustomization | flux-system | scheduling | Ready | main@f573545 | 2026-09-16T14:11:05Z |  |
| Kustomization | flux-system | science | Ready | main@f573545 | 2026-09-16T14:13:07Z |  |
| Kustomization | flux-system | searxng | Ready | main@f573545 | 2026-09-16T14:10:26Z |  |
| Kustomization | flux-system | secret-store | Ready | main@f573545 | 2026-09-16T14:11:04Z |  |
| Kustomization | flux-system | spire | Ready | main@f573545 | 2026-09-16T14:11:08Z |  |
| Kustomization | flux-system | staging | Ready | main@f573545 | 2026-09-16T14:10:26Z |  |
| Kustomization | flux-system | tailscale | Ready | main@f573545 | 2026-09-16T14:11:29Z |  |
| Kustomization | flux-system | temporal | Ready | main@f573545 | 2026-09-16T14:12:50Z |  |
| Kustomization | flux-system | trivy | Ready | main@f573545 | 2026-09-16T14:10:39Z |  |
| Kustomization | flux-system | verification | Ready | main@f573545 | 2026-09-16T14:11:43Z |  |
