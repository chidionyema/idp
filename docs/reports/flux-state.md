# Flux: what is applied

Read from the cluster receipt taken at 2026-10-03T10:00:13Z. Every Kustomization and HelmRelease, with the revision Flux last applied. **Suspended** is a switch somebody turned off on purpose (temporal, commerce, commerce-data, event-bus), not a defect; **Unknown** is a row Flux has never graded.

**68 objects: 48 ready, 18 not ready, 0 unknown, 2 suspended.**

## Not ready right now

- **HelmRelease commerce/lago** since 2026-09-26T09:48:22Z: Could not determine release state: unable to determine state for release with status 'uninstalling'
- **HelmRelease coroot/coroot** since 2026-09-29T06:30:04Z: Helm upgrade failed for release coroot/coroot with chart coroot@0.22.0: failed early due to stalled resources: [Deployment/coroot/coroot-prometheus-server status: 'Failed']
- **HelmRelease crossplane-system/crossplane** since 2026-09-29T07:14:14Z: Helm rollback to previous release crossplane-system/crossplane.v28 with chart crossplane@2.4.0 succeeded
- **HelmRelease dagster/dagster** since 2026-09-29T06:21:51Z: Helm rollback to previous release dagster/dagster.v250 with chart dagster@1.13.19 succeeded
- **HelmRelease flux-system/vendor-bridge** since 2026-10-03T09:56:56Z: Running 'upgrade' action with timeout of 5m0s
- **HelmRelease observability/langfuse** since 2026-09-25T10:40:26Z: dependency 'observability/signoz' is not ready
- **HelmRelease spire-mgmt/spire** since 2026-09-26T20:11:52Z: Helm upgrade failed for release spire-mgmt/spire with chart spire@0.30.1: timeout waiting for: [DaemonSet/spire-mgmt/spire-agent status: 'InProgress', Deployment/spire-mgmt/spire-spiffe-oidc-discovery-provider status: 'InProgress']
- **Kustomization flux-system/agent-workforce** since 2026-10-03T09:54:24Z: dependency 'flux-system/llm' is not ready
- **Kustomization flux-system/estate-db-migrate** since 2026-10-03T09:55:22Z: Job/dagster/estate-db-copy-dagster-r3 dry-run failed (Invalid): Job.batch "estate-db-copy-dagster-r3" is invalid: spec.template: Invalid value: {"labels":{"app.kubernetes.io/name":"estate-db-copy-dagster-r3","app.kubernetes.io/part-of":"idp","batch.kubernetes.io/controller-uid":"60a5ac96-98e9-437f-9c41-4ebb30025a6b","batch.kubernetes.io/job-name":"estate-db-copy-dagster-r3","controller-uid":"60a5ac96-98e9-437f-9c41-4ebb30025a6b","job-name":"estate-db-copy-dagster-r3"},"Spec":{"Volumes":[{"Name":"old","HostPath":null,"EmptyDir":null,"GCEPersistentDisk":null,"AWSElasticBlockStore":null,"GitRepo" ... Seconds":null,"DNSPolicy":"ClusterFirst","NodeSelector":null,"ServiceAccountName":"","AutomountServiceAccountToken":false,"NodeName":"","SecurityContext":{"HostNetwork":false,"HostPID":false,"HostIPC":false,"ShareProcessNamespace":null,"HostUsers":null,"SELinuxOptions":null,"WindowsOptions":null,"RunAsUser":26,"RunAsGroup":26,"RunAsNonRoot":true,"SupplementalGroups":null,"SupplementalGroupsPolicy":null,"FSGroup":26,"FSGroupChangePolicy":null,"Sysctls":null,"SeccompProfile":{"Type":"RuntimeDefault","LocalhostProfile":null},"AppArmorProfile":null,"SELinuxChangePolicy":null},"ImagePullSecrets":null,"Hostname":"","Subdomain":"","SetHostnameAsFQDN":null,"Affinity":{"NodeAffinity":{"RequiredDuringSchedulingIgnoredDuringExecution":null,"PreferredDuringSchedulingIgnoredDuringExecution":[{"Weight":50,"Preference":{"MatchExpressions":[{"Key":"estate.io/capacity","Operator":"In","Values":["preemptible"]}],"MatchFields":null}}]},"PodAffinity":null,"PodAntiAffinity":null},"SchedulerName":"default-scheduler","Tolerations":null,"HostAliases":null,"PriorityClassName":"platform-batch","Priority":null,"PreemptionPolicy":null,"DNSConfig":null,"ReadinessGates":null,"RuntimeClassName":null,"Overhead":null,"EnableServiceLinks":null,"TopologySpreadConstraints":null,"OS":null,"SchedulingGates":null,"ResourceClaims":null,"Resources":null,"HostnameOverride":null,"WorkloadRef":null}}: field is immutable 
- **Kustomization flux-system/hermes-agent** since 2026-10-03T09:55:18Z: dependency 'flux-system/llm' is not ready
- **Kustomization flux-system/hindsight** since 2026-10-03T09:54:24Z: dependency 'flux-system/llm' is not ready
- **Kustomization flux-system/jit** since 2026-10-03T09:54:24Z: health check failed after 620.734229ms: failed early due to stalled resources: [Deployment/jit/jit-broker status: 'Failed']
- **Kustomization flux-system/llm** since 2026-10-01T20:38:26Z: dependency 'flux-system/estate-db-migrate' is not ready
- **Kustomization flux-system/otto-golden** since 2026-10-03T09:54:25Z: dependency 'flux-system/llm' is not ready
- **Kustomization flux-system/quad-ledger** since 2026-10-03T09:55:18Z: health check failed after 34.278063ms: failed early due to stalled resources: [Deployment/quad/quad-ledger status: 'Failed']
- **Kustomization flux-system/research-engine** since 2026-10-03T09:54:25Z: dependency 'flux-system/llm' is not ready
- **Kustomization flux-system/temporal** since 2026-10-03T09:54:25Z: dependency 'flux-system/estate-db-migrate' is not ready
- **Kustomization flux-system/voice-router** since 2026-10-03T09:58:59Z: health check failed after 5m0.02445899s: timeout waiting for: [ExternalSecret/voice-router/newsroom-llm status: 'InProgress', Deployment/voice-router/voice-router-director status: 'InProgress']

## Every row

| Kind | Namespace | Name | State | Applied revision | Since | Message |
|---|---|---|---|---|---|---|
| HelmRelease | commerce | lago | Not ready | 1.28.0 | 2026-09-26T09:48:22Z | Could not determine release state: unable to determine state for release with status 'uninstalling' |
| HelmRelease | coroot | coroot | Not ready | 0.22.0 | 2026-09-29T06:30:04Z | Helm upgrade failed for release coroot/coroot with chart coroot@0.22.0: failed early due to stalled resources: [Deployment/coroot/coroot-prometheus-server statu |
| HelmRelease | crossplane-system | crossplane | Not ready | 1.15.1 | 2026-09-29T07:14:14Z | Helm rollback to previous release crossplane-system/crossplane.v28 with chart crossplane@2.4.0 succeeded |
| HelmRelease | dagster | dagster | Not ready | 1.13.19 | 2026-09-29T06:21:51Z | Helm rollback to previous release dagster/dagster.v250 with chart dagster@1.13.19 succeeded |
| HelmRelease | flux-system | vendor-bridge | Not ready | 0.1.0+e2697573098e | 2026-10-03T09:56:56Z | Running 'upgrade' action with timeout of 5m0s |
| HelmRelease | observability | langfuse | Not ready | 2.0.2 | 2026-09-25T10:40:26Z | dependency 'observability/signoz' is not ready |
| HelmRelease | spire-mgmt | spire | Not ready | 0.30.1 | 2026-09-26T20:11:52Z | Helm upgrade failed for release spire-mgmt/spire with chart spire@0.30.1: timeout waiting for: [DaemonSet/spire-mgmt/spire-agent status: 'InProgress', Deploymen |
| Kustomization | flux-system | agent-workforce | Not ready |  | 2026-10-03T09:54:24Z | dependency 'flux-system/llm' is not ready |
| Kustomization | flux-system | estate-db-migrate | Not ready | main@ff6235c | 2026-10-03T09:55:22Z | Job/dagster/estate-db-copy-dagster-r3 dry-run failed (Invalid): Job.batch "estate-db-copy-dagster-r3" is invalid: spec.template: Invalid value: {"labels":{"app. |
| Kustomization | flux-system | hermes-agent | Not ready | main@ff6235c | 2026-10-03T09:55:18Z | dependency 'flux-system/llm' is not ready |
| Kustomization | flux-system | hindsight | Not ready | main@ff6235c | 2026-10-03T09:54:24Z | dependency 'flux-system/llm' is not ready |
| Kustomization | flux-system | jit | Not ready | main@e269757 | 2026-10-03T09:54:24Z | health check failed after 620.734229ms: failed early due to stalled resources: [Deployment/jit/jit-broker status: 'Failed'] |
| Kustomization | flux-system | llm | Not ready | main@ff6235c | 2026-10-01T20:38:26Z | dependency 'flux-system/estate-db-migrate' is not ready |
| Kustomization | flux-system | otto-golden | Not ready | main@ff6235c | 2026-10-03T09:54:25Z | dependency 'flux-system/llm' is not ready |
| Kustomization | flux-system | quad-ledger | Not ready | main@e269757 | 2026-10-03T09:55:18Z | health check failed after 34.278063ms: failed early due to stalled resources: [Deployment/quad/quad-ledger status: 'Failed'] |
| Kustomization | flux-system | research-engine | Not ready |  | 2026-10-03T09:54:25Z | dependency 'flux-system/llm' is not ready |
| Kustomization | flux-system | temporal | Not ready |  | 2026-10-03T09:54:25Z | dependency 'flux-system/estate-db-migrate' is not ready |
| Kustomization | flux-system | voice-router | Not ready | main@e269757 | 2026-10-03T09:58:59Z | health check failed after 5m0.02445899s: timeout waiting for: [ExternalSecret/voice-router/newsroom-llm status: 'InProgress', Deployment/voice-router/voice-rout |
| HelmRelease | observability | signoz | Suspended | 0.138.0 | 2026-09-26T16:24:12Z |  |
| HelmRelease | tigera-operator | tigera-operator | Suspended | v3.32.2 | 2026-09-06T19:38:02Z |  |
| HelmRelease | cert-manager | cert-manager | Ready | v1.21.1 | 2026-09-30T23:26:48Z |  |
| HelmRelease | edge | external-dns | Ready | 1.21.1 | 2026-09-26T10:39:02Z |  |
| HelmRelease | edge | traefik | Ready | 41.3.0 | 2026-09-26T09:48:30Z |  |
| HelmRelease | estate-db | cloudnative-pg | Ready | 0.29.0 | 2026-09-26T10:01:26Z |  |
| HelmRelease | event-bus | nats | Ready | 2.14.6 | 2026-09-26T09:48:21Z |  |
| HelmRelease | external-secrets | external-secrets | Ready | 2.9.0 | 2026-09-27T17:09:36Z |  |
| HelmRelease | healing | descheduler | Ready | 0.36.0 | 2026-09-26T09:48:21Z |  |
| HelmRelease | healing | k8sgpt-operator | Ready | 0.2.29 | 2026-09-26T09:48:26Z |  |
| HelmRelease | hindsight | hindsight | Ready | 0.9.2 | 2026-09-29T03:07:48Z |  |
| HelmRelease | identity | oauth2-proxy | Ready | 10.7.0 | 2026-09-29T00:03:03Z |  |
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
| HelmRelease | trivy-system | trivy-operator | Ready | 0.36.0 | 2026-09-26T18:25:31Z |  |
| HelmRelease | weave-gitops | weave-gitops | Ready | 4.0.36 | 2026-09-26T09:48:27Z |  |
| Kustomization | flux-system | backstage | Ready | main@e269757 | 2026-10-03T09:54:23Z |  |
| Kustomization | flux-system | backstage-namespace | Ready | main@e269757 | 2026-10-03T09:53:33Z |  |
| Kustomization | flux-system | dns | Ready | main@e269757 | 2026-10-03T09:52:47Z |  |
| Kustomization | flux-system | edge | Ready | main@e269757 | 2026-10-03T09:52:03Z |  |
| Kustomization | flux-system | epistemic-fabric | Ready | main@e269757 | 2026-10-03T09:54:08Z |  |
| Kustomization | flux-system | estate-db | Ready | main@e269757 | 2026-10-03T09:54:35Z |  |
| Kustomization | flux-system | estate-db-operator | Ready | main@e269757 | 2026-10-03T09:53:17Z |  |
| Kustomization | flux-system | event-bus | Ready | main@e269757 | 2026-10-03T09:54:00Z |  |
| Kustomization | flux-system | external-secrets | Ready | main@e269757 | 2026-10-03T09:52:54Z |  |
| Kustomization | flux-system | flannel | Ready | main@e269757 | 2026-10-03T09:52:24Z |  |
| Kustomization | flux-system | flux-system | Ready | main@e269757 | 2026-10-03T09:52:27Z |  |
| Kustomization | flux-system | gateway-api-crds | Ready | v1.5.1@e7677b7 | 2026-10-03T09:51:09Z |  |
| Kustomization | flux-system | github-app-creds | Ready | main@e269757 | 2026-10-03T09:54:36Z |  |
| Kustomization | flux-system | kyverno | Ready | main@e269757 | 2026-10-03T09:53:17Z |  |
| Kustomization | flux-system | mcp | Ready | main@e269757 | 2026-10-03T09:55:18Z |  |
| Kustomization | flux-system | monitoring | Ready | main@e269757 | 2026-10-03T09:52:45Z |  |
| Kustomization | flux-system | monitoring-rules | Ready | main@e269757 | 2026-10-03T09:52:24Z |  |
| Kustomization | flux-system | ns-fences | Ready | main@e269757 | 2026-10-03T09:53:33Z |  |
| Kustomization | flux-system | otto-gateway | Ready | main@e269757 | 2026-10-03T09:55:18Z |  |
| Kustomization | flux-system | otto-golden-secret | Ready | main@e269757 | 2026-10-03T09:54:08Z |  |
| Kustomization | flux-system | priority-classes | Ready | main@e269757 | 2026-10-03T09:52:03Z |  |
| Kustomization | flux-system | quad-ledger-exception | Ready | main@e269757 | 2026-10-03T09:53:33Z |  |
| Kustomization | flux-system | searxng | Ready | main@e269757 | 2026-10-03T09:52:03Z |  |
| Kustomization | flux-system | secret-store | Ready | main@e269757 | 2026-10-03T09:53:33Z |  |
| Kustomization | flux-system | tailscale | Ready | main@e269757 | 2026-10-03T09:54:18Z |  |
| Kustomization | flux-system | unified-memory | Ready | main@e269757 | 2026-10-03T09:55:08Z |  |
