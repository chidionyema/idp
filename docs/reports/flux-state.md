# Flux: what is applied

Read from the cluster receipt taken at 2026-09-04T08:00:10Z. Every Kustomization and HelmRelease, with the revision Flux last applied. **Suspended** is a switch somebody turned off on purpose (temporal, commerce, commerce-data, event-bus), not a defect; **Unknown** is a row Flux has never graded.

**82 objects: 69 ready, 8 not ready, 0 unknown, 5 suspended.**

## Not ready right now

- **Kustomization flux-system/chaos** since 2026-09-04T07:51:56Z: dependency 'flux-system/observability' is not ready
- **Kustomization flux-system/guacamole** since 2026-09-04T07:52:32Z: Namespace/guacamole dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.kyverno.svc-fail": failed to call webhook: Post "https://kyverno-svc.kyverno.svc:443/validate/fail?timeout=10s": context deadline exceeded 
- **Kustomization flux-system/healthchecks** since 2026-09-04T07:52:35Z: Namespace/healthchecks dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.kyverno.svc-fail": failed to call webhook: Post "https://kyverno-svc.kyverno.svc:443/validate/fail?timeout=10s": context deadline exceeded 
- **Kustomization flux-system/hermes-agent** since 2026-09-04T07:52:25Z: Namespace/hermes-agent dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.kyverno.svc-fail": failed to call webhook: Post "https://kyverno-svc.kyverno.svc:443/validate/fail?timeout=10s": context deadline exceeded 
- **Kustomization flux-system/infra-crew** since 2026-09-04T07:52:38Z: Namespace/infra-crew dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.kyverno.svc-fail": failed to call webhook: Post "https://kyverno-svc.kyverno.svc:443/validate/fail?timeout=10s": context deadline exceeded 
- **Kustomization flux-system/notify** since 2026-09-04T07:54:55Z: Reconciliation in progress
- **Kustomization flux-system/observability** since 2026-09-04T07:52:28Z: ClusterRole/telemetry-coverage-reader dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.kyverno.svc-fail": failed to call webhook: Post "https://kyverno-svc.kyverno.svc:443/validate/fail?timeout=10s": context deadline exceeded 
- **Kustomization flux-system/science** since 2026-09-04T07:50:47Z: dependency 'flux-system/observability' is not ready

## Every row

