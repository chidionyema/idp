# Flux: what is applied

Read from the cluster receipt taken at 2026-09-03T11:30:10Z. Every Kustomization and HelmRelease, with the revision Flux last applied. **Suspended** is a switch somebody turned off on purpose (temporal, commerce, commerce-data, event-bus), not a defect; **Unknown** is a row Flux has never graded.

**82 objects: 71 ready, 6 not ready, 0 unknown, 5 suspended.**

## Not ready right now

- **Kustomization flux-system/healing** since 2026-09-03T11:21:28Z: dependency 'flux-system/llm' is not ready
- **Kustomization flux-system/healing-analyzer** since 2026-09-03T11:07:00Z: dependency 'flux-system/healing' is not ready
- **Kustomization flux-system/hindsight** since 2026-09-03T11:21:28Z: dependency 'flux-system/llm' is not ready
- **Kustomization flux-system/infra-crew** since 2026-09-03T11:22:03Z: dependency 'flux-system/llm' is not ready
- **Kustomization flux-system/llm** since 2026-09-03T11:21:55Z: Deployment/llm/litellm-cache dry-run failed: admission webhook "validate.kyverno.svc-fail" denied the request:   resource Deployment/llm/litellm-cache was blocked due to the following policies   require-availability:   founder-facing-runs-two: 'validation error: crew#555: a founder-facing Deployment runs at least 2 replicas. One pod is one node event away from a 503 (the catalogue outage of 2026-08-28 06:20Z). If this workload genuinely cannot be two (one token, one RWO volume), it belongs in platform/availability.yaml with an open issue, not at replicas 1 in a founder-facing namespace. rule founder-facing-runs-two failed at path /spec/replicas/'   founder-facing-spreads-across-nodes: 'validation error: crew#555: two replicas on one node are one replica. Needs a required podAntiAffinity or a DoNotSchedule topologySpreadConstraint on kubernetes.io/hostname. rule founder-facing-spreads-across-nodes[0] failed at path /spec/template/spec/affinity/podAntiAffinity/ rule founder-facing-spreads-across-nodes[1] failed at path /spec/template/spec/topologySpreadConstraints/'  
- **Kustomization flux-system/notify** since 2026-09-03T11:21:42Z: Reconciliation in progress

## Every row

