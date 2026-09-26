# Flux: what is applied

Read from the cluster receipt taken at 2026-09-26T12:30:10Z. Every Kustomization and HelmRelease, with the revision Flux last applied. **Suspended** is a switch somebody turned off on purpose (temporal, commerce, commerce-data, event-bus), not a defect; **Unknown** is a row Flux has never graded.

**35 objects: 22 ready, 12 not ready, 0 unknown, 1 suspended.**

## Not ready right now

- **HelmRelease commerce/lago** since 2026-09-26T09:48:22Z: Could not determine release state: unable to determine state for release with status 'uninstalling'
- **HelmRelease coroot/coroot** since 2026-09-26T12:23:36Z: Helm install failed for release coroot/coroot with chart coroot@0.22.0: create: failed to create: admission webhook "oke-resource-leak-protection.oke.com" denied the request: OKE resource leak protection rejected the request. Cluster has 2778 secrets and the limit is 2000. See https://docs.oracle.com/iaas/Content/ContEng/Tasks/contengprotectingclustersfromresourceleaks.htm for details.
- **HelmRelease crossplane-system/crossplane** since 2026-09-26T12:24:02Z: Helm upgrade failed for release crossplane-system/crossplane with chart crossplane@1.15.1: create: failed to create: admission webhook "oke-resource-leak-protection.oke.com" denied the request: OKE resource leak protection rejected the request. Cluster has 2778 secrets and the limit is 2000. See https://docs.oracle.com/iaas/Content/ContEng/Tasks/contengprotectingclustersfromresourceleaks.htm for details.
- **HelmRelease dagster/dagster** since 2026-09-26T12:23:38Z: Helm upgrade failed for release dagster/dagster with chart dagster@1.13.19: create: failed to create: admission webhook "oke-resource-leak-protection.oke.com" denied the request: OKE resource leak protection rejected the request. Cluster has 2778 secrets and the limit is 2000. See https://docs.oracle.com/iaas/Content/ContEng/Tasks/contengprotectingclustersfromresourceleaks.htm for details.
- **HelmRelease flux-system/vendor-bridge** since 2026-09-26T12:24:15Z: Helm install failed for release flux-system/vendor-bridge with chart vendor-bridge@0.1.0+6e2f8fa915ad: create: failed to create: admission webhook "oke-resource-leak-protection.oke.com" denied the request: OKE resource leak protection rejected the request. Cluster has 2778 secrets and the limit is 2000. See https://docs.oracle.com/iaas/Content/ContEng/Tasks/contengprotectingclustersfromresourceleaks.htm for details.
- **HelmRelease observability/langfuse** since 2026-09-25T10:40:26Z: dependency 'observability/signoz' is not ready
- **HelmRelease observability/signoz** since 2026-09-26T12:23:45Z: Helm upgrade failed for release observability/signoz with chart signoz@0.138.0: create: failed to create: admission webhook "oke-resource-leak-protection.oke.com" denied the request: OKE resource leak protection rejected the request. Cluster has 2778 secrets and the limit is 2000. See https://docs.oracle.com/iaas/Content/ContEng/Tasks/contengprotectingclustersfromresourceleaks.htm for details.
- **HelmRelease spire-mgmt/spire** since 2026-09-26T12:23:41Z: Helm upgrade failed for release spire-mgmt/spire with chart spire@0.30.1: create: failed to create: admission webhook "oke-resource-leak-protection.oke.com" denied the request: OKE resource leak protection rejected the request. Cluster has 2778 secrets and the limit is 2000. See https://docs.oracle.com/iaas/Content/ContEng/Tasks/contengprotectingclustersfromresourceleaks.htm for details.
- **HelmRelease trivy-system/trivy-operator** since 2026-09-26T12:23:40Z: Helm install failed for release trivy-system/trivy-operator with chart trivy-operator@0.36.0: create: failed to create: admission webhook "oke-resource-leak-protection.oke.com" denied the request: OKE resource leak protection rejected the request. Cluster has 2778 secrets and the limit is 2000. See https://docs.oracle.com/iaas/Content/ContEng/Tasks/contengprotectingclustersfromresourceleaks.htm for details.
- **Kustomization flux-system/dns** since 2026-09-26T12:20:13Z: dependency 'flux-system/edge' not found: kustomizations.kustomize.toolkit.fluxcd.io "edge" not found
- **Kustomization flux-system/flux-system** since 2026-09-26T12:29:43Z: ExternalSecret/flux-system/flux-telegram dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-secrets.io": failed to call webhook: Post "https://external-secrets-webhook.external-secrets.svc:443/validate-external-secrets-io-v1-externalsecret?timeout=15s": EOF 
- **Kustomization flux-system/monitoring** since 2026-09-26T12:20:13Z: dependency 'flux-system/edge' not found: kustomizations.kustomize.toolkit.fluxcd.io "edge" not found

## Every row

