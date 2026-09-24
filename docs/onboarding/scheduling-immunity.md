# Onboarding: scheduling immunity (crew#539)

You are adding or changing a platform workload. Three things to know.

**Name a PriorityClass.** Every Deployment, StatefulSet or CronJob in an idp namespace should carry
`spec.template.spec.priorityClassName`. Today that is audited (`kubectl get policyreport -A`); it
will be enforced after the first zero-violation pass. The classes:

| class | value | who |
|---|---|---|
| `infrastructure-critical` | 1000000 | the radio-room set only: langfuse-web, langfuse-worker, agentgateway, hermes-agent-gateway, telemetry-coverage, cluster-state. Adding a seventh is a founder decision, not a PR. |
| (none, or a class you add here with a value between 0 and 999999) | | ordinary platform workloads |
| `balloon` | −1 | the pause pods in `platform/scheduling/balloon.yaml` and nothing else |

**Do not touch the six.** The Kyverno policy `require-priority-class` refuses any of the six that
drops the class; `tests/test_incident_crew539_radio_room_survives_node_swap.py` refuses a seventh.

**A new founder surface is a portal row.** `ping.yml` and oke-check's founder-links both read
`backstage/founder/catalog-info.yaml`; add the URL there and it is probed from outside the
cluster within five minutes. There is no second list.

**Sizing.** The balloon is 2 × 300m on the 4 OCPU node. If the pool changes size, change the
replica count or request so the total stays in 10–20 % of one node (the test checks the band).

**Healing loops.** `platform/healing/` holds the Descheduler and K8sGPT. K8sGPT reads one vault
entry, `k8sgpt` (field `key`, a LiteLLM virtual key), minted by `vault-seed.yml -f entry=k8sgpt`
through `bin/idp-router-key` from the router's master key in the vault — no person mints or pastes
it; it never holds a vendor key.

**Guaranteed QoS on the six, and on the databases under them.** `requests == limits` for cpu and
memory on every container (agentgateway, hermes-agent-gateway, telemetry-coverage, cluster-state,
langfuse web/worker and its Postgres/Redis, Backstage Postgres, SigNoz ClickHouse). The kubelet
evicts BestEffort first, Burstable next, Guaranteed last. The Kyverno rule
`radio-room-set-is-guaranteed` refuses a widened limit on any of the six;
`tests/test_crew539_cp9_radio_room_and_databases_are_guaranteed_qos.py` runs the same rule through
the `kyverno` CLI both ways. Need more CPU for one of them? Raise request AND limit together.

**Crash evidence lands in Telegram.** `platform/robusta/` (Robusta, no SaaS, no bundled
Prometheus) posts the previous container's log and the last eight events on the second
CrashLoopBackOff restart, to the same bot and channel as Flux (`robusta-telegram` ExternalSecret
from vault entry `flux-telegram`). A stuck-Terminating pod has no Robusta built-in; the
Descheduler owns it, and the gap is on crew#539.
