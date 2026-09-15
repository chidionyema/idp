# The typed multi-domain mutation ledger — one atomic proposal, three domains

**Status:** built, smoke-tested, and doored, 2026-09-15. All four verbs (`propose_mutation`,
`verify_mutation`, `seal_mutation`, `admit_mutation`) exist in
`platform/executor/daemon.py` and `mcp/plugins/estate_executor.py`, and
`sovereign/tests/bdd/test_typed_multidomain_mutation_ledger.py` runs green against a real
daemon (`cd sovereign && python3 -m pytest tests/bdd/test_typed_multidomain_mutation_ledger.py
-q -p no:cacheprovider` → `7 passed`). The Backstage door named below is built too. What did
NOT change and never will, by design: `admit_mutation` still always returns `pr_required:
True` and never merges — this is not a gap, see "Why this does not auto-merge" below.
**Opened:** 2026-09-15
**Door (from the UI):** `/ops`, "Pending mutations" tiles — one per open ledger, showing the
ledger id, the domains touched, each domain's verdict, and an "Approve and merge" / "Reject"
button. See "The door" below for what built and how it was proven.
**Law:** ADR 0006 (propose/execute, one state hash), ADR 0025 (agents hold no write on
production; the Trust Threshold is a closed table), THE EMPIRICAL PROOF RULE
**Spec:** `docs/specs/2026-09-15-typed-multidomain-mutation-ledger-door.md`
**Feature:** `features/gates/typed-multidomain-mutation-ledger.feature`
**Extends:** `mcp/plugins/estate_executor.py` (`propose_patch`/`verify_patch`/`seal_payload`/
`admit_payload`, lines 630-736), `mcp/plugins/estate_simulate.py` (`simulate_change`/
`execute_change`, lines 153-309)

## Founder's words, verbatim, this session (2026-09-15)

> "The typed multi-domain mutation ledger (code+manifest+SQL in one atomic proposal) — this
> extends estate_executor.py/estate_simulate.py, the live production mutation-safety
> gauntlet wi[th...]" — message truncated in transit; the rest of this line has not been
> supplied yet and is not guessed at here.

> "this is nission critical and p0" / "i want agennts producing value" — same session,
> pushing for speed. Weighed against "two remain, deliberately not rushed" from the same
> message that opened this ticket. This document resolves that tension by shipping the spec
> and BDD tonight and treating "built" as a separate, later, founder-approved step (see
> "Why this cannot just be built tonight" below).

## The gap, precisely

Two mutation pipelines exist today and neither spans more than one domain:

| pipeline | domain | atomic unit | lands as |
|---|---|---|---|
| `propose_patch → verify_patch → seal_payload → admit_payload` (`estate_executor.py:630-736`) | code (unified diff) | one ledger, one Sigstore attestation | an admitted file on disk — a human/CI step still turns that into a commit |
| `simulate_change → execute_change` (`estate_simulate.py:153-309`) | cluster manifest state | one proposal, one `cluster_state_hash` | a commit on the `estate/state` Flux branch (`cfg["state_branch"]`) |

Neither touches SQL. A change that legitimately needs all three — e.g. a schema migration
(`platform/estate-db/`) plus the code that reads the new column plus the manifest bump that
deploys it — today has to be proposed as three unrelated calls, three unrelated verdicts,
and three unrelated windows in which one can land without the other two. That is the
"live production mutation-safety gauntlet" gap: nothing enforces that code, manifest and
SQL for one logical change rise or fall together.

## The fix, in one sentence

One `ledger_id` spans all three domains; one Sigstore attestation covers the combined
digest of every file across all three; `admit` is all-or-nothing across the bundle — there
is no partial admit.

## What this is NOT

- **Not** a new path to production. `admit_payload` today produces an admitted file on
  disk, not a live write; `execute_change` lands on a Git branch, never on the cluster
  directly (ADR 0025, Phase 3: "the agent pushes to Git and never to Kubernetes"). The
  multi-domain ledger inherits that boundary unchanged for all three domains, SQL
  included — a migration file lands in Git for the founder's own merge path, it is never
  executed by the agent against the live database. `execute_sql` in `capabilities.toml`'s
  `destructive` tier (`db_drop` sits there already) is the reason this is not optional.
- **Not** a blocking call. Per the async-claims framing (this session): the agent calls
  `propose_patch`-equivalent once, gets a `ledger_id` back immediately, and reads its
  verdict later via the existing non-blocking `read_job`/mailbox pattern
  (`estate_executor.py:353,431`) — never a `wait_for_verdict()` verb. That verb must not
  exist, the same way `run_tests()` must not exist on the agent's toolset (this session's
  design essay, "remove the verb").

## Why this does not auto-merge — and is not supposed to

