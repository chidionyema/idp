# 0012. Staging is a namespace on the one cluster; every platform option is a switch that carries its own infra cost; a namespace is never pruned

- Status: ACCEPTED 2026-08-29 (founder's words in sessions a0d64ea4 and f3f21d6e, 00:44Z to 01:55Z; recorded here on his ask "it was yesterday, go and dig it up").
- Date: 2026-08-29
- Deciders: founder; sessions a0d64ea4 (staging, cost, options), f3f21d6e (namespace prune).
- Affects: `platform/features/features.yaml`, `bin/idp-features`, `platform/edge/capacity-policy.yaml`, `platform/staging/*` (crew#584 CP-H), every `Namespace` under `platform/`, `clusters/oke/*.yaml`.

## The night, in plain words

The founder was told, at 00:44Z, that a hot-reload dev loop against the live cluster (mirrord) meant
"no second cluster". He rejected that framing and posted three documents. This page is the record of
what he said, what was decided, and where each decision now lives, so nobody has to search a
transcript for it again.

### 1. "We surely can't be serious that we don't need a staging cluster" (00:49Z)

He posted a cost sheet for a three-node OKE staging cluster (control plane free, three small nodes
about $82 a month, one load balancer about $8, or $0 on the Ampere free tier) and asked for the
exact cost of what we run now plus the extra.

Measured answer that night: production is one Ampere node of 6 cores / 24 GB. Oracle gives 2 cores /
12 GB free per account; the other 4 cores are paid, about $42 a month. Control plane, load balancer,
disk and vault cost nothing. A separate staging node of 2 cores / 12 GB would be all paid (about
$28) plus a second load balancer ($8), about $36 a month.

His follow-up: "so why does our prod cluster cost so much", "why 4 cores, do we need all that
capacity, who made the call, do we have utilisation metrics". The honest answer was that the 6-core
size was chosen from paper requests (7.6 cores asked for across 97 resource blocks), not from a
measured number, and the number had never been on hand although metrics-server, SigNoz and
Prometheus were all running.

**Decision:** staging is a `staging` namespace on the one cluster, with the same Flux tree, and the
lean tier gets it too: "lean should be able to have staging namespace given its lean" (01:55Z).
That is crew#584 CP-H (Namespace, ResourceQuota, LimitRange, `bin/idp-dev <service>` over
mirrord), built and held unpushed for his word. A second cluster is not the answer while every core
on it is a paid core and the first cluster is sized on guesses.

### 2. "Options, and I need serious consideration" (01:09Z, 01:20Z, 01:23Z)

He posted the cost-zealot document (micro requests with burst limits, ClickHouse and retention on a
diet, Temporal on Postgres, no idle capacity) and ruled: "we need to retain as many options as
possible and be able to enable via Backstage, this is the essence of self service"; "it's not just
on/off, we reasoned the reasons why the options, so they need to take into account the infra
requirements and allocate accordingly"; "every capability is an option with a known cost";
"infra sized from the options, not the other way round".

**Decision:** one feature register in git, `platform/features/features.yaml`: core (always on) plus
every optional capability with tiers (enterprise or lean), and for each tier its CPU, memory and
storage floor, its dependencies, and the Flux switches it turns on. Allocation is computed from
what is switched on (`bin/idp-features plan`), never typed. The register is merged; the portal
switch for it is the open part (crew#584, crew#624).

What went with it, as housekeeping under the same ticket: paper CPU requests trimmed from 7.64 to
3.54 cores, a usage-versus-paid row in the 15-minute cluster receipt, and the admission fence that
refuses any request over a quarter core without a measured approval label
(`platform/edge/capacity-policy.yaml`). The fence is why a later Langfuse repair (idp#835) carries
`idp.platform/capacity-approved` and a diagnose run number instead of a guess.

### 3. "Moving a file in git should never destroy a production namespace" (01:17Z)

At 01:05Z the catalogue went 404: a merge moved the Backstage namespace from one Flux row to
another and the old row pruned it. He posted the fix: every Namespace carries
`kustomize.toolkit.fluxcd.io/prune: disabled`, applied by a kustomize patch, not by memory; "no
agent, no human, and no automated GitOps sync can ever prune a critical namespace again".

**Decision:** landed. `platform/backstage/namespace/base/namespace.yaml`, `platform/edge/namespace.yaml`,
`platform/edge/k8s-infra-namespace.yaml` and `clusters/oke/edge.yaml` carry the annotation; `tests/test_incident_a_namespace_moved_between_flux_rows_was_pruned.py` refuses a Namespace without it.

### 4. How the crew works, ruled the same night

- "Frontier models do highly valuable work only" (LAW 42): measuring, trimming and reading CI reds
  are worker tasks; the frontier session ranks by "does this make the platform sellable and
  future-proof" before anything runs.
- "Don't you think we should have had the numbers on hand?": a question is answered from standing
  evidence (the receipt, the science department), never by starting a two-hour dig.
- "We are pairing": one step at a time, named before it runs, when he says so.

## Where to find it

| Topic | Lives at |
|---|---|
| Staging namespace | crew#584 CP-H; `platform/staging/*` (branch, awaiting his word) |
| Feature register and planner | `platform/features/features.yaml`, `bin/idp-features` |
| Capacity fence and budget | `platform/edge/capacity-policy.yaml`, `tests/test_incident_crew584_capacity_requests_need_proof.py` |
| Namespace never pruned | the four namespace files above; `clusters/oke/edge.yaml` |
| Production cost | `estate-defaults.yaml` (free allowance first, $50 cap) |
| The transcripts | `~/.claude/projects/-Users-chidionyema-dev-code/a0d64ea4-*.jsonl`, `f3f21d6e-*.jsonl`, 2026-08-29 00:44Z to 01:57Z |
