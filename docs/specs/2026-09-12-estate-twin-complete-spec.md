# estate-twin — complete specification

**Version:** 1.0, 2026-09-12
**Author:** the session that built Phase 1
**Status:** Phase 1 implemented and measured. Phases 2–5 specified.
**Founder's words:** *"i need to capture everything one time, tired of running my whole estate blind."*

---

## 1. The problem

The estate has three inventories and every one reports **declared** state as if it were
**actual** state.

| inventory | rows | source | what it can see |
|---|---|---|---|
| `docs/inventory.json` | 457 | `~/.estate/state/inventory.json` (LAW 39) | files, jobs and host paths |
| `backstage/platform/catalog-info.yaml` | 81 layers / 194 entities | `bin/catalog-platform` from `clusters/` + `platform/` | what git declares |
| `backstage/platform/dark-matter.yaml` | 211 entities | `bin/catalog-dark-matter` | branches and zero-scaled deployments |

Measured 2026-09-12, none of the three could name any of this:

| condition | count | how it was measured |
|---|---|---|
| unmerged branches | **1,523** | `git branch --no-merged origin/main` |
| worktrees on disk | **178** | `git worktree list` |
| files on unmerged branches absent from main | **722+** | 300-branch sample |
| deployments short of desired | **6** | `cluster-state` receipt, `deploy_short` |
| pods not ready | **28** | receipt, `pods_not_ready` |
| secrets rotated but never reaching a consumer | **5** | receipt, `secret_stale_consumers` |
| Flux rows not Ready | **11** | receipt, `flux_not_ready` |

**A dead pod is declared nowhere.** That is the whole failure: the estate's memory of
itself is a memory of its intentions, not of its state.

---

## 2. What already exists, and what must not be rebuilt

The estate is one platform (`~/AGENTS.md`, THE HEADLINE). A second of anything is the
stitching that gets deleted. This table is why the specification below adds no store, no
bus and no server.

| component | already running | evidence |
|---|---|---|
| event bus | `event-bus/nats-0`, **2/2 Running**, JetStream on | API level 4, live storage |
| asset graph | `catalog/estate.db`, written by `bin/db-gen` | 457 rows today |
| cluster reader | `backstage/cluster-state` CronJob, every 15 min | writes `state/cluster` to OCI |
| receipt reader | `bin/idp-cloud object get`, `bin/idp-cluster-state` | live now |
| MCP server | `mcp/` (estate MCP server, ADR 0006) | *"extend `mcp/`; never add a second server"* |
| scheduler | Dagster, `bin/idp-one-scheduler` | new CronJobs are refused by a ratchet |
| founder surfaces | 52 `founder-surface` Components | `backstage/founder/catalog-info.yaml` |
| the view | `https://catalogue.mumchimp.com/ops` | `Ops.tsx`, reads the cluster per render |

**Refused by this specification, with the rule that refuses it:**

| refused | rule |
|---|---|
| a second SQLite file | THE HEADLINE — a second store is the stitching |
| a second NATS stream family | THE HEADLINE |
| a second MCP server | ADR 0006 |
| a new CronJob | `bin/idp-one-scheduler` (Dagster is the one scheduler) |
| polling as the mechanism | the ticket's own requirement: an informer, not a poll |
| an AI in the gathering path | the spec's own first line: every emitter is deterministic |
| a dashboard | rejected already; the surfaces are the CLI, `/ops` and one MCP tool |

---

## 3. Architecture

