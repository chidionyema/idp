# Flux: what is applied

Read from the cluster receipt taken at 2026-09-16T18:00:19Z. Every Kustomization and HelmRelease, with the revision Flux last applied. **Suspended** is a switch somebody turned off on purpose (temporal, commerce, commerce-data, event-bus), not a defect; **Unknown** is a row Flux has never graded.

**120 objects: 62 ready, 57 not ready, 0 unknown, 1 suspended.**

## Not ready right now

- **HelmRelease commerce/lago** since 2026-09-16T17:52:52Z: Helm install failed for release commerce/lago with chart lago@1.28.0: create: failed to create: admission webhook "oke-resource-leak-protection.oke.com" denied the request: OKE resource leak protection rejected the request. Cluster has 2650 secrets and the limit is 2000. See https://docs.oracle.com/iaas/Content/ContEng/Tasks/contengprotectingclustersfromresourceleaks.htm for details.
- **HelmRelease crossplane-system/crossplane** since 2026-09-16T17:08:05Z: Helm upgrade failed for release crossplane-system/crossplane with chart crossplane@1.15.1: create: failed to create: admission webhook "oke-resource-leak-protection.oke.com" denied the request: OKE resource leak protection rejected the request. Cluster has 2650 secrets and the limit is 2000. See https://docs.oracle.com/iaas/Content/ContEng/Tasks/contengprotectingclustersfromresourceleaks.htm for details.
- **Kustomization flux-system/agent-workforce** since 2026-09-16T17:59:53Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/alerts** since 2026-09-16T17:59:19Z: dependency 'flux-system/alerts-secret' is not ready
- **Kustomization flux-system/alerts-github** since 2026-09-16T17:59:18Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/alerts-secret** since 2026-09-16T17:59:19Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/autoscaler** since 2026-09-16T17:59:18Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/backstage** since 2026-09-16T17:59:53Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/chaos** since 2026-09-16T17:59:53Z: dependency 'flux-system/observability' is not ready
- **Kustomization flux-system/cluster-state** since 2026-09-16T17:59:52Z: Reconciliation in progress
- **Kustomization flux-system/commerce** since 2026-09-16T17:52:45Z: Reconciliation in progress
- **Kustomization flux-system/commerce-data** since 2026-09-16T17:59:52Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/concierge** since 2026-09-16T17:59:18Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/crossplane** since 2026-09-16T17:59:49Z: health check failed after 60.871428ms: failed early due to stalled resources: [HelmRelease/crossplane-system/crossplane status: 'Failed']
- **Kustomization flux-system/crossplane-providerconfig** since 2026-09-16T11:53:07Z: dependency 'flux-system/crossplane-providers' is not ready
- **Kustomization flux-system/crossplane-providers** since 2026-09-16T11:53:06Z: dependency 'flux-system/crossplane' is not ready
- **Kustomization flux-system/crossplane-storage-capability** since 2026-09-16T11:53:07Z: dependency 'flux-system/crossplane-providerconfig' is not ready
- **Kustomization flux-system/dagster** since 2026-09-16T17:59:53Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/dns** since 2026-09-16T17:59:19Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/drills** since 2026-09-16T17:59:19Z: dependency 'flux-system/alerts-github' is not ready
- **Kustomization flux-system/epistemic-fabric** since 2026-09-16T17:59:19Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/estate-db** since 2026-09-16T17:59:17Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/estate-db-migrate** since 2026-09-16T17:59:18Z: dependency 'flux-system/estate-db' is not ready
- **Kustomization flux-system/flux-webhook** since 2026-09-16T17:59:18Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/guacamole** since 2026-09-16T17:52:55Z: dependency 'flux-system/identity' is not ready
- **Kustomization flux-system/gvisor-runtime** since 2026-09-16T17:59:17Z: dependency 'flux-system/nodesoftware-operator' is not ready
- **Kustomization flux-system/healing-analyzer** since 2026-09-16T17:59:19Z: dependency 'flux-system/healing-k8sgpt' is not ready
- **Kustomization flux-system/healing-k8sgpt** since 2026-09-16T17:59:53Z: dependency 'flux-system/llm' is not ready
- **Kustomization flux-system/healthchecks** since 2026-09-16T17:52:51Z: dependency 'flux-system/identity' is not ready
- **Kustomization flux-system/hermes-agent** since 2026-09-16T17:59:52Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/hindsight** since 2026-09-16T17:59:19Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/human-vault** since 2026-09-16T17:59:52Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/human-vault-bridge** since 2026-09-16T17:59:18Z: dependency 'flux-system/human-vault' is not ready
- **Kustomization flux-system/identity** since 2026-09-16T17:59:18Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/idp-agent** since 2026-09-16T17:59:52Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/image-automation** since 2026-09-16T17:59:18Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/llm** since 2026-09-16T17:59:19Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/mcp** since 2026-09-16T17:59:52Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/monitoring** since 2026-09-16T17:59:18Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/monitoring-rules** since 2026-09-16T17:59:19Z: dependency 'flux-system/monitoring' is not ready
- **Kustomization flux-system/nodesoftware-operator** since 2026-09-16T17:59:47Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/notify** since 2026-09-16T17:59:49Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/observability** since 2026-09-16T17:59:53Z: dependency 'flux-system/estate-db-migrate' is not ready
- **Kustomization flux-system/otto-gateway** since 2026-09-16T17:59:52Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/otto-golden** since 2026-09-16T17:59:52Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/otto-golden-secret** since 2026-09-16T17:59:18Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/reloader** since 2026-09-16T17:59:18Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/research-engine** since 2026-09-16T17:59:19Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/robusta** since 2026-09-16T17:59:18Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/router-events** since 2026-09-16T17:59:19Z: dependency 'flux-system/llm' is not ready
- **Kustomization flux-system/science** since 2026-09-16T17:59:19Z: dependency 'flux-system/observability' is not ready
- **Kustomization flux-system/secret-store** since 2026-09-16T17:59:44Z: dependency 'flux-system/external-secrets' is not ready
- **Kustomization flux-system/tailscale** since 2026-09-16T17:59:17Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/temporal** since 2026-09-16T17:59:19Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/verification** since 2026-09-16T17:59:53Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/via-negativa** since 2026-09-16T17:59:19Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/weave-gitops** since 2026-09-16T17:52:46Z: dependency 'flux-system/identity' is not ready