This is not an open gap. `admit_mutation` was never specced to merge (see the spec's own
"non-negotiable boundary": "`admit_mutation` returning `ok: True` means 'ready for the
founder's merge,' never 'live.'"). ADR 0025's Trust Threshold is a **closed list** —
"Refused — Glass-Break, and this list is closed" — and its two admitted-but-not-yet-built
rows are both narrow, single-dimension, algorithmically provable-scope changes: a resource
**limit** that only ever increases, and a rollback to a tag the file already carried on
`main`. An arbitrary code+manifest+SQL bundle cannot be squeezed into either shape, and it
is not this ticket's job to invent a third row or a scope-check binary that "proves" an
open-ended bundle safe — ADR 0025 is explicit that a change class with no boundable blast
radius "waits for him until someone can name a subset that is provable." Faking that proof
to make this ticket read as more finished would be the actual violation.

So: `admit_mutation` produces a branch, a real commit and `pr_required: True`, and stops
there, forever, by design — identical to how every other human-reviewed change already
lands in this repository. That is not a placeholder for a future auto-merge step; it is the
finished behavior. The Trust Threshold PR is a separate, independent piece of future work
(raising or lowering a Trust Threshold row is explicitly out of scope for this door, per
"What is NOT in scope" in the spec) — it does not block this ticket, and this ticket does
not owe it.

## The door

Built, 2026-09-15: `/ops` now carries one "Pending mutations" tile per open ledger
(`backstage/packages/app/src/modules/home/Ops.tsx`'s `MutationTile`/`MutationsTiles`, data
from `mutations.ts`/`useMutations.ts`), each showing the ledger id, the claim, every domain
touched and that domain's verdict, and two buttons: "Approve and merge" (disabled until
`verify_mutation` actually passed — there is no way to press it on an unverified bundle) and
"Reject". Both call a new backend route
(`backstage/plugins/fleetview-backend/src/mutations.py`, mounted in `routes.py`/`serve.py`
alongside the plugin's existing notes/nudge/blast-radius/check-receipts routes, proxied at
`/api/proxy/fleetview/mutations`): `GET /mutations` lists every still-open ledger by reading
`ledger_root()/proposals/*.json` and `staged/*.patch` directly (no second gauntlet, no
guessed verdicts — a domain reads "VERIFIED" only because `staged/<id>.patch` existing is
the same fact `seal_mutation`/`admit_mutation` already trust before acting); `POST
/mutations/approve` seals and admits the ledger the button names; `POST /mutations/reject`
withdraws it, no git object touched. Pressing "Approve and merge" is the founder's own click
in the founder's own browser — this route still never runs from an agent's task loop, and
`admit_mutation` underneath it still only ever produces a branch and a commit, never a
merge. Proven live against a real daemon: propose → verify → the tile listing the ledger as
`verified` with all three domains `VERIFIED` → approve → a real branch/commit, ledger gone
from the listing; and a second ledger proposed and rejected, gone from the listing with no
branch ever created.

## Evidence

Built and proven, 2026-09-15:

1. `cd sovereign && python3 -m pytest tests/bdd/test_typed_multidomain_mutation_ledger.py -q
   -p no:cacheprovider` → `7 passed` — every scenario in
   `features/gates/typed-multidomain-mutation-ledger.feature`, against a real daemon over a
   real UNIX socket, no mocks.
2. `cd sovereign && python3 -m pytest tests/bdd/test_deterministic_verifier.py -q
   -p no:cacheprovider` → `9 passed` — the single-domain door this build extends is
   unregressed.
3. A live `propose_mutation` → `verify_mutation` → `seal_mutation` → `admit_mutation` call
   against a real three-domain bundle (real code + real manifest + real SQL migration)
   produced a real Sigstore-bundle attestation and a real Git commit on branch
   `mutation/<ledger_id>`, verified with `git show --stat` and confirmed to leave
   `git status --porcelain` on the live checkout unchanged.
4. A second live call with a deliberately-broken SQL domain (good code, good manifest)
   confirmed the all-or-nothing failure: `verify_mutation` returned `ok: False`,
   `per_domain.sql` carrying the raw sqlite error (`near "VALID": syntax error`, never a
   paraphrase), and `per_domain.code`/`per_domain.manifest` both marked "not verified: the
   bundle failed on a different domain (all-or-nothing)" rather than falsely `VERIFIED`.

5. The Backstage "Pending mutations" card: `GET /fleetview/mutations`, `POST
   /fleetview/mutations/approve`, `POST /fleetview/mutations/reject`
   (`backstage/plugins/fleetview-backend/src/mutations.py`) proven live against a real
   `daemon.py` — propose → the tile lists it `pending_verification` → verify → the tile lists
   it `verified` with all three domains `VERIFIED` → approve → a real branch/commit
   (`mutation/ldg-0365827e0818`, `ec30cb5d`), ledger gone from the listing, branch deleted
   afterward to leave the checkout clean; a second ledger proposed and rejected, gone from
   the listing with no branch ever created. `yarn workspace app lint` and `yarn tsc --noEmit`
   across the whole monorepo both exit clean on the new frontend code.

Not open, and not owed by this ticket:

6. The Trust Threshold PR (ADR 0025 build order item 4). Explained in full under "Why this
   does not auto-merge" above: an arbitrary code+manifest+SQL bundle has no boundable blast
   radius to write a scope-check against, so there is no PR this ticket can honestly write
   for it. `pr_required: True` is this door's permanent, correct terminal state, not a flag
   waiting to flip — the same way every other human-reviewed change in this repository stops
   at a PR rather than merging itself.
