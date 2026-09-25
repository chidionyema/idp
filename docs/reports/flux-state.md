# Flux: what is applied

Read from the cluster receipt taken at 2026-09-25T12:30:53Z. Every Kustomization and HelmRelease, with the revision Flux last applied. **Suspended** is a switch somebody turned off on purpose (temporal, commerce, commerce-data, event-bus), not a defect; **Unknown** is a row Flux has never graded.

**120 objects: 77 ready, 42 not ready, 0 unknown, 1 suspended.**

## Not ready right now

- **HelmRelease commerce/lago** since 2026-09-25T01:20:15Z: Could not determine release state: unable to determine state for release with status 'uninstalling'
- **HelmRelease coroot/coroot** since 2026-09-25T12:28:24Z: Helm install failed for release coroot/coroot with chart coroot@0.22.0: create: failed to create: admission webhook "oke-resource-leak-protection.oke.com" denied the request: OKE resource leak protection rejected the request. Cluster has 2729 secrets and the limit is 2000. See https://docs.oracle.com/iaas/Content/ContEng/Tasks/contengprotectingclustersfromresourceleaks.htm for details.
- **HelmRelease crossplane-system/crossplane** since 2026-09-25T12:17:36Z: Helm upgrade failed for release crossplane-system/crossplane with chart crossplane@1.15.1: create: failed to create: admission webhook "oke-resource-leak-protection.oke.com" denied the request: OKE resource leak protection rejected the request. Cluster has 2778 secrets and the limit is 2000. See https://docs.oracle.com/iaas/Content/ContEng/Tasks/contengprotectingclustersfromresourceleaks.htm for details.
- **HelmRelease dagster/dagster** since 2026-09-25T12:30:33Z: Helm upgrade failed for release dagster/dagster with chart dagster@1.13.19: create: failed to create: admission webhook "oke-resource-leak-protection.oke.com" denied the request: OKE resource leak protection rejected the request. Cluster has 2729 secrets and the limit is 2000. See https://docs.oracle.com/iaas/Content/ContEng/Tasks/contengprotectingclustersfromresourceleaks.htm for details.
- **HelmRelease flux-system/vendor-bridge** since 2026-09-25T12:27:16Z: Helm install failed for release flux-system/vendor-bridge with chart vendor-bridge@0.1.0+0b337774a481: create: failed to create: admission webhook "oke-resource-leak-protection.oke.com" denied the request: OKE resource leak protection rejected the request. Cluster has 2729 secrets and the limit is 2000. See https://docs.oracle.com/iaas/Content/ContEng/Tasks/contengprotectingclustersfromresourceleaks.htm for details.
- **HelmRelease observability/langfuse** since 2026-09-25T10:40:26Z: dependency 'observability/signoz' is not ready
- **HelmRelease observability/signoz** since 2026-09-25T12:17:49Z: Helm upgrade failed for release observability/signoz with chart signoz@0.138.0: create: failed to create: admission webhook "oke-resource-leak-protection.oke.com" denied the request: OKE resource leak protection rejected the request. Cluster has 2778 secrets and the limit is 2000. See https://docs.oracle.com/iaas/Content/ContEng/Tasks/contengprotectingclustersfromresourceleaks.htm for details.
- **HelmRelease robusta/robusta** since 2026-09-25T12:23:28Z: Helm upgrade failed for release robusta/robusta with chart robusta@0.48.0: create: failed to create: admission webhook "oke-resource-leak-protection.oke.com" denied the request: OKE resource leak protection rejected the request. Cluster has 2729 secrets and the limit is 2000. See https://docs.oracle.com/iaas/Content/ContEng/Tasks/contengprotectingclustersfromresourceleaks.htm for details.
- **HelmRelease spire-mgmt/spire** since 2026-09-25T12:24:35Z: Helm upgrade failed for release spire-mgmt/spire with chart spire@0.30.1: create: failed to create: admission webhook "oke-resource-leak-protection.oke.com" denied the request: OKE resource leak protection rejected the request. Cluster has 2729 secrets and the limit is 2000. See https://docs.oracle.com/iaas/Content/ContEng/Tasks/contengprotectingclustersfromresourceleaks.htm for details.
- **HelmRelease trivy-system/trivy-operator** since 2026-09-25T12:18:25Z: Helm upgrade failed for release trivy-system/trivy-operator with chart trivy-operator@0.36.0: create: failed to create: admission webhook "oke-resource-leak-protection.oke.com" denied the request: OKE resource leak protection rejected the request. Cluster has 2778 secrets and the limit is 2000. See https://docs.oracle.com/iaas/Content/ContEng/Tasks/contengprotectingclustersfromresourceleaks.htm for details.
- **Kustomization flux-system/acg** since 2026-09-25T11:59:17Z: ServiceMonitor/acg/gateway dry-run failed: no matches for kind "ServiceMonitor" in version "v1" 
- **Kustomization flux-system/agent-workforce** since 2026-09-25T10:12:29Z: dependency 'flux-system/llm' is not ready
- **Kustomization flux-system/backstage** since 2026-09-25T12:02:51Z: health check failed after 415.930254ms: failed early due to stalled resources: [Deployment/backstage/catalogue status: 'Failed']
- **Kustomization flux-system/commerce** since 2026-09-25T12:30:20Z: Reconciliation in progress
- **Kustomization flux-system/coroot** since 2026-09-25T12:26:50Z: health check failed after 10m0.034326719s: timeout waiting for: [HelmRelease/coroot/coroot status: 'InProgress']
- **Kustomization flux-system/crossplane** since 2026-09-25T12:28:05Z: health check failed after 15m0.061906075s: timeout waiting for: [HelmRelease/crossplane-system/crossplane status: 'InProgress']
- **Kustomization flux-system/crossplane-providerconfig** since 2026-09-16T11:53:07Z: dependency 'flux-system/crossplane-providers' is not ready
- **Kustomization flux-system/crossplane-providers** since 2026-09-16T11:53:06Z: dependency 'flux-system/crossplane' is not ready
- **Kustomization flux-system/crossplane-storage-capability** since 2026-09-16T11:53:07Z: dependency 'flux-system/crossplane-providerconfig' is not ready
- **Kustomization flux-system/dagster** since 2026-09-25T12:28:05Z: Reconciliation in progress
- **Kustomization flux-system/epistemic-fabric** since 2026-09-25T11:46:54Z: health check failed after 153.357886ms: failed early due to stalled resources: [Deployment/epistemic-fabric/epistemic-ingest-github status: 'Failed']
- **Kustomization flux-system/healing-analyzer** since 2026-09-23T04:22:54Z: dependency 'flux-system/healing-k8sgpt' is not ready
- **Kustomization flux-system/healing-k8sgpt** since 2026-09-25T10:12:29Z: dependency 'flux-system/llm' is not ready
- **Kustomization flux-system/hermes-agent** since 2026-09-25T12:11:53Z: health check failed after 6.091967675s: failed early due to stalled resources: [Deployment/hermes-agent/hermes-agent-gateway status: 'Failed']
- **Kustomization flux-system/hindsight** since 2026-09-25T11:39:41Z: dependency 'flux-system/llm' is not ready
- **Kustomization flux-system/idp-agent** since 2026-09-25T11:59:10Z: Service/idp-agent/idp-agent-redis dry-run failed: admission webhook "validate.kyverno.svc-fail" denied the request:   resource Service/idp-agent/idp-agent-redis was blocked due to the following policies   require-catalogue-entity:   service-names-its-entity: 'validation error: Service idp-agent/idp-agent-redis serves a port but names no catalogue entity. Add the label backstage.io/kubernetes-id with the entity name from backstage/**/catalog-info.yaml, and a founder surface if a person opens it (docs/policy/every-interface-is-a-door.md). rule service-names-its-entity failed at path /metadata/labels/backstage.io/kubernetes-id/'  
- **Kustomization flux-system/jit** since 2026-09-25T12:15:20Z: health check failed after 3m30.563556975s: failed early due to stalled resources: [Deployment/jit/jit-broker status: 'Failed']
- **Kustomization flux-system/llm** since 2026-09-25T12:09:32Z: Deployment/llm/litellm dry-run failed: failed to create typed patch object (llm/litellm; apps/v1, Kind=Deployment): .spec.template.spec.containers[name="litellm"].env: duplicate entries for key [name="ZEROEDGE_URL"] 
- **Kustomization flux-system/mcp** since 2026-09-25T11:53:05Z: health check failed after 10m0.035764886s: timeout waiting for: [Deployment/mcp/estate-mcp status: 'InProgress']
- **Kustomization flux-system/observability** since 2026-09-25T12:05:05Z: health check failed after 20m0.107347549s: timeout waiting for: [HelmRelease/observability/signoz status: 'InProgress', HelmRelease/observability/langfuse status: 'InProgress']
- **Kustomization flux-system/otto-gateway** since 2026-09-25T12:09:31Z: health check failed after 34.369882921s: failed early due to stalled resources: [Deployment/otto-gateway/otto-gateway status: 'Failed']
- **Kustomization flux-system/otto-golden** since 2026-09-25T11:48:06Z: health check failed after 511.925667ms: failed early due to stalled resources: [Deployment/otto-golden/otto-golden status: 'Failed']
- **Kustomization flux-system/research-engine** since 2026-09-25T11:39:41Z: dependency 'flux-system/llm' is not ready
- **Kustomization flux-system/robusta** since 2026-09-25T12:27:47Z: Reconciliation in progress
- **Kustomization flux-system/router-events** since 2026-09-23T04:22:53Z: dependency 'flux-system/llm' is not ready
- **Kustomization flux-system/sandbox-launch** since 2026-09-25T12:05:45Z: health check failed after 3m55.178646106s: failed early due to stalled resources: [Job/demo-sandbox/arm-voice-bench status: 'Failed']
- **Kustomization flux-system/scheduling** since 2026-09-25T12:28:52Z: Reconciliation in progress
- **Kustomization flux-system/science** since 2026-09-25T11:46:18Z: dependency 'flux-system/observability' is not ready
- **Kustomization flux-system/spire** since 2026-09-25T12:28:52Z: health check failed after 15m0.080158445s: timeout waiting for: [HelmRelease/spire-mgmt/spire status: 'InProgress']
- **Kustomization flux-system/temporal** since 2026-09-25T12:16:07Z: Service/temporal/temporal-frontend-mesh dry-run failed: admission webhook "validate.kyverno.svc-fail" denied the request:   resource Service/temporal/temporal-frontend-mesh was blocked due to the following policies   require-catalogue-entity:   service-names-its-entity: 'validation error: Service temporal/temporal-frontend-mesh serves a port but names no catalogue entity. Add the label backstage.io/kubernetes-id with the entity name from backstage/**/catalog-info.yaml, and a founder surface if a person opens it (docs/policy/every-interface-is-a-door.md). rule service-names-its-entity failed at path /metadata/labels/backstage.io/kubernetes-id/'  
- **Kustomization flux-system/trivy** since 2026-09-25T12:25:58Z: health check failed after 15m0.046890848s: timeout waiting for: [HelmRelease/trivy-system/trivy-operator status: 'InProgress']
- **Kustomization flux-system/via-negativa** since 2026-09-25T11:29:54Z: dependency 'flux-system/llm' is not ready