| Kind | Namespace | Name | State | Applied revision | Since | Message |
|---|---|---|---|---|---|---|
| Kustomization | flux-system | chaos | Not ready | main@f1382cd | 2026-09-04T07:51:56Z | dependency 'flux-system/observability' is not ready |
| Kustomization | flux-system | guacamole | Not ready | main@f1382cd | 2026-09-04T07:52:32Z | Namespace/guacamole dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.kyverno.svc-fail": failed to call webhook: Post "h |
| Kustomization | flux-system | healthchecks | Not ready | main@f1382cd | 2026-09-04T07:52:35Z | Namespace/healthchecks dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.kyverno.svc-fail": failed to call webhook: Post |
| Kustomization | flux-system | hermes-agent | Not ready | main@f1382cd | 2026-09-04T07:52:25Z | Namespace/hermes-agent dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.kyverno.svc-fail": failed to call webhook: Post |
| Kustomization | flux-system | infra-crew | Not ready | main@f1382cd | 2026-09-04T07:52:38Z | Namespace/infra-crew dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.kyverno.svc-fail": failed to call webhook: Post " |
| Kustomization | flux-system | notify | Not ready | main@ef2e174 | 2026-09-04T07:54:55Z | Reconciliation in progress |
| Kustomization | flux-system | observability | Not ready | main@f1382cd | 2026-09-04T07:52:28Z | ClusterRole/telemetry-coverage-reader dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.kyverno.svc-fail": failed to cal |
| Kustomization | flux-system | science | Not ready | main@f1382cd | 2026-09-04T07:50:47Z | dependency 'flux-system/observability' is not ready |
| Kustomization | flux-system | commerce | Suspended |  |  |  |
| Kustomization | flux-system | commerce-data | Suspended |  |  |  |
| Kustomization | flux-system | event-bus | Suspended |  |  |  |
| Kustomization | flux-system | otto-gateway | Suspended |  |  |  |
| Kustomization | flux-system | temporal | Suspended | main@1b323ac | 2026-08-30T05:54:22Z |  |
| HelmRelease | cert-manager | cert-manager | Ready | v1.21.1 | 2026-08-31T07:10:44Z |  |
| HelmRelease | chaos-mesh | chaos-mesh | Ready | 2.8.4 | 2026-08-31T07:12:00Z |  |
| HelmRelease | dagster | dagster | Ready | 1.13.19 | 2026-09-02T19:57:44Z |  |
| HelmRelease | edge | external-dns | Ready | 1.21.1 | 2026-08-31T07:11:28Z |  |
| HelmRelease | edge | traefik | Ready | 41.3.0 | 2026-08-31T07:10:46Z |  |
| HelmRelease | external-secrets | external-secrets | Ready | 2.9.0 | 2026-09-02T11:40:21Z |  |
| HelmRelease | healing | descheduler | Ready | 0.36.0 | 2026-08-31T07:11:29Z |  |
| HelmRelease | healing | k8sgpt-operator | Ready | 0.2.29 | 2026-08-31T07:11:29Z |  |
| HelmRelease | hindsight | hindsight | Ready | 0.9.2 | 2026-09-02T23:12:33Z |  |
| HelmRelease | identity | oauth2-proxy | Ready | 10.7.0 | 2026-08-29T07:33:02Z |  |
| HelmRelease | keda | keda | Ready | 2.20.2 | 2026-08-31T07:14:43Z |  |
| HelmRelease | keda | keda-add-ons-http | Ready | 0.15.0 | 2026-08-31T07:14:44Z |  |
| HelmRelease | kyverno | kyverno | Ready | 3.9.0 | 2026-09-02T03:08:09Z |  |
| HelmRelease | metrics-server | metrics-server | Ready | 3.14.0 | 2026-08-31T07:11:28Z |  |
| HelmRelease | monitoring | blackbox | Ready | 11.17.2 | 2026-08-31T07:12:07Z |  |
| HelmRelease | monitoring | kube-prometheus-stack | Ready | 88.6.0 | 2026-08-31T07:12:05Z |  |
| HelmRelease | observability | langfuse | Ready | 2.0.2 | 2026-08-31T07:14:04Z |  |
| HelmRelease | observability | signoz | Ready | 0.138.0 | 2026-08-31T07:12:44Z |  |
| HelmRelease | observability | superset | Ready | 0.22.4 | 2026-09-03T13:21:03Z |  |
| HelmRelease | observability-agent | k8s-infra | Ready | 0.17.0 | 2026-09-03T15:19:29Z |  |
| HelmRelease | reloader | reloader | Ready | 2.2.16 | 2026-08-31T07:11:24Z |  |
| HelmRelease | robusta | robusta | Ready | 0.48.0 | 2026-08-31T07:12:01Z |  |
| HelmRelease | spire-mgmt | spire | Ready | 0.30.1 | 2026-08-31T07:12:31Z |  |
| HelmRelease | spire-mgmt | spire-crds | Ready | 0.6.1 | 2026-08-31T07:12:02Z |  |
| HelmRelease | tailscale | tailscale-operator | Ready | 1.102.3 | 2026-09-02T16:32:30Z |  |
| HelmRelease | temporal | temporal | Ready | 1.6.0 | 2026-08-29T19:01:39Z |  |
| Kustomization | flux-system | alerts | Ready | main@ef2e174 | 2026-09-04T07:51:57Z |  |
| Kustomization | flux-system | alerts-github | Ready | main@ef2e174 | 2026-09-04T07:51:52Z |  |
| Kustomization | flux-system | alerts-secret | Ready | main@ef2e174 | 2026-09-04T07:51:53Z |  |
| Kustomization | flux-system | autoscaler | Ready | main@ef2e174 | 2026-09-04T07:51:54Z |  |
| Kustomization | flux-system | backstage | Ready | main@ef2e174 | 2026-09-04T07:51:53Z |  |
| Kustomization | flux-system | backstage-namespace | Ready | main@ef2e174 | 2026-09-04T07:50:45Z |  |
| Kustomization | flux-system | chaos-mesh | Ready | main@ef2e174 | 2026-09-04T07:51:50Z |  |
| Kustomization | flux-system | cluster-state | Ready | main@ef2e174 | 2026-09-04T07:51:49Z |  |
| Kustomization | flux-system | dagster | Ready | main@ef2e174 | 2026-09-04T07:51:52Z |  |
| Kustomization | flux-system | dns | Ready | main@ef2e174 | 2026-09-04T07:51:56Z |  |
| Kustomization | flux-system | drills | Ready | main@ef2e174 | 2026-09-04T07:51:54Z |  |
| Kustomization | flux-system | edge | Ready | main@ef2e174 | 2026-09-04T07:51:19Z |  |
| Kustomization | flux-system | estate-catalog | Ready | latest@sha256:0bfbbe901b68351d71b27ad788 | 2026-09-04T07:59:59Z |  |
| Kustomization | flux-system | external-secrets | Ready | main@ef2e174 | 2026-09-04T07:51:45Z |  |
| Kustomization | flux-system | flux-system | Ready | main@ef2e174 | 2026-09-04T07:50:48Z |  |
| Kustomization | flux-system | gateway-api-crds | Ready | v1.5.1@e7677b7 | 2026-09-04T07:50:47Z |  |
| Kustomization | flux-system | healing | Ready | main@ef2e174 | 2026-09-04T07:52:01Z |  |
| Kustomization | flux-system | healing-analyzer | Ready | main@ef2e174 | 2026-09-04T07:52:02Z |  |
| Kustomization | flux-system | hindsight | Ready | main@ef2e174 | 2026-09-04T07:52:01Z |  |
| Kustomization | flux-system | human-vault | Ready | main@ef2e174 | 2026-09-04T07:51:53Z |  |
| Kustomization | flux-system | identity | Ready | main@ef2e174 | 2026-09-04T07:51:54Z |  |
| Kustomization | flux-system | image-automation | Ready | main@ef2e174 | 2026-09-04T07:52:00Z |  |
| Kustomization | flux-system | keda | Ready | main@ef2e174 | 2026-09-04T07:51:50Z |  |
| Kustomization | flux-system | kyverno | Ready | main@ef2e174 | 2026-09-04T07:50:46Z |  |
| Kustomization | flux-system | llm | Ready | main@ef2e174 | 2026-09-04T07:51:59Z |  |
| Kustomization | flux-system | mcp | Ready | main@ef2e174 | 2026-09-04T07:52:02Z |  |
| Kustomization | flux-system | metrics-server | Ready | main@ef2e174 | 2026-09-04T07:51:51Z |  |
| Kustomization | flux-system | monitoring | Ready | main@ef2e174 | 2026-09-04T07:51:56Z |  |
| Kustomization | flux-system | monitoring-rules | Ready | main@ef2e174 | 2026-09-04T07:51:58Z |  |
| Kustomization | flux-system | observability-collector | Ready | main@ef2e174 | 2026-09-04T07:51:49Z |  |
| Kustomization | flux-system | otto-golden | Ready | main@ef2e174 | 2026-09-04T07:51:59Z |  |
| Kustomization | flux-system | otto-golden-secret | Ready | main@ef2e174 | 2026-09-04T07:51:56Z |  |
| Kustomization | flux-system | priority-classes | Ready | main@ef2e174 | 2026-09-04T07:50:45Z |  |
| Kustomization | flux-system | prospector | Ready | main@5972126 | 2026-09-04T07:59:41Z |  |
| Kustomization | flux-system | prospector-platform | Ready | main@ef2e174 | 2026-09-04T07:51:48Z |  |
| Kustomization | flux-system | reloader | Ready | main@ef2e174 | 2026-09-04T07:51:51Z |  |
| Kustomization | flux-system | robusta | Ready | main@ef2e174 | 2026-09-04T07:51:59Z |  |
| Kustomization | flux-system | scheduling | Ready | main@ef2e174 | 2026-09-04T07:51:45Z |  |
| Kustomization | flux-system | secret-store | Ready | main@ef2e174 | 2026-09-04T07:51:50Z |  |
| Kustomization | flux-system | spire | Ready | main@ef2e174 | 2026-09-04T07:51:48Z |  |
| Kustomization | flux-system | staging | Ready | main@ef2e174 | 2026-09-04T07:50:45Z |  |
| Kustomization | flux-system | tailscale | Ready | main@ef2e174 | 2026-09-04T07:52:00Z |  |
| Kustomization | flux-system | verification | Ready | main@ef2e174 | 2026-09-04T07:51:55Z |  |
