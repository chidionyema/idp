# Flux: what is applied

Read from the cluster receipt taken at 2026-09-08T17:30:49Z. Every Kustomization and HelmRelease, with the revision Flux last applied. **Suspended** is a switch somebody turned off on purpose (temporal, commerce, commerce-data, event-bus), not a defect; **Unknown** is a row Flux has never graded.

**114 objects: 48 ready, 64 not ready, 0 unknown, 2 suspended.**

## Not ready right now

- **HelmRelease commerce/lago** since 2026-09-08T17:20:59Z: Helm install failed for release commerce/lago with chart lago@1.28.0: failed pre-install: timeout waiting for: [Job/commerce/lago-migrate-db status: 'InProgress']
- **HelmRelease hindsight/hindsight** since 2026-09-08T17:23:35Z: Running 'upgrade' action with timeout of 15m0s
- **Kustomization flux-system/agent-workforce** since 2026-09-08T17:30:11Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/alerts** since 2026-09-08T17:30:10Z: dependency 'flux-system/alerts-secret' is not ready
- **Kustomization flux-system/alerts-github** since 2026-09-08T17:30:09Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/alerts-secret** since 2026-09-08T17:30:09Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/autoscaler** since 2026-09-08T17:30:09Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/backstage** since 2026-09-08T17:30:10Z: dependency 'flux-system/backstage-namespace' revision is not up to date
- **Kustomization flux-system/chaos** since 2026-09-08T17:30:11Z: dependency 'flux-system/chaos-mesh' is not ready
- **Kustomization flux-system/chaos-mesh** since 2026-09-08T17:30:07Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/cluster-state** since 2026-09-08T17:30:08Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/commerce** since 2026-09-08T17:21:57Z: Reconciliation in progress
- **Kustomization flux-system/commerce-data** since 2026-09-08T17:30:10Z: dependency 'flux-system/external-secrets' is not ready
- **Kustomization flux-system/crossplane** since 2026-09-08T17:30:07Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/crossplane-providerconfig** since 2026-09-08T17:30:08Z: dependency 'flux-system/crossplane-providers' revision is not up to date
- **Kustomization flux-system/cyrus** since 2026-09-08T17:30:10Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/dagster** since 2026-09-08T17:30:10Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/dns** since 2026-09-08T17:30:08Z: dependency 'flux-system/edge' is not ready
- **Kustomization flux-system/drills** since 2026-09-08T17:30:10Z: dependency 'flux-system/alerts-github' is not ready
- **Kustomization flux-system/edge** since 2026-09-08T17:30:06Z: dependency 'flux-system/kyverno' revision is not up to date
- **Kustomization flux-system/estate-db** since 2026-09-08T17:30:09Z: dependency 'flux-system/estate-db-operator' revision is not up to date
- **Kustomization flux-system/estate-db-migrate** since 2026-09-08T17:30:10Z: dependency 'flux-system/estate-db' is not ready
- **Kustomization flux-system/event-bus** since 2026-09-08T17:30:07Z: dependency 'flux-system/priority-classes' revision is not up to date
- **Kustomization flux-system/external-secrets** since 2026-09-08T17:30:07Z: dependency 'flux-system/edge' is not ready
- **Kustomization flux-system/feature-register** since 2026-09-08T17:30:06Z: dependency 'flux-system/backstage-namespace' revision is not up to date
- **Kustomization flux-system/flux-system** since 2026-09-08T17:30:12Z: Reconciliation in progress
- **Kustomization flux-system/flux-webhook** since 2026-09-08T17:30:09Z: dependency 'flux-system/edge' is not ready
- **Kustomization flux-system/guacamole** since 2026-09-08T17:30:10Z: dependency 'flux-system/identity' is not ready
- **Kustomization flux-system/gvisor-runtime** since 2026-09-08T10:27:58Z: dependency 'flux-system/nodesoftware-operator' is not ready
- **Kustomization flux-system/healing** since 2026-09-08T17:30:07Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/healing-analyzer** since 2026-09-08T17:30:11Z: dependency 'flux-system/healing-k8sgpt' is not ready
- **Kustomization flux-system/healing-k8sgpt** since 2026-09-08T17:30:11Z: dependency 'flux-system/healing' is not ready
- **Kustomization flux-system/healthchecks** since 2026-09-08T17:30:11Z: dependency 'flux-system/identity' is not ready
- **Kustomization flux-system/hermes-agent** since 2026-09-08T17:30:10Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/hindsight** since 2026-09-08T17:22:37Z: Reconciliation in progress
- **Kustomization flux-system/human-vault** since 2026-09-08T17:30:08Z: dependency 'flux-system/external-secrets' is not ready
- **Kustomization flux-system/human-vault-bridge** since 2026-09-08T17:30:10Z: dependency 'flux-system/human-vault' is not ready
- **Kustomization flux-system/identity** since 2026-09-08T17:30:09Z: dependency 'flux-system/edge' is not ready
- **Kustomization flux-system/image-automation** since 2026-09-08T17:30:09Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/keda** since 2026-09-08T17:30:07Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/llm** since 2026-09-08T17:30:11Z: dependency 'flux-system/edge' is not ready
- **Kustomization flux-system/mcp** since 2026-09-08T17:30:10Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/monitoring** since 2026-09-08T17:30:09Z: dependency 'flux-system/edge' is not ready
- **Kustomization flux-system/monitoring-rules** since 2026-09-08T17:30:10Z: dependency 'flux-system/monitoring' is not ready
- **Kustomization flux-system/nodesoftware-operator** since 2026-09-08T17:30:06Z: health check failed after 8m15.177598441s: failed early due to stalled resources: [Deployment/nodesoftware-operator/nodesoftware-operator status: 'Failed']
- **Kustomization flux-system/notify** since 2026-09-08T17:30:10Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/ns-fences** since 2026-09-08T17:29:53Z: Reconciliation in progress
- **Kustomization flux-system/observability** since 2026-09-08T17:30:11Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/otto-gateway** since 2026-09-08T17:30:11Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/otto-golden** since 2026-09-08T17:30:10Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/otto-golden-secret** since 2026-09-08T17:30:08Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/prospector** since 2026-09-08T17:23:27Z: health check failed after 10m0.040090055s: timeout waiting for: [ClusterIssuer/prospector-letsencrypt status: 'InProgress']
- **Kustomization flux-system/prospector-platform** since 2026-09-08T17:30:08Z: dependency 'flux-system/edge' is not ready
- **Kustomization flux-system/reloader** since 2026-09-08T17:30:09Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/research-engine** since 2026-09-08T17:30:11Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/robusta** since 2026-09-08T17:30:09Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/sandbox-launch** since 2026-09-08T17:30:07Z: dependency 'flux-system/edge' is not ready
- **Kustomization flux-system/scheduling** since 2026-09-08T17:30:07Z: dependency 'flux-system/edge' is not ready
- **Kustomization flux-system/science** since 2026-09-08T17:30:11Z: dependency 'flux-system/observability' is not ready
- **Kustomization flux-system/secret-store** since 2026-09-08T17:30:08Z: dependency 'flux-system/external-secrets' is not ready
- **Kustomization flux-system/spire** since 2026-09-08T17:30:07Z: dependency 'flux-system/scheduling' is not ready
- **Kustomization flux-system/tailscale** since 2026-09-08T17:30:08Z: dependency 'flux-system/secret-store' is not ready
- **Kustomization flux-system/verification** since 2026-09-08T17:30:09Z: dependency 'flux-system/backstage-namespace' revision is not up to date
- **Kustomization flux-system/weave-gitops** since 2026-09-08T17:30:10Z: dependency 'flux-system/identity' is not ready

