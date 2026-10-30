# Estate infrastructure inventory

Measured from git by `bin/idp-infra-inventory` on 2026-10-30T06:07:33Z.
The live control plane is unreachable (incident 2026-10-29), so the manifests are the
declaration of record.

## Totals

- applied workloads: 85
- CPU requests as declared: 3530m
- CPU demand (replica weighted): 3490m
- memory requests as declared: 10080Mi
- memory demand (replica weighted): 9984Mi
- persistent volume claims: 4 (13.0GB)
- workloads with unknown capacity: 16

| workload | source | replicas | cpu | memory | verdict |
|---|---|---|---|---|---|
| agent-workforce/cronjob/agent-workforce | platform/agent-workforce | 1 | 225m | 768Mi | REFUSED |
| agent-workforce/persistentvolumeclaim/agent-workforce-memory | platform/agent-workforce | None | 0m | 0Mi | UNLISTED |
| backstage/deployment/catalogue | platform/backstage/overlays/oke | 1 | 275m | 576Mi | REFUSED |
| backstage/job/estate-db-copy-backstage-r2 | platform/estate-db/migrate | 1 | 50m | 128Mi | REFUSED |
| cert-manager/helmrelease/cert-manager | platform/edge | None | 0m | 0Mi | ADMITTED |
| dagster/job/estate-db-copy-dagster-r3 | platform/estate-db/migrate | 1 | 50m | 128Mi | REFUSED |
| edge/deployment/status-page | platform/edge | 1 | 10m | 16Mi | ADMITTED |
| edge/helmrelease/external-dns | platform/dns | None | 0m | 0Mi | ADMITTED |
| edge/helmrelease/traefik | platform/edge | None | 0m | 0Mi | ADMITTED |
| efda-system/deployment/efda-controller | platform/efda | 1 | 50m | 128Mi | ADMITTED |
| efda-system/deployment/efda-executor | platform/efda | 1 | 50m | 128Mi | ADMITTED |
| efda-system/statefulset/efda-checkpoints | platform/efda | 1 | 50m | 128Mi | ADMITTED |
| epistemic-fabric/deployment/epistemic-ingest-cicd | platform/epistemic-fabric | 1 | 20m | 48Mi | ADMITTED |
| epistemic-fabric/deployment/epistemic-ingest-github | platform/epistemic-fabric | 0 | 20m | 48Mi | ADMITTED |
| epistemic-fabric/deployment/epistemic-ingest-incidents | platform/epistemic-fabric | 1 | 20m | 48Mi | ADMITTED |
| epistemic-fabric/deployment/epistemic-ingest-slack | platform/epistemic-fabric | 0 | 20m | 48Mi | ADMITTED |
| estate-bridge/deployment/estate-bridge | platform/bridge | 1 | 10m | 64Mi | ADMITTED |
| estate-db/cronjob/catalog-schema | platform/catalog | 1 | 10m | 64Mi | ADMITTED |
| estate-db/cronjob/estate-db-backup | platform/estate-db/backup | 1 | 50m | 128Mi | ADMITTED |
| estate-db/helmrelease/cloudnative-pg | platform/estate-db/operator | None | 0m | 0Mi | ADMITTED |
| event-bus/helmrelease/nats | platform/event-bus | None | 0m | 0Mi | ADMITTED |
| external-secrets/helmrelease/external-secrets | platform/secrets | None | 0m | 0Mi | ADMITTED |
| flux-system/deployment/helm-controller | clusters/oke | 1 | 100m | 64Mi | ADMITTED |
| flux-system/deployment/image-automation-controller | clusters/oke | 1 | 100m | 64Mi | ADMITTED |
| flux-system/deployment/image-reflector-controller | clusters/oke | 1 | 100m | 64Mi | ADMITTED |
| flux-system/deployment/kustomize-controller | clusters/oke | 1 | 100m | 64Mi | ADMITTED |
| flux-system/deployment/notification-controller | clusters/oke | 1 | 100m | 64Mi | ADMITTED |
| flux-system/deployment/source-controller | clusters/oke | 1 | 50m | 64Mi | ADMITTED |
| flux-system/helmrelease/vendor-bridge | platform/human-vault-bridge | None | 0m | 0Mi | ADMITTED |
| guacamole/job/estate-db-copy-guacamole-r2 | platform/estate-db/migrate | 1 | 50m | 128Mi | REFUSED |
| healthchecks/job/estate-db-copy-healthchecks-r2 | platform/estate-db/migrate | 1 | 50m | 128Mi | REFUSED |
| hermes-agent/deployment/hermes-agent-gateway | platform/hermes-agent | 1 | 100m | 352Mi | ADMITTED |
| hermes-agent/persistentvolumeclaim/hermes-agent-data | platform/hermes-agent | None | 0m | 0Mi | UNLISTED |
| hindsight/helmrelease/hindsight | platform/hindsight | None | 0m | 0Mi | REFUSED |
| hindsight/job/estate-db-copy-hindsight-r5 | platform/estate-db/migrate | 1 | 50m | 128Mi | REFUSED |
| identity/cronjob/front-door-heartbeat | platform/identity | 1 | 50m | 128Mi | ADMITTED |
| identity/helmrelease/oauth2-proxy | platform/identity | None | 0m | 0Mi | ADMITTED |
| jit/deployment/jit-broker | platform/jit | 1 | 50m | 128Mi | ADMITTED |
| jit/persistentvolumeclaim/jit-ledger | platform/jit | None | 0m | 0Mi | UNLISTED |
| kube-system/daemonset/pod-no-masq | platform/flannel | 1 | 5m | 16Mi | ADMITTED |
| kyverno/helmrelease/kyverno | platform/kyverno | None | 0m | 0Mi | REFUSED |
| llm/cronjob/router-backup | platform/router-events | 1 | 50m | 128Mi | ADMITTED |
| llm/cronjob/spend-velocity-check | platform/llm | 1 | 50m | 64Mi | ADMITTED |
| llm/deployment/litellm | platform/llm | 1 | 50m | 512Mi | ADMITTED |
| llm/deployment/litellm-cache | platform/llm | 1 | 25m | 64Mi | ADMITTED |
| llm/deployment/ollama | platform/llm | 1 | 150m | 768Mi | REFUSED |
| llm/deployment/router-event-publisher | platform/router-events | 1 | 20m | 64Mi | ADMITTED |
| llm/deployment/zeroedge | platform/llm | 1 | 20m | 64Mi | ADMITTED |
| llm/job/estate-db-copy-litellm-r2 | platform/estate-db/migrate | 1 | 50m | 128Mi | REFUSED |
| local-path-storage/deployment/local-path-provisioner | platform/local-path | 1 | 10m | 32Mi | ADMITTED |
| mcp/deployment/agentgateway | platform/mcp | 1 | 50m | 256Mi | ADMITTED |
| mcp/deployment/estate-context-broker | platform/mcp | 1 | 75m | 320Mi | ADMITTED |
| mcp/deployment/estate-mcp | platform/mcp | 1 | 30m | 96Mi | ADMITTED |
| mcp/deployment/github-mcp | platform/mcp | 1 | 20m | 32Mi | ADMITTED |
| mcp/persistentvolumeclaim/estate-context-index | platform/mcp | None | 0m | 0Mi | UNLISTED |
| meridian/deployment/meridian | platform/meridian | 1 | 60m | 160Mi | ADMITTED |
| metrics-server/helmrelease/metrics-server | platform/metrics-server | None | 0m | 0Mi | ADMITTED |
| monitoring/helmrelease/blackbox | platform/monitoring | None | 0m | 0Mi | REFUSED |
| monitoring/helmrelease/kube-prometheus-stack | platform/monitoring | None | 0m | 0Mi | REFUSED |
| observability/deployment/aei | platform/aei | 1 | 50m | 128Mi | ADMITTED |
| observability/job/estate-db-copy-langfuse-r2 | platform/estate-db/migrate | 1 | 50m | 128Mi | REFUSED |
| observability/job/estate-db-copy-superset-r2 | platform/estate-db/migrate | 1 | 50m | 128Mi | REFUSED |
| otto-gateway/cronjob/otto-answer-probe | platform/otto-gateway | 1 | 0m | 64Mi | ADMITTED |
| otto-gateway/cronjob/otto-registration-reconciler | platform/otto-gateway | 1 | 0m | 64Mi | ADMITTED |
| otto-gateway/deployment/otto-gateway | platform/otto-gateway | 1 | 150m | 640Mi | ADMITTED |
| otto-gateway/job/estate-db-copy-otto-gateway-r3 | platform/estate-db/migrate | 1 | 50m | 128Mi | REFUSED |
| otto-gateway/job/otto-memory-store-8 | platform/otto-gateway | 1 | 50m | 128Mi | ADMITTED |
| otto-golden/deployment/otto-golden | platform/otto-golden | 1 | 25m | 128Mi | ADMITTED |
| quad/cronjob/quad-ledger-anchor | platform/quad/ledger | 1 | 20m | 32Mi | ADMITTED |
| quad/cronjob/quad-ledger-verify | platform/quad/ledger | 1 | 20m | 32Mi | ADMITTED |
| quad/deployment/quad-ledger | platform/quad/ledger | 1 | 20m | 32Mi | ADMITTED |
| reloader/helmrelease/reloader | platform/reloader | None | 0m | 0Mi | ADMITTED |
| research/cronjob/exa-credit-probe | platform/research-engine | 1 | 0m | 64Mi | ADMITTED |
| research/cronjob/research-engine | platform/research-engine | 1 | 200m | 512Mi | REFUSED |
| searxng/deployment/searxng | platform/searxng | 1 | 50m | 192Mi | REFUSED |
| spine/deployment/spine-bridge | platform/spine | 1 | 20m | 64Mi | ADMITTED |
| spine/deployment/spine-worker | platform/spine | 1 | 20m | 64Mi | ADMITTED |
| tailscale/helmrelease/tailscale-operator | platform/tailscale | None | 0m | 0Mi | ADMITTED |
| temporal/deployment/sovereign-worker | platform/temporal | 1 | 50m | 128Mi | ADMITTED |
| temporal/helmrelease/temporal | platform/temporal | None | 0m | 0Mi | ADMITTED |
| temporal/job/estate-db-copy-temporal-r3 | platform/estate-db/migrate | 1 | 50m | 128Mi | REFUSED |
| unified-memory/cronjob/unified-memory-consolidate | platform/unified-memory-server | 1 | 20m | 64Mi | ADMITTED |
| unified-memory/deployment/unified-memory-server | platform/unified-memory-server | 1 | 50m | 128Mi | ADMITTED |
| voice-router/deployment/voice-router | platform/voice-router/deploy | 1 | 100m | 512Mi | ADMITTED |
| voice-router/deployment/voice-router-director | platform/voice-router/deploy | 1 | 10m | 64Mi | ADMITTED |

