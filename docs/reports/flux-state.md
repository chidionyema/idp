# Flux: what is applied

Read from the cluster receipt taken at 2026-09-25T17:45:50Z. Every Kustomization and HelmRelease, with the revision Flux last applied. **Suspended** is a switch somebody turned off on purpose (temporal, commerce, commerce-data, event-bus), not a defect; **Unknown** is a row Flux has never graded.

**120 objects: 35 ready, 84 not ready, 0 unknown, 1 suspended.**

## Not ready right now

- **HelmRelease commerce/lago** since 2026-09-25T01:20:15Z: Could not determine release state: unable to determine state for release with status 'uninstalling'
- **HelmRelease coroot/coroot** since 2026-09-25T17:44:06Z: Helm install failed for release coroot/coroot with chart coroot@0.22.0: create: failed to create: admission webhook "oke-resource-leak-protection.oke.com" denied the request: OKE resource leak protection rejected the request. Cluster has 2778 secrets and the limit is 2000. See https://docs.oracle.com/iaas/Content/ContEng/Tasks/contengprotectingclustersfromresourceleaks.htm for details.
- **HelmRelease crossplane-system/crossplane** since 2026-09-25T17:33:23Z: Helm upgrade failed for release crossplane-system/crossplane with chart crossplane@1.15.1: create: failed to create: admission webhook "oke-resource-leak-protection.oke.com" denied the request: OKE resource leak protection rejected the request. Cluster has 2778 secrets and the limit is 2000. See https://docs.oracle.com/iaas/Content/ContEng/Tasks/contengprotectingclustersfromresourceleaks.htm for details.
- **HelmRelease dagster/dagster** since 2026-09-25T17:33:15Z: Helm upgrade failed for release dagster/dagster with chart dagster@1.13.19: create: failed to create: admission webhook "oke-resource-leak-protection.oke.com" denied the request: OKE resource leak protection rejected the request. Cluster has 2778 secrets and the limit is 2000. See https://docs.oracle.com/iaas/Content/ContEng/Tasks/contengprotectingclustersfromresourceleaks.htm for details.
- **HelmRelease flux-system/vendor-bridge** since 2026-09-25T17:43:33Z: Helm install failed for release flux-system/vendor-bridge with chart vendor-bridge@0.1.0+e1f7b069457f: create: failed to create: admission webhook "oke-resource-leak-protection.oke.com" denied the request: OKE resource leak protection rejected the request. Cluster has 2778 secrets and the limit is 2000. See https://docs.oracle.com/iaas/Content/ContEng/Tasks/contengprotectingclustersfromresourceleaks.htm for details.
- **HelmRelease observability/langfuse** since 2026-09-25T10:40:26Z: dependency 'observability/signoz' is not ready
- **HelmRelease observability/signoz** since 2026-09-25T17:33:55Z: Helm upgrade failed for release observability/signoz with chart signoz@0.138.0: create: failed to create: admission webhook "oke-resource-leak-protection.oke.com" denied the request: OKE resource leak protection rejected the request. Cluster has 2778 secrets and the limit is 2000. See https://docs.oracle.com/iaas/Content/ContEng/Tasks/contengprotectingclustersfromresourceleaks.htm for details.
- **HelmRelease robusta/robusta** since 2026-09-25T17:39:58Z: Helm upgrade failed for release robusta/robusta with chart robusta@0.48.0: create: failed to create: admission webhook "oke-resource-leak-protection.oke.com" denied the request: OKE resource leak protection rejected the request. Cluster has 2778 secrets and the limit is 2000. See https://docs.oracle.com/iaas/Content/ContEng/Tasks/contengprotectingclustersfromresourceleaks.htm for details.
- **HelmRelease spire-mgmt/spire** since 2026-09-25T17:41:08Z: Helm upgrade failed for release spire-mgmt/spire with chart spire@0.30.1: create: failed to create: admission webhook "oke-resource-leak-protection.oke.com" denied the request: OKE resource leak protection rejected the request. Cluster has 2778 secrets and the limit is 2000. See https://docs.oracle.com/iaas/Content/ContEng/Tasks/contengprotectingclustersfromresourceleaks.htm for details.
- **HelmRelease trivy-system/trivy-operator** since 2026-09-25T17:35:24Z: Helm upgrade failed for release trivy-system/trivy-operator with chart trivy-operator@0.36.0: create: failed to create: admission webhook "oke-resource-leak-protection.oke.com" denied the request: OKE resource leak protection rejected the request. Cluster has 2778 secrets and the limit is 2000. See https://docs.oracle.com/iaas/Content/ContEng/Tasks/contengprotectingclustersfromresourceleaks.htm for details.
- **Kustomization flux-system/acg** since 2026-09-25T14:33:39Z: dependency 'flux-system/edge' is not ready
- **Kustomization flux-system/agent-workforce** since 2026-09-25T13:02:35Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/alerts** since 2026-09-25T12:52:37Z: dependency 'flux-system/alerts-secret' is not ready
- **Kustomization flux-system/alerts-github** since 2026-09-25T12:41:53Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/alerts-secret** since 2026-09-25T12:40:41Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/autoscaler** since 2026-09-25T12:40:41Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/backstage** since 2026-09-25T17:33:16Z: dependency 'flux-system/external-secrets' is not ready
- **Kustomization flux-system/backstage-namespace** since 2026-09-25T17:40:15Z: Reconciliation in progress
- **Kustomization flux-system/cluster-state** since 2026-09-25T13:11:38Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/commerce** since 2026-09-25T12:59:10Z: dependency 'flux-system/commerce-data' is not ready
- **Kustomization flux-system/commerce-data** since 2026-09-25T13:11:39Z: dependency 'flux-system/external-secrets' is not ready
- **Kustomization flux-system/concierge** since 2026-09-25T12:41:10Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/coroot** since 2026-09-25T12:47:40Z: dependency 'flux-system/monitoring' is not ready
- **Kustomization flux-system/crossplane** since 2026-09-25T13:11:39Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/crossplane-providerconfig** since 2026-09-16T11:53:07Z: dependency 'flux-system/crossplane-providers' is not ready
- **Kustomization flux-system/crossplane-providers** since 2026-09-16T11:53:06Z: dependency 'flux-system/crossplane' is not ready
- **Kustomization flux-system/crossplane-storage-capability** since 2026-09-16T11:53:07Z: dependency 'flux-system/crossplane-providerconfig' is not ready
- **Kustomization flux-system/dagster** since 2026-09-25T13:02:35Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/dns** since 2026-09-25T14:33:38Z: dependency 'flux-system/edge' is not ready
- **Kustomization flux-system/edge** since 2026-09-25T17:33:17Z: Reconciliation in progress
- **Kustomization flux-system/epistemic-fabric** since 2026-09-25T12:46:27Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/estate-db** since 2026-09-25T17:33:16Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/estate-db-migrate** since 2026-09-25T12:41:54Z: dependency 'flux-system/estate-db' is not ready
- **Kustomization flux-system/external-secrets** since 2026-09-25T14:33:38Z: dependency 'flux-system/edge' is not ready
- **Kustomization flux-system/flux-system** since 2026-09-25T17:36:11Z: Reconciliation in progress
- **Kustomization flux-system/flux-webhook** since 2026-09-25T14:26:20Z: dependency 'flux-system/edge' is not ready
- **Kustomization flux-system/github-app-creds** since 2026-09-25T12:40:41Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/guacamole** since 2026-09-25T12:52:37Z: dependency 'flux-system/identity' is not ready
- **Kustomization flux-system/gvisor-runtime** since 2026-09-25T12:52:37Z: dependency 'flux-system/nodesoftware-operator' is not ready
- **Kustomization flux-system/healing** since 2026-09-25T13:05:44Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/healing-analyzer** since 2026-09-23T04:22:54Z: dependency 'flux-system/healing-k8sgpt' is not ready
- **Kustomization flux-system/healing-k8sgpt** since 2026-09-25T13:02:35Z: dependency 'flux-system/healing' is not ready
- **Kustomization flux-system/healthchecks** since 2026-09-25T12:54:32Z: dependency 'flux-system/identity' is not ready
- **Kustomization flux-system/hermes-agent** since 2026-09-25T13:05:38Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/hindsight** since 2026-09-25T12:41:55Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/human-vault** since 2026-09-25T12:59:08Z: dependency 'flux-system/external-secrets' is not ready
- **Kustomization flux-system/human-vault-bridge** since 2026-09-25T12:52:37Z: dependency 'flux-system/human-vault' is not ready
- **Kustomization flux-system/identity** since 2026-09-25T14:33:38Z: dependency 'flux-system/edge' is not ready
- **Kustomization flux-system/idp-agent** since 2026-09-25T12:59:08Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/image-automation** since 2026-09-25T12:38:33Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/jit** since 2026-09-25T17:41:28Z: health check failed after 1.412549943s: failed early due to stalled resources: [Deployment/jit/jit-broker status: 'Failed']
- **Kustomization flux-system/keda** since 2026-09-25T13:05:45Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/kyverno** since 2026-09-25T17:41:31Z: Reconciliation in progress
- **Kustomization flux-system/llm** since 2026-09-25T14:33:38Z: dependency 'flux-system/edge' is not ready
- **Kustomization flux-system/mcp** since 2026-09-25T13:11:39Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/metrics-server** since 2026-09-25T13:05:45Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/monitoring** since 2026-09-25T14:33:38Z: dependency 'flux-system/edge' is not ready
- **Kustomization flux-system/monitoring-rules** since 2026-09-25T12:46:27Z: dependency 'flux-system/monitoring' is not ready
- **Kustomization flux-system/nodesoftware-operator** since 2026-09-25T13:05:44Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/notify** since 2026-09-25T13:02:35Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/observability** since 2026-09-25T13:02:35Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/observability-collector** since 2026-09-25T13:05:38Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/otto-gateway** since 2026-09-25T13:02:35Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/otto-golden** since 2026-09-25T13:05:45Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/otto-golden-secret** since 2026-09-25T12:39:50Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/prospector** since 2026-09-25T13:08:37Z: dependency 'flux-system/prospector-platform' is not ready
- **Kustomization flux-system/prospector-platform** since 2026-09-25T14:33:39Z: dependency 'flux-system/edge' is not ready
- **Kustomization flux-system/rbac** since 2026-09-25T16:22:25Z: dependency 'flux-system/rbac-identity' revision is not up to date
- **Kustomization flux-system/rbac-identity** since 2026-09-25T17:36:10Z: ExternalSecret/flux-system/bridge-identity dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-secrets.io": failed to call webhook: Post "https://external-secrets-webhook.external-secrets.svc:443/validate-external-secrets-io-v1-externalsecret?timeout=15s": context deadline exceeded 
- **Kustomization flux-system/reloader** since 2026-09-25T12:41:10Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/research-engine** since 2026-09-25T12:41:54Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/robusta** since 2026-09-25T13:02:34Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/router-events** since 2026-09-23T04:22:53Z: dependency 'flux-system/llm' is not ready
- **Kustomization flux-system/sandbox-launch** since 2026-09-25T14:33:37Z: dependency 'flux-system/edge' is not ready
- **Kustomization flux-system/scheduling** since 2026-09-25T14:33:38Z: dependency 'flux-system/edge' is not ready
- **Kustomization flux-system/science** since 2026-09-25T11:46:18Z: dependency 'flux-system/observability' is not ready
- **Kustomization flux-system/secret-store** since 2026-09-25T13:05:45Z: dependency 'flux-system/external-secrets' is not ready
- **Kustomization flux-system/spire** since 2026-09-25T13:11:39Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/tailscale** since 2026-09-25T12:39:13Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/temporal** since 2026-09-25T14:33:38Z: dependency 'flux-system/edge' is not ready
- **Kustomization flux-system/trivy** since 2026-09-25T17:25:04Z: health check failed after 15m0.043886476s: timeout waiting for: [HelmRelease/trivy-system/trivy-operator status: 'InProgress']
- **Kustomization flux-system/verification** since 2026-09-25T17:33:16Z: dependency 'flux-system/external-secrets' is not ready
- **Kustomization flux-system/via-negativa** since 2026-09-25T12:40:41Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/weave-gitops** since 2026-09-25T12:41:53Z: dependency 'flux-system/identity' is not ready

