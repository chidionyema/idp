# Flux: what is applied

Read from the cluster receipt taken at 2026-09-15T19:45:17Z. Every Kustomization and HelmRelease, with the revision Flux last applied. **Suspended** is a switch somebody turned off on purpose (temporal, commerce, commerce-data, event-bus), not a defect; **Unknown** is a row Flux has never graded.

**119 objects: 93 ready, 25 not ready, 0 unknown, 1 suspended.**

## Not ready right now

- **HelmRelease commerce/lago** since 2026-09-15T19:30:33Z: Helm install failed for release commerce/lago with chart lago@1.28.0: create: failed to create: admission webhook "oke-resource-leak-protection.oke.com" denied the request: OKE resource leak protection rejected the request. Cluster has 2649 secrets and the limit is 2000. See https://docs.oracle.com/iaas/Content/ContEng/Tasks/contengprotectingclustersfromresourceleaks.htm for details.
- **Kustomization flux-system/agent-workforce** since 2026-09-15T19:39:51Z: dependency 'flux-system/llm' is not ready
- **Kustomization flux-system/alerts** since 2026-09-15T19:36:54Z: dependency 'flux-system/alerts-secret' is not ready
- **Kustomization flux-system/alerts-secret** since 2026-09-15T19:39:12Z: ExternalSecret/flux-system/flux-telegram dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-secrets.io": failed to call webhook: Post "https://external-secrets-webhook.external-secrets.svc:443/validate-external-secrets-io-v1-externalsecret?timeout=15s": context deadline exceeded 
- **Kustomization flux-system/backstage** since 2026-09-15T19:39:00Z: dependency 'flux-system/estate-db-migrate' is not ready
- **Kustomization flux-system/chaos** since 2026-09-15T19:39:00Z: dependency 'flux-system/observability' is not ready
- **Kustomization flux-system/commerce** since 2026-09-15T19:30:29Z: Reconciliation in progress
- **Kustomization flux-system/commerce-data** since 2026-09-15T19:38:54Z: dependency 'flux-system/estate-db' is not ready
- **Kustomization flux-system/crossplane-storage-capability** since 2026-09-15T19:39:19Z: Composition/xobjectstoragebuckets.storage.estate.io dry-run failed: failed to create typed patch object (/xobjectstoragebuckets.storage.estate.io; apiextensions.crossplane.io/v1, Kind=Composition): .spec.resources: field not declared in schema 
- **Kustomization flux-system/dagster** since 2026-09-15T19:38:44Z: dependency 'flux-system/estate-db-migrate' is not ready
- **Kustomization flux-system/epistemic-fabric** since 2026-09-15T19:39:54Z: ExternalSecret/epistemic-fabric/epistemic-fabric-github-api dry-run failed: admission webhook "validate.kyverno.svc-fail" denied the request:   resource ExternalSecret/epistemic-fabric/epistemic-fabric-github-api was blocked due to the following policies   require-auto-reload:   a-timer-minted-secret-says-what-reloader-does-with-it: 'ExternalSecret epistemic-fabric-github-api is re-minted every 10m and says nothing about Reloader, which rolls every workload that mounts it on every mint (Cyrus, 2026-09-08, revision 654). Either put reloader.stakater.com/ignore: "true" under spec.target.template.metadata.annotations because the consumer reads the file per call, or write a sentence under metadata.annotations.idp.platform/reload-on-mint because it reads at boot.'  
- **Kustomization flux-system/estate-db** since 2026-09-15T19:39:11Z: ExternalSecret/estate-db/estate-db-role-superset dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-secrets.io": failed to call webhook: Post "https://external-secrets-webhook.external-secrets.svc:443/validate-external-secrets-io-v1-externalsecret?timeout=15s": context deadline exceeded 
- **Kustomization flux-system/estate-db-migrate** since 2026-09-15T19:38:07Z: dependency 'flux-system/estate-db' is not ready
- **Kustomization flux-system/guacamole** since 2026-09-15T19:39:23Z: dependency 'flux-system/estate-db-migrate' is not ready
- **Kustomization flux-system/healing-analyzer** since 2026-09-15T19:37:49Z: dependency 'flux-system/healing-k8sgpt' is not ready
- **Kustomization flux-system/healing-k8sgpt** since 2026-09-15T19:38:43Z: dependency 'flux-system/llm' is not ready
- **Kustomization flux-system/healthchecks** since 2026-09-15T19:39:19Z: dependency 'flux-system/estate-db-migrate' is not ready
- **Kustomization flux-system/hindsight** since 2026-09-15T19:38:43Z: dependency 'flux-system/llm' is not ready
- **Kustomization flux-system/llm** since 2026-09-15T19:38:54Z: dependency 'flux-system/estate-db-migrate' is not ready
- **Kustomization flux-system/observability** since 2026-09-15T19:38:44Z: dependency 'flux-system/estate-db-migrate' is not ready
- **Kustomization flux-system/research-engine** since 2026-09-15T19:38:42Z: dependency 'flux-system/llm' is not ready
- **Kustomization flux-system/router-events** since 2026-09-15T19:36:51Z: dependency 'flux-system/llm' is not ready
- **Kustomization flux-system/science** since 2026-09-15T19:38:43Z: dependency 'flux-system/observability' is not ready
- **Kustomization flux-system/temporal** since 2026-09-15T19:39:24Z: dependency 'flux-system/estate-db-migrate' is not ready
- **Kustomization flux-system/via-negativa** since 2026-09-15T19:38:42Z: dependency 'flux-system/llm' is not ready

