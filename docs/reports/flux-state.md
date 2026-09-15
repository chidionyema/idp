# Flux: what is applied

Read from the cluster receipt taken at 2026-09-15T20:00:18Z. Every Kustomization and HelmRelease, with the revision Flux last applied. **Suspended** is a switch somebody turned off on purpose (temporal, commerce, commerce-data, event-bus), not a defect; **Unknown** is a row Flux has never graded.

**119 objects: 109 ready, 9 not ready, 0 unknown, 1 suspended.**

## Not ready right now

- **HelmRelease commerce/lago** since 2026-09-15T19:50:07Z: Helm install failed for release commerce/lago with chart lago@1.28.0: create: failed to create: admission webhook "oke-resource-leak-protection.oke.com" denied the request: OKE resource leak protection rejected the request. Cluster has 2649 secrets and the limit is 2000. See https://docs.oracle.com/iaas/Content/ContEng/Tasks/contengprotectingclustersfromresourceleaks.htm for details.
- **Kustomization flux-system/commerce** since 2026-09-15T19:50:01Z: Reconciliation in progress
- **Kustomization flux-system/crossplane-storage-capability** since 2026-09-15T19:56:57Z: Composition/xobjectstoragebuckets.storage.estate.io dry-run failed: failed to create typed patch object (/xobjectstoragebuckets.storage.estate.io; apiextensions.crossplane.io/v1, Kind=Composition): .spec.resources: field not declared in schema 
- **Kustomization flux-system/epistemic-fabric** since 2026-09-15T19:56:01Z: ExternalSecret/epistemic-fabric/epistemic-fabric-github-api dry-run failed: admission webhook "validate.kyverno.svc-fail" denied the request:   resource ExternalSecret/epistemic-fabric/epistemic-fabric-github-api was blocked due to the following policies   require-auto-reload:   a-timer-minted-secret-says-what-reloader-does-with-it: 'ExternalSecret epistemic-fabric-github-api is re-minted every 10m and says nothing about Reloader, which rolls every workload that mounts it on every mint (Cyrus, 2026-09-08, revision 654). Either put reloader.stakater.com/ignore: "true" under spec.target.template.metadata.annotations because the consumer reads the file per call, or write a sentence under metadata.annotations.idp.platform/reload-on-mint because it reads at boot.'  
- **Kustomization flux-system/hermes-agent** since 2026-09-15T19:56:24Z: ExternalSecret/hermes-agent/hermes-agent-a2a dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-secrets.io": failed to call webhook: Post "https://external-secrets-webhook.external-secrets.svc:443/validate-external-secrets-io-v1-externalsecret?timeout=15s": context deadline exceeded 
- **Kustomization flux-system/human-vault** since 2026-09-15T19:55:54Z: ClusterSecretStore/human-vault dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.clustersecretstore.external-secrets.io": failed to call webhook: Post "https://external-secrets-webhook.external-secrets.svc:443/validate-external-secrets-io-v1-clustersecretstore?timeout=15s": context deadline exceeded 
- **Kustomization flux-system/human-vault-bridge** since 2026-09-15T19:54:38Z: dependency 'flux-system/human-vault' is not ready
- **Kustomization flux-system/temporal** since 2026-09-15T19:56:52Z: ExternalSecret/temporal/temporal-db dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-secrets.io": failed to call webhook: Post "https://external-secrets-webhook.external-secrets.svc:443/validate-external-secrets-io-v1-externalsecret?timeout=15s": context deadline exceeded 
- **Kustomization flux-system/via-negativa** since 2026-09-15T19:56:40Z: health check failed after 169.347854ms: failed early due to stalled resources: [Deployment/via-negativa/via-negativa-rca status: 'Failed']

## Every row