## Every row

| Kind | Namespace | Name | State | Applied revision | Since | Message |
|---|---|---|---|---|---|---|
| HelmRelease | commerce | lago | Not ready | 1.28.0 | 2026-09-25T01:20:15Z | Could not determine release state: unable to determine state for release with status 'uninstalling' |
| HelmRelease | coroot | coroot | Not ready | 0.22.0 | 2026-09-25T17:44:06Z | Helm install failed for release coroot/coroot with chart coroot@0.22.0: create: failed to create: admission webhook "oke-resource-leak-protection.oke.com" denie |
| HelmRelease | crossplane-system | crossplane | Not ready | 1.15.1 | 2026-09-25T17:33:23Z | Helm upgrade failed for release crossplane-system/crossplane with chart crossplane@1.15.1: create: failed to create: admission webhook "oke-resource-leak-protec |
| HelmRelease | dagster | dagster | Not ready | 1.13.19 | 2026-09-25T17:33:15Z | Helm upgrade failed for release dagster/dagster with chart dagster@1.13.19: create: failed to create: admission webhook "oke-resource-leak-protection.oke.com" d |
| HelmRelease | flux-system | vendor-bridge | Not ready | 0.1.0+e1f7b069457f | 2026-09-25T17:43:33Z | Helm install failed for release flux-system/vendor-bridge with chart vendor-bridge@0.1.0+e1f7b069457f: create: failed to create: admission webhook "oke-resource |
| HelmRelease | observability | langfuse | Not ready | 2.0.2 | 2026-09-25T10:40:26Z | dependency 'observability/signoz' is not ready |
| HelmRelease | observability | signoz | Not ready | 0.138.0 | 2026-09-25T17:33:55Z | Helm upgrade failed for release observability/signoz with chart signoz@0.138.0: create: failed to create: admission webhook "oke-resource-leak-protection.oke.co |
| HelmRelease | robusta | robusta | Not ready | 0.48.0 | 2026-09-25T17:39:58Z | Helm upgrade failed for release robusta/robusta with chart robusta@0.48.0: create: failed to create: admission webhook "oke-resource-leak-protection.oke.com" de |
| HelmRelease | spire-mgmt | spire | Not ready | 0.30.1 | 2026-09-25T17:41:08Z | Helm upgrade failed for release spire-mgmt/spire with chart spire@0.30.1: create: failed to create: admission webhook "oke-resource-leak-protection.oke.com" den |
| HelmRelease | trivy-system | trivy-operator | Not ready | 0.36.0 | 2026-09-25T17:35:24Z | Helm upgrade failed for release trivy-system/trivy-operator with chart trivy-operator@0.36.0: create: failed to create: admission webhook "oke-resource-leak-pro |
| Kustomization | flux-system | acg | Not ready | main@0b33777 | 2026-09-25T14:33:39Z | dependency 'flux-system/edge' is not ready |
| Kustomization | flux-system | agent-workforce | Not ready | main@689bcd9 | 2026-09-25T13:02:35Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | alerts | Not ready | main@0b33777 | 2026-09-25T12:52:37Z | dependency 'flux-system/alerts-secret' is not ready |
| Kustomization | flux-system | alerts-github | Not ready | main@0b33777 | 2026-09-25T12:41:53Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | alerts-secret | Not ready | main@0b33777 | 2026-09-25T12:40:41Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | autoscaler | Not ready | main@0b33777 | 2026-09-25T12:40:41Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | backstage | Not ready | main@689bcd9 | 2026-09-25T17:33:16Z | dependency 'flux-system/external-secrets' is not ready |
| Kustomization | flux-system | backstage-namespace | Not ready | main@e1f7b06 | 2026-09-25T17:40:15Z | Reconciliation in progress |
| Kustomization | flux-system | cluster-state | Not ready | main@0b33777 | 2026-09-25T13:11:38Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | commerce | Not ready | main@abea14d | 2026-09-25T12:59:10Z | dependency 'flux-system/commerce-data' is not ready |
| Kustomization | flux-system | commerce-data | Not ready | main@0b33777 | 2026-09-25T13:11:39Z | dependency 'flux-system/external-secrets' is not ready |
| Kustomization | flux-system | concierge | Not ready | main@0b33777 | 2026-09-25T12:41:10Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | coroot | Not ready | main@0b33777 | 2026-09-25T12:47:40Z | dependency 'flux-system/monitoring' is not ready |
| Kustomization | flux-system | crossplane | Not ready | main@8d685ec | 2026-09-25T13:11:39Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | crossplane-providerconfig | Not ready | main@8d685ec | 2026-09-16T11:53:07Z | dependency 'flux-system/crossplane-providers' is not ready |
| Kustomization | flux-system | crossplane-providers | Not ready | main@8d685ec | 2026-09-16T11:53:06Z | dependency 'flux-system/crossplane' is not ready |
| Kustomization | flux-system | crossplane-storage-capability | Not ready | main@8d685ec | 2026-09-16T11:53:07Z | dependency 'flux-system/crossplane-providerconfig' is not ready |
| Kustomization | flux-system | dagster | Not ready | main@08aa502 | 2026-09-25T13:02:35Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | dns | Not ready | main@0b33777 | 2026-09-25T14:33:38Z | dependency 'flux-system/edge' is not ready |
| Kustomization | flux-system | edge | Not ready | main@30c7e98 | 2026-09-25T17:33:17Z | Reconciliation in progress |
| Kustomization | flux-system | epistemic-fabric | Not ready | main@0b33777 | 2026-09-25T12:46:27Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | estate-db | Not ready | main@0b33777 | 2026-09-25T17:33:16Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | estate-db-migrate | Not ready | main@0b33777 | 2026-09-25T12:41:54Z | dependency 'flux-system/estate-db' is not ready |
| Kustomization | flux-system | external-secrets | Not ready | main@0b33777 | 2026-09-25T14:33:38Z | dependency 'flux-system/edge' is not ready |
| Kustomization | flux-system | flux-system | Not ready | main@e1f7b06 | 2026-09-25T17:36:11Z | Reconciliation in progress |
| Kustomization | flux-system | flux-webhook | Not ready | main@0b33777 | 2026-09-25T14:26:20Z | dependency 'flux-system/edge' is not ready |
| Kustomization | flux-system | github-app-creds | Not ready | main@0b33777 | 2026-09-25T12:40:41Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | guacamole | Not ready | main@0b33777 | 2026-09-25T12:52:37Z | dependency 'flux-system/identity' is not ready |
| Kustomization | flux-system | gvisor-runtime | Not ready | main@0b33777 | 2026-09-25T12:52:37Z | dependency 'flux-system/nodesoftware-operator' is not ready |
| Kustomization | flux-system | healing | Not ready | main@0b33777 | 2026-09-25T13:05:44Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | healing-analyzer | Not ready | main@689bcd9 | 2026-09-23T04:22:54Z | dependency 'flux-system/healing-k8sgpt' is not ready |
| Kustomization | flux-system | healing-k8sgpt | Not ready | main@689bcd9 | 2026-09-25T13:02:35Z | dependency 'flux-system/healing' is not ready |
| Kustomization | flux-system | healthchecks | Not ready | main@0b33777 | 2026-09-25T12:54:32Z | dependency 'flux-system/identity' is not ready |
| Kustomization | flux-system | hermes-agent | Not ready | main@0df0a74 | 2026-09-25T13:05:38Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | hindsight | Not ready | main@689bcd9 | 2026-09-25T12:41:55Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | human-vault | Not ready | main@0b33777 | 2026-09-25T12:59:08Z | dependency 'flux-system/external-secrets' is not ready |
| Kustomization | flux-system | human-vault-bridge | Not ready | main@0b33777 | 2026-09-25T12:52:37Z | dependency 'flux-system/human-vault' is not ready |
| Kustomization | flux-system | identity | Not ready | main@0b33777 | 2026-09-25T14:33:38Z | dependency 'flux-system/edge' is not ready |
| Kustomization | flux-system | idp-agent | Not ready | main@0b33777 | 2026-09-25T12:59:08Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | image-automation | Not ready | main@0b33777 | 2026-09-25T12:38:33Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | jit | Not ready | main@689bcd9 | 2026-09-25T17:41:28Z | health check failed after 1.412549943s: failed early due to stalled resources: [Deployment/jit/jit-broker status: 'Failed'] |
| Kustomization | flux-system | keda | Not ready | main@0b33777 | 2026-09-25T13:05:45Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | kyverno | Not ready | main@e1f7b06 | 2026-09-25T17:41:31Z | Reconciliation in progress |
| Kustomization | flux-system | llm | Not ready | main@689bcd9 | 2026-09-25T14:33:38Z | dependency 'flux-system/edge' is not ready |
| Kustomization | flux-system | mcp | Not ready | main@689bcd9 | 2026-09-25T13:11:39Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | metrics-server | Not ready | main@0b33777 | 2026-09-25T13:05:45Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | monitoring | Not ready | main@0b33777 | 2026-09-25T14:33:38Z | dependency 'flux-system/edge' is not ready |
| Kustomization | flux-system | monitoring-rules | Not ready | main@0b33777 | 2026-09-25T12:46:27Z | dependency 'flux-system/monitoring' is not ready |
| Kustomization | flux-system | nodesoftware-operator | Not ready | main@0b33777 | 2026-09-25T13:05:44Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | notify | Not ready | main@0b33777 | 2026-09-25T13:02:35Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | observability | Not ready | main@0b33777 | 2026-09-25T13:02:35Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | observability-collector | Not ready | main@0b33777 | 2026-09-25T13:05:38Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | otto-gateway | Not ready | main@cd9eb71 | 2026-09-25T13:02:35Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | otto-golden | Not ready | main@cd9eb71 | 2026-09-25T13:05:45Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | otto-golden-secret | Not ready | main@0b33777 | 2026-09-25T12:39:50Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | prospector | Not ready | main@7453d76 | 2026-09-25T13:08:37Z | dependency 'flux-system/prospector-platform' is not ready |
| Kustomization | flux-system | prospector-platform | Not ready | main@0b33777 | 2026-09-25T14:33:39Z | dependency 'flux-system/edge' is not ready |
| Kustomization | flux-system | rbac | Not ready | main@3ed6bfa | 2026-09-25T16:22:25Z | dependency 'flux-system/rbac-identity' revision is not up to date |
| Kustomization | flux-system | rbac-identity | Not ready | main@13140b8 | 2026-09-25T17:36:10Z | ExternalSecret/flux-system/bridge-identity dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-sec |
| Kustomization | flux-system | reloader | Not ready | main@0b33777 | 2026-09-25T12:41:10Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | research-engine | Not ready | main@689bcd9 | 2026-09-25T12:41:54Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | robusta | Not ready | main@41e996d | 2026-09-25T13:02:34Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | router-events | Not ready | main@689bcd9 | 2026-09-23T04:22:53Z | dependency 'flux-system/llm' is not ready |
| Kustomization | flux-system | sandbox-launch | Not ready | main@ac2a1b1 | 2026-09-25T14:33:37Z | dependency 'flux-system/edge' is not ready |
| Kustomization | flux-system | scheduling | Not ready | main@0b33777 | 2026-09-25T14:33:38Z | dependency 'flux-system/edge' is not ready |
| Kustomization | flux-system | science | Not ready | main@0b33777 | 2026-09-25T11:46:18Z | dependency 'flux-system/observability' is not ready |
| Kustomization | flux-system | secret-store | Not ready | main@0b33777 | 2026-09-25T13:05:45Z | dependency 'flux-system/external-secrets' is not ready |
| Kustomization | flux-system | spire | Not ready | main@0b33777 | 2026-09-25T13:11:39Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | tailscale | Not ready | main@0b33777 | 2026-09-25T12:39:13Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | temporal | Not ready | main@41e996d | 2026-09-25T14:33:38Z | dependency 'flux-system/edge' is not ready |
| Kustomization | flux-system | trivy | Not ready | main@689bcd9 | 2026-09-25T17:25:04Z | health check failed after 15m0.043886476s: timeout waiting for: [HelmRelease/trivy-system/trivy-operator status: 'InProgress'] |
| Kustomization | flux-system | verification | Not ready | main@0b33777 | 2026-09-25T17:33:16Z | dependency 'flux-system/external-secrets' is not ready |
| Kustomization | flux-system | via-negativa | Not ready | main@689bcd9 | 2026-09-25T12:40:41Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | weave-gitops | Not ready | main@0b33777 | 2026-09-25T12:41:53Z | dependency 'flux-system/identity' is not ready |
| HelmRelease | tigera-operator | tigera-operator | Suspended | v3.32.2 | 2026-09-06T19:38:02Z |  |
| HelmRelease | cert-manager | cert-manager | Ready | v1.21.1 | 2026-09-25T01:16:37Z |  |
| HelmRelease | edge | external-dns | Ready | 1.21.1 | 2026-09-25T01:23:11Z |  |
| HelmRelease | edge | traefik | Ready | 41.3.0 | 2026-09-25T01:24:25Z |  |
| HelmRelease | estate-db | cloudnative-pg | Ready | 0.29.0 | 2026-09-25T01:20:16Z |  |
| HelmRelease | event-bus | nats | Ready | 2.14.6 | 2026-09-25T01:16:29Z |  |
| HelmRelease | external-secrets | external-secrets | Ready | 2.9.0 | 2026-09-25T01:27:56Z |  |
| HelmRelease | healing | descheduler | Ready | 0.36.0 | 2026-09-25T01:16:37Z |  |
| HelmRelease | healing | k8sgpt-operator | Ready | 0.2.29 | 2026-09-08T12:01:53Z |  |
| HelmRelease | hindsight | hindsight | Ready | 0.9.2 | 2026-09-25T01:16:31Z |  |
| HelmRelease | identity | oauth2-proxy | Ready | 10.7.0 | 2026-09-25T01:16:35Z |  |
| HelmRelease | keda | keda | Ready | 2.20.2 | 2026-09-25T01:16:41Z |  |
| HelmRelease | keda | keda-add-ons-http | Ready | 0.15.0 | 2026-09-25T01:16:59Z |  |
| HelmRelease | kyverno | kyverno | Ready | 3.9.0 | 2026-09-25T01:16:51Z |  |
| HelmRelease | metrics-server | metrics-server | Ready | 3.14.0 | 2026-09-25T01:18:55Z |  |
| HelmRelease | monitoring | blackbox | Ready | 11.17.2 | 2026-09-25T01:31:29Z |  |
| HelmRelease | monitoring | kube-prometheus-stack | Ready | 88.6.0 | 2026-09-25T01:22:46Z |  |
| HelmRelease | observability | superset | Ready | 0.22.4 | 2026-09-25T01:16:30Z |  |
| HelmRelease | observability-agent | k8s-infra | Ready | 0.17.0 | 2026-09-25T01:27:26Z |  |
| HelmRelease | reloader | reloader | Ready | 2.2.16 | 2026-09-25T01:18:00Z |  |
| HelmRelease | spire-mgmt | spire-crds | Ready | 0.6.1 | 2026-09-25T01:28:36Z |  |
| HelmRelease | tailscale | tailscale-operator | Ready | 1.102.3 | 2026-09-25T01:16:29Z |  |
| HelmRelease | temporal | temporal | Ready | 1.6.0 | 2026-09-25T01:16:37Z |  |
| HelmRelease | weave-gitops | weave-gitops | Ready | 4.0.36 | 2026-09-25T01:16:51Z |  |
| Kustomization | flux-system | calico | Ready | main@e1f7b06 | 2026-09-25T17:19:46Z |  |
| Kustomization | flux-system | estate-catalog | Ready | latest@sha256:b18da2f21a43ec75481e49e6dd | 2026-09-25T17:41:31Z |  |
| Kustomization | flux-system | estate-db-operator | Ready | main@e1f7b06 | 2026-09-25T17:10:10Z |  |
| Kustomization | flux-system | event-bus | Ready | main@e1f7b06 | 2026-09-25T17:33:16Z |  |
| Kustomization | flux-system | feature-register | Ready | main@e1f7b06 | 2026-09-25T17:15:51Z |  |
| Kustomization | flux-system | gateway-api-crds | Ready | v1.5.1@e7677b7 | 2026-09-25T17:40:15Z |  |
| Kustomization | flux-system | ns-fences | Ready | main@e1f7b06 | 2026-09-25T17:20:17Z |  |
| Kustomization | flux-system | priority-classes | Ready | main@e1f7b06 | 2026-09-25T17:10:19Z |  |
| Kustomization | flux-system | rbac-floor | Ready | main@e1f7b06 | 2026-09-25T16:55:25Z |  |
| Kustomization | flux-system | sandbox-live | Ready | sandbox/launch@4830a6e | 2026-09-25T17:36:11Z |  |
| Kustomization | flux-system | searxng | Ready | main@e1f7b06 | 2026-09-25T17:09:07Z |  |
| Kustomization | flux-system | staging | Ready | main@e1f7b06 | 2026-09-25T17:40:07Z |  |
