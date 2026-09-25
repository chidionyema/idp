# Flux: what is applied

Read from the cluster receipt taken at 2026-09-25T21:15:57Z. Every Kustomization and HelmRelease, with the revision Flux last applied. **Suspended** is a switch somebody turned off on purpose (temporal, commerce, commerce-data, event-bus), not a defect; **Unknown** is a row Flux has never graded.

**120 objects: 23 ready, 95 not ready, 0 unknown, 2 suspended.**

## Not ready right now

- **HelmRelease commerce/lago** since 2026-09-25T01:20:15Z: Could not determine release state: unable to determine state for release with status 'uninstalling'
- **HelmRelease coroot/coroot** since 2026-09-25T20:59:35Z: Helm install failed for release coroot/coroot with chart coroot@0.22.0: create: failed to create: admission webhook "oke-resource-leak-protection.oke.com" denied the request: OKE resource leak protection rejected the request. Cluster has 2729 secrets and the limit is 2000. See https://docs.oracle.com/iaas/Content/ContEng/Tasks/contengprotectingclustersfromresourceleaks.htm for details.
- **HelmRelease crossplane-system/crossplane** since 2026-09-25T21:04:40Z: Helm upgrade failed for release crossplane-system/crossplane with chart crossplane@1.15.1: create: failed to create: admission webhook "oke-resource-leak-protection.oke.com" denied the request: OKE resource leak protection rejected the request. Cluster has 2778 secrets and the limit is 2000. See https://docs.oracle.com/iaas/Content/ContEng/Tasks/contengprotectingclustersfromresourceleaks.htm for details.
- **HelmRelease dagster/dagster** since 2026-09-25T21:04:44Z: Helm upgrade failed for release dagster/dagster with chart dagster@1.13.19: create: failed to create: admission webhook "oke-resource-leak-protection.oke.com" denied the request: OKE resource leak protection rejected the request. Cluster has 2778 secrets and the limit is 2000. See https://docs.oracle.com/iaas/Content/ContEng/Tasks/contengprotectingclustersfromresourceleaks.htm for details.
- **HelmRelease flux-system/vendor-bridge** since 2026-09-25T21:12:27Z: HelmChart 'flux-system/flux-system-vendor-bridge' is not ready: does not have an artifact
- **HelmRelease observability/langfuse** since 2026-09-25T10:40:26Z: dependency 'observability/signoz' is not ready
- **HelmRelease observability/signoz** since 2026-09-25T21:04:47Z: Helm upgrade failed for release observability/signoz with chart signoz@0.138.0: create: failed to create: admission webhook "oke-resource-leak-protection.oke.com" denied the request: OKE resource leak protection rejected the request. Cluster has 2778 secrets and the limit is 2000. See https://docs.oracle.com/iaas/Content/ContEng/Tasks/contengprotectingclustersfromresourceleaks.htm for details.
- **HelmRelease robusta/robusta** since 2026-09-25T21:15:09Z: Could not load chart: GET http://source-controller.flux-system.svc.cluster.local./helmchart/robusta/robusta-robusta/robusta-0.48.0.tgz giving up after 10 attempt(s): Get "http://source-controller.flux-system.svc.cluster.local./helmchart/robusta/robusta-robusta/robusta-0.48.0.tgz": dial tcp 10.96.202.29:80: connect: connection refused
- **HelmRelease spire-mgmt/spire** since 2026-09-25T20:57:45Z: Helm upgrade failed for release spire-mgmt/spire with chart spire@0.30.1: create: failed to create: admission webhook "oke-resource-leak-protection.oke.com" denied the request: OKE resource leak protection rejected the request. Cluster has 2729 secrets and the limit is 2000. See https://docs.oracle.com/iaas/Content/ContEng/Tasks/contengprotectingclustersfromresourceleaks.htm for details.
- **HelmRelease trivy-system/trivy-operator** since 2026-09-25T21:06:02Z: Helm upgrade failed for release trivy-system/trivy-operator with chart trivy-operator@0.36.0: create: failed to create: admission webhook "oke-resource-leak-protection.oke.com" denied the request: OKE resource leak protection rejected the request. Cluster has 2778 secrets and the limit is 2000. See https://docs.oracle.com/iaas/Content/ContEng/Tasks/contengprotectingclustersfromresourceleaks.htm for details.
- **Kustomization flux-system/acg** since 2026-09-25T21:14:54Z: Source artifact not found, retrying in 30s
- **Kustomization flux-system/agent-workforce** since 2026-09-25T21:14:54Z: Source artifact not found, retrying in 30s
- **Kustomization flux-system/alerts** since 2026-09-25T21:14:54Z: Source artifact not found, retrying in 30s
- **Kustomization flux-system/alerts-github** since 2026-09-25T21:14:54Z: Source artifact not found, retrying in 30s
- **Kustomization flux-system/alerts-secret** since 2026-09-25T21:14:54Z: Source artifact not found, retrying in 30s
- **Kustomization flux-system/autoscaler** since 2026-09-25T21:14:55Z: Source artifact not found, retrying in 30s
- **Kustomization flux-system/backstage** since 2026-09-25T21:14:55Z: Source artifact not found, retrying in 30s
- **Kustomization flux-system/backstage-namespace** since 2026-09-25T21:14:54Z: Source artifact not found, retrying in 30s
- **Kustomization flux-system/calico** since 2026-09-25T21:14:55Z: Source artifact not found, retrying in 30s
- **Kustomization flux-system/cluster-state** since 2026-09-25T21:14:55Z: Source artifact not found, retrying in 30s
- **Kustomization flux-system/commerce** since 2026-09-25T21:14:54Z: Source artifact not found, retrying in 30s
- **Kustomization flux-system/commerce-data** since 2026-09-25T21:14:55Z: Source artifact not found, retrying in 30s
- **Kustomization flux-system/concierge** since 2026-09-25T21:14:55Z: Source artifact not found, retrying in 30s
- **Kustomization flux-system/coroot** since 2026-09-25T21:14:54Z: Source artifact not found, retrying in 30s
- **Kustomization flux-system/crossplane** since 2026-09-25T21:14:55Z: Source artifact not found, retrying in 30s
- **Kustomization flux-system/crossplane-providerconfig** since 2026-09-25T21:14:55Z: Source artifact not found, retrying in 30s
- **Kustomization flux-system/crossplane-providers** since 2026-09-25T21:14:55Z: Source artifact not found, retrying in 30s
- **Kustomization flux-system/crossplane-storage-capability** since 2026-09-25T21:14:54Z: Source artifact not found, retrying in 30s
- **Kustomization flux-system/dagster** since 2026-09-25T21:14:54Z: Source artifact not found, retrying in 30s
- **Kustomization flux-system/dns** since 2026-09-25T21:14:55Z: Source artifact not found, retrying in 30s
- **Kustomization flux-system/edge** since 2026-09-25T21:14:54Z: Source artifact not found, retrying in 30s
- **Kustomization flux-system/epistemic-fabric** since 2026-09-25T21:14:55Z: Source artifact not found, retrying in 30s
- **Kustomization flux-system/estate-catalog** since 2026-09-25T21:12:14Z: Reconciliation in progress
- **Kustomization flux-system/estate-db** since 2026-09-25T21:14:54Z: Source artifact not found, retrying in 30s
- **Kustomization flux-system/estate-db-migrate** since 2026-09-25T21:14:54Z: Source artifact not found, retrying in 30s
- **Kustomization flux-system/estate-db-operator** since 2026-09-25T21:14:55Z: Source artifact not found, retrying in 30s
- **Kustomization flux-system/event-bus** since 2026-09-25T21:14:54Z: Source artifact not found, retrying in 30s
- **Kustomization flux-system/external-secrets** since 2026-09-25T21:14:55Z: Source artifact not found, retrying in 30s
- **Kustomization flux-system/feature-register** since 2026-09-25T21:14:55Z: Source artifact not found, retrying in 30s
- **Kustomization flux-system/flux-webhook** since 2026-09-25T21:14:54Z: Source artifact not found, retrying in 30s
- **Kustomization flux-system/gateway-api-crds** since 2026-09-25T21:11:57Z: Reconciliation in progress
- **Kustomization flux-system/github-app-creds** since 2026-09-25T21:14:55Z: Source artifact not found, retrying in 30s
- **Kustomization flux-system/guacamole** since 2026-09-25T21:14:54Z: Source artifact not found, retrying in 30s
- **Kustomization flux-system/gvisor-runtime** since 2026-09-25T21:14:54Z: Source artifact not found, retrying in 30s
- **Kustomization flux-system/healing** since 2026-09-25T21:14:55Z: Source artifact not found, retrying in 30s
- **Kustomization flux-system/healing-analyzer** since 2026-09-25T21:14:55Z: Source artifact not found, retrying in 30s
- **Kustomization flux-system/healing-k8sgpt** since 2026-09-25T21:14:54Z: Source artifact not found, retrying in 30s
- **Kustomization flux-system/healthchecks** since 2026-09-25T21:14:55Z: Source artifact not found, retrying in 30s
- **Kustomization flux-system/hermes-agent** since 2026-09-25T21:14:54Z: Source artifact not found, retrying in 30s
- **Kustomization flux-system/hindsight** since 2026-09-25T21:14:55Z: Source artifact not found, retrying in 30s
- **Kustomization flux-system/human-vault** since 2026-09-25T21:14:54Z: Source artifact not found, retrying in 30s
- **Kustomization flux-system/human-vault-bridge** since 2026-09-25T21:14:54Z: Source artifact not found, retrying in 30s
- **Kustomization flux-system/identity** since 2026-09-25T21:14:54Z: Source artifact not found, retrying in 30s
- **Kustomization flux-system/idp-agent** since 2026-09-25T21:14:54Z: Source artifact not found, retrying in 30s
- **Kustomization flux-system/image-automation** since 2026-09-25T21:14:55Z: Source artifact not found, retrying in 30s
- **Kustomization flux-system/jit** since 2026-09-25T21:14:54Z: Source artifact not found, retrying in 30s
- **Kustomization flux-system/keda** since 2026-09-25T21:14:55Z: Source artifact not found, retrying in 30s
- **Kustomization flux-system/kyverno** since 2026-09-25T21:14:54Z: Source artifact not found, retrying in 30s
- **Kustomization flux-system/llm** since 2026-09-25T21:14:54Z: Source artifact not found, retrying in 30s
- **Kustomization flux-system/mcp** since 2026-09-25T21:14:55Z: Source artifact not found, retrying in 30s
- **Kustomization flux-system/metrics-server** since 2026-09-25T21:14:55Z: Source artifact not found, retrying in 30s
- **Kustomization flux-system/monitoring** since 2026-09-25T21:14:55Z: Source artifact not found, retrying in 30s
- **Kustomization flux-system/monitoring-rules** since 2026-09-25T21:14:54Z: Source artifact not found, retrying in 30s
- **Kustomization flux-system/nodesoftware-operator** since 2026-09-25T21:14:54Z: Source artifact not found, retrying in 30s
- **Kustomization flux-system/notify** since 2026-09-25T21:14:55Z: Source artifact not found, retrying in 30s
- **Kustomization flux-system/ns-fences** since 2026-09-25T21:14:54Z: Source artifact not found, retrying in 30s
- **Kustomization flux-system/observability** since 2026-09-25T21:14:54Z: Source artifact not found, retrying in 30s
- **Kustomization flux-system/observability-collector** since 2026-09-25T21:14:54Z: Source artifact not found, retrying in 30s
- **Kustomization flux-system/otto-gateway** since 2026-09-25T21:14:54Z: Source artifact not found, retrying in 30s
- **Kustomization flux-system/otto-golden** since 2026-09-25T21:14:55Z: Source artifact not found, retrying in 30s
- **Kustomization flux-system/otto-golden-secret** since 2026-09-25T21:14:55Z: Source artifact not found, retrying in 30s
- **Kustomization flux-system/priority-classes** since 2026-09-25T21:14:55Z: Source artifact not found, retrying in 30s
- **Kustomization flux-system/prospector** since 2026-09-25T21:10:48Z: dependency 'flux-system/prospector-platform' is not ready
- **Kustomization flux-system/prospector-platform** since 2026-09-25T21:14:55Z: Source artifact not found, retrying in 30s
- **Kustomization flux-system/rbac** since 2026-09-25T21:14:54Z: Source artifact not found, retrying in 30s
- **Kustomization flux-system/rbac-floor** since 2026-09-25T21:14:54Z: Source artifact not found, retrying in 30s
- **Kustomization flux-system/rbac-identity** since 2026-09-25T21:14:55Z: Source artifact not found, retrying in 30s
- **Kustomization flux-system/reloader** since 2026-09-25T21:14:54Z: Source artifact not found, retrying in 30s
- **Kustomization flux-system/research-engine** since 2026-09-25T21:14:55Z: Source artifact not found, retrying in 30s
- **Kustomization flux-system/robusta** since 2026-09-25T21:14:55Z: Source artifact not found, retrying in 30s
- **Kustomization flux-system/router-events** since 2026-09-25T21:14:55Z: Source artifact not found, retrying in 30s
- **Kustomization flux-system/sandbox-launch** since 2026-09-25T21:14:54Z: Source artifact not found, retrying in 30s
- **Kustomization flux-system/sandbox-live** since 2026-09-25T21:14:54Z: Source artifact not found, retrying in 30s
- **Kustomization flux-system/scheduling** since 2026-09-25T21:14:54Z: Source artifact not found, retrying in 30s
- **Kustomization flux-system/science** since 2026-09-25T21:14:54Z: Source artifact not found, retrying in 30s
- **Kustomization flux-system/searxng** since 2026-09-25T21:14:55Z: Source artifact not found, retrying in 30s
- **Kustomization flux-system/secret-store** since 2026-09-25T21:14:54Z: Source artifact not found, retrying in 30s
- **Kustomization flux-system/spire** since 2026-09-25T21:14:54Z: Source artifact not found, retrying in 30s
- **Kustomization flux-system/staging** since 2026-09-25T21:14:55Z: Source artifact not found, retrying in 30s
- **Kustomization flux-system/tailscale** since 2026-09-25T21:14:54Z: Source artifact not found, retrying in 30s
- **Kustomization flux-system/temporal** since 2026-09-25T21:14:54Z: Source artifact not found, retrying in 30s
- **Kustomization flux-system/trivy** since 2026-09-25T21:14:54Z: Source artifact not found, retrying in 30s
- **Kustomization flux-system/verification** since 2026-09-25T21:14:55Z: Source artifact not found, retrying in 30s
- **Kustomization flux-system/via-negativa** since 2026-09-25T21:14:54Z: Source artifact not found, retrying in 30s
- **Kustomization flux-system/weave-gitops** since 2026-09-25T21:14:55Z: Source artifact not found, retrying in 30s

