# Flux: what is applied

Read from the cluster receipt taken at 2026-09-16T14:00:16Z. Every Kustomization and HelmRelease, with the revision Flux last applied. **Suspended** is a switch somebody turned off on purpose (temporal, commerce, commerce-data, event-bus), not a defect; **Unknown** is a row Flux has never graded.

**119 objects: 104 ready, 14 not ready, 0 unknown, 1 suspended.**

## Not ready right now

- **HelmRelease commerce/lago** since 2026-09-16T13:54:47Z: Helm install failed for release commerce/lago with chart lago@1.28.0: failed early due to stalled resources: [Deployment/commerce/lago-clock-worker status: 'Failed']
- **HelmRelease crossplane-system/crossplane** since 2026-09-16T13:56:01Z: Helm rollback to previous release crossplane-system/crossplane.v4 with chart crossplane@2.4.0 failed: create: failed to create: admission webhook "oke-resource-leak-protection.oke.com" denied the request: OKE resource leak protection rejected the request. Cluster has 2650 secrets and the limit is 2000. See https://docs.oracle.com/iaas/Content/ContEng/Tasks/contengprotectingclustersfromresourceleaks.htm for details.
- **Kustomization flux-system/backstage** since 2026-09-16T13:53:14Z: ExternalSecret/backstage/backstage-env dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-secrets.io": failed to call webhook: Post "https://external-secrets-webhook.external-secrets.svc:443/validate-external-secrets-io-v1-externalsecret?timeout=15s": context deadline exceeded 
- **Kustomization flux-system/chaos** since 2026-09-16T13:53:44Z: dependency 'flux-system/backstage' is not ready
- **Kustomization flux-system/commerce** since 2026-09-16T13:57:32Z: Reconciliation in progress
- **Kustomization flux-system/crossplane** since 2026-09-16T13:56:15Z: Reconciliation in progress
- **Kustomization flux-system/crossplane-providerconfig** since 2026-09-16T11:53:07Z: dependency 'flux-system/crossplane-providers' is not ready
- **Kustomization flux-system/crossplane-providers** since 2026-09-16T11:53:06Z: dependency 'flux-system/crossplane' is not ready
- **Kustomization flux-system/crossplane-storage-capability** since 2026-09-16T11:53:07Z: dependency 'flux-system/crossplane-providerconfig' is not ready
- **Kustomization flux-system/edge** since 2026-09-16T14:00:08Z: Reconciliation in progress
- **Kustomization flux-system/epistemic-fabric** since 2026-09-16T13:52:56Z: ExternalSecret/epistemic-fabric/epistemic-fabric-github-api dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-secrets.io": failed to call webhook: Post "https://external-secrets-webhook.external-secrets.svc:443/validate-external-secrets-io-v1-externalsecret?timeout=15s": context deadline exceeded 
- **Kustomization flux-system/hindsight** since 2026-09-16T13:52:41Z: ExternalSecret/hindsight/hindsight-env dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-secrets.io": failed to call webhook: Post "https://external-secrets-webhook.external-secrets.svc:443/validate-external-secrets-io-v1-externalsecret?timeout=15s": context deadline exceeded 
- **Kustomization flux-system/verification** since 2026-09-16T13:51:39Z: ExternalSecret/backstage/verdict-key-wall dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-secrets.io": failed to call webhook: Post "https://external-secrets-webhook.external-secrets.svc:443/validate-external-secrets-io-v1-externalsecret?timeout=15s": context deadline exceeded 
- **Kustomization flux-system/via-negativa** since 2026-09-16T13:52:34Z: ExternalSecret/via-negativa/via-negativa-db dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-secrets.io": failed to call webhook: Post "https://external-secrets-webhook.external-secrets.svc:443/validate-external-secrets-io-v1-externalsecret?timeout=15s": context deadline exceeded 

## Every row