## Every row

| Kind | Namespace | Name | State | Applied revision | Since | Message |
|---|---|---|---|---|---|---|
| HelmRelease | commerce | lago | Not ready | 1.28.0 | 2026-09-15T19:30:33Z | Helm install failed for release commerce/lago with chart lago@1.28.0: create: failed to create: admission webhook "oke-resource-leak-protection.oke.com" denied  |
| Kustomization | flux-system | agent-workforce | Not ready | main@3b8ede3 | 2026-09-15T19:39:51Z | dependency 'flux-system/llm' is not ready |
| Kustomization | flux-system | alerts | Not ready | main@3b8ede3 | 2026-09-15T19:36:54Z | dependency 'flux-system/alerts-secret' is not ready |
| Kustomization | flux-system | alerts-secret | Not ready | main@3b8ede3 | 2026-09-15T19:39:12Z | ExternalSecret/flux-system/flux-telegram dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-secre |
| Kustomization | flux-system | backstage | Not ready | main@3b8ede3 | 2026-09-15T19:39:00Z | dependency 'flux-system/estate-db-migrate' is not ready |
| Kustomization | flux-system | chaos | Not ready | main@3b8ede3 | 2026-09-15T19:39:00Z | dependency 'flux-system/observability' is not ready |
| Kustomization | flux-system | commerce | Not ready | main@abea14d | 2026-09-15T19:30:29Z | Reconciliation in progress |
| Kustomization | flux-system | commerce-data | Not ready | main@3b8ede3 | 2026-09-15T19:38:54Z | dependency 'flux-system/estate-db' is not ready |
| Kustomization | flux-system | crossplane-storage-capability | Not ready | main@f4e4621 | 2026-09-15T19:39:19Z | Composition/xobjectstoragebuckets.storage.estate.io dry-run failed: failed to create typed patch object (/xobjectstoragebuckets.storage.estate.io; apiextensions |
| Kustomization | flux-system | dagster | Not ready | main@3b8ede3 | 2026-09-15T19:38:44Z | dependency 'flux-system/estate-db-migrate' is not ready |
| Kustomization | flux-system | epistemic-fabric | Not ready | main@f4e4621 | 2026-09-15T19:39:54Z | ExternalSecret/epistemic-fabric/epistemic-fabric-github-api dry-run failed: admission webhook "validate.kyverno.svc-fail" denied the request:   resource Externa |
| Kustomization | flux-system | estate-db | Not ready | main@3b8ede3 | 2026-09-15T19:39:11Z | ExternalSecret/estate-db/estate-db-role-superset dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.extern |
| Kustomization | flux-system | estate-db-migrate | Not ready | main@3b8ede3 | 2026-09-15T19:38:07Z | dependency 'flux-system/estate-db' is not ready |
| Kustomization | flux-system | guacamole | Not ready | main@3b8ede3 | 2026-09-15T19:39:23Z | dependency 'flux-system/estate-db-migrate' is not ready |
| Kustomization | flux-system | healing-analyzer | Not ready | main@3b8ede3 | 2026-09-15T19:37:49Z | dependency 'flux-system/healing-k8sgpt' is not ready |
| Kustomization | flux-system | healing-k8sgpt | Not ready | main@3b8ede3 | 2026-09-15T19:38:43Z | dependency 'flux-system/llm' is not ready |
| Kustomization | flux-system | healthchecks | Not ready | main@3b8ede3 | 2026-09-15T19:39:19Z | dependency 'flux-system/estate-db-migrate' is not ready |
| Kustomization | flux-system | hindsight | Not ready | main@3b8ede3 | 2026-09-15T19:38:43Z | dependency 'flux-system/llm' is not ready |
| Kustomization | flux-system | llm | Not ready | main@3b8ede3 | 2026-09-15T19:38:54Z | dependency 'flux-system/estate-db-migrate' is not ready |
| Kustomization | flux-system | observability | Not ready | main@3b8ede3 | 2026-09-15T19:38:44Z | dependency 'flux-system/estate-db-migrate' is not ready |
| Kustomization | flux-system | research-engine | Not ready | main@3b8ede3 | 2026-09-15T19:38:42Z | dependency 'flux-system/llm' is not ready |
| Kustomization | flux-system | router-events | Not ready | main@3b8ede3 | 2026-09-15T19:36:51Z | dependency 'flux-system/llm' is not ready |
| Kustomization | flux-system | science | Not ready | main@3b8ede3 | 2026-09-15T19:38:43Z | dependency 'flux-system/observability' is not ready |
| Kustomization | flux-system | temporal | Not ready | main@3b8ede3 | 2026-09-15T19:39:24Z | dependency 'flux-system/estate-db-migrate' is not ready |
| Kustomization | flux-system | via-negativa | Not ready | main@3b8ede3 | 2026-09-15T19:38:42Z | dependency 'flux-system/llm' is not ready |
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
| Kustomization | flux-system | alerts-github | Ready | main@f4e4621 | 2026-09-15T19:39:23Z |  |
| Kustomization | flux-system | autoscaler | Ready | main@f4e4621 | 2026-09-15T19:38:44Z |  |
| Kustomization | flux-system | backstage-namespace | Ready | main@f4e4621 | 2026-09-15T19:38:03Z |  |
| Kustomization | flux-system | calico | Ready | main@f4e4621 | 2026-09-15T19:37:57Z |  |
| Kustomization | flux-system | chaos-mesh | Ready | main@f4e4621 | 2026-09-15T19:38:36Z |  |
| Kustomization | flux-system | cluster-state | Ready | main@f4e4621 | 2026-09-15T19:38:43Z |  |
| Kustomization | flux-system | concierge | Ready | main@f4e4621 | 2026-09-15T19:39:13Z |  |
| Kustomization | flux-system | cross-node-drill | Ready | main@f4e4621 | 2026-09-15T19:38:02Z |  |
| Kustomization | flux-system | crossplane | Ready | main@f4e4621 | 2026-09-15T19:38:39Z |  |
| Kustomization | flux-system | crossplane-providerconfig | Ready | main@f4e4621 | 2026-09-15T19:39:18Z |  |
| Kustomization | flux-system | crossplane-providers | Ready | main@f4e4621 | 2026-09-15T19:39:07Z |  |
| Kustomization | flux-system | dns | Ready | main@f4e4621 | 2026-09-15T19:38:58Z |  |
| Kustomization | flux-system | drills | Ready | main@f4e4621 | 2026-09-15T19:39:43Z |  |
| Kustomization | flux-system | edge | Ready | main@f4e4621 | 2026-09-15T19:38:09Z |  |
| Kustomization | flux-system | estate-catalog | Ready | latest@sha256:c081573de56f907d90b587cce5 | 2026-09-15T19:39:04Z |  |
| Kustomization | flux-system | estate-db-operator | Ready | main@f4e4621 | 2026-09-15T19:38:04Z |  |
| Kustomization | flux-system | event-bus | Ready | main@f4e4621 | 2026-09-15T19:38:02Z |  |
| Kustomization | flux-system | external-secrets | Ready | main@f4e4621 | 2026-09-15T19:38:36Z |  |
| Kustomization | flux-system | feature-register | Ready | main@f4e4621 | 2026-09-15T19:38:21Z |  |
| Kustomization | flux-system | flux-system | Ready | main@f4e4621 | 2026-09-15T19:37:59Z |  |
| Kustomization | flux-system | flux-webhook | Ready | main@f4e4621 | 2026-09-15T19:38:55Z |  |
| Kustomization | flux-system | gateway-api-crds | Ready | v1.5.1@e7677b7 | 2026-09-15T19:37:54Z |  |
| Kustomization | flux-system | gvisor-runtime | Ready | main@f4e4621 | 2026-09-15T19:39:49Z |  |
| Kustomization | flux-system | healing | Ready | main@f4e4621 | 2026-09-15T19:38:41Z |  |
| Kustomization | flux-system | hermes-agent | Ready | main@f4e4621 | 2026-09-15T19:40:42Z |  |
| Kustomization | flux-system | human-vault | Ready | main@f4e4621 | 2026-09-15T19:38:53Z |  |
| Kustomization | flux-system | human-vault-bridge | Ready | main@f4e4621 | 2026-09-15T19:39:37Z |  |
| Kustomization | flux-system | identity | Ready | main@f4e4621 | 2026-09-15T19:39:17Z |  |
| Kustomization | flux-system | image-automation | Ready | main@f4e4621 | 2026-09-15T19:39:00Z |  |
| Kustomization | flux-system | jit | Ready | main@f4e4621 | 2026-09-15T19:38:04Z |  |
| Kustomization | flux-system | keda | Ready | main@f4e4621 | 2026-09-15T19:38:36Z |  |
| Kustomization | flux-system | kyverno | Ready | main@f4e4621 | 2026-09-15T19:37:59Z |  |
| Kustomization | flux-system | mcp | Ready | main@f4e4621 | 2026-09-15T19:39:59Z |  |
| Kustomization | flux-system | metrics-server | Ready | main@f4e4621 | 2026-09-15T19:38:33Z |  |
| Kustomization | flux-system | monitoring | Ready | main@f4e4621 | 2026-09-15T19:38:53Z |  |
| Kustomization | flux-system | monitoring-rules | Ready | main@f4e4621 | 2026-09-15T19:39:22Z |  |
| Kustomization | flux-system | nodesoftware-operator | Ready | main@f4e4621 | 2026-09-15T19:39:21Z |  |
| Kustomization | flux-system | notify | Ready | main@f4e4621 | 2026-09-15T19:39:15Z |  |
| Kustomization | flux-system | ns-fences | Ready | main@f4e4621 | 2026-09-15T19:38:18Z |  |
| Kustomization | flux-system | observability-collector | Ready | main@f4e4621 | 2026-09-15T19:38:38Z |  |
| Kustomization | flux-system | otto-gateway | Ready | main@f4e4621 | 2026-09-15T19:39:29Z |  |
| Kustomization | flux-system | otto-golden | Ready | main@f4e4621 | 2026-09-15T19:39:23Z |  |
| Kustomization | flux-system | otto-golden-secret | Ready | main@f4e4621 | 2026-09-15T19:39:13Z |  |
| Kustomization | flux-system | priority-classes | Ready | main@f4e4621 | 2026-09-15T19:37:56Z |  |
| Kustomization | flux-system | prospector | Ready | main@7453d76 | 2026-09-15T19:43:05Z |  |
| Kustomization | flux-system | prospector-platform | Ready | main@f4e4621 | 2026-09-15T19:38:53Z |  |
| Kustomization | flux-system | rbac | Ready | main@f4e4621 | 2026-09-15T19:38:05Z |  |
| Kustomization | flux-system | rbac-floor | Ready | main@f4e4621 | 2026-09-15T19:37:53Z |  |
| Kustomization | flux-system | rbac-identity | Ready | main@f4e4621 | 2026-09-15T19:37:55Z |  |
| Kustomization | flux-system | reloader | Ready | main@f4e4621 | 2026-09-15T19:38:56Z |  |
| Kustomization | flux-system | robusta | Ready | main@f4e4621 | 2026-09-15T19:39:15Z |  |
| Kustomization | flux-system | sandbox-launch | Ready | main@f4e4621 | 2026-09-15T19:38:40Z |  |
| Kustomization | flux-system | sandbox-live | Ready | sandbox/launch@4830a6e | 2026-09-15T19:44:22Z |  |
| Kustomization | flux-system | scheduling | Ready | main@f4e4621 | 2026-09-15T19:38:30Z |  |
| Kustomization | flux-system | searxng | Ready | main@f4e4621 | 2026-09-15T19:37:58Z |  |
| Kustomization | flux-system | secret-store | Ready | main@f4e4621 | 2026-09-15T19:38:41Z |  |
| Kustomization | flux-system | spire | Ready | main@f4e4621 | 2026-09-15T19:38:38Z |  |
| Kustomization | flux-system | staging | Ready | main@f4e4621 | 2026-09-15T19:37:59Z |  |
| Kustomization | flux-system | tailscale | Ready | main@f4e4621 | 2026-09-15T19:38:57Z |  |
| Kustomization | flux-system | trivy | Ready | main@f4e4621 | 2026-09-15T19:37:53Z |  |
| Kustomization | flux-system | verification | Ready | main@f4e4621 | 2026-09-15T19:38:44Z |  |
| Kustomization | flux-system | weave-gitops | Ready | main@f4e4621 | 2026-09-15T19:39:43Z |  |
