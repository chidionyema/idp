# Flux: what is applied

Read from the cluster receipt taken at 2026-09-24T12:30:18Z. Every Kustomization and HelmRelease, with the revision Flux last applied. **Suspended** is a switch somebody turned off on purpose (temporal, commerce, commerce-data, event-bus), not a defect; **Unknown** is a row Flux has never graded.

**118 objects: 41 ready, 76 not ready, 0 unknown, 1 suspended.**

## Not ready right now

- **HelmRelease commerce/lago** since 2026-09-18T21:16:37Z: Could not determine release state: unable to determine state for release with status 'uninstalling'
- **HelmRelease crossplane-system/crossplane** since 2026-09-24T12:28:07Z: Helm upgrade failed for release crossplane-system/crossplane with chart crossplane@1.15.1: create: failed to create: admission webhook "oke-resource-leak-protection.oke.com" denied the request: OKE resource leak protection rejected the request. Cluster has 2778 secrets and the limit is 2000. See https://docs.oracle.com/iaas/Content/ContEng/Tasks/contengprotectingclustersfromresourceleaks.htm for details.
- **HelmRelease dagster/dagster** since 2026-09-24T12:17:06Z: Helm upgrade failed for release dagster/dagster with chart dagster@1.13.19: values don't meet the specifications of the schema(s) in the following chart(s): dagster: failing loading "https://raw.githubusercontent.com/yannh/kubernetes-json-schema/master/v1.19.0/_definitions.json": HTTP request failed for https://raw.githubusercontent.com/yannh/kubernetes-json-schema/master/v1.19.0/_definitions.json: Get "https://raw.githubusercontent.com/yannh/kubernetes-json-schema/master/v1.19.0/_definitions.json": dial tcp: lookup raw.githubusercontent.com on 10.96.5.5:53: server misbehavingdagster-user-deployments: failing loading "https://raw.githubusercontent.com/yannh/kubernetes-json-schema/master/v1.19.0/_definitions.json": HTTP request failed for https://raw.githubusercontent.com/yannh/kubernetes-json-schema/master/v1.19.0/_definitions.json: Get "https://raw.githubusercontent.com/yannh/kubernetes-json-schema/master/v1.19.0/_definitions.json": dial tcp: lookup raw.githubusercontent.com on 10.96.5.5:53: server misbehaving
- **HelmRelease flux-system/vendor-bridge** since 2026-09-24T12:27:24Z: Helm install failed for release flux-system/vendor-bridge with chart vendor-bridge@0.1.0+41e996d8294e: create: failed to create: admission webhook "oke-resource-leak-protection.oke.com" denied the request: OKE resource leak protection rejected the request. Cluster has 2778 secrets and the limit is 2000. See https://docs.oracle.com/iaas/Content/ContEng/Tasks/contengprotectingclustersfromresourceleaks.htm for details.
- **HelmRelease trivy-system/trivy-operator** since 2026-09-24T12:24:37Z: Helm upgrade failed for release trivy-system/trivy-operator with chart trivy-operator@0.36.0: create: failed to create: admission webhook "oke-resource-leak-protection.oke.com" denied the request: OKE resource leak protection rejected the request. Cluster has 2778 secrets and the limit is 2000. See https://docs.oracle.com/iaas/Content/ContEng/Tasks/contengprotectingclustersfromresourceleaks.htm for details.
- **Kustomization flux-system/acg** since 2026-09-23T17:20:28Z: dependency 'flux-system/edge' is not ready
- **Kustomization flux-system/agent-workforce** since 2026-09-23T17:23:29Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/alerts** since 2026-09-23T17:28:36Z: dependency 'flux-system/alerts-secret' is not ready
- **Kustomization flux-system/alerts-github** since 2026-09-23T17:29:03Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/alerts-secret** since 2026-09-23T17:25:35Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/autoscaler** since 2026-09-23T17:35:30Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/backstage** since 2026-09-24T11:30:37Z: dependency 'flux-system/external-secrets' is not ready
- **Kustomization flux-system/cluster-state** since 2026-09-23T17:23:06Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/commerce** since 2026-09-23T17:48:45Z: dependency 'flux-system/commerce-data' is not ready
- **Kustomization flux-system/commerce-data** since 2026-09-23T17:28:11Z: dependency 'flux-system/external-secrets' is not ready
- **Kustomization flux-system/concierge** since 2026-09-23T17:25:36Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/crossplane** since 2026-09-23T17:31:36Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/crossplane-providerconfig** since 2026-09-16T11:53:07Z: dependency 'flux-system/crossplane-providers' is not ready
- **Kustomization flux-system/crossplane-providers** since 2026-09-16T11:53:06Z: dependency 'flux-system/crossplane' is not ready
- **Kustomization flux-system/crossplane-storage-capability** since 2026-09-16T11:53:07Z: dependency 'flux-system/crossplane-providerconfig' is not ready
- **Kustomization flux-system/dagster** since 2026-09-23T17:23:29Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/dns** since 2026-09-23T17:21:47Z: dependency 'flux-system/edge' is not ready
- **Kustomization flux-system/edge** since 2026-09-24T12:24:36Z: health check failed after 10m0.030834519s: timeout waiting for: [HelmRepository/cert-manager/jetstack status: 'InProgress', HelmRepository/edge/traefik status: 'InProgress']
- **Kustomization flux-system/epistemic-fabric** since 2026-09-23T17:28:36Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/estate-db** since 2026-09-24T12:23:12Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/estate-db-migrate** since 2026-09-23T17:28:06Z: dependency 'flux-system/estate-db' is not ready
- **Kustomization flux-system/event-bus** since 2026-09-24T12:20:38Z: health check failed after 10m0.043336731s: timeout waiting for: [HelmRepository/event-bus/nats status: 'InProgress']
- **Kustomization flux-system/external-secrets** since 2026-09-23T17:21:07Z: dependency 'flux-system/edge' is not ready
- **Kustomization flux-system/flux-webhook** since 2026-09-23T17:19:21Z: dependency 'flux-system/edge' is not ready
- **Kustomization flux-system/github-app-creds** since 2026-09-23T17:28:06Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/guacamole** since 2026-09-23T17:23:35Z: dependency 'flux-system/identity' is not ready
- **Kustomization flux-system/gvisor-runtime** since 2026-09-23T16:43:46Z: dependency 'flux-system/nodesoftware-operator' is not ready
- **Kustomization flux-system/healing** since 2026-09-23T17:28:53Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/healing-analyzer** since 2026-09-23T04:22:54Z: dependency 'flux-system/healing-k8sgpt' is not ready
- **Kustomization flux-system/healing-k8sgpt** since 2026-09-23T17:29:10Z: dependency 'flux-system/healing' is not ready
- **Kustomization flux-system/healthchecks** since 2026-09-23T17:28:12Z: dependency 'flux-system/identity' is not ready
- **Kustomization flux-system/hermes-agent** since 2026-09-23T17:28:36Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/hindsight** since 2026-09-23T17:23:29Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/human-vault** since 2026-09-23T17:22:18Z: dependency 'flux-system/external-secrets' is not ready
- **Kustomization flux-system/human-vault-bridge** since 2026-09-23T17:25:35Z: dependency 'flux-system/human-vault' is not ready
- **Kustomization flux-system/identity** since 2026-09-23T17:22:18Z: dependency 'flux-system/edge' is not ready
- **Kustomization flux-system/idp-agent** since 2026-09-23T17:28:10Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/image-automation** since 2026-09-23T17:23:36Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/jit** since 2026-09-24T12:24:00Z: health check failed after 366.27351ms: failed early due to stalled resources: [Deployment/jit/jit-broker status: 'Failed']
- **Kustomization flux-system/keda** since 2026-09-23T17:28:10Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/llm** since 2026-09-23T17:22:18Z: dependency 'flux-system/edge' is not ready
- **Kustomization flux-system/mcp** since 2026-09-23T17:23:06Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/metrics-server** since 2026-09-23T17:28:11Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/monitoring** since 2026-09-23T17:21:26Z: dependency 'flux-system/edge' is not ready
- **Kustomization flux-system/monitoring-rules** since 2026-09-23T17:23:35Z: dependency 'flux-system/monitoring' is not ready
- **Kustomization flux-system/nodesoftware-operator** since 2026-09-23T17:23:29Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/notify** since 2026-09-23T17:22:18Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/observability** since 2026-09-23T17:23:36Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/observability-collector** since 2026-09-23T17:23:35Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/otto-gateway** since 2026-09-23T17:23:36Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/otto-golden** since 2026-09-23T17:23:06Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/otto-golden-secret** since 2026-09-23T17:23:36Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/priority-classes** since 2026-09-24T12:30:12Z: Reconciliation in progress
- **Kustomization flux-system/prospector** since 2026-09-23T17:28:11Z: dependency 'flux-system/prospector-platform' is not ready
- **Kustomization flux-system/prospector-platform** since 2026-09-23T17:21:47Z: dependency 'flux-system/edge' is not ready
- **Kustomization flux-system/reloader** since 2026-09-23T17:23:36Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/research-engine** since 2026-09-23T17:23:29Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/robusta** since 2026-09-23T17:25:35Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/router-events** since 2026-09-23T04:22:53Z: dependency 'flux-system/llm' is not ready
- **Kustomization flux-system/sandbox-launch** since 2026-09-23T17:18:27Z: dependency 'flux-system/edge' is not ready
- **Kustomization flux-system/scheduling** since 2026-09-23T17:21:26Z: dependency 'flux-system/edge' is not ready
- **Kustomization flux-system/science** since 2026-09-23T17:32:03Z: dependency 'flux-system/observability' is not ready
- **Kustomization flux-system/secret-store** since 2026-09-23T17:21:47Z: dependency 'flux-system/external-secrets' is not ready
- **Kustomization flux-system/spire** since 2026-09-23T17:28:56Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/staging** since 2026-09-24T12:30:06Z: Reconciliation in progress
- **Kustomization flux-system/tailscale** since 2026-09-23T17:23:29Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/temporal** since 2026-09-23T17:19:22Z: dependency 'flux-system/edge' is not ready
- **Kustomization flux-system/trivy** since 2026-09-24T12:23:32Z: Reconciliation in progress
- **Kustomization flux-system/verification** since 2026-09-24T11:30:38Z: dependency 'flux-system/external-secrets' is not ready
- **Kustomization flux-system/via-negativa** since 2026-09-23T17:23:28Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/weave-gitops** since 2026-09-23T17:23:06Z: dependency 'flux-system/identity' is not ready