| Kind | Namespace | Name | State | Applied revision | Since | Message |
|---|---|---|---|---|---|---|
| Kustomization | flux-system | healing | Not ready | main@bab90ea | 2026-09-03T11:21:28Z | dependency 'flux-system/llm' is not ready |
| Kustomization | flux-system | healing-analyzer | Not ready | main@bab90ea | 2026-09-03T11:07:00Z | dependency 'flux-system/healing' is not ready |
| Kustomization | flux-system | hindsight | Not ready | main@bab90ea | 2026-09-03T11:21:28Z | dependency 'flux-system/llm' is not ready |
| Kustomization | flux-system | infra-crew | Not ready | main@bab90ea | 2026-09-03T11:22:03Z | dependency 'flux-system/llm' is not ready |
| Kustomization | flux-system | llm | Not ready | main@bab90ea | 2026-09-03T11:21:55Z | Deployment/llm/litellm-cache dry-run failed: admission webhook "validate.kyverno.svc-fail" denied the request:   resource Deployment/llm/litellm-cache was block |
| Kustomization | flux-system | notify | Not ready | main@765d740 | 2026-09-03T11:21:42Z | Reconciliation in progress |
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
| HelmRelease | observability | superset | Ready | 0.22.4 | 2026-09-03T11:04:09Z |  |
| HelmRelease | observability-agent | k8s-infra | Ready | 0.17.0 | 2026-08-31T03:17:25Z |  |
| HelmRelease | reloader | reloader | Ready | 2.2.16 | 2026-08-31T07:11:24Z |  |
| HelmRelease | robusta | robusta | Ready | 0.48.0 | 2026-08-31T07:12:01Z |  |
| HelmRelease | spire-mgmt | spire | Ready | 0.30.1 | 2026-08-31T07:12:31Z |  |
| HelmRelease | spire-mgmt | spire-crds | Ready | 0.6.1 | 2026-08-31T07:12:02Z |  |
| HelmRelease | tailscale | tailscale-operator | Ready | 1.102.3 | 2026-09-02T16:32:30Z |  |
| HelmRelease | temporal | temporal | Ready | 1.6.0 | 2026-08-29T19:01:39Z |  |
| Kustomization | flux-system | alerts | Ready | main@765d740 | 2026-09-03T11:21:28Z |  |
| Kustomization | flux-system | alerts-github | Ready | main@765d740 | 2026-09-03T11:21:53Z |  |
| Kustomization | flux-system | alerts-secret | Ready | main@765d740 | 2026-09-03T11:21:24Z |  |
| Kustomization | flux-system | autoscaler | Ready | main@765d740 | 2026-09-03T11:21:27Z |  |
| Kustomization | flux-system | backstage | Ready | main@765d740 | 2026-09-03T11:21:29Z |  |
| Kustomization | flux-system | backstage-namespace | Ready | main@765d740 | 2026-09-03T11:29:59Z |  |
| Kustomization | flux-system | chaos | Ready | main@765d740 | 2026-09-03T11:22:03Z |  |
| Kustomization | flux-system | chaos-mesh | Ready | main@765d740 | 2026-09-03T11:21:23Z |  |
| Kustomization | flux-system | cluster-state | Ready | main@765d740 | 2026-09-03T11:22:02Z |  |
| Kustomization | flux-system | dagster | Ready | main@765d740 | 2026-09-03T11:21:53Z |  |
| Kustomization | flux-system | dns | Ready | main@765d740 | 2026-09-03T11:21:24Z |  |
| Kustomization | flux-system | drills | Ready | main@765d740 | 2026-09-03T11:21:59Z |  |
| Kustomization | flux-system | edge | Ready | main@765d740 | 2026-09-03T11:20:53Z |  |
| Kustomization | flux-system | estate-catalog | Ready | latest@sha256:6ea0df74cfe64b1d0087f3f9eb | 2026-09-03T11:20:28Z |  |
| Kustomization | flux-system | external-secrets | Ready | main@765d740 | 2026-09-03T11:21:18Z |  |
| Kustomization | flux-system | flux-system | Ready | main@765d740 | 2026-09-03T11:20:21Z |  |
| Kustomization | flux-system | gateway-api-crds | Ready | v1.5.1@e7677b7 | 2026-09-03T11:20:21Z |  |
| Kustomization | flux-system | guacamole | Ready | main@765d740 | 2026-09-03T11:22:04Z |  |
| Kustomization | flux-system | healthchecks | Ready | main@765d740 | 2026-09-03T11:22:01Z |  |
| Kustomization | flux-system | hermes-agent | Ready | main@765d740 | 2026-09-03T11:25:06Z |  |
| Kustomization | flux-system | human-vault | Ready | main@765d740 | 2026-09-03T11:21:58Z |  |
| Kustomization | flux-system | identity | Ready | main@765d740 | 2026-09-03T11:21:53Z |  |
| Kustomization | flux-system | image-automation | Ready | main@765d740 | 2026-09-03T11:21:25Z |  |
| Kustomization | flux-system | keda | Ready | main@765d740 | 2026-09-03T11:22:04Z |  |
| Kustomization | flux-system | kyverno | Ready | main@765d740 | 2026-09-03T11:20:20Z |  |
| Kustomization | flux-system | mcp | Ready | main@765d740 | 2026-09-03T11:22:00Z |  |
| Kustomization | flux-system | metrics-server | Ready | main@765d740 | 2026-09-03T11:21:22Z |  |
| Kustomization | flux-system | monitoring | Ready | main@765d740 | 2026-09-03T11:21:27Z |  |
| Kustomization | flux-system | monitoring-rules | Ready | main@765d740 | 2026-09-03T11:21:52Z |  |
| Kustomization | flux-system | observability | Ready | main@765d740 | 2026-09-03T11:21:57Z |  |
| Kustomization | flux-system | observability-collector | Ready | main@765d740 | 2026-09-03T11:21:25Z |  |
| Kustomization | flux-system | otto-golden | Ready | main@765d740 | 2026-09-03T11:21:55Z |  |
| Kustomization | flux-system | otto-golden-secret | Ready | main@765d740 | 2026-09-03T11:21:26Z |  |
| Kustomization | flux-system | priority-classes | Ready | main@765d740 | 2026-09-03T11:20:18Z |  |
| Kustomization | flux-system | prospector | Ready | main@b6ce2fc | 2026-09-03T11:22:38Z |  |
| Kustomization | flux-system | prospector-platform | Ready | main@765d740 | 2026-09-03T11:21:23Z |  |
| Kustomization | flux-system | reloader | Ready | main@765d740 | 2026-09-03T11:21:52Z |  |
| Kustomization | flux-system | robusta | Ready | main@765d740 | 2026-09-03T11:21:28Z |  |
| Kustomization | flux-system | scheduling | Ready | main@765d740 | 2026-09-03T11:21:18Z |  |
| Kustomization | flux-system | science | Ready | main@765d740 | 2026-09-03T11:22:02Z |  |
| Kustomization | flux-system | secret-store | Ready | main@765d740 | 2026-09-03T11:21:22Z |  |
| Kustomization | flux-system | spire | Ready | main@765d740 | 2026-09-03T11:21:25Z |  |
| Kustomization | flux-system | staging | Ready | main@765d740 | 2026-09-03T11:20:19Z |  |
| Kustomization | flux-system | tailscale | Ready | main@765d740 | 2026-09-03T11:21:58Z |  |
| Kustomization | flux-system | verification | Ready | main@765d740 | 2026-09-03T11:21:54Z |  |