## Every row

| Kind | Namespace | Name | State | Applied revision | Since | Message |
|---|---|---|---|---|---|---|
| HelmRelease | commerce | lago | Not ready | 1.28.0 | 2026-09-16T17:52:52Z | Helm install failed for release commerce/lago with chart lago@1.28.0: create: failed to create: admission webhook "oke-resource-leak-protection.oke.com" denied  |
| HelmRelease | crossplane-system | crossplane | Not ready | 1.15.1 | 2026-09-16T17:08:05Z | Helm upgrade failed for release crossplane-system/crossplane with chart crossplane@1.15.1: create: failed to create: admission webhook "oke-resource-leak-protec |
| Kustomization | flux-system | agent-workforce | Not ready | main@ba72d0f | 2026-09-16T17:59:53Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | alerts | Not ready | main@ba72d0f | 2026-09-16T17:59:19Z | dependency 'flux-system/alerts-secret' is not ready |
| Kustomization | flux-system | alerts-github | Not ready | main@ba72d0f | 2026-09-16T17:59:18Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | alerts-secret | Not ready | main@ba72d0f | 2026-09-16T17:59:19Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | autoscaler | Not ready | main@ba72d0f | 2026-09-16T17:59:18Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | backstage | Not ready | main@ba72d0f | 2026-09-16T17:59:53Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | chaos | Not ready | main@ba72d0f | 2026-09-16T17:59:53Z | dependency 'flux-system/observability' is not ready |
| Kustomization | flux-system | cluster-state | Not ready | main@ba72d0f | 2026-09-16T17:59:52Z | Reconciliation in progress |
| Kustomization | flux-system | commerce | Not ready | main@abea14d | 2026-09-16T17:52:45Z | Reconciliation in progress |
| Kustomization | flux-system | commerce-data | Not ready | main@ba72d0f | 2026-09-16T17:59:52Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | concierge | Not ready | main@ba72d0f | 2026-09-16T17:59:18Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | crossplane | Not ready | main@8d685ec | 2026-09-16T17:59:49Z | health check failed after 60.871428ms: failed early due to stalled resources: [HelmRelease/crossplane-system/crossplane status: 'Failed'] |
| Kustomization | flux-system | crossplane-providerconfig | Not ready | main@8d685ec | 2026-09-16T11:53:07Z | dependency 'flux-system/crossplane-providers' is not ready |
| Kustomization | flux-system | crossplane-providers | Not ready | main@8d685ec | 2026-09-16T11:53:06Z | dependency 'flux-system/crossplane' is not ready |
| Kustomization | flux-system | crossplane-storage-capability | Not ready | main@8d685ec | 2026-09-16T11:53:07Z | dependency 'flux-system/crossplane-providerconfig' is not ready |
| Kustomization | flux-system | dagster | Not ready | main@ba72d0f | 2026-09-16T17:59:53Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | dns | Not ready | main@ba72d0f | 2026-09-16T17:59:19Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | drills | Not ready | main@ba72d0f | 2026-09-16T17:59:19Z | dependency 'flux-system/alerts-github' is not ready |
| Kustomization | flux-system | epistemic-fabric | Not ready | main@ba72d0f | 2026-09-16T17:59:19Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | estate-db | Not ready | main@ba72d0f | 2026-09-16T17:59:17Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | estate-db-migrate | Not ready | main@ba72d0f | 2026-09-16T17:59:18Z | dependency 'flux-system/estate-db' is not ready |
| Kustomization | flux-system | flux-webhook | Not ready | main@ba72d0f | 2026-09-16T17:59:18Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | guacamole | Not ready | main@581aedd | 2026-09-16T17:52:55Z | dependency 'flux-system/identity' is not ready |
| Kustomization | flux-system | gvisor-runtime | Not ready | main@ba72d0f | 2026-09-16T17:59:17Z | dependency 'flux-system/nodesoftware-operator' is not ready |
| Kustomization | flux-system | healing-analyzer | Not ready | main@ba72d0f | 2026-09-16T17:59:19Z | dependency 'flux-system/healing-k8sgpt' is not ready |
| Kustomization | flux-system | healing-k8sgpt | Not ready | main@ba72d0f | 2026-09-16T17:59:53Z | dependency 'flux-system/llm' is not ready |
| Kustomization | flux-system | healthchecks | Not ready | main@dd440cf | 2026-09-16T17:52:51Z | dependency 'flux-system/identity' is not ready |
| Kustomization | flux-system | hermes-agent | Not ready | main@ba72d0f | 2026-09-16T17:59:52Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | hindsight | Not ready | main@ba72d0f | 2026-09-16T17:59:19Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | human-vault | Not ready | main@ba72d0f | 2026-09-16T17:59:52Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | human-vault-bridge | Not ready | main@ba72d0f | 2026-09-16T17:59:18Z | dependency 'flux-system/human-vault' is not ready |
| Kustomization | flux-system | identity | Not ready | main@ba72d0f | 2026-09-16T17:59:18Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | idp-agent | Not ready | main@ba72d0f | 2026-09-16T17:59:52Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | image-automation | Not ready | main@ba72d0f | 2026-09-16T17:59:18Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | llm | Not ready | main@ba72d0f | 2026-09-16T17:59:19Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | mcp | Not ready | main@ba72d0f | 2026-09-16T17:59:52Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | monitoring | Not ready | main@ba72d0f | 2026-09-16T17:59:18Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | monitoring-rules | Not ready | main@ba72d0f | 2026-09-16T17:59:19Z | dependency 'flux-system/monitoring' is not ready |
| Kustomization | flux-system | nodesoftware-operator | Not ready | main@ba72d0f | 2026-09-16T17:59:47Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | notify | Not ready | main@ba72d0f | 2026-09-16T17:59:49Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | observability | Not ready | main@ba72d0f | 2026-09-16T17:59:53Z | dependency 'flux-system/estate-db-migrate' is not ready |
| Kustomization | flux-system | otto-gateway | Not ready | main@ba72d0f | 2026-09-16T17:59:52Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | otto-golden | Not ready | main@ba72d0f | 2026-09-16T17:59:52Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | otto-golden-secret | Not ready | main@ba72d0f | 2026-09-16T17:59:18Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | reloader | Not ready | main@ba72d0f | 2026-09-16T17:59:18Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | research-engine | Not ready | main@ba72d0f | 2026-09-16T17:59:19Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | robusta | Not ready | main@ba72d0f | 2026-09-16T17:59:18Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | router-events | Not ready | main@ba72d0f | 2026-09-16T17:59:19Z | dependency 'flux-system/llm' is not ready |
| Kustomization | flux-system | science | Not ready | main@ba72d0f | 2026-09-16T17:59:19Z | dependency 'flux-system/observability' is not ready |
| Kustomization | flux-system | secret-store | Not ready | main@ba72d0f | 2026-09-16T17:59:44Z | dependency 'flux-system/external-secrets' is not ready |
| Kustomization | flux-system | tailscale | Not ready | main@ba72d0f | 2026-09-16T17:59:17Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | temporal | Not ready | main@aae56f0 | 2026-09-16T17:59:19Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | verification | Not ready | main@ba72d0f | 2026-09-16T17:59:53Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | via-negativa | Not ready | main@ba72d0f | 2026-09-16T17:59:19Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | weave-gitops | Not ready | main@ba72d0f | 2026-09-16T17:52:46Z | dependency 'flux-system/identity' is not ready |
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
| Kustomization | flux-system | backstage-namespace | Ready | main@a7c073a | 2026-09-16T17:59:06Z |  |
| Kustomization | flux-system | calico | Ready | main@a7c073a | 2026-09-16T17:59:09Z |  |
| Kustomization | flux-system | chaos-mesh | Ready | main@a7c073a | 2026-09-16T17:59:47Z |  |
| Kustomization | flux-system | cross-node-drill | Ready | main@a7c073a | 2026-09-16T17:59:03Z |  |
| Kustomization | flux-system | edge | Ready | main@a7c073a | 2026-09-16T17:59:17Z |  |
| Kustomization | flux-system | estate-catalog | Ready | latest@sha256:779d68f6c22944615c802cd380 | 2026-09-16T17:52:30Z |  |
| Kustomization | flux-system | estate-db-operator | Ready | main@a7c073a | 2026-09-16T17:59:05Z |  |
| Kustomization | flux-system | event-bus | Ready | main@a7c073a | 2026-09-16T17:59:18Z |  |
| Kustomization | flux-system | external-secrets | Ready | main@a7c073a | 2026-09-16T17:59:47Z |  |
| Kustomization | flux-system | feature-register | Ready | main@a7c073a | 2026-09-16T17:59:15Z |  |
| Kustomization | flux-system | flux-system | Ready | main@a7c073a | 2026-09-16T17:59:14Z |  |
| Kustomization | flux-system | gateway-api-crds | Ready | v1.5.1@e7677b7 | 2026-09-16T17:59:01Z |  |
| Kustomization | flux-system | healing | Ready | main@a7c073a | 2026-09-16T17:59:51Z |  |
| Kustomization | flux-system | jit | Ready | main@a7c073a | 2026-09-16T17:59:35Z |  |
| Kustomization | flux-system | keda | Ready | main@a7c073a | 2026-09-16T17:59:52Z |  |
| Kustomization | flux-system | kyverno | Ready | main@a7c073a | 2026-09-16T17:59:00Z |  |
| Kustomization | flux-system | metrics-server | Ready | main@a7c073a | 2026-09-16T17:59:49Z |  |
| Kustomization | flux-system | ns-fences | Ready | main@a7c073a | 2026-09-16T17:59:19Z |  |
| Kustomization | flux-system | observability-collector | Ready | main@a7c073a | 2026-09-16T17:59:51Z |  |
| Kustomization | flux-system | priority-classes | Ready | main@a7c073a | 2026-09-16T17:59:11Z |  |
| Kustomization | flux-system | prospector | Ready | main@7453d76 | 2026-09-16T17:56:31Z |  |
| Kustomization | flux-system | prospector-platform | Ready | main@a7c073a | 2026-09-16T17:59:52Z |  |
| Kustomization | flux-system | rbac | Ready | main@a7c073a | 2026-09-16T17:59:17Z |  |
| Kustomization | flux-system | rbac-floor | Ready | main@a7c073a | 2026-09-16T17:59:04Z |  |
| Kustomization | flux-system | rbac-identity | Ready | main@a7c073a | 2026-09-16T17:59:07Z |  |
| Kustomization | flux-system | sandbox-launch | Ready | main@a7c073a | 2026-09-16T17:59:34Z |  |
| Kustomization | flux-system | sandbox-live | Ready | sandbox/launch@4830a6e | 2026-09-16T17:59:36Z |  |
| Kustomization | flux-system | scheduling | Ready | main@a7c073a | 2026-09-16T17:59:36Z |  |
| Kustomization | flux-system | searxng | Ready | main@a7c073a | 2026-09-16T17:59:08Z |  |
| Kustomization | flux-system | spire | Ready | main@a7c073a | 2026-09-16T17:59:49Z |  |
| Kustomization | flux-system | staging | Ready | main@a7c073a | 2026-09-16T17:59:02Z |  |
| Kustomization | flux-system | trivy | Ready | main@a7c073a | 2026-09-16T17:59:06Z |  |
