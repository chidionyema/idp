# The estate discovery door - what exists, what is true about it, and where the oracle sits

Status: SUPERSEDED (2026-10-26) by docs/specs/2026-10-25-estate-capability-registry.md and
bin/capability-index. This document is kept as the record of what was measured on 2026-10-26.

WHY IT IS SUPERSEDED. The door this document describes (`bin/estate-discover`) was a VIEW:
it read the estate's maps and answered on demand, but it stored nothing, held no invariant,
had no agent-facing surface, and its gate could only compare counts against a baseline. The
programme's registry raises the bar - one store, one writer per plane, five falsifiable
invariants, one query contract over CLI and MCP, and a committed machine-generated snapshot
CI can prove drift-free - so the lesser door was merged into it (its census became the
registry's writers, its coverage baseline became the drift check) and deleted in the same
change (AGENTS.md section 6, raise-the-bar clause).

WHAT SURVIVED, AND WHERE. Every capability this door could name is now a record in the
registry: `bin/capability-index query`, `... get <id>`, `... status`, `... cover`. The
measurements in this document (433 scripts, 344 intents, 150 services, 51 gates, 47 launchd
jobs) are the numbers the registry's census now starts from; they have moved since, and the
registry counts them live.

Claim: #7168. Date: 2026-10-26.

## 1. The question, in the founder's words

> How do we discover what services exist — their features, their capabilities, their
> dependencies, their operational status, their metrics — everything knowable about services,
> scripts etc? And where does the "mega oracle" sit, the thing you can ask anything?

Two parts: a **question** (how do we find out what the estate has and what is true about it),
and a **plan** (the mega oracle — a planned component, not a running thing).

## 2. The answer, in plain English

There were three answers before this, and each one was partly true:

1. **The catalogue** (`docs/marketing/capabilities.yaml`, 195 entities) — what the estate
   *offers*. It says nothing about dependencies, metrics, or whether a thing is up.
2. **The crew datamap registry** (`science/sources.json`, 44 sources) — where knowledge
   *comes from*. It does not describe the machinery.
3. **The plan** (`docs/specs/2026-10-25-estate-capability-registry.md`, epic 25 Phase A) — a
   spec for a real registry, shipped as a document on 2026-10-25 (PR #7161, squash
   `faec7d4e1`). No code answered the question.

What was missing was a **door**: one command that names everything the estate has and
reports, per thing, what is actually known — and says BLIND where nothing is known.

That door is `bin/estate-discover`, and `bin/estate-discover-gate` is the check that keeps
it honest.

## 3. What the door sees (measured 2026-10-26, this machine)

| kind | records | where the fact comes from |
|------|---------|----------------------------|
| script | 433 | `idp/bin/` — one per executable script |
| intent | 344 | `~/.estate/intents/*.yaml` (+ 2 declared in repo but not installed) |
| service | 150 | `idp/platform/`, `idp/clusters/` — Deployment, StatefulSet, DaemonSet, CronJob, Service, Job |
| gate | 51 | `idp/bin/` — the checks that refuse |
| launchd | 47 | `~/.estate/state/inventory.json` — what the mac plane actually runs |
| harness | 5 | `~/.estate/harness/` + the executor ledger |
| **total** | **1030** | |

Status, from real instruments only:

- intents: **238 healthy, 70 failed, 36 unknown** — from `~/.estate/estate.db`
  (`intent_tickets`), the executor's own ledger. This is the one place where the estate has a
  genuine receipt trail.
- launchd jobs: **43 ORPHAN, 4 MANAGED** — from the launchd inventory
  (`generated_at 2026-09-26T16:47:38Z`).
- scripts (433), services (150), gates (51): **no status instrument exists** — they are
  BLIND, and the door says so rather than guessing.

The honest headline: **671 of 1030 records (65%) have no status instrument.** That number is
the answer to "how well do we know our own estate", and before this door nobody could even
state it.

## 4. What the door answers, per thing

Each record carries: `id`, `kind`, `summary`, `features`, `contract{inputs,outputs,errors}`,
`owner` (from CODEOWNERS), `plane`, `depends_on[]`, `consumers[]`,
`health{state,source,observed_at,blind}`, `metrics[]`, `proof{receipt,window_s,rung}`,
`blind[]`, `cost_class`, `latency_class`.

The record shape is the one the registry spec asks for, plus the two fields the spec was
measured to be missing: **`depends_on`** and **`metrics`**.

Dependencies are edges with evidence, not prose:

- script → script: a script names another script (`exec beta-tool.sh`).
- intent → script: the intent's own YAML names a script.
- service → image / config / secret / serviceaccount / service: read out of the manifest.
- consumer edges are the reverse of every dependency edge.

## 5. Where the mega oracle sits

The mega oracle is **planned, not running** — epic R-50 / W-46, "EPIC-061 Brain API v0".
Its spine is the Phase A registry (`docs/specs/2026-10-25-estate-capability-registry.md`).

This door does **not** become the oracle and does not compete with it. It is the *view* over
the estate's existing maps, and the registry is the *store* that will eventually hold those
records. The seam is the `SOURCES` table at the top of `bin/estate-discover`: every fact
comes from a named source, so when the registry lands, the sources become the registry and
the view reads it. One of each layer: no second store, no eleventh copy.

The oracle's own door will need what this door already measures: which things exist, what
depends on what, what is up, what it costs, and what is provable. This is that substrate,
delivered early and honestly.

## 6. Why a view and not a registry

- The estate already keeps the maps: `idp/bin/`, `~/.estate/intents/`, `platform/`,
  `clusters/`, `estate.db`, `inventory.json`. A new store would be a fourth copy of truth
  that has to be kept in step with the others.
- A view cannot go stale silently — it reads what is there at the moment you ask.
- The registry needs an owner, a schema, a migration and a steady hand. That is Phase A work
  (#7158), not this branch.

## 7. The gate (a gate that can fail)

`bin/estate-discover-gate` refuses when:

1. a source became unreadable (the census cannot see part of the estate);
2. a kind of record shrank below `catalog/estate-discover-baseline.json` — something stopped
   being enumerated, a silent loss of discoverability;
3. with `--strict`, any record has no status instrument.

Measured on the real estate today:

```
$ ./bin/estate-discover-gate
records: 1030 (gate=51, harness=5, intent=344, launchd=47, script=433, service=150)
BLIND records (no status instrument): 671  [contract.errors=433, contract.outputs=433, health=671, metrics=671]
ok      estate-discover-gate  the estate is at least as knowable as its baseline

$ ./bin/estate-discover-gate --strict
FAIL    estate-discover-gate  671 records have no status instrument (BLIND): contract.errors=433, contract.outputs=433, health=671, metrics=671
$ echo $?
1
```

The strict gate fails **today**, on purpose: it is the founder's question asked as a verdict.
Closing that gap is the registry's job (Phase A) and the executor's job (per-script receipts).

## 8. Usage

```
bin/estate-discover list --kind service
bin/estate-discover list --kind intent --state failed
bin/estate-discover show script:bin/epistemic_firewall.py
bin/estate-discover deps intent:lane-submit
bin/estate-discover status
bin/estate-discover metrics --kind intent
bin/estate-discover cover
bin/estate-discover baseline --write
```

`bin/estate-discover-gate [--strict] [--json]` — the check.

## 9. What is still missing (the BLIND list)

- **Script and gate status** (484 records): no runtime instrument. The executor ledger knows
  which *intents* ran; it does not know which *scripts* ran. Fix: the executor records script
  invocations the way it records intents.
- **Service status** (150 records): manifests say what should run, not what is running. Fix:
  the cluster has the truth; a read-only probe (or the existing `k8s.debug` intent) can supply
  it.
- **Metrics** for everything except intents: only the executor's ledger has numbers today.
- **Contract outputs and errors** for 433 scripts: a script's docstring does not state its
  exit codes. Fix: a declared contract, or an honest "unknown".

## 10. How this was proven

- `tests/test_estate_discover.py` — 14 tests, all passing. Most are **falsifiers**: the
  estate is broken on purpose (a source removed, a baseline set above reality, a record left
  blind) and the gate must refuse.
- The gate was run against the real estate, not a fixture: it passes in normal mode and
  **exits 1** in `--strict` mode.
- `ruff check --select E9,F,B,S --ignore S603,S607` and `ruff format --check` are clean on
  all three files.
