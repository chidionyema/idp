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

A Helm-backed surface is graded on the values this repository sets, because a chart's default is
not a decision anyone here made -- oauth2-proxy 10.7.0 defaults to `replicaCount: 1`.

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
  `platform/availability-waivers.yaml` against idp#544. The estate can go blind without going down.

## How it is enforced

`bin/idp-availability-gate`, run by `bin/idp-ci` on every change. It grades the **rendered**
manifests (`kustomize build`), never the file text, so an overlay that fixes a base is judged on
what actually reaches the cluster. It has no silent pass: a surface it cannot resolve is `BLIND`
(exit 2), a waiver without a reason and an open issue is a `FAIL`, and every waiver prints a
`WAIVED` row on every run so the debt is read out loud each time CI speaks. The list is meant to
reach zero.

The drain side of the same incident -- refusing to cordon into a PDB deadlock or a cluster with no
room, and silencing Alertmanager for the window -- is `bin/idp-oke-break-glass` (idp#543).
