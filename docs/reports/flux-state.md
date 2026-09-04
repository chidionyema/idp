# Flux: what is applied

Read from the cluster receipt taken at 2026-09-04T20:00:10Z. Every Kustomization and HelmRelease, with the revision Flux last applied. **Suspended** is a switch somebody turned off on purpose (temporal, commerce, commerce-data, event-bus), not a defect; **Unknown** is a row Flux has never graded.

**95 objects: 73 ready, 19 not ready, 0 unknown, 3 suspended.**

## Not ready right now

- **HelmRelease tigera-operator/tigera-operator** since 2026-09-04T19:48:39Z: Helm install failed for release tigera-operator/tigera-operator with chart tigera-operator@v3.32.2: unable to build kubernetes objects from release manifest: [resource mapping not found for name: "default" namespace: "" from "": no matches for kind "APIServer" in version "operator.tigera.io/v1" ensure CRDs are installed first, resource mapping not found for name: "default" namespace: "" from "": no matches for kind "Goldmane" in version "operator.tigera.io/v1" ensure CRDs are installed first, resource mapping not found for name: "default" namespace: "" from "": no matches for kind "Installation" in version "operator.tigera.io/v1" ensure CRDs are installed first, resource mapping not found for name: "default" namespace: "" from "": no matches for kind "Whisker" in version "operator.tigera.io/v1" ensure CRDs are installed first]
- **Kustomization flux-system/backstage** since 2026-09-04T19:17:14Z: dependency 'flux-system/estate-db-migrate' is not ready
- **Kustomization flux-system/chaos** since 2026-09-04T19:17:47Z: dependency 'flux-system/observability' is not ready
- **Kustomization flux-system/dagster** since 2026-09-04T19:17:13Z: dependency 'flux-system/estate-db-migrate' is not ready
- **Kustomization flux-system/estate-db** since 2026-09-04T19:55:46Z: Database/estate-db/guacamole dry-run failed (InternalError): Internal error occurred: failed calling webhook "mdatabase.cnpg.io": failed to call webhook: Post "https://cnpg-webhook-service.estate-db.svc:443/mutate-postgresql-cnpg-io-v1-database?timeout=10s": EOF 
- **Kustomization flux-system/estate-db-migrate** since 2026-09-04T19:57:16Z: dependency 'flux-system/estate-db' is not ready
- **Kustomization flux-system/guacamole** since 2026-09-04T19:17:13Z: dependency 'flux-system/estate-db-migrate' is not ready
- **Kustomization flux-system/healing** since 2026-09-04T19:17:13Z: dependency 'flux-system/llm' is not ready
- **Kustomization flux-system/healing-analyzer** since 2026-09-04T19:10:40Z: dependency 'flux-system/healing' is not ready
- **Kustomization flux-system/healthchecks** since 2026-09-04T19:17:13Z: dependency 'flux-system/estate-db-migrate' is not ready
- **Kustomization flux-system/hindsight** since 2026-09-04T19:17:13Z: dependency 'flux-system/llm' is not ready
- **Kustomization flux-system/image-automation** since 2026-09-04T19:52:07Z: Reconciliation in progress
- **Kustomization flux-system/infra-crew** since 2026-09-04T19:17:14Z: dependency 'flux-system/llm' is not ready
- **Kustomization flux-system/llm** since 2026-09-04T19:17:13Z: dependency 'flux-system/estate-db-migrate' is not ready
- **Kustomization flux-system/notify** since 2026-09-04T19:50:32Z: Reconciliation in progress
- **Kustomization flux-system/observability** since 2026-09-04T19:17:13Z: dependency 'flux-system/estate-db-migrate' is not ready
- **Kustomization flux-system/otto-gateway** since 2026-09-04T19:17:14Z: dependency 'flux-system/estate-db-migrate' is not ready
- **Kustomization flux-system/research-engine** since 2026-09-04T19:17:13Z: dependency 'flux-system/llm' is not ready
- **Kustomization flux-system/science** since 2026-09-04T19:10:40Z: dependency 'flux-system/observability' is not ready

## Every row