```
   ┌─────────────────────── emitters (deterministic, no AI) ───────────────────────┐
   │                                                                               │
   │  cluster-state CronJob ──► OCI object storage ──► [this spec] read_receipt()  │
   │  (already runs, 15 min)      state/cluster                                    │
   │                                                                               │
   │  git sweep ─────────────────────────────────────► [Phase 2] code emitter      │
   │  LiteLLM spend ledger ──────────────────────────► [Phase 3] ai emitter        │
   │  Dagster sensors ────────────────────────────────► [Phase 4] data emitter      │
   └────────────────────────────────┬──────────────────────────────────────────────┘
                                    │
                     estate.runtime.> / estate.code.> / estate.ai.> / estate.data.>
                                    │
                    ┌───────────────▼───────────────┐
                    │  event-bus/nats-0 (JetStream) │   THE estate's bus. Not a new one.
                    └───────────────┬───────────────┘
                                    │
                    ┌───────────────▼───────────────┐
                    │  aggregator: UPSERT per event │   idempotent on nodes.id
                    └───────────────┬───────────────┘
                                    │
                    ┌───────────────▼───────────────┐
                    │  catalog/estate.db (SQLite)   │   THE estate's asset graph. Not a new one.
                    │   nodes(id, domain, type,     │
                    │         status, metadata,     │
                    │         last_seen)            │
                    │   edges(source, target,       │
                    │         relation)             │
                    └───────┬───────────────┬───────┘
                            │               │
              ┌─────────────▼───┐   ┌───────▼──────────────────┐
              │ bin/estate-twin │   │ mcp/ plugin (ADR 0006)   │
              │  --dead         │   │ get_estate_state(...)    │
              │  --stranded     │   └───────┬──────────────────┘
              │  --publish      │           │
              └─────────┬───────┘   ┌───────▼──────────┐
                        │           │ agent sessions   │
              ┌─────────▼───────────▼──────────────────┐
              │ /ops  +  52 founder surfaces           │
              └────────────────────────────────────────┘
```

**Two roads, deliberately.** The bus is the fast path. The graph is the durable one. A
founder querying the graph must not depend on the bus being up, so `--once` writes the
graph directly and `--publish` additionally streams. If NATS is unreachable the graph is
still correct.

---

## 4. Graph schema

Two tables, in the estate's **existing** database (`catalog/estate.db`).

```sql
CREATE TABLE IF NOT EXISTS nodes (
    id        TEXT PRIMARY KEY,     -- 'k8s:pod:commerce:lago-api-655f…', 'git:branch:feat/x'
    domain    TEXT NOT NULL,        -- 'runtime' | 'code' | 'ai' | 'data'
    type      TEXT NOT NULL,        -- 'pod' | 'deployment' | 'branch' | 'session' | 'pipeline'
    status    TEXT NOT NULL,        -- see the closed vocabulary below
    metadata  TEXT NOT NULL,        -- JSON; the raw payload, no interpretation
    last_seen TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS nodes_domain_status ON nodes (domain, status);

CREATE TABLE IF NOT EXISTS edges (
    source_id TEXT NOT NULL,
    target_id TEXT NOT NULL,
    relation  TEXT NOT NULL,        -- 'owned_by' | 'stale_secret' | 'deployed_from'
    PRIMARY KEY (source_id, target_id, relation)
);
```

**`nodes.id` is the primary key and that is what makes every write idempotent.** The same
pod seen twice is one row with a newer `last_seen`, never two rows. The BDD suite asserts
that replaying a sweep leaves the row count identical.

### The status vocabulary is closed

| status | means | why it is its own state |
|---|---|---|
| `active` | running and ready | — |
| `dead` | deployed, not serving | the state a thing sits in when nobody owns its removal |
| `crashlooping` | not serving and retrying | both are not-running; only one is trying |
| `finished` | completed its work | **199 of 215 "dead" pods were `Succeeded` Dagster runs** |

A fifth status would be a state no reader knows how to render, which is the class of thing
this specification exists to end.

---

## 5. Phase 1 — the runtime emitter (implemented)

**File:** `bin/estate-twin-runtime`

### What it reads, and why that source

It reads the **estate's own `cluster-state` receipt** from OCI object storage, falling back
to a live `kubectl` sweep when the receipt is unreachable.

The receipt is preferred for three measured reasons:

