# Spec — the door onto the typed multi-domain mutation ledger

**STATUS: BUILT, GREEN, AND DOORED, 2026-09-15.** All four verbs below exist in
`platform/executor/daemon.py` and `mcp/plugins/estate_executor.py`, the acceptance
suite named at the bottom of this file passes (`7 passed`), and the Backstage "Pending
mutations" card is built and proven (Evidence item 5 below). One deviation from the
contract as originally written, made necessary by the pipeline rather than by choice: see
"Deviation: the `tests` field" under `propose_mutation` below. `admit_mutation` always
returns `pr_required: True` and never merges — this is not a gap ADR 0025 leaves open, it
is that spec's actual, permanent boundary for a change class with no boundable blast
radius (see "What is NOT in scope" and Evidence item 4 below). Read
`docs/tickets/2026-09-15-typed-multidomain-mutation-ledger.md` for the evidence and the
current status in full.

## Why it was written

Two mutation pipelines exist and neither spans more than one domain (see the ticket for the
full gap analysis). The founder asked for a "typed multi-domain mutation ledger
(code+manifest+SQL in one atomic proposal)" extending `estate_executor.py`/
`estate_simulate.py`. This spec is the exact contract a build must satisfy, in the same
shape as `docs/specs/2026-09-13-deterministic-verifier-door.md` — that door's four verbs
are the pattern this one extends, not replaces.

## The non-negotiable boundary (read this before anything else)

Every verb below is **non-blocking** and **never writes live state**:

- No verb waits for a verdict. `propose_mutation` returns a `ledger_id` in the same call;
  the verdict is read later, non-blocking, through `read_job` (`estate_executor.py:353`) —
  the existing mailbox. A verb named anything like `wait_for_verdict` or `run_tests` must
  not be added to this module. If a reviewer finds one, the build fails review regardless
  of what else passes.
- No verb executes SQL against a live database, applies a manifest to a live cluster, or
  pushes a commit directly to `main`. Every successful `admit_mutation` produces a Git
  commit on a proposal branch for the founder's own merge path (ADR 0025 Phase 3) — the
  same shape `execute_change` already lands on `estate/state`. `admit_mutation` returning
  `ok: True` means "ready for the founder's merge," never "live."

## The four verbs

All four are new functions in `mcp/plugins/estate_executor.py`, calling through the same
`_verifier_call`/Unix-socket pattern the existing four verbs use (`_verifier_socket()`,
`estate_executor.py:576-627`) — no second transport, no second daemon (LAW 43, same
citation the deterministic-verifier door used).

### 1. `propose_mutation(code_patch, manifest_patch, sql_migration, claim)`

Request over the socket: `{"verb": "propose_mutation", "code_patch": <diff str|"">,
"manifest_patch": <diff str|"">, "sql_migration": <str|"">, "claim": <str>}`. At least one
of the three payload fields must be non-empty; a call with all three empty is refused
before a ledger is opened (`ok: False`, `error: "nothing to propose"`).

Reply must carry:
- `ok: True`
- `ledger_id`: a non-empty string, unique per proposal
- `ledger_dir`: a directory, sterile (no `.git`), outside the live worktree — same
  constraint `propose_patch` already proves (`test_deterministic_verifier.py`'s ledger
  sterility assertion extends to this ledger without change)
- `domains`: the subset of `["code", "manifest", "sql"]` actually supplied
- `suspended: True`

Constraints:
- One ledger, one directory, all supplied domains' files written into it — never three
  separate ledgers correlated after the fact. Correlating after the fact is exactly the
  "three unrelated windows" gap this ticket exists to close.
- `{"verb": "health"}` reports `ledgers_pending >= 1`, identical accounting to the existing
  four verbs — no second counter.

**Deviation: the `tests` field.** The actual request also accepts an optional `tests`
field: `{"verb": "propose_mutation", ..., "tests": <str|"">}`. This was not in the request
shape as originally specified above, and is a gap in this spec's first draft, not a design
choice made freely: `verify_mutation` reuses the existing `sovereign.verifier.verify()`
gauntlet unchanged (LAW 43 — no second gauntlet), and that gauntlet's execution stage
(`stage_execution`) needs `Ledger.tests` populated to run anything. Without this field,
`verify_mutation` could grade structural/SQL/symbolic but never execution, which is not
the three-stage-plus-SQL gauntlet this door promises. `claim` remains optional exactly as
specified.

### 2. `verify_mutation(ledger_id)`

Request: `{"verb": "verify_mutation", "ledger_id": <str>}`

Runs, for every domain present in the ledger:
- `code`/`manifest`: the existing three verifier stages (structural, symbolic, execution)
  per file, unchanged from `stage_structural`/`stage_symbolic`/`stage_execution` in
  `sovereign/verifier.py`.
- `sql`: a new stage — parse the migration with a SQL parser (no live connection; a
  migration that requires a live schema to validate is out of scope for this verb and is
  refused with `error: "sql stage cannot validate against live schema; supply a
  self-contained migration"`).

Reply on success: `ok: True`, `subject_digest` (sha256 over every file across every
domain, sorted by path — not per-domain digests glued together), `attestation`,
`admissible: True`, `per_domain: {code: "VERIFIED"|absent, manifest: ..., sql: ...}`,
`claim_verdict`.

Reply on failure: `ok: False`, `per_domain` names exactly which domain(s) failed and each
failing domain's own real stage message (never a paraphrase — same rule the deterministic
verifier door already proves), `attestation: None`, ledger destroyed.

Constraint: **all-or-nothing**. If any domain fails, `ok` is `False` for the whole
mutation — there is no reply shape where `code` passed and the caller can admit `code`
alone. This is the one new invariant this door adds beyond what the four existing verbs
already prove.

