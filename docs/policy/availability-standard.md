# The availability standard

**Every surface the founder can open survives losing one node. This is checked before the change
merges, not after the outage.**

2026-08-28 06:20-06:39Z a node was cordoned. `https://catalogue.mumchimp.com` answered 503 for
about fifteen minutes and the founder found it before any instrument did. Nothing had broken: the
manifest said `replicas: 1` and `strategy: Recreate`, `platform/` contained no PodDisruptionBudget
at all, and the oauth2-proxy in front of every surface ran on the chart's default of one replica.
The estate had no availability requirement, so no review could fail one and no risk register could
carry it. The outage was the written standard working exactly as written. This page replaces it.

## What a routed surface must render

An HTTPRoute is the definition of founder-facing: if a route reaches it, it is graded.

| # | Requirement | Why this exact shape |
|---|---|---|
| 1 | `replicas >= 2` | one pod is one node event from a 503 |
| 2 | a PodDisruptionBudget that still permits a drain -- `maxUnavailable`, or `minAvailable` **strictly below** the replica count | a budget whose floor equals the replica count refuses every drain for ever; that is what the clickhouse PDB did to this same drain at 06:30:43Z |
| 3 | replicas kept off one node: a required `podAntiAffinity` or a `DoNotSchedule` `topologySpreadConstraint` on `kubernetes.io/hostname` | two replicas on one node are one replica; `ScheduleAnyway` collapses onto one node exactly when the cluster is tight, which is the moment the spread was for |
| 4 | a `readinessProbe` and a `livenessProbe` | a rollout with no readiness gate takes the last healthy pod down before the new one serves |

The blast radius is the namespace, not the one pod a route points at. `mcp.${ESTATE_ZONE}` graded
green on its gateway while `estate-mcp` and `github-mcp` -- the servers that gateway proxies to --
each ran a single pod, so the surface still died with a node. Every Deployment sharing a namespace
with a routed surface is graded. StatefulSets are not: a database here is one instance by design,
which is stated below rather than hidden.

A Helm-backed surface is graded on the values this repository sets, because a chart's default is
not a decision anyone here made -- oauth2-proxy 10.7.0 defaults to `replicaCount: 1`.

## The front door is a surface too

Seven surfaces that each survive a node are decorative if the one workload they all enter through
does not. Every HTTPRoute names a Gateway in `parentRefs`; nothing in any manifest says which
workload implements that Gateway, because `gatewayClassName` is resolved by a controller at
runtime. So `platform/availability.yaml` declares the mapping (`prospector/prospector-edge` ->
`edge/traefik`), the gate grades that workload by the same four requirements, and **a `parentRef`
no row claims is BLIND** -- a new gateway cannot arrive unseen. Traefik ran `replicas: 1` until
2026-08-28 and no manifest, review or instrument anywhere said so.

The same file's `also_graded` list holds workloads that carry founder traffic without a route of
their own (`hermes-agent/hermes-agent-gateway`, a ClusterIP every hermes workload calls). Named by
a human, graded identically.

## What is guaranteed, and what is not

Guaranteed, and provable by drilling it: **any one node can be cordoned, drained, replaced or lost
without a founder-facing surface returning an error.** Every graded surface runs two pods on two
different nodes, a disruption budget stops an eviction taking the last one, and the balloon pods
(`platform/scheduling/balloon.yaml`) hold preemptible headroom so an evicted pod lands in
milliseconds instead of waiting for a new machine to boot.

Not guaranteed, stated plainly rather than discovered later:

- **Losing two nodes at once.** The cluster runs two nodes; a two-node loss is a full outage.
- **The database tier.** `postgres` under backstage, healthchecks, llm, temporal and hindsight is
  one instance with one volume. A node loss there is a restart, not a failover -- minutes, not
  milliseconds. Making that highly available is a topology change with a mature operator, not a
  replica count.
- **Observability.** SigNoz and Langfuse stand on a single ClickHouse and are waived by name in
  `platform/availability.yaml` against idp#544. The estate can go blind without going down.
- **The agent gateway.** `hermes-agent/hermes-agent-gateway` holds one Telegram token (two
  long-pollers are 409s on both) and one ReadWriteOnce volume carrying `state.db`. Two replicas
  there is an outage, not a fix; idp#547 carries the real remedy (webhook, or a lease). A node
  loss stops The Architect until the pod reschedules.

## Why it went unshouted, and what stops that

Prometheus, Robusta and SigNoz are runtime monitors: they scream when something is *already*
dying. None of them reads a manifest and says "Traefik has no PodDisruptionBudget" the day before
a drain. The gap was configuration auditing, and the estate had none. Three things close it, and
each one is loud in a different place:

| When | What | Where the red light is |
|---|---|---|
| Before merge | `bin/idp-availability-gate` in `bin/idp-ci` | the PR is refused; `FAIL`/`BLIND` rows name the surface and the hostname |
| At admission | `platform/scheduling/require-availability.yaml` (Kyverno `Enforce`) | `kubectl apply`, a chart upgrade or a hand edit is rejected by the API server with the reason |
| Every run, for ever | the `WAIVED` rows | every waiver prints its reason and its open issue on every single CI run |

The gate and admission cannot drift apart: Kyverno is scoped by the namespace label
`availability.idp/tier: founder-facing`, and the gate **FAILS any namespace whose surfaces it just
passed that does not carry that label** -- CI proves the cluster is armed, rather than assuming it.

There is deliberately no PDB-existence rule in the ClusterPolicy: the `apiCall` shape it needs
panics Kyverno CLI 1.19.0, which `bin/idp-kyverno-render` and CI both run, and a policy that takes
the estate's own judge down is a worse outage than the one it prevents. The gate does that check
instead, on the whole rendered directory at once, where apply ordering does not exist.

## How it is enforced

`bin/idp-availability-gate`, run by `bin/idp-ci` on every change. It grades the **rendered**
manifests (`kustomize build`), never the file text, so an overlay that fixes a base is judged on
what actually reaches the cluster. It has no silent pass: a surface it cannot resolve is `BLIND`
(exit 2), a waiver without a reason and an open issue is a `FAIL`, and every waiver prints a
`WAIVED` row on every run so the debt is read out loud each time CI speaks. The list is meant to
reach zero.

The drain side of the same incident -- refusing to cordon into a PDB deadlock or a cluster with no
room, and silencing Alertmanager for the window -- is `bin/idp-oke-break-glass` (idp#543).