## Every row

| Kind | Namespace | Name | State | Applied revision | Since | Message |
|---|---|---|---|---|---|---|
| HelmRelease | commerce | lago | Not ready | 1.28.0 | 2026-09-25T01:20:15Z | Could not determine release state: unable to determine state for release with status 'uninstalling' |
| HelmRelease | coroot | coroot | Not ready | 0.22.0 | 2026-09-25T12:28:24Z | Helm install failed for release coroot/coroot with chart coroot@0.22.0: create: failed to create: admission webhook "oke-resource-leak-protection.oke.com" denie |
| HelmRelease | crossplane-system | crossplane | Not ready | 1.15.1 | 2026-09-25T12:17:36Z | Helm upgrade failed for release crossplane-system/crossplane with chart crossplane@1.15.1: create: failed to create: admission webhook "oke-resource-leak-protec |
| HelmRelease | dagster | dagster | Not ready | 1.13.19 | 2026-09-25T12:30:33Z | Helm upgrade failed for release dagster/dagster with chart dagster@1.13.19: create: failed to create: admission webhook "oke-resource-leak-protection.oke.com" d |
| HelmRelease | flux-system | vendor-bridge | Not ready | 0.1.0+0b337774a481 | 2026-09-25T12:27:16Z | Helm install failed for release flux-system/vendor-bridge with chart vendor-bridge@0.1.0+0b337774a481: create: failed to create: admission webhook "oke-resource |
| HelmRelease | observability | langfuse | Not ready | 2.0.2 | 2026-09-25T10:40:26Z | dependency 'observability/signoz' is not ready |
| HelmRelease | observability | signoz | Not ready | 0.138.0 | 2026-09-25T12:17:49Z | Helm upgrade failed for release observability/signoz with chart signoz@0.138.0: create: failed to create: admission webhook "oke-resource-leak-protection.oke.co |
| HelmRelease | robusta | robusta | Not ready | 0.48.0 | 2026-09-25T12:23:28Z | Helm upgrade failed for release robusta/robusta with chart robusta@0.48.0: create: failed to create: admission webhook "oke-resource-leak-protection.oke.com" de |
| HelmRelease | spire-mgmt | spire | Not ready | 0.30.1 | 2026-09-25T12:24:35Z | Helm upgrade failed for release spire-mgmt/spire with chart spire@0.30.1: create: failed to create: admission webhook "oke-resource-leak-protection.oke.com" den |
| HelmRelease | trivy-system | trivy-operator | Not ready | 0.36.0 | 2026-09-25T12:18:25Z | Helm upgrade failed for release trivy-system/trivy-operator with chart trivy-operator@0.36.0: create: failed to create: admission webhook "oke-resource-leak-pro |
| Kustomization | flux-system | acg | Not ready | main@0b33777 | 2026-09-25T11:59:17Z | ServiceMonitor/acg/gateway dry-run failed: no matches for kind "ServiceMonitor" in version "v1"  |
| Kustomization | flux-system | agent-workforce | Not ready | main@689bcd9 | 2026-09-25T10:12:29Z | dependency 'flux-system/llm' is not ready |
| Kustomization | flux-system | backstage | Not ready | main@689bcd9 | 2026-09-25T12:02:51Z | health check failed after 415.930254ms: failed early due to stalled resources: [Deployment/backstage/catalogue status: 'Failed'] |
| Kustomization | flux-system | commerce | Not ready | main@abea14d | 2026-09-25T12:30:20Z | Reconciliation in progress |
| Kustomization | flux-system | coroot | Not ready | main@0b33777 | 2026-09-25T12:26:50Z | health check failed after 10m0.034326719s: timeout waiting for: [HelmRelease/coroot/coroot status: 'InProgress'] |
| Kustomization | flux-system | crossplane | Not ready | main@8d685ec | 2026-09-25T12:28:05Z | health check failed after 15m0.061906075s: timeout waiting for: [HelmRelease/crossplane-system/crossplane status: 'InProgress'] |
| Kustomization | flux-system | crossplane-providerconfig | Not ready | main@8d685ec | 2026-09-16T11:53:07Z | dependency 'flux-system/crossplane-providers' is not ready |
| Kustomization | flux-system | crossplane-providers | Not ready | main@8d685ec | 2026-09-16T11:53:06Z | dependency 'flux-system/crossplane' is not ready |
| Kustomization | flux-system | crossplane-storage-capability | Not ready | main@8d685ec | 2026-09-16T11:53:07Z | dependency 'flux-system/crossplane-providerconfig' is not ready |
| Kustomization | flux-system | dagster | Not ready | main@08aa502 | 2026-09-25T12:28:05Z | Reconciliation in progress |
| Kustomization | flux-system | epistemic-fabric | Not ready | main@0b33777 | 2026-09-25T11:46:54Z | health check failed after 153.357886ms: failed early due to stalled resources: [Deployment/epistemic-fabric/epistemic-ingest-github status: 'Failed'] |
| Kustomization | flux-system | healing-analyzer | Not ready | main@689bcd9 | 2026-09-23T04:22:54Z | dependency 'flux-system/healing-k8sgpt' is not ready |
| Kustomization | flux-system | healing-k8sgpt | Not ready | main@689bcd9 | 2026-09-25T10:12:29Z | dependency 'flux-system/llm' is not ready |
| Kustomization | flux-system | hermes-agent | Not ready | main@0df0a74 | 2026-09-25T12:11:53Z | health check failed after 6.091967675s: failed early due to stalled resources: [Deployment/hermes-agent/hermes-agent-gateway status: 'Failed'] |
| Kustomization | flux-system | hindsight | Not ready | main@689bcd9 | 2026-09-25T11:39:41Z | dependency 'flux-system/llm' is not ready |
| Kustomization | flux-system | idp-agent | Not ready | main@0b33777 | 2026-09-25T11:59:10Z | Service/idp-agent/idp-agent-redis dry-run failed: admission webhook "validate.kyverno.svc-fail" denied the request:   resource Service/idp-agent/idp-agent-redis |
| Kustomization | flux-system | jit | Not ready | main@689bcd9 | 2026-09-25T12:15:20Z | health check failed after 3m30.563556975s: failed early due to stalled resources: [Deployment/jit/jit-broker status: 'Failed'] |
| Kustomization | flux-system | llm | Not ready | main@689bcd9 | 2026-09-25T12:09:32Z | Deployment/llm/litellm dry-run failed: failed to create typed patch object (llm/litellm; apps/v1, Kind=Deployment): .spec.template.spec.containers[name="litellm |
| Kustomization | flux-system | mcp | Not ready | main@689bcd9 | 2026-09-25T11:53:05Z | health check failed after 10m0.035764886s: timeout waiting for: [Deployment/mcp/estate-mcp status: 'InProgress'] |
| Kustomization | flux-system | observability | Not ready | main@0b33777 | 2026-09-25T12:05:05Z | health check failed after 20m0.107347549s: timeout waiting for: [HelmRelease/observability/signoz status: 'InProgress', HelmRelease/observability/langfuse statu |
| Kustomization | flux-system | otto-gateway | Not ready | main@cd9eb71 | 2026-09-25T12:09:31Z | health check failed after 34.369882921s: failed early due to stalled resources: [Deployment/otto-gateway/otto-gateway status: 'Failed'] |
| Kustomization | flux-system | otto-golden | Not ready | main@cd9eb71 | 2026-09-25T11:48:06Z | health check failed after 511.925667ms: failed early due to stalled resources: [Deployment/otto-golden/otto-golden status: 'Failed'] |
| Kustomization | flux-system | research-engine | Not ready | main@689bcd9 | 2026-09-25T11:39:41Z | dependency 'flux-system/llm' is not ready |
| Kustomization | flux-system | robusta | Not ready | main@41e996d | 2026-09-25T12:27:47Z | Reconciliation in progress |
| Kustomization | flux-system | router-events | Not ready | main@689bcd9 | 2026-09-23T04:22:53Z | dependency 'flux-system/llm' is not ready |
| Kustomization | flux-system | sandbox-launch | Not ready | main@ac2a1b1 | 2026-09-25T12:05:45Z | health check failed after 3m55.178646106s: failed early due to stalled resources: [Job/demo-sandbox/arm-voice-bench status: 'Failed'] |
| Kustomization | flux-system | scheduling | Not ready | main@0b33777 | 2026-09-25T12:28:52Z | Reconciliation in progress |
| Kustomization | flux-system | science | Not ready | main@0b33777 | 2026-09-25T11:46:18Z | dependency 'flux-system/observability' is not ready |
| Kustomization | flux-system | spire | Not ready | main@0b33777 | 2026-09-25T12:28:52Z | health check failed after 15m0.080158445s: timeout waiting for: [HelmRelease/spire-mgmt/spire status: 'InProgress'] |
| Kustomization | flux-system | temporal | Not ready | main@41e996d | 2026-09-25T12:16:07Z | Service/temporal/temporal-frontend-mesh dry-run failed: admission webhook "validate.kyverno.svc-fail" denied the request:   resource Service/temporal/temporal-f |
| Kustomization | flux-system | trivy | Not ready | main@689bcd9 | 2026-09-25T12:25:58Z | health check failed after 15m0.046890848s: timeout waiting for: [HelmRelease/trivy-system/trivy-operator status: 'InProgress'] |
| Kustomization | flux-system | via-negativa | Not ready | main@689bcd9 | 2026-09-25T11:29:54Z | dependency 'flux-system/llm' is not ready |
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
| Kustomization | flux-system | alerts | Ready | main@0b33777 | 2026-09-25T12:27:22Z |  |
| Kustomization | flux-system | alerts-github | Ready | main@0b33777 | 2026-09-25T12:04:22Z |  |
| Kustomization | flux-system | alerts-secret | Ready | main@0b33777 | 2026-09-25T11:58:35Z |  |
| Kustomization | flux-system | autoscaler | Ready | main@0b33777 | 2026-09-25T12:00:13Z |  |
| Kustomization | flux-system | backstage-namespace | Ready | main@0b33777 | 2026-09-25T12:02:00Z |  |
| Kustomization | flux-system | calico | Ready | main@0b33777 | 2026-09-25T11:50:33Z |  |
| Kustomization | flux-system | cluster-state | Ready | main@0b33777 | 2026-09-25T11:50:22Z |  |
| Kustomization | flux-system | commerce-data | Ready | main@0b33777 | 2026-09-25T11:51:50Z |  |
| Kustomization | flux-system | concierge | Ready | main@0b33777 | 2026-09-25T12:03:09Z |  |
| Kustomization | flux-system | dns | Ready | main@0b33777 | 2026-09-25T12:00:12Z |  |
| Kustomization | flux-system | edge | Ready | main@0b33777 | 2026-09-25T12:27:03Z |  |
| Kustomization | flux-system | estate-catalog | Ready | latest@sha256:34e0ec564cd51e17c960ebf7b0 | 2026-09-25T12:05:07Z |  |
| Kustomization | flux-system | estate-db | Ready | main@0b33777 | 2026-09-25T12:02:20Z |  |
| Kustomization | flux-system | estate-db-migrate | Ready | main@0b33777 | 2026-09-25T12:05:16Z |  |
| Kustomization | flux-system | estate-db-operator | Ready | main@0b33777 | 2026-09-25T11:55:43Z |  |
| Kustomization | flux-system | event-bus | Ready | main@0b33777 | 2026-09-25T12:26:22Z |  |
| Kustomization | flux-system | external-secrets | Ready | main@0b33777 | 2026-09-25T12:30:20Z |  |
| Kustomization | flux-system | feature-register | Ready | main@0b33777 | 2026-09-25T12:26:40Z |  |
| Kustomization | flux-system | flux-system | Ready | main@0b33777 | 2026-09-25T11:52:19Z |  |
| Kustomization | flux-system | flux-webhook | Ready | main@0b33777 | 2026-09-25T11:52:34Z |  |
| Kustomization | flux-system | gateway-api-crds | Ready | v1.5.1@e7677b7 | 2026-09-25T11:48:09Z |  |
| Kustomization | flux-system | github-app-creds | Ready | main@0b33777 | 2026-09-25T11:57:05Z |  |
| Kustomization | flux-system | guacamole | Ready | main@0b33777 | 2026-09-25T12:27:47Z |  |
| Kustomization | flux-system | gvisor-runtime | Ready | main@0b33777 | 2026-09-25T12:28:06Z |  |
| Kustomization | flux-system | healing | Ready | main@0b33777 | 2026-09-25T11:47:41Z |  |
| Kustomization | flux-system | healthchecks | Ready | main@0b33777 | 2026-09-25T11:54:58Z |  |
| Kustomization | flux-system | human-vault | Ready | main@0b33777 | 2026-09-25T11:57:37Z |  |
| Kustomization | flux-system | human-vault-bridge | Ready | main@0b33777 | 2026-09-25T11:51:27Z |  |
| Kustomization | flux-system | identity | Ready | main@0b33777 | 2026-09-25T12:00:56Z |  |
| Kustomization | flux-system | image-automation | Ready | main@0b33777 | 2026-09-25T11:53:06Z |  |
| Kustomization | flux-system | keda | Ready | main@0b33777 | 2026-09-25T11:48:55Z |  |
| Kustomization | flux-system | kyverno | Ready | main@0b33777 | 2026-09-25T12:09:59Z |  |
| Kustomization | flux-system | metrics-server | Ready | main@0b33777 | 2026-09-25T11:48:27Z |  |
| Kustomization | flux-system | monitoring | Ready | main@0b33777 | 2026-09-25T11:57:04Z |  |
| Kustomization | flux-system | monitoring-rules | Ready | main@0b33777 | 2026-09-25T11:47:16Z |  |
| Kustomization | flux-system | nodesoftware-operator | Ready | main@0b33777 | 2026-09-25T12:16:29Z |  |
| Kustomization | flux-system | notify | Ready | main@0b33777 | 2026-09-25T12:06:10Z |  |
| Kustomization | flux-system | ns-fences | Ready | main@0b33777 | 2026-09-25T12:08:44Z |  |
| Kustomization | flux-system | observability-collector | Ready | main@0b33777 | 2026-09-25T12:11:45Z |  |
| Kustomization | flux-system | otto-golden-secret | Ready | main@0b33777 | 2026-09-25T11:56:17Z |  |
| Kustomization | flux-system | priority-classes | Ready | main@0b33777 | 2026-09-25T11:53:30Z |  |
| Kustomization | flux-system | prospector | Ready | main@7453d76 | 2026-09-25T11:57:17Z |  |
| Kustomization | flux-system | prospector-platform | Ready | main@0b33777 | 2026-09-25T11:51:01Z |  |
| Kustomization | flux-system | rbac | Ready | main@0b33777 | 2026-09-25T12:15:46Z |  |
| Kustomization | flux-system | rbac-floor | Ready | main@0b33777 | 2026-09-25T12:04:02Z |  |
| Kustomization | flux-system | rbac-identity | Ready | main@0b33777 | 2026-09-25T12:07:10Z |  |
| Kustomization | flux-system | reloader | Ready | main@0b33777 | 2026-09-25T12:03:34Z |  |
| Kustomization | flux-system | sandbox-live | Ready | sandbox/launch@4830a6e | 2026-09-25T11:59:18Z |  |
| Kustomization | flux-system | searxng | Ready | main@0b33777 | 2026-09-25T12:07:49Z |  |
| Kustomization | flux-system | secret-store | Ready | main@0b33777 | 2026-09-25T11:49:34Z |  |
| Kustomization | flux-system | staging | Ready | main@0b33777 | 2026-09-25T12:13:03Z |  |
| Kustomization | flux-system | tailscale | Ready | main@0b33777 | 2026-09-25T11:54:42Z |  |
| Kustomization | flux-system | verification | Ready | main@0b33777 | 2026-09-25T11:59:47Z |  |
| Kustomization | flux-system | weave-gitops | Ready | main@0b33777 | 2026-09-25T12:04:50Z |  |
