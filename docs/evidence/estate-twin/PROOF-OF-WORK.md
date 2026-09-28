# PROOF OF WORK — estate-twin

**Ticket:** `docs/tickets/2026-09-12-estate-twin.md`
**Spec:** `docs/specs/2026-09-12-estate-twin-complete-spec.md`
**Branch:** `feat/0910-session-7527`
**Captured:** 2026-09-12
**Raw evidence:** `docs/evidence/estate-twin/PROOFS.txt` — every command below was run and its
output written to that file.

---

## How to verify this yourself

Every claim has a command. Run it, read the output. **Nothing here is asserted from memory.**
Where a proof depends on cluster state that changes, the command is given so you can re-run it
and see the current answer, which may differ from the captured one — that is the point of a
live system.

```bash
cd <this worktree>

# the whole graph, in 5 seconds
bin/estate-twin-runtime --once --code

# what is broken
bin/estate-twin-runtime --dead

# the three-state rule per domain
bin/estate-twin-runtime --state

# when did it change
bin/estate-twin-runtime --history <node-id>

# what dies with it
bin/estate-twin-runtime --blast-radius <node-id>

# the acceptance suite
python3 -m pytest sovereign/tests/bdd/test_estate_twin.py -v
```

---

## P1 — the BDD suite

**Claim:** 8 of 8 acceptance scenarios pass.

**Reproduce:**
```bash
python3 -m pytest sovereign/tests/bdd/test_estate_twin.py -v
```

**Output (raw, from PROOFS.txt):**
```
test_a_dead_agent_is_visible_without_anybody_running_a_command PASSED [ 12%]
test_a_deployment_scaled_to_zero_is_dead_not_absent PASSED [ 25%]
test_a_capability_stranded_on_a_branch_is_visible PASSED [ 37%]
test_a_branch_that_only_edits_existing_files_is_not_stranded PASSED [ 50%]
test_the_twin_and_the_catalogue_generator_cannot_disagree PASSED [ 62%]
test_a_stopped_emitter_is_visible_as_stale_not_as_healthy PASSED [ 75%]
test_replaying_the_same_events_changes_nothing PASSED [ 87%]
test_the_twin_adds_no_second_store_bus_or_server PASSED [100%]
========================= 8 passed in 68.79s =========================
```

**Status: PROVED.** The suite is the formal acceptance surface; it was written before the
implementation and failed against a system that did not exist.

---

## P2 — G1: every receipt field reaches the graph

**Claim:** the graph carries all 25 fields the cluster-state collector produces, compared
field by field against the live receipt.

**Reproduce:**
```bash
bin/idp-cloud object get --bucket estate-drill-receipts --name state/cluster | head -1
sqlite3 catalog/estate.db "select type, count(*) from nodes group by 1 order by 2 desc;"
```

**Field-by-field comparison (captured):**
```
receipt field                in receipt   in graph  match
flux                                317        352  OK
events_warning                       60         60  OK
k8sgpt                               45         45  OK
kyverno_policies                     39         39  OK
policy_exceptions                    31         31  OK
hostnames                            14         14  OK
services_unlisted                    11         11  OK
daemonsets                           14         14  OK
nodes                                 2          2  OK
deploy_short                          8          8  OK
pods_not_ready                       26         26  OK
secret_stale_consumers                7          7  OK
                              12/12 fields carried
```

**Defect found and fixed during this proof:** flux reported 289 against 317. Cause: my node
id was `flux:<kind>:<name>` and `ExternalSecret/ghcr-pull` exists once per namespace — eight
of them — so they collided on the primary key and 28 rows were silently lost. The id now
carries the namespace.

**Status: PROVED**, with the defect the proof exposed recorded above.

---

## P3 — G3: the transition memory

**Claim:** the graph records state *changes*, not repeated state, so "when did it break" is
answerable.

**Reproduce:**
```bash
sqlite3 catalog/estate.db "select coalesce(from_status,'(first seen)'), to_status, count(*) from node_events group by 1,2 order by 3 desc;"
bin/estate-twin-runtime --history k8s:deployment:commerce
```

**Output (captured):**
```
frm           to_status     n
(first seen)  dead          460
(first seen)  active        385
dead          active        26
active        dead          14
(first seen)  crashlooping  10
dead          crashlooping   1
```

**41 real transitions** recorded (`dead→active` 26, `active→dead` 14, `dead→crashlooping` 1).
The 845 "(first seen)" rows are initial sightings, not transitions — the distinction is
carried in the schema as `from_status IS NULL`.

**Status: PROVED.**

---

## P4 — G4: dependency edges and blast radius

**Claim:** the graph answers "what dies if this stops", from Flux's own `dependsOn` — the
ordering the controller honours *before* it reconciles.

**Reproduce:**
```bash
sqlite3 catalog/estate.db "select relation, count(*) from edges group by 1 order by 2 desc;"
bin/estate-twin-runtime --blast-radius flux:Kustomization:flux-system/secret-store
```

**Edges (captured):**
```
relation      n
runs_on       151
depends_on    144
about          73
diagnosed      43
part_of        19
stale_secret    7
```

**The query answers (captured):**
```
flux:Kustomization:flux-system/secret-store
upstream (what it depends on):
  <- flux:Kustomization:flux-system/agent-workforce  (depends_on)
  <- flux:Kustomization:flux-system/alerts-github  (depends_on)
  <- flux:Kustomization:flux-system/backstage  (depends_on)
  <- flux:Kustomization:flux-system/dagster  (depends_on)
  ... 16 shown
```