## Declared but never applied

| path | decision | reason |
|---|---|---|
| backstage/founder | reserved | the founder's catalogue, rendered by bin/catalog-gen and read by /fleet |
| backstage/org | reserved | the organisation catalogue, rendered by bin/catalog-gen |
| backstage/platform | reserved | the platform catalogue, rendered by bin/catalog-platform |
| platform/acg | cut | a second context and graph layer; the estate's memory is the estate context broker and growmos, and one of each layer is the rule |
| platform/alerts | reserved | the alert rules for the estate's own services |
| platform/alerts-github | reserved | the GitHub delivery path for those alerts |
| platform/alerts-secret | reserved | the secret the alert delivery path reads |
| platform/backstage/base | reserved | the Backstage base the laptop developer portal builds from |
| platform/backstage/namespace/base | reserved | the Backstage namespace base |
| platform/backstage/overlays/local | reserved | the laptop overlay of the developer portal |
| platform/calico | cut | the dead OKE cluster's CNI; the one node runs flannel |
| platform/calico/raw | cut | the raw Calico manifests for the dead OKE cluster |
| platform/commerce/app | cut | a product never admitted to a node; its data path is estate-db |
| platform/commerce/data | cut | a product never admitted to a node; its data path is estate-db |
| platform/compiled/agent-foundry-hf | cut | a compiled artefact directory, not a workload |
| platform/crossplane | cut | a cloud provisioning layer the estate never enabled; the ladder places workloads on free tiers first |
| platform/crossplane/capabilities/storage | cut | unused under the crossplane layer |
| platform/crossplane/providerconfig | cut | unused under the crossplane layer |
| platform/crossplane/providers | cut | unused under the crossplane layer |
| platform/dagster | cut | a second orchestrator; the estate has the sovereign bus |
| platform/features | reserved | the feature register bin/idp-features reads and CI checks |
| platform/flux-webhook | reserved | the webhook receiver Flux calls when the node returns |
| platform/guacamole | cut | a product never admitted to a node and with no user |
| platform/gvisor-runtime | reserved | the runtime cell the demo sandbox needs; bin/catalog-platform names it |
| platform/healing | cut | self-healing runbooks for a cluster with no spare capacity; the estate's healing runs in the laptop agent |
| platform/healing/analyzer | cut | the analyser behind the healing layer |
| platform/healing/k8sgpt | cut | the k8sgpt analyser behind the healing layer |
| platform/healthchecks | cut | a product never admitted; the edge status page answers the same question |
| platform/idp_agent | reserved | the agent's own pod template, used by the laptop harness |
| platform/nodesoftware-operator | cut | an OKE add-on, and OKE is gone |
| platform/notify | reserved | the notification layer |
| platform/observability | cut | the telemetry collector duplicates the free tier the estate now uses |
| platform/observability-collector | cut | the collector behind the observability layer |
| platform/prospector | cut | the dead prospector experiment; the edge issuer is applied from platform/edge |
| platform/rbac | reserved | the RBAC floor every workload is bound to |
| platform/rbac-identity | reserved | the identity roles the RBAC floor binds |
| platform/sandbox/launch | reserved | the demo sandbox (ADR 0025): a GitHub Actions lane, never a node workload |
| platform/sandbox/vcluster | reserved | the demo sandbox's virtual cluster (ADR 0025), with its expiry reaper; demo only, never admitted to the node |
| platform/scheduling | reserved | the scheduling knobs and the one-scheduler policy |
| platform/science | cut | an experiment with no consumer |
| platform/spire | reserved | the SPIFFE trust layer: the estate's intents, libexec, trust code and key broker still name it, so it is cut in the follow-on sweep with those references, not in this one |
| platform/staging | cut | staging environments for a cluster that no longer exists |
| platform/staging/canary | cut | staging environments for a cluster that no longer exists |
| platform/state | reserved | the cluster state ledger |
| platform/trivy | reserved | the node-side image scanner; the estate scans images in the build pipeline, so this stays in git for a second cluster and takes no capacity |
| platform/verification | reserved | the verification layer |
| platform/via-negativa | cut | a product layer never admitted to a node |