| Kind | Namespace | Name | State | Applied revision | Since | Message |
|---|---|---|---|---|---|---|
| HelmRelease | commerce | lago | Not ready | 1.28.0 | 2026-09-16T13:54:47Z | Helm install failed for release commerce/lago with chart lago@1.28.0: failed early due to stalled resources: [Deployment/commerce/lago-clock-worker status: 'Fai |
| HelmRelease | crossplane-system | crossplane | Not ready | 1.15.1 | 2026-09-16T13:56:01Z | Helm rollback to previous release crossplane-system/crossplane.v4 with chart crossplane@2.4.0 failed: create: failed to create: admission webhook "oke-resource- |
| Kustomization | flux-system | backstage | Not ready | main@79f78a1 | 2026-09-16T13:53:14Z | ExternalSecret/backstage/backstage-env dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-secrets |
| Kustomization | flux-system | chaos | Not ready | main@79f78a1 | 2026-09-16T13:53:44Z | dependency 'flux-system/backstage' is not ready |
| Kustomization | flux-system | commerce | Not ready | main@abea14d | 2026-09-16T13:57:32Z | Reconciliation in progress |
| Kustomization | flux-system | crossplane | Not ready | main@8d685ec | 2026-09-16T13:56:15Z | Reconciliation in progress |
| Kustomization | flux-system | crossplane-providerconfig | Not ready | main@8d685ec | 2026-09-16T11:53:07Z | dependency 'flux-system/crossplane-providers' is not ready |
| Kustomization | flux-system | crossplane-providers | Not ready | main@8d685ec | 2026-09-16T11:53:06Z | dependency 'flux-system/crossplane' is not ready |
| Kustomization | flux-system | crossplane-storage-capability | Not ready | main@8d685ec | 2026-09-16T11:53:07Z | dependency 'flux-system/crossplane-providerconfig' is not ready |
| Kustomization | flux-system | edge | Not ready | main@5c09168 | 2026-09-16T14:00:08Z | Reconciliation in progress |
| Kustomization | flux-system | epistemic-fabric | Not ready | main@5c09168 | 2026-09-16T13:52:56Z | ExternalSecret/epistemic-fabric/epistemic-fabric-github-api dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalse |
| Kustomization | flux-system | hindsight | Not ready | main@320c45c | 2026-09-16T13:52:41Z | ExternalSecret/hindsight/hindsight-env dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-secrets |
| Kustomization | flux-system | verification | Not ready | main@320c45c | 2026-09-16T13:51:39Z | ExternalSecret/backstage/verdict-key-wall dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-secr |
| Kustomization | flux-system | via-negativa | Not ready | main@5c09168 | 2026-09-16T13:52:34Z | ExternalSecret/via-negativa/via-negativa-db dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-se |
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
| Kustomization | flux-system | agent-workforce | Ready | main@5c09168 | 2026-09-16T13:53:20Z |  |
| Kustomization | flux-system | alerts | Ready | main@5c09168 | 2026-09-16T13:53:52Z |  |
| Kustomization | flux-system | alerts-github | Ready | main@5c09168 | 2026-09-16T13:51:59Z |  |
| Kustomization | flux-system | alerts-secret | Ready | main@5c09168 | 2026-09-16T13:53:22Z |  |
| Kustomization | flux-system | autoscaler | Ready | main@5c09168 | 2026-09-16T13:50:59Z |  |
| Kustomization | flux-system | backstage-namespace | Ready | main@5c09168 | 2026-09-16T13:59:20Z |  |
| Kustomization | flux-system | calico | Ready | main@5c09168 | 2026-09-16T13:59:39Z |  |
| Kustomization | flux-system | chaos-mesh | Ready | main@5c09168 | 2026-09-16T13:53:17Z |  |
| Kustomization | flux-system | cluster-state | Ready | main@5c09168 | 2026-09-16T13:51:18Z |  |
| Kustomization | flux-system | commerce-data | Ready | main@5c09168 | 2026-09-16T13:52:02Z |  |
| Kustomization | flux-system | concierge | Ready | main@5c09168 | 2026-09-16T13:50:53Z |  |
| Kustomization | flux-system | cross-node-drill | Ready | main@5c09168 | 2026-09-16T13:59:52Z |  |
| Kustomization | flux-system | dagster | Ready | main@5c09168 | 2026-09-16T13:51:58Z |  |
| Kustomization | flux-system | dns | Ready | main@5c09168 | 2026-09-16T13:51:44Z |  |
| Kustomization | flux-system | drills | Ready | main@5c09168 | 2026-09-16T13:52:38Z |  |
| Kustomization | flux-system | estate-catalog | Ready | latest@sha256:779d68f6c22944615c802cd380 | 2026-09-16T13:58:46Z |  |
| Kustomization | flux-system | estate-db | Ready | main@5c09168 | 2026-09-16T13:50:57Z |  |
| Kustomization | flux-system | estate-db-migrate | Ready | main@5c09168 | 2026-09-16T13:51:57Z |  |
| Kustomization | flux-system | estate-db-operator | Ready | main@5c09168 | 2026-09-16T13:59:45Z |  |
| Kustomization | flux-system | event-bus | Ready | main@5c09168 | 2026-09-16T13:50:15Z |  |
| Kustomization | flux-system | external-secrets | Ready | main@5c09168 | 2026-09-16T13:50:17Z |  |
| Kustomization | flux-system | feature-register | Ready | main@5c09168 | 2026-09-16T13:59:41Z |  |
| Kustomization | flux-system | flux-system | Ready | main@5c09168 | 2026-09-16T13:59:37Z |  |
| Kustomization | flux-system | flux-webhook | Ready | main@5c09168 | 2026-09-16T13:51:17Z |  |
| Kustomization | flux-system | gateway-api-crds | Ready | v1.5.1@e7677b7 | 2026-09-16T13:59:31Z |  |
| Kustomization | flux-system | guacamole | Ready | main@5c09168 | 2026-09-16T13:53:40Z |  |
| Kustomization | flux-system | gvisor-runtime | Ready | main@5c09168 | 2026-09-16T13:52:10Z |  |
| Kustomization | flux-system | healing | Ready | main@5c09168 | 2026-09-16T13:50:50Z |  |
| Kustomization | flux-system | healing-analyzer | Ready | main@5c09168 | 2026-09-16T13:52:39Z |  |
| Kustomization | flux-system | healing-k8sgpt | Ready | main@5c09168 | 2026-09-16T13:52:17Z |  |
| Kustomization | flux-system | healthchecks | Ready | main@5c09168 | 2026-09-16T13:53:06Z |  |
| Kustomization | flux-system | hermes-agent | Ready | main@5c09168 | 2026-09-16T13:52:45Z |  |
| Kustomization | flux-system | human-vault | Ready | main@5c09168 | 2026-09-16T13:51:32Z |  |
| Kustomization | flux-system | human-vault-bridge | Ready | main@5c09168 | 2026-09-16T13:53:31Z |  |
| Kustomization | flux-system | identity | Ready | main@5c09168 | 2026-09-16T13:51:23Z |  |
| Kustomization | flux-system | image-automation | Ready | main@5c09168 | 2026-09-16T13:51:11Z |  |
| Kustomization | flux-system | jit | Ready | main@5c09168 | 2026-09-16T13:50:13Z |  |
| Kustomization | flux-system | keda | Ready | main@5c09168 | 2026-09-16T13:51:41Z |  |
| Kustomization | flux-system | kyverno | Ready | main@5c09168 | 2026-09-16T14:00:06Z |  |
| Kustomization | flux-system | llm | Ready | main@5c09168 | 2026-09-16T13:52:08Z |  |
| Kustomization | flux-system | mcp | Ready | main@5c09168 | 2026-09-16T13:52:48Z |  |
| Kustomization | flux-system | metrics-server | Ready | main@5c09168 | 2026-09-16T13:50:52Z |  |
| Kustomization | flux-system | monitoring | Ready | main@5c09168 | 2026-09-16T13:51:56Z |  |
| Kustomization | flux-system | monitoring-rules | Ready | main@5c09168 | 2026-09-16T13:52:11Z |  |
| Kustomization | flux-system | nodesoftware-operator | Ready | main@5c09168 | 2026-09-16T13:51:43Z |  |
| Kustomization | flux-system | notify | Ready | main@5c09168 | 2026-09-16T13:50:56Z |  |
| Kustomization | flux-system | ns-fences | Ready | main@5c09168 | 2026-09-16T13:50:07Z |  |
| Kustomization | flux-system | observability | Ready | main@5c09168 | 2026-09-16T13:52:09Z |  |
| Kustomization | flux-system | observability-collector | Ready | main@5c09168 | 2026-09-16T13:51:33Z |  |
| Kustomization | flux-system | otto-gateway | Ready | main@5c09168 | 2026-09-16T13:52:51Z |  |
| Kustomization | flux-system | otto-golden | Ready | main@5c09168 | 2026-09-16T13:52:05Z |  |
| Kustomization | flux-system | otto-golden-secret | Ready | main@5c09168 | 2026-09-16T13:51:12Z |  |
| Kustomization | flux-system | priority-classes | Ready | main@5c09168 | 2026-09-16T13:59:53Z |  |
| Kustomization | flux-system | prospector | Ready | main@7453d76 | 2026-09-16T13:57:10Z |  |
| Kustomization | flux-system | prospector-platform | Ready | main@5c09168 | 2026-09-16T13:50:20Z |  |
| Kustomization | flux-system | rbac | Ready | main@5c09168 | 2026-09-16T13:50:16Z |  |
| Kustomization | flux-system | rbac-floor | Ready | main@5c09168 | 2026-09-16T13:49:46Z |  |
| Kustomization | flux-system | rbac-identity | Ready | main@5c09168 | 2026-09-16T13:59:40Z |  |
| Kustomization | flux-system | reloader | Ready | main@5c09168 | 2026-09-16T13:53:18Z |  |
| Kustomization | flux-system | research-engine | Ready | main@5c09168 | 2026-09-16T13:52:36Z |  |
| Kustomization | flux-system | robusta | Ready | main@5c09168 | 2026-09-16T13:50:53Z |  |
| Kustomization | flux-system | router-events | Ready | main@5c09168 | 2026-09-16T13:52:25Z |  |
| Kustomization | flux-system | sandbox-launch | Ready | main@5c09168 | 2026-09-16T13:50:18Z |  |
| Kustomization | flux-system | sandbox-live | Ready | sandbox/launch@4830a6e | 2026-09-16T13:59:23Z |  |
| Kustomization | flux-system | scheduling | Ready | main@5c09168 | 2026-09-16T13:50:45Z |  |
| Kustomization | flux-system | science | Ready | main@5c09168 | 2026-09-16T13:52:12Z |  |
| Kustomization | flux-system | searxng | Ready | main@5c09168 | 2026-09-16T13:49:56Z |  |
| Kustomization | flux-system | secret-store | Ready | main@5c09168 | 2026-09-16T13:50:51Z |  |
| Kustomization | flux-system | spire | Ready | main@5c09168 | 2026-09-16T13:50:49Z |  |
| Kustomization | flux-system | staging | Ready | main@5c09168 | 2026-09-16T14:00:06Z |  |
| Kustomization | flux-system | tailscale | Ready | main@5c09168 | 2026-09-16T13:53:21Z |  |
| Kustomization | flux-system | temporal | Ready | main@5c09168 | 2026-09-16T13:52:01Z |  |
| Kustomization | flux-system | trivy | Ready | main@5c09168 | 2026-09-16T13:59:44Z |  |
| Kustomization | flux-system | weave-gitops | Ready | main@5c09168 | 2026-09-16T13:53:16Z |  |
