# The Media Department — M0 baseline and M1 contract

Governing issue: [idp#7395](https://github.com/chidionyema/idp/issues/7395). Charter: *IDP Autonomous Media
Department — implementation charter v1* (2026-10-28, status **PROPOSED**). This change is the charter's first
PR (§10): **M0 measured baseline + M1 department contract and BDD only**. It adds no runtime, starts no
workload, publishes nothing and spends nothing. Nothing here is deployed, and nothing here is operating.

Authority: `AGENTS.md`, ADR 0037 (the film is a deterministic twin of the event spine), ADR 0038 (one scene
contract), `docs/specs/2026-10-23-estate-as-movie-director-engine.md`, `docs/epics/2026-10-25-estate-master-epic.md`.

## M0 — what exists, measured

| file | what it is |
|---|---|
| `bin/media-dept-baseline` | measures each capability row with recorded commands; refuses to write a matrix that breaks its invariants |
| `m0-capability-matrix.json` | the committed result: `implemented` / `tested` / `ci_wired` / `observed_live` / `broken` / `unknown` per row, with the source sha, every command and its exit code, and the ranked gap list |
| `tests/test_media_department_baseline.py` | grades the committed matrix and proves the check can fail |

`observed_live` is **BLIND** for every cluster-placed row: the OKE API did not answer when this was measured
(2026-10-29). Blind means *not measured*, not *down* and not *up*. Deployment is never inferred from YAML. The
laptop `voice-router` process (which hosts the director, ADR 0040) is recorded as a process listing, which
is not evidence that frames are emitted, so that row is blind too.

Re-measure after any change to the rows' paths, or when the cluster returns:

```bash
bin/media-dept-baseline --run-tests --live
bin/media-dept-baseline --check
```

## M1 — the department contract

| file | what it is |
|---|---|
| `schema/department/v1/envelope.schema.json` | the charter's mandatory envelope (21 fields + `payload`); nullable fields declared |
| `schema/department/v1/{objective,opportunity,experiment,artifact,review,decision,outcome,event}.schema.json` | one schema per record kind: envelope + typed payload |
| `platform/department/contract.py` | `admit()`: the one admission function; `TRANSITIONS`: the legal state machine |
| `platform/department/media.yaml` | the Media Department as configuration: roles, the states and kinds each may write, the authorization doors, the per-day cap |
| `features/media-department/m1_contract.feature` + `tests/test_media_department_contract.py` | the BDD, bound to the real `admit()` |

The contract refuses, with a typed code: `schema_invalid`, `missing_source_ref`, `unauthorized_write`,
`duplicate_idempotency_key`, `illegal_transition`, `missing_authorization`, `self_certification`,
`missing_independent_evidence`, `budget_overflow`, `stale_provenance`. Admission is a pure function of
(record, writer, ledger, config, context): time and source revisions are passed in, so a replay gives the
same verdicts.

`media.yaml` grants **no workers**: every write is refused as `unauthorized_write` until M2 grants
capability-scoped workers in the same change that wires them to the existing Temporal workers. The contract
fails closed.

### Reuse, not new layers (AGENTS.md §6)

- **Approval** is the existing `founder.decision` door (`sovereign/otto/decision.py`); `APPROVED` must cite an
  `allow` from a door listed in `authorization_doors`. The department hosts no approval stack.
- **The ledger** in `contract.py` is an in-memory interface. M2 backs it with the existing JetStream stream;
  it does not get a store of its own.
- **`work_item`** (master epic §12, EPIC-060) is not on main yet. `contract.WORK_ITEM_STATE` maps every
  department state onto its states, so when it lands the department joins it by `run_id` and does not become
  a second action record.
- **Second departments** (Research, Science; charter M7) are a second config file over the same schemas and
  the same `admit()`.

### Compatibility and migration policy

1. `schema_version` is `department.v1`, a constant. Within v1 only **additive** changes are allowed: a new
   optional payload property, or a new enum value that existing readers ignore safely. A new required field, a
   removed field, a renamed state or a tightened pattern is a **breaking** change.
2. A breaking change is `department.v2` in `schema/department/v2/`, landed together with a migration function
   `v1 -> v2` in `platform/department/` and a test that migrates every v1 fixture. v1 records stay readable
   (the ledger is immutable); they are never rewritten in place.
3. A change to `TRANSITIONS` that **removes** an edge is breaking. A change that adds one needs a scenario in
   the feature showing the new edge and the refusals around it.
4. The envelope is shared by every department: a field one department needs goes in its `payload`, not in the
   envelope.

## Out of scope here (M2–M7)

The durable runtime, the scene renderer, the research/prototype loop, independent grading and the department
page in Fleet/Face are later work packages, each with its own claim.