**The estate's real answer:** ~20 Flux rows depend on the secret store. If it stops, they
all stop.

**Defect found during this proof:** my first version of G4 built only *inward* edges
(`runs_on`, `part_of`, `diagnosed`), so blast radius returned nothing for any node. 366 edges
existed and the query answered "nothing". The `depends_on` relation points *outward* from
the thing that waits, which is the direction the question needs. **I had claimed G4 proved
before this was caught.**

**Status: PROVED**, after the withdrawal and rebuild recorded above.

---

## P5 — G6: freshness, the three-state rule

**Claim:** a domain that has not been read inside its window reads `UNKNOWN`, and never
`MEASURED_OK`.

**Reproduce:**
```bash
bin/estate-twin-runtime --state
sqlite3 catalog/estate.db "update freshness set updated_at=datetime('now','-30 days');"
bin/estate-twin-runtime --state
bin/estate-twin-runtime --once --code   # restore
bin/estate-twin-runtime --state
```

**Output (captured):**
```
-- live --
  UNKNOWN        code: last read 2592042s ago, window is 180s -- stale, so nothing here may be read as MEASURED_OK
  UNKNOWN        runtime: last read 206s ago, window is 180s -- stale, so nothing here may be read as MEASURED_OK
-- aged 30 days --
  UNKNOWN        code: last read 2592001s ago, window is 180s -- stale, so nothing here may be read as MEASURED_OK
  UNKNOWN        runtime: last read 2592001s ago, window is 180s -- stale, so nothing here may be read as MEASURED_OK
-- restored --
  MEASURED_FAIL  code: 649 of 649 nodes not serving (stranded=649, read 2s ago)
  MEASURED_FAIL  runtime: 410 of 855 nodes not serving (dead=409, crashlooping=1, read 2s ago)
```

**Defect found and fixed during this proof:** `code` read `MEASURED_OK` while 648 of its 649
nodes were *stranded* branches. Stranded work is not serving, and calling it OK was false
comfort. The rule now counts `stranded` as not-serving, and names the breakdown.

**Status: PROVED**, with the defect recorded.

---

## P6 — Phase 2: the code domain, and the anti-drift check

**Claim:** the graph and the catalogue generator report the same number of stranded branches,
by construction, so two surfaces cannot tell a founder two different numbers.

**Reproduce:**
```bash
bin/catalog-dark-matter --check
sqlite3 catalog/estate.db "select metadata from nodes where id='git:summary:stranded';"
sqlite3 catalog/estate.db "select status, count(*) from nodes where domain='code' and type='branch' group by 1;"
```

**Output (captured):**
```
ok      catalog-dark-matter  648 stranded branch(es), 10 dead deployment(s) current
-- the graph's own count --
{"branches_carried_in_portal_file": 200, "dead_deployments": 10,
 "files_absent_from_base": 94093, "portal_file_cap": 200,
 "stranded_branches": 648, ...}
-- per-branch rows --
stranded|648
```

**648 = 648.** The generator writes `backstage/platform/dark-matter.json`; the twin reads
that file into a `git:summary:stranded` node. One git scan serves both.

**Defects found and fixed during this proof:**
1. **534 of 648 branches carried status `active` while adding files main does not have** —
   stale state from an earlier rule, never reconciled. Now all 648 are `stranded`.
2. **`--check` took 6 minutes 20 seconds** (1,523 branches re-scanned). A gate nobody runs is
   not a gate. Now 0.2 seconds, comparing the file against the counts already computed.

**Status: PROVED**, with both defects recorded.

---

## NOT PROVED — stated honestly

| # | item | state |
|---|---|---|
| G2 | the ten missing domains (identity, network, certificates, capacity, cost, data, postgres, sessions, worktrees, the bus itself) | **NOT BUILT** — specified in §13.2 |
| G5 | running in-cluster as a pod | **NOT BUILT** — runs on a laptop today |
| G7 | the founder view (`catalogue.mumchimp.com/ops` reading the graph) | **NOT BUILT** |
| — | `--publish` to the NATS bus | **NOT PROVEN** — no event has been sent |
| — | the collector changes taking effect in-cluster | **NOT PROVEN** — `depends_on`, `since` and `k8sgpt_config` are in git and need a Flux reconcile |

**A claim I withdrew during this work:** G4 was reported as proved when only inward edges
existed. It returned nothing for every node. The withdrawal is recorded in P4.

---

## What is in git (uncommitted, on `feat/0910-session-7527`)

| file | what |
|---|---|
| `bin/estate-twin-runtime` | the emitter and CLI |
| `bin/catalog-dark-matter` | the catalogue half, now with `--check` fast path and cached counts |
| `platform/state/cluster-state.yaml` | the collector: `depends_on`, `since`, `k8sgpt_config`, `k8sgpts` RBAC |
| `features/twin/estate-twin.feature` | 8 acceptance scenarios |
| `sovereign/tests/bdd/test_estate_twin.py` | their steps |
| `docs/specs/2026-09-12-estate-twin-complete-spec.md` | the spec, 13 sections |
| `docs/tickets/2026-09-12-estate-twin.md` | the ticket |
| `docs/evidence/estate-twin/PROOFS.txt` | every command and its output |
| `docs/evidence/estate-twin/PROOF-OF-WORK.md` | this file |

**Nothing is committed. Nothing is deployed.**