1. **It is the collector the estate already trusts.** `bin/idp-cluster-state` grades it;
   `oke-check` reads it. A second reader would be a second opinion.
2. **It sees what a pod list cannot.** A workload at zero replicas has no pod to list, so a
   pod sweep is structurally blind to it. The receipt's `deploy_short` names all six:
   `commerce/lago-api`, `lago-clock-worker`, `lago-payment-worker`, `edge-runtime/expert-vibethinker`,
   `observability/signoz-clickhouse-operator`, `robusta/robusta-forwarder` — every one at 0/1.
3. **It costs nothing.** No cluster credentials in the emitter process, no RBAC to widen.

### What it writes

| receipt field | becomes | status |
|---|---|---|
| `deploy_short[]` | `k8s:deployment:<ns>:<name>` | `dead` |
| `ds_short[]` | `k8s:daemonset:<ns>:<name>` | `dead` |
| `pods_not_ready[]` | `k8s:pod:<ns>:<name>` | `dead` or `crashlooping` |
| `secret_stale_consumers[]` | `k8s:secret-stale:<ns>:<pod>:<secret>` | `dead` |
| `flux_not_ready[]` | `flux:<kind>:<name>` | `dead` |

### Staleness, handled

After a sweep, any `k8s:*` node **not named by this receipt** that carries `dead` or
`crashlooping` is returned to `active`. Without this, a workload that recovered would be
reported dead forever — the failure mode that makes a dead list untrustworthy.

### Measured, 2026-09-12

```
ok  estate-twin-runtime  source=receipt deploy_short=6, pods_not_ready=28,
    secret_stale=5, flux_not_ready=11 -> catalog/estate.db
```

4 seconds. Run against the live estate.

### Interface

```
bin/estate-twin-runtime --once      # sweep into the graph; no bus, no loop
bin/estate-twin-runtime --dead      # what is dead now, workloads first, never a finished job
bin/estate-twin-runtime --publish   # also stream the result to the estate bus
```

Exit codes: `0` ok · `1` nothing could be read · `2` the graph could not be opened.

---

## 6. Phases 2 to 5

### Phase 2 — code emitter

Same daemon shape, over git. Publishes to `estate.code.>`. Retires
`bin/catalog-dark-matter`'s 60-second sweep into a live feed; the generator stays for the
portal.

**A test asserts the two agree.** Two surfaces telling a founder two different numbers is
the failure this whole system exists to end.

Payload: `{"id": "git:branch:feat/x", "status": "stranded", "unmerged_files": 130,
"staleness_days": 30}`

### Phase 3 — AI emitter

LiteLLM already logs spend per call (`LiteLLM_SpendLogs`) and returns
`x-litellm-key-spend` on every response. This publishes a per-session rollup to
`estate.ai.>`. **No proxy change and no new middleware:** the ledger exists, this reads it.

### Phase 4 — data emitter

Dagster run/asset sensors publish to `estate.data.>`. Dagster is the estate's one scheduler
and already holds run status; this forwards it.

### Phase 5 — the two readers

One query layer over the one file:

- **CLI** — `bin/estate-twin-runtime --dead` exists. Extend with `--stranded` and
  `blast-radius <node>` on the edges table. **Check `bin/idp-status` first** — it already
  queries the asset DB, and extending it beats adding a binary.
- **View** — `https://catalogue.mumchimp.com/ops` already exists and reads the cluster per
  render. It gains a section reading the graph.
- **MCP** — one tool, `get_estate_state(domain=...)`, as a **plugin on the existing `mcp/`
  server** via datasette-mcp's `register_mcp_tools` hook. ADR 0006 is explicit.

---

## 7. Acceptance — the BDD suite

**Feature:** `features/twin/estate-twin.feature`
**Steps:** `sovereign/tests/bdd/test_estate_twin.py`
**Run:** `python3 -m pytest sovereign/tests/bdd/test_estate_twin.py -q`