| Kind | Namespace | Name | State | Applied revision | Since | Message |
|---|---|---|---|---|---|---|
| HelmRelease | commerce | lago | Not ready | 1.28.0 | 2026-09-26T09:48:22Z | Could not determine release state: unable to determine state for release with status 'uninstalling' |
| HelmRelease | coroot | coroot | Not ready | 0.22.0 | 2026-09-26T12:23:36Z | Helm install failed for release coroot/coroot with chart coroot@0.22.0: create: failed to create: admission webhook "oke-resource-leak-protection.oke.com" denie |
| HelmRelease | crossplane-system | crossplane | Not ready | 1.15.1 | 2026-09-26T12:24:02Z | Helm upgrade failed for release crossplane-system/crossplane with chart crossplane@1.15.1: create: failed to create: admission webhook "oke-resource-leak-protec |
| HelmRelease | dagster | dagster | Not ready | 1.13.19 | 2026-09-26T12:23:38Z | Helm upgrade failed for release dagster/dagster with chart dagster@1.13.19: create: failed to create: admission webhook "oke-resource-leak-protection.oke.com" d |
| HelmRelease | flux-system | vendor-bridge | Not ready | 0.1.0+6e2f8fa915ad | 2026-09-26T12:24:15Z | Helm install failed for release flux-system/vendor-bridge with chart vendor-bridge@0.1.0+6e2f8fa915ad: create: failed to create: admission webhook "oke-resource |
| HelmRelease | observability | langfuse | Not ready | 2.0.2 | 2026-09-25T10:40:26Z | dependency 'observability/signoz' is not ready |
| HelmRelease | observability | signoz | Not ready | 0.138.0 | 2026-09-26T12:23:45Z | Helm upgrade failed for release observability/signoz with chart signoz@0.138.0: create: failed to create: admission webhook "oke-resource-leak-protection.oke.co |
| HelmRelease | spire-mgmt | spire | Not ready | 0.30.1 | 2026-09-26T12:23:41Z | Helm upgrade failed for release spire-mgmt/spire with chart spire@0.30.1: create: failed to create: admission webhook "oke-resource-leak-protection.oke.com" den |
| HelmRelease | trivy-system | trivy-operator | Not ready | 0.36.0 | 2026-09-26T12:23:40Z | Helm install failed for release trivy-system/trivy-operator with chart trivy-operator@0.36.0: create: failed to create: admission webhook "oke-resource-leak-pro |
| Kustomization | flux-system | dns | Not ready | main@0b33777 | 2026-09-26T12:20:13Z | dependency 'flux-system/edge' not found: kustomizations.kustomize.toolkit.fluxcd.io "edge" not found |
| Kustomization | flux-system | flux-system | Not ready | main@eca1b80 | 2026-09-26T12:29:43Z | ExternalSecret/flux-system/flux-telegram dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-secre |
| Kustomization | flux-system | monitoring | Not ready | main@0b33777 | 2026-09-26T12:20:13Z | dependency 'flux-system/edge' not found: kustomizations.kustomize.toolkit.fluxcd.io "edge" not found |
| HelmRelease | tigera-operator | tigera-operator | Suspended | v3.32.2 | 2026-09-06T19:38:02Z |  |
| HelmRelease | cert-manager | cert-manager | Ready | v1.21.1 | 2026-09-26T10:39:03Z |  |
| HelmRelease | edge | external-dns | Ready | 1.21.1 | 2026-09-26T10:39:02Z |  |
| HelmRelease | edge | traefik | Ready | 41.3.0 | 2026-09-26T09:48:30Z |  |
| HelmRelease | estate-db | cloudnative-pg | Ready | 0.29.0 | 2026-09-26T10:01:26Z |  |
| HelmRelease | event-bus | nats | Ready | 2.14.6 | 2026-09-26T09:48:21Z |  |
| HelmRelease | external-secrets | external-secrets | Ready | 2.9.0 | 2026-09-26T09:48:27Z |  |
| HelmRelease | healing | descheduler | Ready | 0.36.0 | 2026-09-26T09:48:21Z |  |
| HelmRelease | healing | k8sgpt-operator | Ready | 0.2.29 | 2026-09-26T09:48:26Z |  |
| HelmRelease | hindsight | hindsight | Ready | 0.9.2 | 2026-09-26T09:48:29Z |  |
| HelmRelease | identity | oauth2-proxy | Ready | 10.7.0 | 2026-09-26T10:01:26Z |  |
| HelmRelease | keda | keda | Ready | 2.20.2 | 2026-09-26T10:39:03Z |  |
| HelmRelease | keda | keda-add-ons-http | Ready | 0.15.0 | 2026-09-26T10:39:31Z |  |
| HelmRelease | kyverno | kyverno | Ready | 3.9.0 | 2026-09-26T10:01:28Z |  |
| HelmRelease | metrics-server | metrics-server | Ready | 3.14.0 | 2026-09-26T09:48:29Z |  |
| HelmRelease | monitoring | blackbox | Ready | 11.17.2 | 2026-09-26T11:01:14Z |  |
| HelmRelease | monitoring | kube-prometheus-stack | Ready | 88.6.0 | 2026-09-26T10:01:27Z |  |
| HelmRelease | observability | superset | Ready | 0.22.4 | 2026-09-26T10:39:02Z |  |
| HelmRelease | spire-mgmt | spire-crds | Ready | 0.6.1 | 2026-09-26T09:48:25Z |  |
| HelmRelease | tailscale | tailscale-operator | Ready | 1.102.3 | 2026-09-26T09:48:27Z |  |
| HelmRelease | temporal | temporal | Ready | 1.6.0 | 2026-09-26T10:39:02Z |  |
| HelmRelease | weave-gitops | weave-gitops | Ready | 4.0.36 | 2026-09-26T09:48:27Z |  |
| Kustomization | flux-system | kyverno | Ready | main@6e2f8fa | 2026-09-26T12:29:57Z |  |
