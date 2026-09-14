# Flux: what is applied

Read from the cluster receipt taken at 2026-09-14T15:45:16Z. Every Kustomization and HelmRelease, with the revision Flux last applied. **Suspended** is a switch somebody turned off on purpose (temporal, commerce, commerce-data, event-bus), not a defect; **Unknown** is a row Flux has never graded.

**116 objects: 99 ready, 15 not ready, 0 unknown, 2 suspended.**

## Not ready right now

- **HelmRelease commerce/lago** since 2026-09-14T13:45:55Z: Helm install failed for release commerce/lago with chart lago@1.28.0: failed early due to stalled resources: [Deployment/commerce/lago-worker status: 'Failed']
- **Kustomization flux-system/backstage** since 2026-09-14T15:44:18Z: dependency 'flux-system/estate-db-migrate' is not ready
- **Kustomization flux-system/chaos** since 2026-09-14T15:45:08Z: dependency 'flux-system/observability' is not ready
- **Kustomization flux-system/commerce** since 2026-09-14T14:20:45Z: dependency 'flux-system/commerce-data' is not ready
- **Kustomization flux-system/commerce-data** since 2026-09-14T15:44:09Z: dependency 'flux-system/estate-db' is not ready
- **Kustomization flux-system/dagster** since 2026-09-14T15:43:58Z: dependency 'flux-system/estate-db-migrate' is not ready
- **Kustomization flux-system/estate-db** since 2026-09-14T15:43:13Z: Database/estate-db/aevum-evidence dry-run failed (InternalError): Internal error occurred: failed calling webhook "vdatabase.cnpg.io": failed to call webhook: Post "https://cnpg-webhook-service.estate-db.svc:443/validate-postgresql-cnpg-io-v1-database?timeout=10s": EOF 
- **Kustomization flux-system/estate-db-migrate** since 2026-09-14T15:43:51Z: dependency 'flux-system/estate-db' is not ready
- **Kustomization flux-system/guacamole** since 2026-09-14T15:44:31Z: dependency 'flux-system/estate-db-migrate' is not ready
- **Kustomization flux-system/llm** since 2026-09-14T15:44:48Z: dependency 'flux-system/estate-db-migrate' is not ready
- **Kustomization flux-system/mcp** since 2026-09-14T15:43:38Z: health check failed after 10m0.032336796s: timeout waiting for: [Deployment/mcp/estate-mcp status: 'InProgress']
- **Kustomization flux-system/observability** since 2026-09-14T15:44:01Z: dependency 'flux-system/estate-db-migrate' is not ready
- **Kustomization flux-system/otto-gateway** since 2026-09-14T15:43:50Z: ExternalSecret/otto-gateway/hermes-agent-env dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-secrets.io": failed to call webhook: Post "https://external-secrets-webhook.external-secrets.svc:443/validate-external-secrets-io-v1-externalsecret?timeout=5s": context deadline exceeded 
- **Kustomization flux-system/research-engine** since 2026-09-14T15:44:53Z: dependency 'flux-system/llm' is not ready
- **Kustomization flux-system/science** since 2026-09-14T15:44:29Z: dependency 'flux-system/observability' is not ready

## Every row