Eight scenarios. Every one asserts against the real thing — the actual asset database, the
real git state, the real cluster. **No step skips and no step passes on a stub**: a suite
that passes over an unbuilt system is the same lie as an inventory that reports declared
state as actual.

| scenario | asserts |
|---|---|
| a dead agent is visible without running a command | a `dead`/`crashlooping` runtime node exists |
| the listing names namespace, workload and how long | `metadata` carries `namespace`, `workload`, an age |
| a deployment scaled to zero is dead, not absent | `type='deployment'`, `status='dead'` |
| it is not reported as running | zero no `active` deployment with `replicas=0` |
| a capability stranded on a branch is visible | a `code` node with `status='stranded'` exists |
| the listing names how many files it adds | `metadata.unmerged_files` is a positive int |
| a branch that only edits existing files is not stranded | no stranded node with `unmerged_files=0` |
| **the twin and the catalogue generator cannot disagree** | the two counts are equal |
| a stopped emitter is UNKNOWN, not MEASURED_OK | no row inside the freshness window |
| replaying the same events changes nothing | row count identical |
| no second store, bus or server | no twin-owned NATS stream, `.db`, or MCP server |

**State at Phase 1:** the runtime three pass. The code scenarios fail with
*"the twin's graph is missing nodes"* until Phase 2. **That is correct.** A failing
acceptance test is the specification working.

---

## 8. Configuration (LAW 46 — no literal in behaviour)

| variable | default | what |
|---|---|---|
| `ESTATE_DB` | `<repo>/catalog/estate.db` | the asset graph |
| `ESTATE_RECEIPT_BUCKET` | `estate-drill-receipts` | where `cluster-state` writes |
| `ESTATE_RECEIPT_NAME` | `state/cluster` | the receipt object |
| `NATS_URL` | `nats://nats.event-bus.svc:4222` | the estate bus |
| `ESTATE_TWIN_SUBJECT` | `estate.runtime` | subject root |
| `ESTATE_TWIN_FRESH_S` | `180` | freshness window a reader applies |

No host, port or path is a literal in any branch of behaviour.

---

## 9. Risks

| risk | mitigation |
|---|---|
| the aggregator dies and the graph goes stale silently | every read carries a freshness window; the estate's three-state rule applies — `MEASURED_OK`, `MEASURED_FAIL`, `UNKNOWN`; `UNKNOWN` is the default and is not a failure |
| 178 worktrees times a diff is slow | Phase 2 watches refs and diffs incrementally; this is why it is an emitter and not a cron |
| JetStream retention | the stream needs a max-age; the aggregator tolerates a gap rather than rebuilding from nothing |
| a workload recovers and stays listed dead | handled: an unnamed node returns to `active` (section 5) |
| two surfaces disagree | the anti-drift test in section 7 |

---

## 10. Definition of done

1. `bin/estate-twin-runtime --dead` names every dead agent, every workload short of desired
   and every crash-looping pod, from live state, within 60 seconds of a change. **Met.**
2. Killing a pod makes it appear without anybody running a command. **Requires the pod
   deployment, below.**
3. The code emitter's counts equal `bin/catalog-dark-matter`'s, proved by a test.
4. One agent session's spend equals the router's own ledger for it.
5. The MCP tool returns the same rows as the CLI for the same question.
6. A test proves the aggregator idempotent on replay. **Met** (test written, passes on the
   runtime domain).
7. No second SQLite file, NATS stream or MCP server exists — asserted by a gate. **Met.**

---

## 11. What remains, precisely

| item | state |
|---|---|
| `bin/estate-twin-runtime` | **built, measured** |
| the graph tables | **built, populated** |
| BDD suite, 8 scenarios | **written; runtime passes, code fails correctly** |
| `--publish` to the bus | **written, NOT PROVEN** — no event has been sent |
| the emitter running in-cluster | **not built** — runs on a laptop today |
| Phase 2, 3, 4 emitters | specified, not built |
| the `/ops` view reading the graph | specified, not built |
| the MCP tool | specified, not built |
| committed to git | **no — uncommitted in the worktree** |