## Node budget

- node CPU requests: 3600m
- node memory requests: 21504Mi
- node disk: 200GB
- PVC storage ceiling: 120GB
- admitted, concurrent: 3415m / 11456Mi
- refused, concurrent: 2050m
- the applied surface oversubscribes the node by 1865m
- one-shot burst, outside the concurrent budget: 550m / 1408Mi

## Admitted to the node

| workload | cpu | memory | rung | justification |
|---|---|---|---|---|
| cert-manager/helmrelease/cert-manager | 100m | 384Mi | 7 | the cert-manager service the estate runs; its measured request (100m/384Mi) fits the one-node budget and it has no free-tier home |
| edge/deployment/status-page | 10m | 16Mi | 7 | the edge the founder reaches: ingress, certificates, DNS and the status page; its measured request (10m/16Mi) fits the one-node budget and it has no free-tier home |
| edge/helmrelease/external-dns | 50m | 128Mi | 7 | the edge the founder reaches: ingress, certificates, DNS and the status page; its measured request (50m/128Mi) fits the one-node budget and it has no free-tier home |
| edge/helmrelease/traefik | 100m | 256Mi | 7 | the edge the founder reaches: ingress, certificates, DNS and the status page; its measured request (100m/256Mi) fits the one-node budget and it has no free-tier home |
| efda-system/deployment/efda-controller | 50m | 128Mi | 7 | the effect-based detection agent, its executor and its checkpoints; its measured request (50m/128Mi) fits the one-node budget and it has no free-tier home |
| efda-system/deployment/efda-executor | 50m | 128Mi | 7 | the effect-based detection agent, its executor and its checkpoints; its measured request (50m/128Mi) fits the one-node budget and it has no free-tier home |
| efda-system/statefulset/efda-checkpoints | 50m | 128Mi | 7 | the effect-based detection agent, its executor and its checkpoints; its measured request (50m/128Mi) fits the one-node budget and it has no free-tier home |
| epistemic-fabric/deployment/epistemic-ingest-cicd | 20m | 48Mi | 7 | the ingest workers that turn the estate's events into memory; its measured request (20m/48Mi) fits the one-node budget and it has no free-tier home |
| epistemic-fabric/deployment/epistemic-ingest-github | 0m | 0Mi | 7 | the ingest workers that turn the estate's events into memory; its measured request (0m/0Mi) fits the one-node budget and it has no free-tier home |
| epistemic-fabric/deployment/epistemic-ingest-incidents | 20m | 48Mi | 7 | the ingest workers that turn the estate's events into memory; its measured request (20m/48Mi) fits the one-node budget and it has no free-tier home |
| epistemic-fabric/deployment/epistemic-ingest-slack | 0m | 0Mi | 7 | the ingest workers that turn the estate's events into memory; its measured request (0m/0Mi) fits the one-node budget and it has no free-tier home |
| estate-bridge/deployment/estate-bridge | 10m | 64Mi | 7 | the bridge between the estate's surfaces and the human vault; its measured request (10m/64Mi) fits the one-node budget and it has no free-tier home |
| estate-db/cronjob/catalog-schema | 10m | 64Mi | 7 | the catalogue schema migration, on a schedule; its measured request (10m/64Mi) fits the one-node budget and it has no free-tier home |
| estate-db/cronjob/estate-db-backup | 50m | 128Mi | 7 | the nightly backup of the estate's own database; its measured request (50m/128Mi) fits the one-node budget and it has no free-tier home |
| estate-db/helmrelease/cloudnative-pg | 400m | 2048Mi | 7 | the estate's own database and its backups; its measured request (400m/2048Mi) fits the one-node budget and it has no free-tier home |
| event-bus/helmrelease/nats | 100m | 512Mi | 7 | the JetStream bus every agent state change travels over; its measured request (100m/512Mi) fits the one-node budget and it has no free-tier home |
| external-secrets/helmrelease/external-secrets | 50m | 256Mi | 7 | the bridge that puts vault values into pods without a secret in git; its measured request (50m/256Mi) fits the one-node budget and it has no free-tier home |
| flux-system/deployment/helm-controller | 100m | 64Mi | 7 | the Flux controllers that reconcile the estate's declared state; the estate cannot converge without them; its measured request (100m/64Mi) fits the one-node budget and it has no free-tier home |
| flux-system/deployment/image-automation-controller | 100m | 64Mi | 7 | the Flux controllers that reconcile the estate's declared state; the estate cannot converge without them; its measured request (100m/64Mi) fits the one-node budget and it has no free-tier home |
| flux-system/deployment/image-reflector-controller | 100m | 64Mi | 7 | the Flux controllers that reconcile the estate's declared state; the estate cannot converge without them; its measured request (100m/64Mi) fits the one-node budget and it has no free-tier home |
| flux-system/deployment/kustomize-controller | 100m | 64Mi | 7 | the Flux controllers that reconcile the estate's declared state; the estate cannot converge without them; its measured request (100m/64Mi) fits the one-node budget and it has no free-tier home |
| flux-system/deployment/notification-controller | 100m | 64Mi | 7 | the Flux controllers that reconcile the estate's declared state; the estate cannot converge without them; its measured request (100m/64Mi) fits the one-node budget and it has no free-tier home |
| flux-system/deployment/source-controller | 50m | 64Mi | 7 | the Flux controllers that reconcile the estate's declared state; the estate cannot converge without them; its measured request (50m/64Mi) fits the one-node budget and it has no free-tier home |
| flux-system/helmrelease/vendor-bridge | 50m | 128Mi | 7 | the Flux controllers that reconcile the estate's declared state; the estate cannot converge without them; its measured request (50m/128Mi) fits the one-node budget and it has no free-tier home |
| hermes-agent/deployment/hermes-agent-gateway | 100m | 352Mi | 7 | the agent gateway the founder's clients reach; its measured request (100m/352Mi) fits the one-node budget and it has no free-tier home |
| identity/cronjob/front-door-heartbeat | 50m | 128Mi | 7 | the front door's own liveness beat; its measured request (50m/128Mi) fits the one-node budget and it has no free-tier home |
| identity/helmrelease/oauth2-proxy | 50m | 128Mi | 7 | the front door every agent call comes through; its measured request (50m/128Mi) fits the one-node budget and it has no free-tier home |
| jit/deployment/jit-broker | 50m | 128Mi | 7 | the just-in-time ledger the estate's agents write to; its measured request (50m/128Mi) fits the one-node budget and it has no free-tier home |
| kube-system/daemonset/pod-no-masq | 5m | 16Mi | 7 | the node's own flannel datapath; its measured request (5m/16Mi) fits the one-node budget and it has no free-tier home |
| llm/cronjob/router-backup | 50m | 128Mi | 7 | the router's configuration backup; its measured request (50m/128Mi) fits the one-node budget and it has no free-tier home |
| llm/cronjob/spend-velocity-check | 50m | 64Mi | 7 | the check that keeps the estate off paid lanes; its measured request (50m/64Mi) fits the one-node budget and it has no free-tier home |
| llm/deployment/litellm | 50m | 512Mi | 7 | the fallback router: the cloud route is the default, this lane answers when the cloud is unreachable; its measured request (50m/512Mi) fits the one-node budget and it has no free-tier home |
| llm/deployment/litellm-cache | 25m | 64Mi | 7 | the router's answer cache, which is what keeps the estate off paid lanes; its measured request (25m/64Mi) fits the one-node budget and it has no free-tier home |
| llm/deployment/router-event-publisher | 20m | 64Mi | 7 | the router lane: the cloud route is the default and this is the fallback; its measured request (20m/64Mi) fits the one-node budget and it has no free-tier home |
| llm/deployment/zeroedge | 20m | 64Mi | 7 | the router lane: the cloud route is the default and this is the fallback; its measured request (20m/64Mi) fits the one-node budget and it has no free-tier home |
| local-path-storage/deployment/local-path-provisioner | 10m | 32Mi | 7 | the provisioner for the node's own persistent volumes; its measured request (10m/32Mi) fits the one-node budget and it has no free-tier home |
| mcp/deployment/agentgateway | 50m | 256Mi | 7 | the MCP surface the agents call, including the estate context broker; its measured request (50m/256Mi) fits the one-node budget and it has no free-tier home |
| mcp/deployment/estate-context-broker | 75m | 320Mi | 7 | the context broker: the one place an agent's context is read from, and the reason this ADR exists; its measured request (75m/320Mi) fits the one-node budget and it has no free-tier home |
| mcp/deployment/estate-mcp | 30m | 96Mi | 7 | the MCP surface the agents call, including the estate context broker; its measured request (30m/96Mi) fits the one-node budget and it has no free-tier home |
| mcp/deployment/github-mcp | 20m | 32Mi | 7 | the MCP surface the agents call, including the estate context broker; its measured request (20m/32Mi) fits the one-node budget and it has no free-tier home |
| meridian/deployment/meridian | 60m | 160Mi | 7 | the meridian service that times the estate's own calls; its measured request (60m/160Mi) fits the one-node budget and it has no free-tier home |
| metrics-server/helmrelease/metrics-server | 50m | 128Mi | 7 | the metrics-server service the estate runs; its measured request (50m/128Mi) fits the one-node budget and it has no free-tier home |
| observability/deployment/aei | 50m | 128Mi | 7 | the audit record of what the estate did; its measured request (50m/128Mi) fits the one-node budget and it has no free-tier home |
| otto-gateway/cronjob/otto-answer-probe | 0m | 64Mi | 7 | the probe that proves the gateway still answers; its measured request (0m/64Mi) fits the one-node budget and it has no free-tier home |
| otto-gateway/cronjob/otto-registration-reconciler | 0m | 64Mi | 7 | the reconciler that keeps the gateway's registration honest; its measured request (0m/64Mi) fits the one-node budget and it has no free-tier home |
| otto-gateway/deployment/otto-gateway | 150m | 640Mi | 7 | the gateway that answers the founder, at one replica because the second replica would sit on the same A1 VM; its measured request (150m/640Mi) fits the one-node budget and it has no free-tier home |
| otto-gateway/job/otto-memory-store-8 | 50m | 128Mi | 7 | a one-shot seeding job for the memory store; a burst, not a standing claim; its measured request (50m/128Mi) fits the one-node budget and it has no free-tier home |
| otto-golden/deployment/otto-golden | 25m | 128Mi | 7 | the golden-set evaluator that grades the estate's answers; its measured request (25m/128Mi) fits the one-node budget and it has no free-tier home |
| quad/cronjob/quad-ledger-anchor | 20m | 32Mi | 7 | the ledger's periodic anchor; its measured request (20m/32Mi) fits the one-node budget and it has no free-tier home |
| quad/cronjob/quad-ledger-verify | 20m | 32Mi | 7 | the ledger's periodic verification; its measured request (20m/32Mi) fits the one-node budget and it has no free-tier home |
| quad/deployment/quad-ledger | 20m | 32Mi | 7 | the quad ledger and its anchors; its measured request (20m/32Mi) fits the one-node budget and it has no free-tier home |
| reloader/helmrelease/reloader | 25m | 64Mi | 7 | the reloader service the estate runs; its measured request (25m/64Mi) fits the one-node budget and it has no free-tier home |
| research/cronjob/exa-credit-probe | 0m | 64Mi | 7 | the probe that keeps the search lane's credit honest; its measured request (0m/64Mi) fits the one-node budget and it has no free-tier home |
| spine/deployment/spine-bridge | 20m | 64Mi | 7 | the generic spine that carries work between the estate's planes; its measured request (20m/64Mi) fits the one-node budget and it has no free-tier home |
| spine/deployment/spine-worker | 20m | 64Mi | 7 | the generic spine that carries work between the estate's planes; its measured request (20m/64Mi) fits the one-node budget and it has no free-tier home |
| tailscale/helmrelease/tailscale-operator | 50m | 128Mi | 7 | the tailscale service the estate runs; its measured request (50m/128Mi) fits the one-node budget and it has no free-tier home |
| temporal/deployment/sovereign-worker | 50m | 128Mi | 7 | the sovereign worker the estate's long work runs on; its measured request (50m/128Mi) fits the one-node budget and it has no free-tier home |
| temporal/helmrelease/temporal | 350m | 1536Mi | 7 | the sovereign worker the estate's long work runs on; its measured request (350m/1536Mi) fits the one-node budget and it has no free-tier home |
| unified-memory/cronjob/unified-memory-consolidate | 20m | 64Mi | 7 | the memory layer's consolidation; its measured request (20m/64Mi) fits the one-node budget and it has no free-tier home |
| unified-memory/deployment/unified-memory-server | 50m | 128Mi | 7 | the estate's one memory layer; its measured request (50m/128Mi) fits the one-node budget and it has no free-tier home |
| voice-router/deployment/voice-router | 100m | 512Mi | 7 | the voice surface the founder speaks to; its measured request (100m/512Mi) fits the one-node budget and it has no free-tier home |
| voice-router/deployment/voice-router-director | 10m | 64Mi | 7 | the voice-first surface: the founder speaks and the estate answers; its measured request (10m/64Mi) fits the one-node budget and it has no free-tier home |