## Every row

| Kind | Namespace | Name | State | Applied revision | Since | Message |
|---|---|---|---|---|---|---|
| HelmRelease | commerce | lago | Not ready | 1.28.0 | 2026-09-08T17:20:59Z | Helm install failed for release commerce/lago with chart lago@1.28.0: failed pre-install: timeout waiting for: [Job/commerce/lago-migrate-db status: 'InProgress |
| HelmRelease | hindsight | hindsight | Not ready | 0.9.2 | 2026-09-08T17:23:35Z | Running 'upgrade' action with timeout of 15m0s |
| Kustomization | flux-system | agent-workforce | Not ready | main@a613fd6 | 2026-09-08T17:30:11Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | alerts | Not ready | main@a613fd6 | 2026-09-08T17:30:10Z | dependency 'flux-system/alerts-secret' is not ready |
| Kustomization | flux-system | alerts-github | Not ready | main@a613fd6 | 2026-09-08T17:30:09Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | alerts-secret | Not ready | main@a613fd6 | 2026-09-08T17:30:09Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | autoscaler | Not ready | main@a613fd6 | 2026-09-08T17:30:09Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | backstage | Not ready | main@a613fd6 | 2026-09-08T17:30:10Z | dependency 'flux-system/backstage-namespace' revision is not up to date |
| Kustomization | flux-system | chaos | Not ready | main@a613fd6 | 2026-09-08T17:30:11Z | dependency 'flux-system/chaos-mesh' is not ready |
| Kustomization | flux-system | chaos-mesh | Not ready | main@a613fd6 | 2026-09-08T17:30:07Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | cluster-state | Not ready | main@a613fd6 | 2026-09-08T17:30:08Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | commerce | Not ready | main@a613fd6 | 2026-09-08T17:21:57Z | Reconciliation in progress |
| Kustomization | flux-system | commerce-data | Not ready | main@a613fd6 | 2026-09-08T17:30:10Z | dependency 'flux-system/external-secrets' is not ready |
| Kustomization | flux-system | crossplane | Not ready | main@a613fd6 | 2026-09-08T17:30:07Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | crossplane-providerconfig | Not ready | main@a613fd6 | 2026-09-08T17:30:08Z | dependency 'flux-system/crossplane-providers' revision is not up to date |
| Kustomization | flux-system | cyrus | Not ready | main@a613fd6 | 2026-09-08T17:30:10Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | dagster | Not ready | main@a613fd6 | 2026-09-08T17:30:10Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | dns | Not ready | main@a613fd6 | 2026-09-08T17:30:08Z | dependency 'flux-system/edge' is not ready |
| Kustomization | flux-system | drills | Not ready | main@a613fd6 | 2026-09-08T17:30:10Z | dependency 'flux-system/alerts-github' is not ready |
| Kustomization | flux-system | edge | Not ready | main@a613fd6 | 2026-09-08T17:30:06Z | dependency 'flux-system/kyverno' revision is not up to date |
| Kustomization | flux-system | estate-db | Not ready | main@a613fd6 | 2026-09-08T17:30:09Z | dependency 'flux-system/estate-db-operator' revision is not up to date |
| Kustomization | flux-system | estate-db-migrate | Not ready | main@a613fd6 | 2026-09-08T17:30:10Z | dependency 'flux-system/estate-db' is not ready |
| Kustomization | flux-system | event-bus | Not ready | main@a613fd6 | 2026-09-08T17:30:07Z | dependency 'flux-system/priority-classes' revision is not up to date |
| Kustomization | flux-system | external-secrets | Not ready | main@a613fd6 | 2026-09-08T17:30:07Z | dependency 'flux-system/edge' is not ready |
| Kustomization | flux-system | feature-register | Not ready | main@a613fd6 | 2026-09-08T17:30:06Z | dependency 'flux-system/backstage-namespace' revision is not up to date |
| Kustomization | flux-system | flux-system | Not ready | main@a613fd6 | 2026-09-08T17:30:12Z | Reconciliation in progress |
| Kustomization | flux-system | flux-webhook | Not ready | main@a613fd6 | 2026-09-08T17:30:09Z | dependency 'flux-system/edge' is not ready |
| Kustomization | flux-system | guacamole | Not ready | main@a613fd6 | 2026-09-08T17:30:10Z | dependency 'flux-system/identity' is not ready |
| Kustomization | flux-system | gvisor-runtime | Not ready | main@8e1bade | 2026-09-08T10:27:58Z | dependency 'flux-system/nodesoftware-operator' is not ready |
| Kustomization | flux-system | healing | Not ready | main@a613fd6 | 2026-09-08T17:30:07Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | healing-analyzer | Not ready | main@a613fd6 | 2026-09-08T17:30:11Z | dependency 'flux-system/healing-k8sgpt' is not ready |
| Kustomization | flux-system | healing-k8sgpt | Not ready | main@a613fd6 | 2026-09-08T17:30:11Z | dependency 'flux-system/healing' is not ready |
| Kustomization | flux-system | healthchecks | Not ready | main@a613fd6 | 2026-09-08T17:30:11Z | dependency 'flux-system/identity' is not ready |
| Kustomization | flux-system | hermes-agent | Not ready | main@a613fd6 | 2026-09-08T17:30:10Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | hindsight | Not ready | main@a295542 | 2026-09-08T17:22:37Z | Reconciliation in progress |
| Kustomization | flux-system | human-vault | Not ready | main@a613fd6 | 2026-09-08T17:30:08Z | dependency 'flux-system/external-secrets' is not ready |
| Kustomization | flux-system | human-vault-bridge | Not ready | main@a613fd6 | 2026-09-08T17:30:10Z | dependency 'flux-system/human-vault' is not ready |
| Kustomization | flux-system | identity | Not ready | main@a613fd6 | 2026-09-08T17:30:09Z | dependency 'flux-system/edge' is not ready |
| Kustomization | flux-system | image-automation | Not ready | main@a613fd6 | 2026-09-08T17:30:09Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | keda | Not ready | main@a613fd6 | 2026-09-08T17:30:07Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | llm | Not ready | main@a613fd6 | 2026-09-08T17:30:11Z | dependency 'flux-system/edge' is not ready |
| Kustomization | flux-system | mcp | Not ready | main@a613fd6 | 2026-09-08T17:30:10Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | monitoring | Not ready | main@a613fd6 | 2026-09-08T17:30:09Z | dependency 'flux-system/edge' is not ready |
| Kustomization | flux-system | monitoring-rules | Not ready | main@a613fd6 | 2026-09-08T17:30:10Z | dependency 'flux-system/monitoring' is not ready |
| Kustomization | flux-system | nodesoftware-operator | Not ready | main@8e1bade | 2026-09-08T17:30:06Z | health check failed after 8m15.177598441s: failed early due to stalled resources: [Deployment/nodesoftware-operator/nodesoftware-operator status: 'Failed'] |
| Kustomization | flux-system | notify | Not ready | main@a613fd6 | 2026-09-08T17:30:10Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | ns-fences | Not ready | main@a613fd6 | 2026-09-08T17:29:53Z | Reconciliation in progress |
| Kustomization | flux-system | observability | Not ready | main@a613fd6 | 2026-09-08T17:30:11Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | otto-gateway | Not ready | main@aa3ee81 | 2026-09-08T17:30:11Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | otto-golden | Not ready | main@a613fd6 | 2026-09-08T17:30:10Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | otto-golden-secret | Not ready | main@a613fd6 | 2026-09-08T17:30:08Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | prospector | Not ready | main@7453d76 | 2026-09-08T17:23:27Z | health check failed after 10m0.040090055s: timeout waiting for: [ClusterIssuer/prospector-letsencrypt status: 'InProgress'] |
| Kustomization | flux-system | prospector-platform | Not ready | main@a613fd6 | 2026-09-08T17:30:08Z | dependency 'flux-system/edge' is not ready |
| Kustomization | flux-system | reloader | Not ready | main@a613fd6 | 2026-09-08T17:30:09Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | research-engine | Not ready | main@a613fd6 | 2026-09-08T17:30:11Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | robusta | Not ready | main@a613fd6 | 2026-09-08T17:30:09Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | sandbox-launch | Not ready | main@a613fd6 | 2026-09-08T17:30:07Z | dependency 'flux-system/edge' is not ready |
| Kustomization | flux-system | scheduling | Not ready | main@a613fd6 | 2026-09-08T17:30:07Z | dependency 'flux-system/edge' is not ready |
| Kustomization | flux-system | science | Not ready | main@a613fd6 | 2026-09-08T17:30:11Z | dependency 'flux-system/observability' is not ready |
| Kustomization | flux-system | secret-store | Not ready | main@a613fd6 | 2026-09-08T17:30:08Z | dependency 'flux-system/external-secrets' is not ready |
| Kustomization | flux-system | spire | Not ready | main@a613fd6 | 2026-09-08T17:30:07Z | dependency 'flux-system/scheduling' is not ready |
| Kustomization | flux-system | tailscale | Not ready | main@a613fd6 | 2026-09-08T17:30:08Z | dependency 'flux-system/secret-store' is not ready |
| Kustomization | flux-system | verification | Not ready | main@a613fd6 | 2026-09-08T17:30:09Z | dependency 'flux-system/backstage-namespace' revision is not up to date |
| Kustomization | flux-system | weave-gitops | Not ready | main@a613fd6 | 2026-09-08T17:30:10Z | dependency 'flux-system/identity' is not ready |
| HelmRelease | tigera-operator | tigera-operator | Suspended | v3.32.2 | 2026-09-06T19:38:02Z |  |
| Kustomization | flux-system | temporal | Suspended | main@1b323ac | 2026-08-30T05:54:22Z |  |
| HelmRelease | cert-manager | cert-manager | Ready | v1.21.1 | 2026-09-08T11:56:22Z |  |
| HelmRelease | chaos-mesh | chaos-mesh | Ready | 2.8.4 | 2026-09-08T09:36:49Z |  |
| HelmRelease | crossplane-system | crossplane | Ready | 2.4.0 | 2026-09-08T07:05:25Z |  |
| HelmRelease | dagster | dagster | Ready | 1.13.19 | 2026-09-08T06:32:55Z |  |
| HelmRelease | edge | external-dns | Ready | 1.21.1 | 2026-09-06T19:33:35Z |  |
| HelmRelease | edge | traefik | Ready | 41.3.0 | 2026-09-06T19:35:13Z |  |
| HelmRelease | estate-db | cloudnative-pg | Ready | 0.29.0 | 2026-09-06T19:45:25Z |  |
| HelmRelease | event-bus | nats | Ready | 2.14.6 | 2026-09-06T19:39:37Z |  |
| HelmRelease | external-secrets | external-secrets | Ready | 2.9.0 | 2026-09-08T11:57:40Z |  |
| HelmRelease | healing | descheduler | Ready | 0.36.0 | 2026-09-08T10:45:39Z |  |
| HelmRelease | healing | k8sgpt-operator | Ready | 0.2.29 | 2026-09-08T12:01:53Z |  |
| HelmRelease | identity | oauth2-proxy | Ready | 10.7.0 | 2026-09-08T10:18:34Z |  |
| HelmRelease | keda | keda | Ready | 2.20.2 | 2026-09-08T10:19:32Z |  |
| HelmRelease | keda | keda-add-ons-http | Ready | 0.15.0 | 2026-09-08T10:20:22Z |  |
| HelmRelease | kyverno | kyverno | Ready | 3.9.0 | 2026-09-08T10:19:02Z |  |
| HelmRelease | metrics-server | metrics-server | Ready | 3.14.0 | 2026-09-06T19:34:02Z |  |
| HelmRelease | monitoring | blackbox | Ready | 11.17.2 | 2026-09-06T19:47:10Z |  |
| HelmRelease | monitoring | kube-prometheus-stack | Ready | 88.6.0 | 2026-09-06T20:26:45Z |  |
| HelmRelease | observability | langfuse | Ready | 2.0.2 | 2026-09-08T08:30:33Z |  |
| HelmRelease | observability | signoz | Ready | 0.138.0 | 2026-09-08T12:05:11Z |  |
| HelmRelease | observability | superset | Ready | 0.22.4 | 2026-09-06T19:46:05Z |  |
| HelmRelease | observability-agent | k8s-infra | Ready | 0.17.0 | 2026-09-08T11:24:56Z |  |
| HelmRelease | reloader | reloader | Ready | 2.2.16 | 2026-09-06T19:33:25Z |  |
| HelmRelease | robusta | robusta | Ready | 0.48.0 | 2026-09-06T20:26:45Z |  |
| HelmRelease | spire-mgmt | spire | Ready | 0.30.1 | 2026-09-08T09:39:33Z |  |
| HelmRelease | spire-mgmt | spire-crds | Ready | 0.6.1 | 2026-09-06T20:26:47Z |  |
| HelmRelease | tailscale | tailscale-operator | Ready | 1.102.3 | 2026-09-06T19:33:35Z |  |
| HelmRelease | temporal | temporal | Ready | 1.6.0 | 2026-09-06T19:33:25Z |  |
| HelmRelease | trivy-system | trivy-operator | Ready | 0.36.0 | 2026-09-06T20:26:45Z |  |
| HelmRelease | weave-gitops | weave-gitops | Ready | 4.0.36 | 2026-09-06T20:26:45Z |  |
| Kustomization | flux-system | backstage-namespace | Ready | main@a613fd6 | 2026-09-08T17:29:16Z |  |
| Kustomization | flux-system | calico | Ready | main@a613fd6 | 2026-09-08T17:29:10Z |  |
| Kustomization | flux-system | crossplane-providers | Ready | main@a613fd6 | 2026-09-08T17:29:49Z |  |
| Kustomization | flux-system | estate-catalog | Ready | latest@sha256:f7f786c2fa5181853901494a5f | 2026-09-08T17:20:40Z |  |
| Kustomization | flux-system | estate-db-operator | Ready | main@a613fd6 | 2026-09-08T17:29:27Z |  |
| Kustomization | flux-system | gateway-api-crds | Ready | v1.5.1@e7677b7 | 2026-09-08T17:19:43Z |  |
| Kustomization | flux-system | jit | Ready | main@a613fd6 | 2026-09-08T17:19:44Z |  |
| Kustomization | flux-system | kyverno | Ready | main@5d3ea06 | 2026-09-08T17:30:12Z |  |
| Kustomization | flux-system | metrics-server | Ready | main@a613fd6 | 2026-09-08T17:29:53Z |  |
| Kustomization | flux-system | observability-collector | Ready | main@a613fd6 | 2026-09-08T17:29:47Z |  |
| Kustomization | flux-system | priority-classes | Ready | main@a613fd6 | 2026-09-08T17:29:17Z |  |
| Kustomization | flux-system | rbac | Ready | main@a613fd6 | 2026-09-08T17:29:32Z |  |
| Kustomization | flux-system | rbac-floor | Ready | main@a613fd6 | 2026-09-08T17:29:29Z |  |
| Kustomization | flux-system | rbac-identity | Ready | main@a613fd6 | 2026-09-08T17:29:27Z |  |
| Kustomization | flux-system | sandbox-live | Ready | sandbox/launch@929c1d7 | 2026-09-08T17:29:26Z |  |
| Kustomization | flux-system | searxng | Ready | main@a613fd6 | 2026-09-08T17:29:33Z |  |
| Kustomization | flux-system | staging | Ready | main@a613fd6 | 2026-09-08T17:19:37Z |  |
| Kustomization | flux-system | trivy | Ready | main@a613fd6 | 2026-09-08T17:29:36Z |  |