## Every row

| Kind | Namespace | Name | State | Applied revision | Since | Message |
|---|---|---|---|---|---|---|
| HelmRelease | commerce | lago | Not ready | 1.28.0 | 2026-09-18T21:16:37Z | Could not determine release state: unable to determine state for release with status 'uninstalling' |
| HelmRelease | crossplane-system | crossplane | Not ready | 1.15.1 | 2026-09-24T12:28:07Z | Helm upgrade failed for release crossplane-system/crossplane with chart crossplane@1.15.1: create: failed to create: admission webhook "oke-resource-leak-protec |
| HelmRelease | dagster | dagster | Not ready | 1.13.19 | 2026-09-24T12:17:06Z | Helm upgrade failed for release dagster/dagster with chart dagster@1.13.19: values don't meet the specifications of the schema(s) in the following chart(s): dag |
| HelmRelease | flux-system | vendor-bridge | Not ready | 0.1.0+41e996d8294e | 2026-09-24T12:27:24Z | Helm install failed for release flux-system/vendor-bridge with chart vendor-bridge@0.1.0+41e996d8294e: create: failed to create: admission webhook "oke-resource |
| HelmRelease | trivy-system | trivy-operator | Not ready | 0.36.0 | 2026-09-24T12:24:37Z | Helm upgrade failed for release trivy-system/trivy-operator with chart trivy-operator@0.36.0: create: failed to create: admission webhook "oke-resource-leak-pro |
| Kustomization | flux-system | acg | Not ready | main@41e996d | 2026-09-23T17:20:28Z | dependency 'flux-system/edge' is not ready |
| Kustomization | flux-system | agent-workforce | Not ready | main@689bcd9 | 2026-09-23T17:23:29Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | alerts | Not ready | main@41e996d | 2026-09-23T17:28:36Z | dependency 'flux-system/alerts-secret' is not ready |
| Kustomization | flux-system | alerts-github | Not ready | main@41e996d | 2026-09-23T17:29:03Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | alerts-secret | Not ready | main@41e996d | 2026-09-23T17:25:35Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | autoscaler | Not ready | main@41e996d | 2026-09-23T17:35:30Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | backstage | Not ready | main@689bcd9 | 2026-09-24T11:30:37Z | dependency 'flux-system/external-secrets' is not ready |
| Kustomization | flux-system | cluster-state | Not ready | main@41e996d | 2026-09-23T17:23:06Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | commerce | Not ready | main@abea14d | 2026-09-23T17:48:45Z | dependency 'flux-system/commerce-data' is not ready |
| Kustomization | flux-system | commerce-data | Not ready | main@41e996d | 2026-09-23T17:28:11Z | dependency 'flux-system/external-secrets' is not ready |
| Kustomization | flux-system | concierge | Not ready | main@41e996d | 2026-09-23T17:25:36Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | crossplane | Not ready | main@8d685ec | 2026-09-23T17:31:36Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | crossplane-providerconfig | Not ready | main@8d685ec | 2026-09-16T11:53:07Z | dependency 'flux-system/crossplane-providers' is not ready |
| Kustomization | flux-system | crossplane-providers | Not ready | main@8d685ec | 2026-09-16T11:53:06Z | dependency 'flux-system/crossplane' is not ready |
| Kustomization | flux-system | crossplane-storage-capability | Not ready | main@8d685ec | 2026-09-16T11:53:07Z | dependency 'flux-system/crossplane-providerconfig' is not ready |
| Kustomization | flux-system | dagster | Not ready | main@08aa502 | 2026-09-23T17:23:29Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | dns | Not ready | main@41e996d | 2026-09-23T17:21:47Z | dependency 'flux-system/edge' is not ready |
| Kustomization | flux-system | edge | Not ready | main@41e996d | 2026-09-24T12:24:36Z | health check failed after 10m0.030834519s: timeout waiting for: [HelmRepository/cert-manager/jetstack status: 'InProgress', HelmRepository/edge/traefik status:  |
| Kustomization | flux-system | epistemic-fabric | Not ready | main@41e996d | 2026-09-23T17:28:36Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | estate-db | Not ready | main@41e996d | 2026-09-24T12:23:12Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | estate-db-migrate | Not ready | main@41e996d | 2026-09-23T17:28:06Z | dependency 'flux-system/estate-db' is not ready |
| Kustomization | flux-system | event-bus | Not ready | main@41e996d | 2026-09-24T12:20:38Z | health check failed after 10m0.043336731s: timeout waiting for: [HelmRepository/event-bus/nats status: 'InProgress'] |
| Kustomization | flux-system | external-secrets | Not ready | main@41e996d | 2026-09-23T17:21:07Z | dependency 'flux-system/edge' is not ready |
| Kustomization | flux-system | flux-webhook | Not ready | main@41e996d | 2026-09-23T17:19:21Z | dependency 'flux-system/edge' is not ready |
| Kustomization | flux-system | github-app-creds | Not ready | main@41e996d | 2026-09-23T17:28:06Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | guacamole | Not ready | main@41e996d | 2026-09-23T17:23:35Z | dependency 'flux-system/identity' is not ready |
| Kustomization | flux-system | gvisor-runtime | Not ready | main@41e996d | 2026-09-23T16:43:46Z | dependency 'flux-system/nodesoftware-operator' is not ready |
| Kustomization | flux-system | healing | Not ready | main@41e996d | 2026-09-23T17:28:53Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | healing-analyzer | Not ready | main@689bcd9 | 2026-09-23T04:22:54Z | dependency 'flux-system/healing-k8sgpt' is not ready |
| Kustomization | flux-system | healing-k8sgpt | Not ready | main@689bcd9 | 2026-09-23T17:29:10Z | dependency 'flux-system/healing' is not ready |
| Kustomization | flux-system | healthchecks | Not ready | main@41e996d | 2026-09-23T17:28:12Z | dependency 'flux-system/identity' is not ready |
| Kustomization | flux-system | hermes-agent | Not ready | main@0df0a74 | 2026-09-23T17:28:36Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | hindsight | Not ready | main@689bcd9 | 2026-09-23T17:23:29Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | human-vault | Not ready | main@41e996d | 2026-09-23T17:22:18Z | dependency 'flux-system/external-secrets' is not ready |
| Kustomization | flux-system | human-vault-bridge | Not ready | main@41e996d | 2026-09-23T17:25:35Z | dependency 'flux-system/human-vault' is not ready |
| Kustomization | flux-system | identity | Not ready | main@41e996d | 2026-09-23T17:22:18Z | dependency 'flux-system/edge' is not ready |
| Kustomization | flux-system | idp-agent | Not ready | main@41e996d | 2026-09-23T17:28:10Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | image-automation | Not ready | main@41e996d | 2026-09-23T17:23:36Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | jit | Not ready | main@689bcd9 | 2026-09-24T12:24:00Z | health check failed after 366.27351ms: failed early due to stalled resources: [Deployment/jit/jit-broker status: 'Failed'] |
| Kustomization | flux-system | keda | Not ready | main@41e996d | 2026-09-23T17:28:10Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | llm | Not ready | main@689bcd9 | 2026-09-23T17:22:18Z | dependency 'flux-system/edge' is not ready |
| Kustomization | flux-system | mcp | Not ready | main@689bcd9 | 2026-09-23T17:23:06Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | metrics-server | Not ready | main@41e996d | 2026-09-23T17:28:11Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | monitoring | Not ready | main@41e996d | 2026-09-23T17:21:26Z | dependency 'flux-system/edge' is not ready |
| Kustomization | flux-system | monitoring-rules | Not ready | main@41e996d | 2026-09-23T17:23:35Z | dependency 'flux-system/monitoring' is not ready |
| Kustomization | flux-system | nodesoftware-operator | Not ready | main@41e996d | 2026-09-23T17:23:29Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | notify | Not ready | main@41e996d | 2026-09-23T17:22:18Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | observability | Not ready | main@41e996d | 2026-09-23T17:23:36Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | observability-collector | Not ready | main@41e996d | 2026-09-23T17:23:35Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | otto-gateway | Not ready | main@cd9eb71 | 2026-09-23T17:23:36Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | otto-golden | Not ready | main@cd9eb71 | 2026-09-23T17:23:06Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | otto-golden-secret | Not ready | main@41e996d | 2026-09-23T17:23:36Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | priority-classes | Not ready | main@41e996d | 2026-09-24T12:30:12Z | Reconciliation in progress |
| Kustomization | flux-system | prospector | Not ready | main@7453d76 | 2026-09-23T17:28:11Z | dependency 'flux-system/prospector-platform' is not ready |
| Kustomization | flux-system | prospector-platform | Not ready | main@41e996d | 2026-09-23T17:21:47Z | dependency 'flux-system/edge' is not ready |
| Kustomization | flux-system | reloader | Not ready | main@41e996d | 2026-09-23T17:23:36Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | research-engine | Not ready | main@689bcd9 | 2026-09-23T17:23:29Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | robusta | Not ready | main@41e996d | 2026-09-23T17:25:35Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | router-events | Not ready | main@689bcd9 | 2026-09-23T04:22:53Z | dependency 'flux-system/llm' is not ready |
| Kustomization | flux-system | sandbox-launch | Not ready | main@ac2a1b1 | 2026-09-23T17:18:27Z | dependency 'flux-system/edge' is not ready |
| Kustomization | flux-system | scheduling | Not ready | main@41e996d | 2026-09-23T17:21:26Z | dependency 'flux-system/edge' is not ready |
| Kustomization | flux-system | science | Not ready | main@41e996d | 2026-09-23T17:32:03Z | dependency 'flux-system/observability' is not ready |
| Kustomization | flux-system | secret-store | Not ready | main@41e996d | 2026-09-23T17:21:47Z | dependency 'flux-system/external-secrets' is not ready |
| Kustomization | flux-system | spire | Not ready | main@41e996d | 2026-09-23T17:28:56Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | staging | Not ready | main@41e996d | 2026-09-24T12:30:06Z | Reconciliation in progress |
| Kustomization | flux-system | tailscale | Not ready | main@41e996d | 2026-09-23T17:23:29Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | temporal | Not ready | main@41e996d | 2026-09-23T17:19:22Z | dependency 'flux-system/edge' is not ready |
| Kustomization | flux-system | trivy | Not ready | main@689bcd9 | 2026-09-24T12:23:32Z | Reconciliation in progress |
| Kustomization | flux-system | verification | Not ready | main@41e996d | 2026-09-24T11:30:38Z | dependency 'flux-system/external-secrets' is not ready |
| Kustomization | flux-system | via-negativa | Not ready | main@689bcd9 | 2026-09-23T17:23:28Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | weave-gitops | Not ready | main@41e996d | 2026-09-23T17:23:06Z | dependency 'flux-system/identity' is not ready |
| HelmRelease | tigera-operator | tigera-operator | Suspended | v3.32.2 | 2026-09-06T19:38:02Z |  |
| HelmRelease | cert-manager | cert-manager | Ready | v1.21.1 | 2026-09-08T11:56:22Z |  |
| HelmRelease | edge | external-dns | Ready | 1.21.1 | 2026-09-06T19:33:35Z |  |
| HelmRelease | edge | traefik | Ready | 41.3.0 | 2026-09-06T19:35:13Z |  |
| HelmRelease | estate-db | cloudnative-pg | Ready | 0.29.0 | 2026-09-06T19:45:25Z |  |
| HelmRelease | event-bus | nats | Ready | 2.14.6 | 2026-09-06T19:39:37Z |  |
| HelmRelease | external-secrets | external-secrets | Ready | 2.9.0 | 2026-09-14T20:24:54Z |  |
| HelmRelease | healing | descheduler | Ready | 0.36.0 | 2026-09-08T10:45:39Z |  |
| HelmRelease | healing | k8sgpt-operator | Ready | 0.2.29 | 2026-09-08T12:01:53Z |  |
| HelmRelease | hindsight | hindsight | Ready | 0.9.2 | 2026-09-17T11:41:29Z |  |
| HelmRelease | identity | oauth2-proxy | Ready | 10.7.0 | 2026-09-08T10:18:34Z |  |
| HelmRelease | keda | keda | Ready | 2.20.2 | 2026-09-08T10:19:32Z |  |
| HelmRelease | keda | keda-add-ons-http | Ready | 0.15.0 | 2026-09-23T04:37:42Z |  |
| HelmRelease | kyverno | kyverno | Ready | 3.9.0 | 2026-09-08T10:19:02Z |  |
| HelmRelease | metrics-server | metrics-server | Ready | 3.14.0 | 2026-09-06T19:34:02Z |  |
| HelmRelease | monitoring | blackbox | Ready | 11.17.2 | 2026-09-06T19:47:10Z |  |
| HelmRelease | monitoring | kube-prometheus-stack | Ready | 88.6.0 | 2026-09-06T20:26:45Z |  |
| HelmRelease | observability | langfuse | Ready | 2.0.2 | 2026-09-23T05:34:02Z |  |
| HelmRelease | observability | signoz | Ready | 0.138.0 | 2026-09-13T10:24:12Z |  |
| HelmRelease | observability | superset | Ready | 0.22.4 | 2026-09-06T19:46:05Z |  |
| HelmRelease | observability-agent | k8s-infra | Ready | 0.17.0 | 2026-09-14T18:09:18Z |  |
| HelmRelease | reloader | reloader | Ready | 2.2.16 | 2026-09-06T19:33:25Z |  |
| HelmRelease | robusta | robusta | Ready | 0.48.0 | 2026-09-06T20:26:45Z |  |
| HelmRelease | spire-mgmt | spire | Ready | 0.30.1 | 2026-09-23T04:43:23Z |  |
| HelmRelease | spire-mgmt | spire-crds | Ready | 0.6.1 | 2026-09-06T20:26:47Z |  |
| HelmRelease | tailscale | tailscale-operator | Ready | 1.102.3 | 2026-09-06T19:33:35Z |  |
| HelmRelease | temporal | temporal | Ready | 1.6.0 | 2026-09-15T14:03:10Z |  |
| HelmRelease | weave-gitops | weave-gitops | Ready | 4.0.36 | 2026-09-06T20:26:45Z |  |
| Kustomization | flux-system | backstage-namespace | Ready | main@41e996d | 2026-09-24T12:21:32Z |  |
| Kustomization | flux-system | calico | Ready | main@41e996d | 2026-09-24T12:20:33Z |  |
| Kustomization | flux-system | estate-catalog | Ready | latest@sha256:cfd0a76a2aad036d104de5fe10 | 2026-09-24T12:26:08Z |  |
| Kustomization | flux-system | estate-db-operator | Ready | main@41e996d | 2026-09-24T12:22:53Z |  |
| Kustomization | flux-system | feature-register | Ready | main@41e996d | 2026-09-24T12:26:22Z |  |
| Kustomization | flux-system | flux-system | Ready | main@41e996d | 2026-09-24T12:21:40Z |  |
| Kustomization | flux-system | gateway-api-crds | Ready | v1.5.1@e7677b7 | 2026-09-24T12:25:31Z |  |
| Kustomization | flux-system | kyverno | Ready | main@41e996d | 2026-09-24T12:26:05Z |  |
| Kustomization | flux-system | ns-fences | Ready | main@41e996d | 2026-09-24T12:24:33Z |  |
| Kustomization | flux-system | rbac | Ready | main@41e996d | 2026-09-24T12:22:40Z |  |
| Kustomization | flux-system | rbac-floor | Ready | main@41e996d | 2026-09-24T12:25:37Z |  |
| Kustomization | flux-system | rbac-identity | Ready | main@41e996d | 2026-09-24T12:23:07Z |  |
| Kustomization | flux-system | sandbox-live | Ready | sandbox/launch@4830a6e | 2026-09-24T12:29:44Z |  |
| Kustomization | flux-system | searxng | Ready | main@41e996d | 2026-09-24T12:20:30Z |  |