## Refused: moved off the node

| workload | cpu | memory | destination | reason |
|---|---|---|---|---|
| agent-workforce/cronjob/agent-workforce | 225m | 768Mi | a GitHub Actions schedule workflow | a 225m batch on a schedule whose output is a repository artefact |
| backstage/deployment/catalogue | 275m | 576Mi | the laptop developer portal | the developer portal is not the founder's surface (/fleet is), and 275m of always-on capacity is the wrong spend on a one-node estate |
| backstage/job/estate-db-copy-backstage-r2 | 50m | 128Mi | the product's own deployment path (GitHub Actions), with the product | a one-shot copy of a per-application database for a product that is not admitted to this node; the copy follows the product |
| dagster/job/estate-db-copy-dagster-r3 | 50m | 128Mi | the product's own deployment path (GitHub Actions), with the product | a one-shot copy of a per-application database for a product that is not admitted to this node; the copy follows the product |
| guacamole/job/estate-db-copy-guacamole-r2 | 50m | 128Mi | the product's own deployment path (GitHub Actions), with the product | a one-shot copy of a per-application database for a product that is not admitted to this node; the copy follows the product |
| healthchecks/job/estate-db-copy-healthchecks-r2 | 50m | 128Mi | the product's own deployment path (GitHub Actions), with the product | a one-shot copy of a per-application database for a product that is not admitted to this node; the copy follows the product |
| hindsight/helmrelease/hindsight | 200m | 768Mi | cut: merged into the estate's one memory layer, no new home | a second memory layer; the estate's memory is the unified-memory server plus the estate context broker, and one of each layer is the rule |
| hindsight/job/estate-db-copy-hindsight-r5 | 50m | 128Mi | the product's own deployment path (GitHub Actions), with the product | a one-shot copy of a per-application database for a product that is not admitted to this node; the copy follows the product |
| kyverno/helmrelease/kyverno | 250m | 1024Mi | the laptop admission gate and the git pre-push hook (bin/idp-ci) | admission control needs 250m and 1Gi on a node that cannot spare it, and the estate already refuses bad changes deterministically at write, commit and push |
| llm/deployment/ollama | 150m | 768Mi | the cloud router's free ollama floor lane (llm.mumchimp.com) | a local model lane on the node is a third copy of the floor the cloud router already holds; the cloud route is the default and this node is the fallback of the fallback |
| llm/job/estate-db-copy-litellm-r2 | 50m | 128Mi | the product's own deployment path (GitHub Actions), with the product | a one-shot copy of a per-application database for a product that is not admitted to this node; the copy follows the product |
| monitoring/helmrelease/blackbox | 100m | 256Mi | Grafana Cloud free (OTLP ingest) | the blackbox prober answers the same questions from the free telemetry tier |
| monitoring/helmrelease/kube-prometheus-stack | 600m | 2560Mi | Grafana Cloud free (OTLP ingest) | Prometheus on one node costs 600m and 2.5Gi to keep a dashboard that the free tier holds for nothing; the estate's telemetry is exactly rung 3 |
| observability/job/estate-db-copy-langfuse-r2 | 50m | 128Mi | the product's own deployment path (GitHub Actions), with the product | a one-shot copy of a per-application database for a product that is not admitted to this node; the copy follows the product |
| observability/job/estate-db-copy-superset-r2 | 50m | 128Mi | the product's own deployment path (GitHub Actions), with the product | a one-shot copy of a per-application database for a product that is not admitted to this node; the copy follows the product |
| otto-gateway/job/estate-db-copy-otto-gateway-r3 | 50m | 128Mi | the product's own deployment path (GitHub Actions), with the product | a one-shot copy of a per-application database for a product that is not admitted to this node; the copy follows the product |
| research/cronjob/research-engine | 200m | 512Mi | a GitHub Actions schedule workflow | a 200m batch that wakes on a schedule and holds nothing between runs |
| searxng/deployment/searxng | 50m | 192Mi | cut: the exa-backed search lane in the router | a 50m always-on pod for search the exa-backed lane in the router already answers |
| temporal/job/estate-db-copy-temporal-r3 | 50m | 128Mi | the product's own deployment path (GitHub Actions), with the product | a one-shot copy of a per-application database for a product that is not admitted to this node; the copy follows the product |