| Kind | Namespace | Name | State | Applied revision | Since | Message |
|---|---|---|---|---|---|---|
| HelmRelease | commerce | lago | Not ready | 1.28.0 | 2026-09-14T13:45:55Z | Helm install failed for release commerce/lago with chart lago@1.28.0: failed early due to stalled resources: [Deployment/commerce/lago-worker status: 'Failed'] |
| Kustomization | flux-system | backstage | Not ready | main@a9a9418 | 2026-09-14T15:44:18Z | dependency 'flux-system/estate-db-migrate' is not ready |
| Kustomization | flux-system | chaos | Not ready | main@a9a9418 | 2026-09-14T15:45:08Z | dependency 'flux-system/observability' is not ready |
| Kustomization | flux-system | commerce | Not ready | main@abea14d | 2026-09-14T14:20:45Z | dependency 'flux-system/commerce-data' is not ready |
| Kustomization | flux-system | commerce-data | Not ready | main@421242f | 2026-09-14T15:44:09Z | dependency 'flux-system/estate-db' is not ready |
| Kustomization | flux-system | dagster | Not ready | main@a9a9418 | 2026-09-14T15:43:58Z | dependency 'flux-system/estate-db-migrate' is not ready |
| Kustomization | flux-system | estate-db | Not ready | main@a9a9418 | 2026-09-14T15:43:13Z | Database/estate-db/aevum-evidence dry-run failed (InternalError): Internal error occurred: failed calling webhook "vdatabase.cnpg.io": failed to call webhook: P |
| Kustomization | flux-system | estate-db-migrate | Not ready | main@a9a9418 | 2026-09-14T15:43:51Z | dependency 'flux-system/estate-db' is not ready |
| Kustomization | flux-system | guacamole | Not ready | main@a9a9418 | 2026-09-14T15:44:31Z | dependency 'flux-system/estate-db-migrate' is not ready |
| Kustomization | flux-system | llm | Not ready | main@a9a9418 | 2026-09-14T15:44:48Z | dependency 'flux-system/estate-db-migrate' is not ready |
| Kustomization | flux-system | mcp | Not ready | main@6558812 | 2026-09-14T15:43:38Z | health check failed after 10m0.032336796s: timeout waiting for: [Deployment/mcp/estate-mcp status: 'InProgress'] |
| Kustomization | flux-system | observability | Not ready | main@a9a9418 | 2026-09-14T15:44:01Z | dependency 'flux-system/estate-db-migrate' is not ready |
| Kustomization | flux-system | otto-gateway | Not ready | main@a9a9418 | 2026-09-14T15:43:50Z | ExternalSecret/otto-gateway/hermes-agent-env dry-run failed (InternalError): Internal error occurred: failed calling webhook "validate.externalsecret.external-s |
| Kustomization | flux-system | research-engine | Not ready | main@a9a9418 | 2026-09-14T15:44:53Z | dependency 'flux-system/llm' is not ready |
| Kustomization | flux-system | science | Not ready | main@a9a9418 | 2026-09-14T15:44:29Z | dependency 'flux-system/observability' is not ready |
| HelmRelease | tigera-operator | tigera-operator | Suspended | v3.32.2 | 2026-09-06T19:38:02Z |  |
| Kustomization | flux-system | temporal | Suspended | main@1b323ac | 2026-09-08T20:23:54Z |  |
| HelmRelease | cert-manager | cert-manager | Ready | v1.21.1 | 2026-09-08T11:56:22Z |  |
| HelmRelease | chaos-mesh | chaos-mesh | Ready | 2.8.4 | 2026-09-13T04:26:37Z |  |
| HelmRelease | crossplane-system | crossplane | Ready | 2.4.0 | 2026-09-08T07:05:25Z |  |
| HelmRelease | dagster | dagster | Ready | 1.13.19 | 2026-09-12T12:32:50Z |  |
| HelmRelease | edge | external-dns | Ready | 1.21.1 | 2026-09-06T19:33:35Z |  |
| HelmRelease | edge | traefik | Ready | 41.3.0 | 2026-09-06T19:35:13Z |  |
| HelmRelease | estate-db | cloudnative-pg | Ready | 0.29.0 | 2026-09-06T19:45:25Z |  |
| HelmRelease | event-bus | nats | Ready | 2.14.6 | 2026-09-06T19:39:37Z |  |
| HelmRelease | external-secrets | external-secrets | Ready | 2.9.0 | 2026-09-08T11:57:40Z |  |
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
| HelmRelease | observability-agent | k8s-infra | Ready | 0.17.0 | 2026-09-09T14:28:44Z |  |
| HelmRelease | reloader | reloader | Ready | 2.2.16 | 2026-09-06T19:33:25Z |  |
| HelmRelease | robusta | robusta | Ready | 0.48.0 | 2026-09-06T20:26:45Z |  |
| HelmRelease | spire-mgmt | spire | Ready | 0.30.1 | 2026-09-08T09:39:33Z |  |
| HelmRelease | spire-mgmt | spire-crds | Ready | 0.6.1 | 2026-09-06T20:26:47Z |  |
| HelmRelease | tailscale | tailscale-operator | Ready | 1.102.3 | 2026-09-06T19:33:35Z |  |
| HelmRelease | temporal | temporal | Ready | 1.6.0 | 2026-09-08T23:12:29Z |  |
| HelmRelease | trivy-system | trivy-operator | Ready | 0.36.0 | 2026-09-06T20:26:45Z |  |
| HelmRelease | weave-gitops | weave-gitops | Ready | 4.0.36 | 2026-09-06T20:26:45Z |  |
| Kustomization | flux-system | agent-workforce | Ready | main@a9a9418 | 2026-09-14T15:44:49Z |  |
| Kustomization | flux-system | alerts | Ready | main@a9a9418 | 2026-09-14T15:43:29Z |  |
| Kustomization | flux-system | alerts-github | Ready | main@a9a9418 | 2026-09-14T15:43:42Z |  |
| Kustomization | flux-system | alerts-secret | Ready | main@a9a9418 | 2026-09-14T15:43:15Z |  |
| Kustomization | flux-system | autoscaler | Ready | main@a9a9418 | 2026-09-14T15:43:25Z |  |
| Kustomization | flux-system | backstage-namespace | Ready | main@a9a9418 | 2026-09-14T15:40:13Z |  |
| Kustomization | flux-system | calico | Ready | main@a9a9418 | 2026-09-14T15:41:12Z |  |
| Kustomization | flux-system | chaos-mesh | Ready | main@a9a9418 | 2026-09-14T15:41:18Z |  |
| Kustomization | flux-system | cluster-state | Ready | main@a9a9418 | 2026-09-14T15:43:42Z |  |
| Kustomization | flux-system | concierge | Ready | main@a9a9418 | 2026-09-14T15:43:30Z |  |
| Kustomization | flux-system | cross-node-drill | Ready | main@a9a9418 | 2026-09-14T15:40:10Z |  |
| Kustomization | flux-system | crossplane | Ready | main@a9a9418 | 2026-09-14T15:43:10Z |  |
| Kustomization | flux-system | crossplane-providerconfig | Ready | main@a9a9418 | 2026-09-14T15:44:00Z |  |
| Kustomization | flux-system | crossplane-providers | Ready | main@a9a9418 | 2026-09-14T15:43:53Z |  |
| Kustomization | flux-system | dns | Ready | main@a9a9418 | 2026-09-14T15:43:06Z |  |
| Kustomization | flux-system | drills | Ready | main@a9a9418 | 2026-09-14T15:44:16Z |  |
| Kustomization | flux-system | edge | Ready | main@a9a9418 | 2026-09-14T15:43:20Z |  |
| Kustomization | flux-system | estate-catalog | Ready | latest@sha256:c7d6047f10973294dd3de3b9ac | 2026-09-14T15:41:13Z |  |
| Kustomization | flux-system | estate-db-operator | Ready | main@a9a9418 | 2026-09-14T15:40:59Z |  |
| Kustomization | flux-system | event-bus | Ready | main@a9a9418 | 2026-09-14T15:41:20Z |  |
| Kustomization | flux-system | external-secrets | Ready | main@a9a9418 | 2026-09-14T15:41:44Z |  |
| Kustomization | flux-system | feature-register | Ready | main@a9a9418 | 2026-09-14T15:41:04Z |  |
| Kustomization | flux-system | flux-system | Ready | main@a9a9418 | 2026-09-14T15:43:08Z |  |
| Kustomization | flux-system | flux-webhook | Ready | main@a9a9418 | 2026-09-14T15:43:26Z |  |
| Kustomization | flux-system | gateway-api-crds | Ready | v1.5.1@e7677b7 | 2026-09-14T15:40:30Z |  |
| Kustomization | flux-system | gvisor-runtime | Ready | main@a9a9418 | 2026-09-14T15:44:22Z |  |
| Kustomization | flux-system | healing | Ready | main@a9a9418 | 2026-09-14T15:43:03Z |  |
| Kustomization | flux-system | healing-analyzer | Ready | main@a9a9418 | 2026-09-14T15:35:03Z |  |
| Kustomization | flux-system | healing-k8sgpt | Ready | main@a9a9418 | 2026-09-14T15:44:49Z |  |
| Kustomization | flux-system | healthchecks | Ready | main@a9a9418 | 2026-09-14T15:43:51Z |  |
| Kustomization | flux-system | hermes-agent | Ready | main@a9a9418 | 2026-09-14T15:44:10Z |  |
| Kustomization | flux-system | hindsight | Ready | main@a9a9418 | 2026-09-14T15:34:47Z |  |
| Kustomization | flux-system | human-vault | Ready | main@a9a9418 | 2026-09-14T15:43:12Z |  |
| Kustomization | flux-system | human-vault-bridge | Ready | main@a9a9418 | 2026-09-14T15:43:27Z |  |
| Kustomization | flux-system | identity | Ready | main@a9a9418 | 2026-09-14T15:43:08Z |  |
| Kustomization | flux-system | image-automation | Ready | main@a9a9418 | 2026-09-14T15:43:27Z |  |
| Kustomization | flux-system | jit | Ready | main@a9a9418 | 2026-09-14T15:42:38Z |  |
| Kustomization | flux-system | keda | Ready | main@a9a9418 | 2026-09-14T15:42:31Z |  |
| Kustomization | flux-system | kyverno | Ready | main@a9a9418 | 2026-09-14T15:41:12Z |  |
| Kustomization | flux-system | metrics-server | Ready | main@a9a9418 | 2026-09-14T15:42:58Z |  |
| Kustomization | flux-system | monitoring | Ready | main@a9a9418 | 2026-09-14T15:43:24Z |  |
| Kustomization | flux-system | monitoring-rules | Ready | main@a9a9418 | 2026-09-14T15:43:32Z |  |
| Kustomization | flux-system | nodesoftware-operator | Ready | main@a9a9418 | 2026-09-14T15:43:34Z |  |
| Kustomization | flux-system | notify | Ready | main@a9a9418 | 2026-09-14T15:42:52Z |  |
| Kustomization | flux-system | ns-fences | Ready | main@a9a9418 | 2026-09-14T15:42:28Z |  |
| Kustomization | flux-system | observability-collector | Ready | main@a9a9418 | 2026-09-14T15:42:20Z |  |
| Kustomization | flux-system | otto-golden | Ready | main@a9a9418 | 2026-09-14T15:43:46Z |  |
| Kustomization | flux-system | otto-golden-secret | Ready | main@a9a9418 | 2026-09-14T15:43:32Z |  |
| Kustomization | flux-system | priority-classes | Ready | main@a9a9418 | 2026-09-14T15:42:40Z |  |
| Kustomization | flux-system | prospector | Ready | main@7453d76 | 2026-09-14T15:41:06Z |  |
| Kustomization | flux-system | prospector-platform | Ready | main@a9a9418 | 2026-09-14T15:40:47Z |  |
| Kustomization | flux-system | rbac | Ready | main@a9a9418 | 2026-09-14T15:40:38Z |  |
| Kustomization | flux-system | rbac-floor | Ready | main@a9a9418 | 2026-09-14T15:40:42Z |  |
| Kustomization | flux-system | rbac-identity | Ready | main@a9a9418 | 2026-09-14T15:40:31Z |  |
| Kustomization | flux-system | reloader | Ready | main@a9a9418 | 2026-09-14T15:43:25Z |  |
| Kustomization | flux-system | robusta | Ready | main@a9a9418 | 2026-09-14T15:43:12Z |  |
| Kustomization | flux-system | router-events | Ready | main@a9a9418 | 2026-09-14T15:44:46Z |  |
| Kustomization | flux-system | sandbox-launch | Ready | main@a9a9418 | 2026-09-14T15:42:28Z |  |
| Kustomization | flux-system | sandbox-live | Ready | sandbox/launch@4830a6e | 2026-09-14T15:44:19Z |  |
| Kustomization | flux-system | scheduling | Ready | main@a9a9418 | 2026-09-14T15:42:46Z |  |
| Kustomization | flux-system | searxng | Ready | main@a9a9418 | 2026-09-14T15:40:27Z |  |
| Kustomization | flux-system | secret-store | Ready | main@a9a9418 | 2026-09-14T15:43:28Z |  |
| Kustomization | flux-system | spire | Ready | main@a9a9418 | 2026-09-14T15:42:13Z |  |
| Kustomization | flux-system | staging | Ready | main@a9a9418 | 2026-09-14T15:41:28Z |  |
| Kustomization | flux-system | tailscale | Ready | main@a9a9418 | 2026-09-14T15:43:18Z |  |
| Kustomization | flux-system | trivy | Ready | main@a9a9418 | 2026-09-14T15:40:29Z |  |
| Kustomization | flux-system | verification | Ready | main@a9a9418 | 2026-09-14T15:43:30Z |  |
| Kustomization | flux-system | weave-gitops | Ready | main@a9a9418 | 2026-09-14T15:44:08Z |  |