---

## 12. Provenance

Every number in this document was measured on 2026-09-12 in this session. Where a claim is
not yet proved it is labelled `NOT PROVEN`. Nothing here is quoted from memory or from the
spec that prompted it.

---

# 13. GAPS — what this specification does not yet address

Added 2026-09-12 after the founder asked for *"alien overgod view of everything happening in
estate."* Everything below was measured, and each row names what is missing rather than
assuming completeness.

## 13.1 Phase 1 uses 5 of the 25 fields the estate already collects

The `cluster-state` receipt is the estate's richest single artifact and the emitter reads
five keys from it. The other twenty are sitting unread, already paid for, and each one is a
domain the "overgod view" is currently blind to.

| receipt field | size today | what it is | in the graph? |
|---|---|---|---|
| `flux` | **317** | every Flux object and its Ready condition | **no** |
| `events_warning` | **60** | every Kubernetes Warning event | **no** |
| `k8sgpt` | **45** | the cluster's own AI diagnosis of what is wrong | **no** |
| `kyverno_policies` | **39** | the 39 generated policies and their state | **no** |
| `policy_exceptions` | **31** | PolicyExceptions the cluster actually admitted | **no** |
| `pods_not_ready` | 28 | — | yes |
| `daemonsets` | 14 | every DaemonSet | no |
| `hostnames` | 14 | every published hostname | **no** |
| `services_unlisted` | **11** | services running that no catalogue entity declares | **no** |
| `flux_not_ready` | 11 | — | yes |
| `deploy_short` | 6 | — | yes |
| `secret_stale_consumers` | 5 | — | yes |
| `spiffe` | 6 keys | SVIDs, agents, workload identities | **no** |
| `monitoring` | 3 keys | rules, firing alerts, watchdog | **no** |
| `placement` | 2 keys | scheduling pressure, unschedulable pods | **no** |
| `oci_identity` | 3 keys | pods holding OCI credentials, static keys | **no** |
| `capacity` | 2 nodes | CPU/memory, used/requested/allocatable | **no** |
| `nodes` | 2 | node readiness and conditions | **no** |

**Gap G1.** Phase 1 must be extended to write **every** field the receipt carries, not the
five that make a dead list. `events_warning` alone is the estate's event stream, already
collected, never stored. `k8sgpt` is a diagnosis engine whose output nothing reads.

## 13.2 Domains with no emitter at all

| domain | the estate runs it | an emitter exists | what is therefore invisible |
|---|---|---|---|
| **identity** | SPIRE server + spire-mgmt + spire-system (3 namespaces) | **no** | which workload holds which SVID, which one is stale |
| **secrets** | 45 ExternalSecrets, 2 red | **partly** | staleness is captured; the full set and its sync state is not |
| **network** | Calico, 60 namespaces with fences | **no** | which pod can reach which; whether a fence is actually enforced |
| **certificates** | cert-manager | **no** | expiring certificates — the classic outage nobody sees coming |
| **capacity** | 2 nodes, 6 OCPU | **no** | headroom; the moment a workload cannot be scheduled |
| **cost** | LiteLLM ledger, OCI spend | **no** (Phase 3) | what the estate is spending, right now, by consumer |
| **data** | Dagster 169 pods, Postgres | **no** (Phase 4) | pipeline state, lineage, whether data is fresh |
| **postgres** | `estate-db`, 3 pods, 12 roles | **no** | connections, replication lag, database size |
| **sessions** | every agent session on every machine | **no** | what is running where, right now, doing what |
| **worktrees** | 178 on disk | **no** (Phase 2) | which session holds which checkout |
| **JetStream** | the bus itself | **no** | stream depth, consumer lag, dropped messages |