## Chart capacity reserves

| chart | cpu | memory | basis |
|---|---|---|---|
| cert-manager/helmrelease/cert-manager | 100m | 384Mi | three controllers (cert-manager, cainjector, webhook) at 30m/128Mi each; the chart's own defaults declare no requests, so this is a forecast, not a measurement |
| edge/helmrelease/external-dns | 50m | 128Mi | one deployment, the chart's default request ceiling for a single-replica DNS watcher; forecast, the chart declares no requests |
| edge/helmrelease/traefik | 100m | 256Mi | one ingress controller at the estate's own edge request (see platform/edge/status-page.yaml); forecast, the chart declares no requests |
| estate-db/helmrelease/cloudnative-pg | 400m | 2048Mi | the operator (50m) plus one Postgres instance (350m/1.5Gi), which is what the estate's database actually costs; forecast, the chart declares no requests |
| event-bus/helmrelease/nats | 100m | 512Mi | one JetStream server with the file store the estate's bus needs; forecast, the chart declares no requests |
| external-secrets/helmrelease/external-secrets | 50m | 256Mi | three controllers (webhook, cert-controller, controller) sharing 50m/256Mi; forecast, the chart declares no requests |
| flux-system/helmrelease/vendor-bridge | 50m | 128Mi | one bridge pod from the human-vault chart; forecast, the chart declares no requests |
| hindsight/helmrelease/hindsight | 200m | 768Mi | the chart's own published single-replica envelope; forecast, the chart declares no requests |
| identity/helmrelease/oauth2-proxy | 50m | 128Mi | one proxy replica in front of the identity front door; forecast, the chart declares no requests |
| kyverno/helmrelease/kyverno | 250m | 1024Mi | the chart's published single-replica envelope for admission, background and reports; forecast, the chart declares no requests |
| metrics-server/helmrelease/metrics-server | 50m | 128Mi | one metrics-server replica; forecast, the chart declares no requests |
| monitoring/helmrelease/blackbox | 100m | 256Mi | one prober replica; forecast, the chart declares no requests |
| monitoring/helmrelease/kube-prometheus-stack | 600m | 2560Mi | Prometheus plus the operator, the chart's lean profile without the alertmanager and without the long-term store; forecast, the chart declares no requests |
| reloader/helmrelease/reloader | 25m | 64Mi | one reloader replica; forecast, the chart declares no requests |
| tailscale/helmrelease/tailscale-operator | 50m | 128Mi | one operator replica; forecast, the chart declares no requests |
| temporal/helmrelease/temporal | 350m | 1536Mi | server, worker and UI on one node, the profile the estate's sovereign bus runs; forecast, the chart declares no requests |