## Every row

| Kind | Namespace | Name | State | Applied revision | Since | Message |
|---|---|---|---|---|---|---|
| HelmRelease | commerce | lago | Not ready | 1.28.0 | 2026-09-25T01:20:15Z | Could not determine release state: unable to determine state for release with status 'uninstalling' |
| HelmRelease | coroot | coroot | Not ready | 0.22.0 | 2026-09-25T20:59:35Z | Helm install failed for release coroot/coroot with chart coroot@0.22.0: create: failed to create: admission webhook "oke-resource-leak-protection.oke.com" denie |
| HelmRelease | crossplane-system | crossplane | Not ready | 1.15.1 | 2026-09-25T21:04:40Z | Helm upgrade failed for release crossplane-system/crossplane with chart crossplane@1.15.1: create: failed to create: admission webhook "oke-resource-leak-protec |
| HelmRelease | dagster | dagster | Not ready | 1.13.19 | 2026-09-25T21:04:44Z | Helm upgrade failed for release dagster/dagster with chart dagster@1.13.19: create: failed to create: admission webhook "oke-resource-leak-protection.oke.com" d |
| HelmRelease | flux-system | vendor-bridge | Not ready | 0.1.0+339ce2d2f194 | 2026-09-25T21:12:27Z | HelmChart 'flux-system/flux-system-vendor-bridge' is not ready: does not have an artifact |
| HelmRelease | observability | langfuse | Not ready | 2.0.2 | 2026-09-25T10:40:26Z | dependency 'observability/signoz' is not ready |
| HelmRelease | observability | signoz | Not ready | 0.138.0 | 2026-09-25T21:04:47Z | Helm upgrade failed for release observability/signoz with chart signoz@0.138.0: create: failed to create: admission webhook "oke-resource-leak-protection.oke.co |
| HelmRelease | robusta | robusta | Not ready | 0.48.0 | 2026-09-25T21:15:09Z | Could not load chart: GET http://source-controller.flux-system.svc.cluster.local./helmchart/robusta/robusta-robusta/robusta-0.48.0.tgz giving up after 10 attemp |
| HelmRelease | spire-mgmt | spire | Not ready | 0.30.1 | 2026-09-25T20:57:45Z | Helm upgrade failed for release spire-mgmt/spire with chart spire@0.30.1: create: failed to create: admission webhook "oke-resource-leak-protection.oke.com" den |
| HelmRelease | trivy-system | trivy-operator | Not ready | 0.36.0 | 2026-09-25T21:06:02Z | Helm upgrade failed for release trivy-system/trivy-operator with chart trivy-operator@0.36.0: create: failed to create: admission webhook "oke-resource-leak-pro |
| Kustomization | flux-system | acg | Not ready | main@0b33777 | 2026-09-25T21:14:54Z | Source artifact not found, retrying in 30s |
| Kustomization | flux-system | agent-workforce | Not ready | main@689bcd9 | 2026-09-25T21:14:54Z | Source artifact not found, retrying in 30s |
| Kustomization | flux-system | alerts | Not ready | main@0b33777 | 2026-09-25T21:14:54Z | Source artifact not found, retrying in 30s |
| Kustomization | flux-system | alerts-github | Not ready | main@0b33777 | 2026-09-25T21:14:54Z | Source artifact not found, retrying in 30s |
| Kustomization | flux-system | alerts-secret | Not ready | main@0b33777 | 2026-09-25T21:14:54Z | Source artifact not found, retrying in 30s |
| Kustomization | flux-system | autoscaler | Not ready | main@0b33777 | 2026-09-25T21:14:55Z | Source artifact not found, retrying in 30s |
| Kustomization | flux-system | backstage | Not ready | main@689bcd9 | 2026-09-25T21:14:55Z | Source artifact not found, retrying in 30s |
| Kustomization | flux-system | backstage-namespace | Not ready | main@cca4450 | 2026-09-25T21:14:54Z | Source artifact not found, retrying in 30s |
| Kustomization | flux-system | calico | Not ready | main@cca4450 | 2026-09-25T21:14:55Z | Source artifact not found, retrying in 30s |
| Kustomization | flux-system | cluster-state | Not ready | main@0b33777 | 2026-09-25T21:14:55Z | Source artifact not found, retrying in 30s |
| Kustomization | flux-system | commerce | Not ready | main@abea14d | 2026-09-25T21:14:54Z | Source artifact not found, retrying in 30s |
| Kustomization | flux-system | commerce-data | Not ready | main@0b33777 | 2026-09-25T21:14:55Z | Source artifact not found, retrying in 30s |
| Kustomization | flux-system | concierge | Not ready | main@0b33777 | 2026-09-25T21:14:55Z | Source artifact not found, retrying in 30s |
| Kustomization | flux-system | coroot | Not ready | main@0b33777 | 2026-09-25T21:14:54Z | Source artifact not found, retrying in 30s |
| Kustomization | flux-system | crossplane | Not ready | main@8d685ec | 2026-09-25T21:14:55Z | Source artifact not found, retrying in 30s |
| Kustomization | flux-system | crossplane-providerconfig | Not ready | main@8d685ec | 2026-09-25T21:14:55Z | Source artifact not found, retrying in 30s |
| Kustomization | flux-system | crossplane-providers | Not ready | main@8d685ec | 2026-09-25T21:14:55Z | Source artifact not found, retrying in 30s |
| Kustomization | flux-system | crossplane-storage-capability | Not ready | main@8d685ec | 2026-09-25T21:14:54Z | Source artifact not found, retrying in 30s |
| Kustomization | flux-system | dagster | Not ready | main@08aa502 | 2026-09-25T21:14:54Z | Source artifact not found, retrying in 30s |
| Kustomization | flux-system | dns | Not ready | main@0b33777 | 2026-09-25T21:14:55Z | Source artifact not found, retrying in 30s |
| Kustomization | flux-system | edge | Not ready | main@e1f7b06 | 2026-09-25T21:14:54Z | Source artifact not found, retrying in 30s |
| Kustomization | flux-system | epistemic-fabric | Not ready | main@0b33777 | 2026-09-25T21:14:55Z | Source artifact not found, retrying in 30s |
| Kustomization | flux-system | estate-catalog | Not ready | latest@sha256:e794b2a02a783228ae858acd84 | 2026-09-25T21:12:14Z | Reconciliation in progress |
| Kustomization | flux-system | estate-db | Not ready | main@0b33777 | 2026-09-25T21:14:54Z | Source artifact not found, retrying in 30s |
| Kustomization | flux-system | estate-db-migrate | Not ready | main@0b33777 | 2026-09-25T21:14:54Z | Source artifact not found, retrying in 30s |
| Kustomization | flux-system | estate-db-operator | Not ready | main@cca4450 | 2026-09-25T21:14:55Z | Source artifact not found, retrying in 30s |
| Kustomization | flux-system | event-bus | Not ready | main@e1f7b06 | 2026-09-25T21:14:54Z | Source artifact not found, retrying in 30s |
| Kustomization | flux-system | external-secrets | Not ready | main@0b33777 | 2026-09-25T21:14:55Z | Source artifact not found, retrying in 30s |
| Kustomization | flux-system | feature-register | Not ready | main@2518219 | 2026-09-25T21:14:55Z | Source artifact not found, retrying in 30s |
| Kustomization | flux-system | flux-webhook | Not ready | main@0b33777 | 2026-09-25T21:14:54Z | Source artifact not found, retrying in 30s |
| Kustomization | flux-system | gateway-api-crds | Not ready | v1.5.1@e7677b7 | 2026-09-25T21:11:57Z | Reconciliation in progress |
| Kustomization | flux-system | github-app-creds | Not ready | main@0b33777 | 2026-09-25T21:14:55Z | Source artifact not found, retrying in 30s |
| Kustomization | flux-system | guacamole | Not ready | main@0b33777 | 2026-09-25T21:14:54Z | Source artifact not found, retrying in 30s |
| Kustomization | flux-system | gvisor-runtime | Not ready | main@0b33777 | 2026-09-25T21:14:54Z | Source artifact not found, retrying in 30s |
| Kustomization | flux-system | healing | Not ready | main@0b33777 | 2026-09-25T21:14:55Z | Source artifact not found, retrying in 30s |
| Kustomization | flux-system | healing-analyzer | Not ready | main@689bcd9 | 2026-09-25T21:14:55Z | Source artifact not found, retrying in 30s |
| Kustomization | flux-system | healing-k8sgpt | Not ready | main@689bcd9 | 2026-09-25T21:14:54Z | Source artifact not found, retrying in 30s |
| Kustomization | flux-system | healthchecks | Not ready | main@0b33777 | 2026-09-25T21:14:55Z | Source artifact not found, retrying in 30s |
| Kustomization | flux-system | hermes-agent | Not ready | main@0df0a74 | 2026-09-25T21:14:54Z | Source artifact not found, retrying in 30s |
| Kustomization | flux-system | hindsight | Not ready | main@689bcd9 | 2026-09-25T21:14:55Z | Source artifact not found, retrying in 30s |
| Kustomization | flux-system | human-vault | Not ready | main@0b33777 | 2026-09-25T21:14:54Z | Source artifact not found, retrying in 30s |
| Kustomization | flux-system | human-vault-bridge | Not ready | main@0b33777 | 2026-09-25T21:14:54Z | Source artifact not found, retrying in 30s |
| Kustomization | flux-system | identity | Not ready | main@0b33777 | 2026-09-25T21:14:54Z | Source artifact not found, retrying in 30s |
| Kustomization | flux-system | idp-agent | Not ready | main@0b33777 | 2026-09-25T21:14:54Z | Source artifact not found, retrying in 30s |
| Kustomization | flux-system | image-automation | Not ready | main@0b33777 | 2026-09-25T21:14:55Z | Source artifact not found, retrying in 30s |
| Kustomization | flux-system | jit | Not ready | main@689bcd9 | 2026-09-25T21:14:54Z | Source artifact not found, retrying in 30s |
| Kustomization | flux-system | keda | Not ready | main@0b33777 | 2026-09-25T21:14:55Z | Source artifact not found, retrying in 30s |
| Kustomization | flux-system | kyverno | Not ready | main@cca4450 | 2026-09-25T21:14:54Z | Source artifact not found, retrying in 30s |
| Kustomization | flux-system | llm | Not ready | main@689bcd9 | 2026-09-25T21:14:54Z | Source artifact not found, retrying in 30s |
| Kustomization | flux-system | mcp | Not ready | main@689bcd9 | 2026-09-25T21:14:55Z | Source artifact not found, retrying in 30s |
| Kustomization | flux-system | metrics-server | Not ready | main@0b33777 | 2026-09-25T21:14:55Z | Source artifact not found, retrying in 30s |
| Kustomization | flux-system | monitoring | Not ready | main@0b33777 | 2026-09-25T21:14:55Z | Source artifact not found, retrying in 30s |
| Kustomization | flux-system | monitoring-rules | Not ready | main@0b33777 | 2026-09-25T21:14:54Z | Source artifact not found, retrying in 30s |
| Kustomization | flux-system | nodesoftware-operator | Not ready | main@0b33777 | 2026-09-25T21:14:54Z | Source artifact not found, retrying in 30s |
| Kustomization | flux-system | notify | Not ready | main@0b33777 | 2026-09-25T21:14:55Z | Source artifact not found, retrying in 30s |
| Kustomization | flux-system | ns-fences | Not ready | main@cca4450 | 2026-09-25T21:14:54Z | Source artifact not found, retrying in 30s |
| Kustomization | flux-system | observability | Not ready | main@0b33777 | 2026-09-25T21:14:54Z | Source artifact not found, retrying in 30s |
| Kustomization | flux-system | observability-collector | Not ready | main@0b33777 | 2026-09-25T21:14:54Z | Source artifact not found, retrying in 30s |
| Kustomization | flux-system | otto-gateway | Not ready | main@cd9eb71 | 2026-09-25T21:14:54Z | Source artifact not found, retrying in 30s |
| Kustomization | flux-system | otto-golden | Not ready | main@cd9eb71 | 2026-09-25T21:14:55Z | Source artifact not found, retrying in 30s |
| Kustomization | flux-system | otto-golden-secret | Not ready | main@0b33777 | 2026-09-25T21:14:55Z | Source artifact not found, retrying in 30s |
| Kustomization | flux-system | priority-classes | Not ready | main@cca4450 | 2026-09-25T21:14:55Z | Source artifact not found, retrying in 30s |
| Kustomization | flux-system | prospector | Not ready | main@7453d76 | 2026-09-25T21:10:48Z | dependency 'flux-system/prospector-platform' is not ready |
| Kustomization | flux-system | prospector-platform | Not ready | main@0b33777 | 2026-09-25T21:14:55Z | Source artifact not found, retrying in 30s |
| Kustomization | flux-system | rbac | Not ready | main@3ed6bfa | 2026-09-25T21:14:54Z | Source artifact not found, retrying in 30s |
| Kustomization | flux-system | rbac-floor | Not ready | main@cca4450 | 2026-09-25T21:14:54Z | Source artifact not found, retrying in 30s |
| Kustomization | flux-system | rbac-identity | Not ready | main@2518219 | 2026-09-25T21:14:55Z | Source artifact not found, retrying in 30s |
| Kustomization | flux-system | reloader | Not ready | main@0b33777 | 2026-09-25T21:14:54Z | Source artifact not found, retrying in 30s |
| Kustomization | flux-system | research-engine | Not ready | main@689bcd9 | 2026-09-25T21:14:55Z | Source artifact not found, retrying in 30s |
| Kustomization | flux-system | robusta | Not ready | main@41e996d | 2026-09-25T21:14:55Z | Source artifact not found, retrying in 30s |
| Kustomization | flux-system | router-events | Not ready | main@689bcd9 | 2026-09-25T21:14:55Z | Source artifact not found, retrying in 30s |
| Kustomization | flux-system | sandbox-launch | Not ready | main@ac2a1b1 | 2026-09-25T21:14:54Z | Source artifact not found, retrying in 30s |
| Kustomization | flux-system | sandbox-live | Not ready | sandbox/launch@4830a6e | 2026-09-25T21:14:54Z | Source artifact not found, retrying in 30s |
| Kustomization | flux-system | scheduling | Not ready | main@0b33777 | 2026-09-25T21:14:54Z | Source artifact not found, retrying in 30s |
| Kustomization | flux-system | science | Not ready | main@0b33777 | 2026-09-25T21:14:54Z | Source artifact not found, retrying in 30s |
| Kustomization | flux-system | searxng | Not ready | main@cca4450 | 2026-09-25T21:14:55Z | Source artifact not found, retrying in 30s |
| Kustomization | flux-system | secret-store | Not ready | main@0b33777 | 2026-09-25T21:14:54Z | Source artifact not found, retrying in 30s |
| Kustomization | flux-system | spire | Not ready | main@0b33777 | 2026-09-25T21:14:54Z | Source artifact not found, retrying in 30s |
| Kustomization | flux-system | staging | Not ready | main@cca4450 | 2026-09-25T21:14:55Z | Source artifact not found, retrying in 30s |
| Kustomization | flux-system | tailscale | Not ready | main@0b33777 | 2026-09-25T21:14:54Z | Source artifact not found, retrying in 30s |
| Kustomization | flux-system | temporal | Not ready | main@41e996d | 2026-09-25T21:14:54Z | Source artifact not found, retrying in 30s |
| Kustomization | flux-system | trivy | Not ready | main@689bcd9 | 2026-09-25T21:14:54Z | Source artifact not found, retrying in 30s |
| Kustomization | flux-system | verification | Not ready | main@0b33777 | 2026-09-25T21:14:55Z | Source artifact not found, retrying in 30s |
| Kustomization | flux-system | via-negativa | Not ready | main@689bcd9 | 2026-09-25T21:14:54Z | Source artifact not found, retrying in 30s |
| Kustomization | flux-system | weave-gitops | Not ready | main@0b33777 | 2026-09-25T21:14:55Z | Source artifact not found, retrying in 30s |
| HelmRelease | tigera-operator | tigera-operator | Suspended | v3.32.2 | 2026-09-06T19:38:02Z |  |
| Kustomization | flux-system | flux-system | Suspended | main@cca4450 | 2026-09-25T21:12:37Z |  |
| HelmRelease | cert-manager | cert-manager | Ready | v1.21.1 | 2026-09-25T21:09:39Z |  |
| HelmRelease | edge | external-dns | Ready | 1.21.1 | 2026-09-25T01:23:11Z |  |
| HelmRelease | edge | traefik | Ready | 41.3.0 | 2026-09-25T21:09:40Z |  |
| HelmRelease | estate-db | cloudnative-pg | Ready | 0.29.0 | 2026-09-25T21:09:40Z |  |
| HelmRelease | event-bus | nats | Ready | 2.14.6 | 2026-09-25T01:16:29Z |  |
| HelmRelease | external-secrets | external-secrets | Ready | 2.9.0 | 2026-09-25T19:42:56Z |  |
| HelmRelease | healing | descheduler | Ready | 0.36.0 | 2026-09-25T21:09:40Z |  |
| HelmRelease | healing | k8sgpt-operator | Ready | 0.2.29 | 2026-09-08T12:01:53Z |  |
| HelmRelease | hindsight | hindsight | Ready | 0.9.2 | 2026-09-25T01:16:31Z |  |
| HelmRelease | identity | oauth2-proxy | Ready | 10.7.0 | 2026-09-25T01:16:35Z |  |
| HelmRelease | keda | keda | Ready | 2.20.2 | 2026-09-25T01:16:41Z |  |
| HelmRelease | keda | keda-add-ons-http | Ready | 0.15.0 | 2026-09-25T21:09:40Z |  |
| HelmRelease | kyverno | kyverno | Ready | 3.9.0 | 2026-09-25T19:42:55Z |  |
| HelmRelease | metrics-server | metrics-server | Ready | 3.14.0 | 2026-09-25T01:18:55Z |  |
| HelmRelease | monitoring | blackbox | Ready | 11.17.2 | 2026-09-25T21:09:46Z |  |
| HelmRelease | monitoring | kube-prometheus-stack | Ready | 88.6.0 | 2026-09-25T01:22:46Z |  |
| HelmRelease | observability | superset | Ready | 0.22.4 | 2026-09-25T01:16:30Z |  |
| HelmRelease | observability-agent | k8s-infra | Ready | 0.17.0 | 2026-09-25T01:27:26Z |  |
| HelmRelease | reloader | reloader | Ready | 2.2.16 | 2026-09-25T01:18:00Z |  |
| HelmRelease | spire-mgmt | spire-crds | Ready | 0.6.1 | 2026-09-25T01:28:36Z |  |
| HelmRelease | tailscale | tailscale-operator | Ready | 1.102.3 | 2026-09-25T21:09:40Z |  |
| HelmRelease | temporal | temporal | Ready | 1.6.0 | 2026-09-25T01:16:37Z |  |
| HelmRelease | weave-gitops | weave-gitops | Ready | 4.0.36 | 2026-09-25T01:16:51Z |  |