| Kind | Namespace | Name | State | Applied revision | Since | Message |
|---|---|---|---|---|---|---|
| HelmRelease | commerce | lago | Not ready | 1.28.0 | 2026-09-15T19:50:07Z | Helm install failed for release commerce/lago with chart lago@1.28.0: create: failed to create: admission webhook "oke-resource-leak-protection.oke.com" denied  |
| Kustomization | flux-system | commerce | Not ready | main@abea14d | 2026-09-15T19:50:01Z | Reconciliation in progress |
| Kustomization | flux-system | crossplane-storage-capability | Not ready | main@25cf923 | 2026-09-15T19:56:57Z | Composition/xobjectstoragebuckets.storage.estate.io dry-run failed: failed to create typed patch object (/xobjectstoragebuckets.storage.estate.io; apiextensions |
| Kustomization | flux-system | epistemic-fabric | Not ready | main@25cf923 | 2026-09-15T19:56:01Z | ExternalSecret/epistemic-fabric/epistemic-fabric-github-api dry-run failed: admission webhook "validate.kyverno.svc-fail" denied the request:   resource Externa |
| Kustomization | flux-system | hermes-agent | Not ready | main@f4e4621 | 2026-09-15T19:56:24Z | ExternalSecret/hermes-agent/hermes-agent-a2a dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-s |
| Kustomization | flux-system | human-vault | Not ready | main@f4e4621 | 2026-09-15T19:55:54Z | ClusterSecretStore/human-vault dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.clustersecretstore.external-secrets.io" |
| Kustomization | flux-system | human-vault-bridge | Not ready | main@f4e4621 | 2026-09-15T19:54:38Z | dependency 'flux-system/human-vault' is not ready |
| Kustomization | flux-system | temporal | Not ready | main@f4e4621 | 2026-09-15T19:56:52Z | ExternalSecret/temporal/temporal-db dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-secrets.io |
| Kustomization | flux-system | via-negativa | Not ready | main@25cf923 | 2026-09-15T19:56:40Z | health check failed after 169.347854ms: failed early due to stalled resources: [Deployment/via-negativa/via-negativa-rca status: 'Failed'] |
| HelmRelease | tigera-operator | tigera-operator | Suspended | v3.32.2 | 2026-09-06T19:38:02Z |  |
| HelmRelease | cert-manager | cert-manager | Ready | v1.21.1 | 2026-09-08T11:56:22Z |  |
| HelmRelease | chaos-mesh | chaos-mesh | Ready | 2.8.4 | 2026-09-15T14:48:03Z |  |
| HelmRelease | crossplane-system | crossplane | Ready | 2.4.0 | 2026-09-08T07:05:25Z |  |
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
| Kustomization | flux-system | agent-workforce | Ready | main@25cf923 | 2026-09-15T19:56:48Z |  |
| Kustomization | flux-system | alerts | Ready | main@25cf923 | 2026-09-15T19:55:46Z |  |
| Kustomization | flux-system | alerts-github | Ready | main@25cf923 | 2026-09-15T19:55:41Z |  |
| Kustomization | flux-system | alerts-secret | Ready | main@25cf923 | 2026-09-15T19:55:45Z |  |
| Kustomization | flux-system | autoscaler | Ready | main@25cf923 | 2026-09-15T19:55:42Z |  |
| Kustomization | flux-system | backstage | Ready | main@25cf923 | 2026-09-15T19:56:42Z |  |
| Kustomization | flux-system | backstage-namespace | Ready | main@25cf923 | 2026-09-15T19:54:22Z |  |
| Kustomization | flux-system | calico | Ready | main@25cf923 | 2026-09-15T19:54:16Z |  |
| Kustomization | flux-system | chaos | Ready | main@25cf923 | 2026-09-15T19:57:10Z |  |
| Kustomization | flux-system | chaos-mesh | Ready | main@25cf923 | 2026-09-15T19:55:30Z |  |
| Kustomization | flux-system | cluster-state | Ready | main@25cf923 | 2026-09-15T19:55:13Z |  |
| Kustomization | flux-system | commerce-data | Ready | main@25cf923 | 2026-09-15T19:56:07Z |  |
| Kustomization | flux-system | concierge | Ready | main@25cf923 | 2026-09-15T19:55:46Z |  |
| Kustomization | flux-system | cross-node-drill | Ready | main@25cf923 | 2026-09-15T19:54:26Z |  |
| Kustomization | flux-system | crossplane | Ready | main@25cf923 | 2026-09-15T19:55:39Z |  |
| Kustomization | flux-system | crossplane-providerconfig | Ready | main@25cf923 | 2026-09-15T19:56:27Z |  |
| Kustomization | flux-system | crossplane-providers | Ready | main@25cf923 | 2026-09-15T19:56:25Z |  |
| Kustomization | flux-system | dagster | Ready | main@25cf923 | 2026-09-15T19:56:34Z |  |
| Kustomization | flux-system | dns | Ready | main@25cf923 | 2026-09-15T19:56:31Z |  |
| Kustomization | flux-system | drills | Ready | main@25cf923 | 2026-09-15T19:55:55Z |  |
| Kustomization | flux-system | edge | Ready | main@25cf923 | 2026-09-15T19:54:39Z |  |
| Kustomization | flux-system | estate-catalog | Ready | latest@sha256:c081573de56f907d90b587cce5 | 2026-09-15T19:59:49Z |  |
| Kustomization | flux-system | estate-db | Ready | main@25cf923 | 2026-09-15T19:55:44Z |  |
| Kustomization | flux-system | estate-db-migrate | Ready | main@25cf923 | 2026-09-15T19:56:07Z |  |
| Kustomization | flux-system | estate-db-operator | Ready | main@25cf923 | 2026-09-15T19:54:27Z |  |
| Kustomization | flux-system | event-bus | Ready | main@25cf923 | 2026-09-15T19:54:20Z |  |
| Kustomization | flux-system | external-secrets | Ready | main@25cf923 | 2026-09-15T19:54:59Z |  |
| Kustomization | flux-system | feature-register | Ready | main@25cf923 | 2026-09-15T19:54:52Z |  |
| Kustomization | flux-system | flux-system | Ready | main@25cf923 | 2026-09-15T19:54:23Z |  |
| Kustomization | flux-system | flux-webhook | Ready | main@25cf923 | 2026-09-15T19:56:31Z |  |
| Kustomization | flux-system | gateway-api-crds | Ready | v1.5.1@e7677b7 | 2026-09-15T19:54:20Z |  |
| Kustomization | flux-system | guacamole | Ready | main@25cf923 | 2026-09-15T19:56:36Z |  |
| Kustomization | flux-system | gvisor-runtime | Ready | main@25cf923 | 2026-09-15T19:56:28Z |  |
| Kustomization | flux-system | healing | Ready | main@25cf923 | 2026-09-15T19:55:29Z |  |
| Kustomization | flux-system | healing-analyzer | Ready | main@25cf923 | 2026-09-15T19:57:19Z |  |
| Kustomization | flux-system | healing-k8sgpt | Ready | main@25cf923 | 2026-09-15T19:56:54Z |  |
| Kustomization | flux-system | healthchecks | Ready | main@25cf923 | 2026-09-15T19:56:41Z |  |
| Kustomization | flux-system | hindsight | Ready | main@25cf923 | 2026-09-15T19:56:49Z |  |
| Kustomization | flux-system | identity | Ready | main@25cf923 | 2026-09-15T19:56:00Z |  |
| Kustomization | flux-system | image-automation | Ready | main@25cf923 | 2026-09-15T19:55:43Z |  |
| Kustomization | flux-system | jit | Ready | main@25cf923 | 2026-09-15T19:54:37Z |  |
| Kustomization | flux-system | keda | Ready | main@25cf923 | 2026-09-15T19:55:28Z |  |
| Kustomization | flux-system | kyverno | Ready | main@25cf923 | 2026-09-15T19:54:26Z |  |
| Kustomization | flux-system | llm | Ready | main@25cf923 | 2026-09-15T19:56:35Z |  |
| Kustomization | flux-system | mcp | Ready | main@25cf923 | 2026-09-15T19:56:22Z |  |
| Kustomization | flux-system | metrics-server | Ready | main@25cf923 | 2026-09-15T19:55:23Z |  |
| Kustomization | flux-system | monitoring | Ready | main@25cf923 | 2026-09-15T19:55:39Z |  |
| Kustomization | flux-system | monitoring-rules | Ready | main@25cf923 | 2026-09-15T19:55:42Z |  |
| Kustomization | flux-system | nodesoftware-operator | Ready | main@25cf923 | 2026-09-15T19:55:59Z |  |
| Kustomization | flux-system | notify | Ready | main@25cf923 | 2026-09-15T19:56:03Z |  |
| Kustomization | flux-system | ns-fences | Ready | main@25cf923 | 2026-09-15T19:54:57Z |  |
| Kustomization | flux-system | observability | Ready | main@25cf923 | 2026-09-15T19:56:38Z |  |
| Kustomization | flux-system | observability-collector | Ready | main@25cf923 | 2026-09-15T19:55:31Z |  |
| Kustomization | flux-system | otto-gateway | Ready | main@25cf923 | 2026-09-15T19:56:05Z |  |
| Kustomization | flux-system | otto-golden | Ready | main@25cf923 | 2026-09-15T19:56:27Z |  |
| Kustomization | flux-system | otto-golden-secret | Ready | main@25cf923 | 2026-09-15T19:55:57Z |  |
| Kustomization | flux-system | priority-classes | Ready | main@25cf923 | 2026-09-15T19:54:17Z |  |
| Kustomization | flux-system | prospector | Ready | main@7453d76 | 2026-09-15T19:52:52Z |  |
| Kustomization | flux-system | prospector-platform | Ready | main@25cf923 | 2026-09-15T19:55:10Z |  |
| Kustomization | flux-system | rbac | Ready | main@25cf923 | 2026-09-15T19:54:51Z |  |
| Kustomization | flux-system | rbac-floor | Ready | main@25cf923 | 2026-09-15T19:54:22Z |  |
| Kustomization | flux-system | rbac-identity | Ready | main@25cf923 | 2026-09-15T19:54:24Z |  |
| Kustomization | flux-system | reloader | Ready | main@25cf923 | 2026-09-15T19:56:23Z |  |
| Kustomization | flux-system | research-engine | Ready | main@25cf923 | 2026-09-15T19:56:46Z |  |
| Kustomization | flux-system | robusta | Ready | main@25cf923 | 2026-09-15T19:55:57Z |  |
| Kustomization | flux-system | router-events | Ready | main@25cf923 | 2026-09-15T19:56:44Z |  |
| Kustomization | flux-system | sandbox-launch | Ready | main@25cf923 | 2026-09-15T19:55:09Z |  |
| Kustomization | flux-system | sandbox-live | Ready | sandbox/launch@4830a6e | 2026-09-15T20:00:11Z |  |
| Kustomization | flux-system | scheduling | Ready | main@25cf923 | 2026-09-15T19:55:09Z |  |
| Kustomization | flux-system | science | Ready | main@25cf923 | 2026-09-15T19:56:45Z |  |
| Kustomization | flux-system | searxng | Ready | main@25cf923 | 2026-09-15T19:54:24Z |  |
| Kustomization | flux-system | secret-store | Ready | main@25cf923 | 2026-09-15T19:55:31Z |  |
| Kustomization | flux-system | spire | Ready | main@25cf923 | 2026-09-15T19:55:30Z |  |
| Kustomization | flux-system | staging | Ready | main@25cf923 | 2026-09-15T19:54:28Z |  |
| Kustomization | flux-system | tailscale | Ready | main@25cf923 | 2026-09-15T19:56:20Z |  |
| Kustomization | flux-system | trivy | Ready | main@25cf923 | 2026-09-15T19:54:16Z |  |
| Kustomization | flux-system | verification | Ready | main@25cf923 | 2026-09-15T19:55:40Z |  |
| Kustomization | flux-system | weave-gitops | Ready | main@25cf923 | 2026-09-15T19:56:30Z |  |