## One image, several workloads

- `docker.io/library/python:3.11-slim`: otto-gateway/cronjob/otto-answer-probe, otto-gateway/cronjob/otto-registration-reconciler, research/cronjob/exa-credit-probe
- `docker.io/library/redis:7.4-alpine`: efda-system/statefulset/efda-checkpoints, llm/deployment/litellm-cache
- `ghcr.io/chidionyema/efda:main-14976-9063f99d33ba5f9ff7079a8c2633434b7e0c483a`: efda-system/deployment/efda-controller, efda-system/deployment/efda-executor
- `ghcr.io/chidionyema/epistemic-ingest:main-14961-7919fa308dbb319ed0541d5ac251cc9f7a18709d`: epistemic-fabric/deployment/epistemic-ingest-cicd, epistemic-fabric/deployment/epistemic-ingest-github, epistemic-fabric/deployment/epistemic-ingest-incidents, epistemic-fabric/deployment/epistemic-ingest-slack
- `ghcr.io/chidionyema/hermes-agent:main-111-d1fb6f455a5947c96c9adaaa32889c91541ddcec`: hermes-agent/deployment/hermes-agent-gateway, otto-gateway/deployment/otto-gateway, otto-gateway/job/otto-memory-store-8, otto-golden/deployment/otto-golden
- `ghcr.io/chidionyema/quad-ledger:main-14823-f1a6f263c1a9df6f0a041050d7aecd4544b880ed`: quad/cronjob/quad-ledger-anchor, quad/cronjob/quad-ledger-verify, quad/deployment/quad-ledger
- `ghcr.io/chidionyema/spine:main-14976-9063f99d33ba5f9ff7079a8c2633434b7e0c483a`: spine/deployment/spine-bridge, spine/deployment/spine-worker
- `ghcr.io/chidionyema/unified-memory-server:main-14961-7919fa308dbb319ed0541d5ac251cc9f7a18709d`: unified-memory/cronjob/unified-memory-consolidate, unified-memory/deployment/unified-memory-server
- `ghcr.io/chidionyema/voice-router:main-14961-7919fa308dbb319ed0541d5ac251cc9f7a18709d`: voice-router/deployment/voice-router, voice-router/deployment/voice-router-director
- `ghcr.io/cloudnative-pg/postgresql:18.1-standard-bookworm`: backstage/job/estate-db-copy-backstage-r2, dagster/job/estate-db-copy-dagster-r3, guacamole/job/estate-db-copy-guacamole-r2, healthchecks/job/estate-db-copy-healthchecks-r2, hindsight/job/estate-db-copy-hindsight-r5, llm/job/estate-db-copy-litellm-r2, observability/job/estate-db-copy-langfuse-r2, observability/job/estate-db-copy-superset-r2, otto-gateway/job/estate-db-copy-otto-gateway-r3, temporal/job/estate-db-copy-temporal-r3
- `ghcr.io/oracle/oci-cli:20260826`: estate-db/cronjob/estate-db-backup, identity/cronjob/front-door-heartbeat, llm/cronjob/router-backup
- `ghcr.io/tailscale/tailscale:v1.102.3`: hermes-agent/deployment/hermes-agent-gateway, otto-gateway/deployment/otto-gateway