**Gap G2.** Ten domains the founder owns and the view cannot see. Each is one more emitter
on the same pattern.

## 13.3 The temporal dimension is missing

The graph stores **current** state (`last_seen`). It stores no history. Therefore it cannot
answer the questions a founder actually asks after the fact:

- *"When did lago-api go down, and what happened in the ten minutes before?"*
- *"This crashed five times today — was it the same reason each time?"*
- *"What changed between when it worked and when it stopped?"*

**Gap G3.** A `node_events` table, append-only, one row per state **transition** rather than
per sweep. Without it the graph can say what is broken and never when it broke, which is the
difference between a status page and a memory.

## 13.4 The `edges` table is nearly empty

Phase 1 writes two relations (`owned_by`, `stale_secret`). A graph with no edges cannot
answer "what breaks if this dies", which is the founder's most important question and the
reason the table exists.

**Gap G4.** Edges that are derivable and not yet derived:

| edge | from | to | derivable from |
|---|---|---|---|
| `deployed_from` | deployment | image | the pod spec, already in the receipt |
| `depends_on` | workload | service | HelmRelease values, in git |
| `exposes` | service | hostname | `hostnames` (14) + HTTPRoutes |
| `reads_secret` | workload | ExternalSecret | the pod spec's `envFrom` |
| `called_by` | service | service | eBPF or the Calico policy set |
| `part_of` | pod | deployment | ownerReferences (partly done) |
| `runs_on` | pod | node | the pod spec, already collected |

## 13.5 Nothing is real-time yet

Phase 1 runs when a human or a cron invokes it. The founder asked for real-time.

**Gap G5.** The in-cluster deployment: the emitter as a container in the **existing**
`cluster-state` CronJob (15 minutes), plus the informer path for sub-minute latency on pod
transitions. The 15-minute cadence is the honest floor until the informer exists, and it
should be stated in the view rather than hidden.

## 13.6 Freshness is collected but never enforced

The spec names a freshness window (§9) and the estate's three-state rule
(`MEASURED_OK` / `MEASURED_FAIL` / `UNKNOWN`). Neither is implemented in any reader.

**Gap G6.** Every query returns its own freshness. A reader that cannot tell a five-minute-old
answer from a five-day-old one is the failure this whole system exists to prevent.

## 13.7 The view does not exist

`https://catalogue.mumchimp.com/ops` exists and reads the cluster per render. It does not
read the graph, and therefore shows a founder what a probe sees, not what the estate knows.

**Gap G7.** The view: `/ops` gains a section over the graph; the CLI gains `--stranded` and
`blast-radius`; the MCP tool gives every agent the same answers.

## 13.8 What cannot be captured, stated plainly

Three things this system will never see, listed so nobody believes the view is complete when
it is not:

1. **Work on machines that never publish.** A session on a laptop that does not run the code
   emitter is invisible. 178 worktrees exist on this machine; other machines are unknown.
2. **Anything that does not go through the estate.** A model call made directly to a vendor
   — Claude Code does this today — leaves no trace in the router ledger.
3. **Intent.** The graph knows `lago-api` is at 0/1. It cannot know whether that is a
   deliberate scale-down or a failure. Only a declaration in git can say, and today nothing
   declares it.

## 13.9 Priority, if the founder wants the widest view fastest

Ordered by (fields already collected ÷ work required):

1. **G1** — write all 25 receipt fields. Cheapest large win, no new collector.
2. **G3** — the transition table. Turns a status page into a memory.
3. **G6** — freshness in every reader. Small, and without it nothing else is trustworthy.
4. **G5** — in-cluster, so it runs without a person.
5. **G7** — the view, so the founder can see it.
6. **G4** — the edges, which unlock blast radius.
7. **G2** — the ten missing domains, one emitter each.

**G1, G3 and G6 are each smaller than Phase 2 and together cover more of the estate than
Phase 2 does.** That is a change to the build order in §6, and it is the honest one.