### 3. `seal_mutation(ledger_id, tests, claim)`

Request: `{"verb": "seal_mutation", "ledger_id": <str>, "tests": <str>, "claim": <str>}`

Reply: `ok: True`, `attestation` whose subject is the bundle digest from `verify_mutation`
— never a single file's digest. Refuses (`ok: False`) if `verify_mutation` was not called
first or did not return `admissible: True` for this `ledger_id`.

### 4. `admit_mutation(ledger_id, attestation)`

Request: `{"verb": "admit_mutation", "ledger_id": <str>, "attestation": <dict>}`

Unattested or tampered: `ok: False`, `intercepted: True`, `violation_code: "UNATTESTED"` —
identical code path to `admit_payload`'s existing enforcement point
(`platform/executor/daemon.py`), not a second one. `rules.yaml`'s
`test_rule_4_has_two_enforcement_points`-style count must still find exactly the files it
expects; this verb adds no third file carrying that literal.

Attested and valid: `ok: True`, `branch`: the name of a new Git branch (never `main`,
never the founder's own state branch directly) carrying one commit with all supplied
domains' files, `commit_sha`, `pr_required: True`. **This verb never merges.** Merge is
the founder's own path (ADR 0025 — "he is the only merger on every Glass-Break change"),
until and unless a Trust Threshold row admits this class of change, at which point
`pr_required` becomes the scope-check gate's job to flip, not this verb's.

## Speculative-execution / async-claims framing (for the builder, not graded here)

Per the async-claims design discussed with the founder this session: the caller should
treat `propose_mutation` → `verify_mutation` as fire-and-forget, polling `read_job` rather
than blocking. This spec does not mandate a specific polling cadence or a mailbox schema
change — `read_job`'s existing shape (`estate_executor.py:353-372`) already answers
"pass/fail/pending" for any `ledger_id`, so no new mailbox is needed. A future ticket may
add contract-graph-driven speculation (running a second, dependent proposal before the
first's verdict returns) — explicitly out of scope here; this door proves the atomic
tri-domain bundle first.

## What is NOT in scope

- Live SQL execution or schema introspection against a running database, from this door,
  ever.
- A second Backstage/UI door beyond the "Pending mutations" card named in the ticket. That
  card (built, 2026-09-15 — see the ticket's "The door" and Evidence item 5 below) is UI
  wiring over these four verbs, not a fifth verb this spec defines.
- Raising or lowering anything in ADR 0025's Trust Threshold table. That is a separate
  pull request per ADR 0025's own build order, and this door's `pr_required: True` is the
  explicit acknowledgment that this spec does not attempt it.
- Rewriting `propose_patch`/`simulate_change`. They stay as the single-domain fast path.

## Acceptance test (once built — the ONLY definition of done)

```
cd sovereign && python3 -m pytest tests/bdd/test_typed_multidomain_mutation_ledger.py -q -p no:cacheprovider
```

must exit 0, driving `features/gates/typed-multidomain-mutation-ledger.feature` scenario
by scenario, against the live daemon over `~/.estate/executor.sock` — not a mocked
handler, same standard the deterministic-verifier door proved to.

## Evidence (delivered, 2026-09-15)

1. Pytest tail: `cd sovereign && python3 -m pytest tests/bdd/test_typed_multidomain_mutation_ledger.py
   -q -p no:cacheprovider` → `7 passed in 16.05s`. The single-domain door's own suite
   (`test_deterministic_verifier.py`) still passes unchanged: `9 passed`.
2. Each of the four verbs exercised from the command line against a running daemon:
   `propose_mutation` → `ledger_id`, `domains: ["code","manifest","sql"]`, `suspended: true`;
   `verify_mutation` → `ok: true`, `per_domain` all `"VERIFIED"`, real Sigstore-bundle
   attestation; `seal_mutation` → attestation over the bundle digest; `admit_mutation` →
   `branch: "mutation/<ledger_id>"`, real `commit_sha`, `pr_required: true`. A second run
   with a deliberately-broken SQL domain (good code, good manifest) proved the all-or-nothing
   failure: `verify_mutation` returned `ok: false`, `per_domain.sql` carrying the raw sqlite
   error (`near "VALID": syntax error`), and `per_domain.code`/`per_domain.manifest` both
   `"not verified: the bundle failed on a different domain (all-or-nothing)"` — never a false
   `VERIFIED`.
3. `git status --porcelain` on the live checkout: clean of unintended files both after the
   manual smoke test and after the BDD suite (the suite's own `created_branches` fixture
   deletes every `mutation/ldg-*` branch it creates, in its own teardown).
4. `pr_required: True` is this door's permanent terminal state, not a placeholder for a
   Trust Threshold PR. An arbitrary code+manifest+SQL bundle has no boundable blast radius
   to write a scope-check against (ADR 0025's Trust Threshold table is closed, and its two
   open rows — resource-limit-increase-only, rollback-to-known-tag — are both narrower than
   anything this door produces), so there is no honest PR this spec can write to flip that
   flag, now or later. This door merges to `main` the same way every other human-reviewed
   change here does: a person opens the PR `admit_mutation` already prepared and merges it
   themselves.
5. The Backstage "Pending mutations" card (`docs/tickets/2026-09-15-typed-multidomain-mutation-ledger.md`,
   "The door"): built at `/ops`, backed by `GET/POST /fleetview/mutations*`
   (`backstage/plugins/fleetview-backend/src/mutations.py`), proven live against a real
   daemon — propose, verify, approve (real branch/commit, `pr_required: true`, branch
   cleaned up after the smoke test) and reject, all exercised end to end. `yarn workspace
   app lint` and a monorepo-wide `yarn tsc --noEmit` both exit clean on the new code.