| Kind | Namespace | Name | State | Applied revision | Since | Message |
|---|---|---|---|---|---|---|
| HelmRelease | tigera-operator | tigera-operator | Not ready | v3.32.2 | 2026-09-04T19:48:39Z | Helm install failed for release tigera-operator/tigera-operator with chart tigera-operator@v3.32.2: unable to build kubernetes objects from release manifest: [r |
| Kustomization | flux-system | backstage | Not ready | main@c61560f | 2026-09-04T19:17:14Z | dependency 'flux-system/estate-db-migrate' is not ready |
| Kustomization | flux-system | chaos | Not ready | main@c61560f | 2026-09-04T19:17:47Z | dependency 'flux-system/observability' is not ready |
| Kustomization | flux-system | dagster | Not ready | main@36f470b | 2026-09-04T19:17:13Z | dependency 'flux-system/estate-db-migrate' is not ready |
| Kustomization | flux-system | estate-db | Not ready | main@49bb741 | 2026-09-04T19:55:46Z | Database/estate-db/guacamole dry-run failed (InternalError): Internal error occurred: failed calling webhook "mdatabase.cnpg.io": failed to call webhook: Post " |
| Kustomization | flux-system | estate-db-migrate | Not ready | main@36f470b | 2026-09-04T19:57:16Z | dependency 'flux-system/estate-db' is not ready |
| Kustomization | flux-system | guacamole | Not ready | main@36f470b | 2026-09-04T19:17:13Z | dependency 'flux-system/estate-db-migrate' is not ready |
| Kustomization | flux-system | healing | Not ready | main@36f470b | 2026-09-04T19:17:13Z | dependency 'flux-system/llm' is not ready |
| Kustomization | flux-system | healing-analyzer | Not ready | main@36f470b | 2026-09-04T19:10:40Z | dependency 'flux-system/healing' is not ready |
| Kustomization | flux-system | healthchecks | Not ready | main@36f470b | 2026-09-04T19:17:13Z | dependency 'flux-system/estate-db-migrate' is not ready |
| Kustomization | flux-system | hindsight | Not ready | main@36f470b | 2026-09-04T19:17:13Z | dependency 'flux-system/llm' is not ready |
| Kustomization | flux-system | image-automation | Not ready | main@190b364 | 2026-09-04T19:52:07Z | Reconciliation in progress |
| Kustomization | flux-system | infra-crew | Not ready | main@9d9d3f9 | 2026-09-04T19:17:14Z | dependency 'flux-system/llm' is not ready |
| Kustomization | flux-system | llm | Not ready | main@36f470b | 2026-09-04T19:17:13Z | dependency 'flux-system/estate-db-migrate' is not ready |
| Kustomization | flux-system | notify | Not ready | main@7f565ca | 2026-09-04T19:50:32Z | Reconciliation in progress |
| Kustomization | flux-system | observability | Not ready | main@36f470b | 2026-09-04T19:17:13Z | dependency 'flux-system/estate-db-migrate' is not ready |
| Kustomization | flux-system | otto-gateway | Not ready | main@9d9d3f9 | 2026-09-04T19:17:14Z | dependency 'flux-system/estate-db-migrate' is not ready |
| Kustomization | flux-system | research-engine | Not ready | main@36f470b | 2026-09-04T19:17:13Z | dependency 'flux-system/llm' is not ready |
| Kustomization | flux-system | science | Not ready | main@36f470b | 2026-09-04T19:10:40Z | dependency 'flux-system/observability' is not ready |
| Kustomization | flux-system | commerce | Suspended |  |  |  |
| Kustomization | flux-system | commerce-data | Suspended |  |  |  |
| Kustomization | flux-system | temporal | Suspended | main@1b323ac | 2026-08-30T05:54:22Z |  |
| HelmRelease | cert-manager | cert-manager | Ready | v1.21.1 | 2026-08-31T07:10:44Z |  |
| HelmRelease | chaos-mesh | chaos-mesh | Ready | 2.8.4 | 2026-08-31T07:12:00Z |  |
| HelmRelease | dagster | dagster | Ready | 1.13.19 | 2026-09-04T18:15:02Z |  |
| HelmRelease | edge | external-dns | Ready | 1.21.1 | 2026-08-31T07:11:28Z |  |
| HelmRelease | edge | traefik | Ready | 41.3.0 | 2026-08-31T07:10:46Z |  |
| HelmRelease | estate-db | cloudnative-pg | Ready | 0.29.0 | 2026-09-04T13:28:55Z |  |
| HelmRelease | event-bus | nats | Ready | 2.14.6 | 2026-09-04T12:12:19Z |  |
| HelmRelease | external-secrets | external-secrets | Ready | 2.9.0 | 2026-09-02T11:40:21Z |  |
| HelmRelease | healing | descheduler | Ready | 0.36.0 | 2026-08-31T07:11:29Z |  |
| HelmRelease | healing | k8sgpt-operator | Ready | 0.2.29 | 2026-08-31T07:11:29Z |  |
| HelmRelease | hindsight | hindsight | Ready | 0.9.2 | 2026-09-04T18:35:26Z |  |
| HelmRelease | identity | oauth2-proxy | Ready | 10.7.0 | 2026-08-29T07:33:02Z |  |
| HelmRelease | keda | keda | Ready | 2.20.2 | 2026-08-31T07:14:43Z |  |
| HelmRelease | keda | keda-add-ons-http | Ready | 0.15.0 | 2026-08-31T07:14:44Z |  |
| HelmRelease | kyverno | kyverno | Ready | 3.9.0 | 2026-09-04T11:31:56Z |  |
| HelmRelease | metrics-server | metrics-server | Ready | 3.14.0 | 2026-08-31T07:11:28Z |  |
| HelmRelease | monitoring | blackbox | Ready | 11.17.2 | 2026-08-31T07:12:07Z |  |
| HelmRelease | monitoring | kube-prometheus-stack | Ready | 88.6.0 | 2026-08-31T07:12:05Z |  |
| HelmRelease | observability | langfuse | Ready | 2.0.2 | 2026-09-04T18:18:00Z |  |
| HelmRelease | observability | signoz | Ready | 0.138.0 | 2026-08-31T07:12:44Z |  |
| HelmRelease | observability | superset | Ready | 0.22.4 | 2026-09-04T18:34:35Z |  |
| HelmRelease | observability-agent | k8s-infra | Ready | 0.17.0 | 2026-09-03T15:19:29Z |  |
| HelmRelease | reloader | reloader | Ready | 2.2.16 | 2026-08-31T07:11:24Z |  |
| HelmRelease | robusta | robusta | Ready | 0.48.0 | 2026-08-31T07:12:01Z |  |
| HelmRelease | spire-mgmt | spire | Ready | 0.30.1 | 2026-08-31T07:12:31Z |  |
| HelmRelease | spire-mgmt | spire-crds | Ready | 0.6.1 | 2026-08-31T07:12:02Z |  |
| HelmRelease | tailscale | tailscale-operator | Ready | 1.102.3 | 2026-09-02T16:32:30Z |  |
| HelmRelease | temporal | temporal | Ready | 1.6.0 | 2026-08-29T19:01:39Z |  |
| HelmRelease | weave-gitops | weave-gitops | Ready | 4.0.36 | 2026-09-04T08:56:00Z |  |
| Kustomization | flux-system | alerts | Ready | main@b569911 | 2026-09-04T19:55:48Z |  |
| Kustomization | flux-system | alerts-github | Ready | main@b569911 | 2026-09-04T19:55:53Z |  |
| Kustomization | flux-system | alerts-secret | Ready | main@b569911 | 2026-09-04T19:55:45Z |  |
| Kustomization | flux-system | autoscaler | Ready | main@b569911 | 2026-09-04T19:55:47Z |  |
| Kustomization | flux-system | backstage-namespace | Ready | main@b569911 | 2026-09-04T19:55:22Z |  |
| Kustomization | flux-system | calico | Ready | main@b569911 | 2026-09-04T19:55:59Z |  |
| Kustomization | flux-system | chaos-mesh | Ready | main@b569911 | 2026-09-04T19:55:54Z |  |
| Kustomization | flux-system | cluster-state | Ready | main@b569911 | 2026-09-04T19:55:41Z |  |
| Kustomization | flux-system | dns | Ready | main@b569911 | 2026-09-04T19:55:50Z |  |
| Kustomization | flux-system | drills | Ready | main@b569911 | 2026-09-04T19:55:55Z |  |
| Kustomization | flux-system | edge | Ready | main@b569911 | 2026-09-04T19:55:32Z |  |
| Kustomization | flux-system | estate-catalog | Ready | latest@sha256:bde1cc743b076aac1760cebecd | 2026-09-04T19:51:27Z |  |
| Kustomization | flux-system | estate-db-operator | Ready | main@b569911 | 2026-09-04T19:55:25Z |  |
| Kustomization | flux-system | event-bus | Ready | main@b569911 | 2026-09-04T19:55:34Z |  |
| Kustomization | flux-system | external-secrets | Ready | main@b569911 | 2026-09-04T19:55:35Z |  |
| Kustomization | flux-system | flux-system | Ready | main@b569911 | 2026-09-04T19:55:30Z |  |
| Kustomization | flux-system | flux-webhook | Ready | main@b569911 | 2026-09-04T19:55:51Z |  |
| Kustomization | flux-system | gateway-api-crds | Ready | v1.5.1@e7677b7 | 2026-09-04T19:55:26Z |  |
| Kustomization | flux-system | hermes-agent | Ready | main@b569911 | 2026-09-04T19:55:57Z |  |
| Kustomization | flux-system | human-vault | Ready | main@b569911 | 2026-09-04T19:55:45Z |  |
| Kustomization | flux-system | identity | Ready | main@b569911 | 2026-09-04T19:55:42Z |  |
| Kustomization | flux-system | keda | Ready | main@b569911 | 2026-09-04T19:55:38Z |  |
| Kustomization | flux-system | kyverno | Ready | main@b569911 | 2026-09-04T19:55:24Z |  |
| Kustomization | flux-system | mcp | Ready | main@b569911 | 2026-09-04T19:55:58Z |  |
| Kustomization | flux-system | metrics-server | Ready | main@b569911 | 2026-09-04T19:55:47Z |  |
| Kustomization | flux-system | monitoring | Ready | main@b569911 | 2026-09-04T19:55:43Z |  |
| Kustomization | flux-system | monitoring-rules | Ready | main@b569911 | 2026-09-04T19:55:51Z |  |
| Kustomization | flux-system | ns-fences | Ready | main@b569911 | 2026-09-04T19:55:33Z |  |
| Kustomization | flux-system | observability-collector | Ready | main@b569911 | 2026-09-04T19:55:38Z |  |
| Kustomization | flux-system | otto-golden | Ready | main@b569911 | 2026-09-04T19:55:49Z |  |
| Kustomization | flux-system | otto-golden-secret | Ready | main@b569911 | 2026-09-04T19:55:39Z |  |
| Kustomization | flux-system | priority-classes | Ready | main@b569911 | 2026-09-04T19:55:23Z |  |
| Kustomization | flux-system | prospector | Ready | main@6c20302 | 2026-09-04T19:51:26Z |  |
| Kustomization | flux-system | prospector-platform | Ready | main@b569911 | 2026-09-04T19:55:35Z |  |
| Kustomization | flux-system | reloader | Ready | main@b569911 | 2026-09-04T19:55:52Z |  |
| Kustomization | flux-system | robusta | Ready | main@b569911 | 2026-09-04T19:55:41Z |  |
| Kustomization | flux-system | scheduling | Ready | main@b569911 | 2026-09-04T19:55:36Z |  |
| Kustomization | flux-system | searxng | Ready | main@b569911 | 2026-09-04T19:55:23Z |  |
| Kustomization | flux-system | secret-store | Ready | main@b569911 | 2026-09-04T19:55:37Z |  |
| Kustomization | flux-system | spire | Ready | main@b569911 | 2026-09-04T19:55:40Z |  |
| Kustomization | flux-system | staging | Ready | main@b569911 | 2026-09-04T19:55:22Z |  |
| Kustomization | flux-system | tailscale | Ready | main@b569911 | 2026-09-04T19:55:44Z |  |
| Kustomization | flux-system | verification | Ready | main@b569911 | 2026-09-04T19:55:50Z |  |
| Kustomization | flux-system | weave-gitops | Ready | main@b569911 | 2026-09-04T19:55:53Z |  |
