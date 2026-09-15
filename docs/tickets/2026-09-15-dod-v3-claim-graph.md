# DoD v3 as a graph contract, not a document — scoped against what already exists

**Status:** scoped, not built. This ticket records a decision and names one buildable next
step; per DoD v3 itself, nothing here may be called `DONE:` until an independent check runs
against it.
**Opened:** 2026-09-15
**Door (from the UI):** none yet, by design — see "The one next step" below for the first
concrete door (`mcp__estate__execute_sql` against `catalog/estate.db`, already an approved
query surface under ADR 0006) and what a later Backstage/FleetView door would need.
**Law:** ADR 0006 (the platform answers for itself over one MCP server — never a second
store/bus/server), ADR 0025 (agents hold no write on production; Flux is sole actuator),
THE HEADLINE ("never script what a proven platform already solves"), the 2026-09-09 door
rule, the 2026-09-15 DoD v3 standing rule this ticket extends.
**Extends:** `catalog/estate.db` (schema only — no second store), `~/.claude/scripts/dod-guard.py`,
`rules.yaml`'s `dod-v3-verified-not-asserted` row (`bin/dod-live-claim-gate`, landed today,
commit `7c774c97` on `chore/dod-v3-enforcement`, not yet merged).

## Founder's words, verbatim, this session (2026-09-15)

A detailed architecture was proposed for making DoD v3 machine-enforced rather than a CLAUDE.md
rule an agent can argue with: a signed claim graph in Postgres, five independent verifier
services (sellable / installable / continuous / procurement / owner), a policy store in
OPA, promotion gates that read the graph instead of trusting an agent's word, hourly
re-attestation with auto-revocation, and an 8-week rollout citing SLSA, Sigstore, in-toto,
and NIST zero-trust identity as the frontier this pattern comes from. Closing instruction:
**"add teickt so we track."**

The instinct behind the proposal is correct and matches a pattern this estate has hit
repeatedly today: a rule that only lives in a document is something an agent can talk its way
around; a rule the environment enforces is not. That is DoD v3's own first clause. The
mechanism proposed to get there, though, is a fresh green-field build — Postgres, five new
services, a new signing layer — and THE HEADLINE says not to build what the estate already has.
Most of it, it already has.

## What the proposal asks for, mapped onto what exists today

| Proposed component | Estate equivalent, today | Gap |
|---|---|---|
| Policy Store (Git + OPA, versioned, signed) | `rules.yaml` — one file, git-versioned, graded by `bin/idp-rules` on three planes (session/ci/cluster-admission), `docs/policy/rules-table.md` generated from it | Not cryptographically signed. Minor; git history + branch ownership (`pi-session` claim) already answers "who changed the rule." |
| Claim Graph (Postgres + signatures) | `catalog/estate.db` — already has `nodes`, `edges`, `node_events` (an event/attestation log), `meta`, `freshness`, `drills_never_run`, `linear_dispatch_queue` tables, reachable only via the estate MCP server (ADR 0006) | No `claims`/`verifications` tables yet. This is a schema extension, not a new store — building Postgres here would be exactly the "second store" ADR 0006 forbids. |
| Verifier Fleet (5 independent identity services) | `qa-agent` ("ticks the box only on a real green run, builds nothing, fixes nothing"), `login-drill.yml` (runs hourly, screenshot evidence in the collector), `bin/dod-live-claim-gate` (landed today) | No verifier yet for checks (a) sellable, (b) installable-fast-benchmarked, (d) procurement-passable, (e) owned — those have no graded schema anywhere in this repo. Real gap, not a reinvention. |
| Promotion Gate (reads graph, blocks commit→merge→GA) | `bin/idp-ci` + `rules.yaml`'s three planes already block on session/CI; cluster admission (Kyverno) exists but is in audit-only posture, zero enforced policies recorded in three weeks (per the 2026-09-15 inventory audit) | The gate exists; it does not yet read a `claims` table, because that table doesn't exist yet. |
| Continuous Attestation (hourly, auto-revoke) | The drill already runs hourly. Nothing currently revokes a `DONE:` claim when the drill goes red — the drill and the DoD claim are two separate systems today. | Real gap: wiring the drill's result to flip a claim's status. |
| Cryptographic agent identity (Sigstore/OIDC keypairs) | SPIFFE/SPIRE workload identity exists for cluster workloads (security one-pager, decision on identity); git `pi-session` branch claims exist for session ownership | No per-agent signing of claims. Genuinely new if pursued — but the identity substrate to build it *on* (SPIFFE/SPIRE) already exists; this would extend it, not import Sigstore fresh. |

**Verdict: roughly two-thirds of the proposed architecture already exists under different
names.** The genuinely new work is: a `claims`/`verifications` schema in the existing estate
graph, the four missing verifiers (a, b, d, e), and wiring the drill's result to a claim's
status. That is a schema migration and four small services, not an 8-week Postgres+OPA+Sigstore
build. The 8-week rollout in the original proposal is not authorized by this ticket — it is a
resourcing decision for the founder, not something to start on scope inferred from an AI-written
plan pasted into chat.

## The one next step (buildable today, no new infra)

1. Add two tables to `catalog/estate.db` via the schema the estate MCP server owns (never a
   second store): `claims(id, product, claim_text, producer_identity, created_at)` and
   `verifications(claim_id, verifier_identity, result, evidence, checked_at)`.
2. `bin/dod-live-claim-gate` (landed today) writes to `claims`/`verifications` instead of only
   printing pass/fail — it already *is* a non-builder verifier for check (c); this makes its
   result durable and queryable instead of a point-in-time CI log line.
3. `dod-guard.py` stops being the only place a `DONE:` claim is checked — it writes the claim,
   the independent gate verifies it, and the reply-time block becomes a read of that result, not
   a re-derivation of it. This is the "mailbox, not synchronous block" property the proposal
   asked for, built on the hook that already exists instead of a new one.
4. Door once this lands: `mcp__estate__execute_sql` against `catalog/estate.db` answers "what
   is claimed done, and did an independent check confirm it" today, for any founder or agent,
   through the one approved query surface (ADR 0006). A Backstage/FleetView panel over the same
   query is the later door, blocked on FleetView actually having a reachable backend (open, see
   `docs/tickets/2026-09-15-typed-multidomain-mutation-ledger.md`'s dependency on
   `backstage/plugins/fleetview-backend/`, still not cluster-deployed as of tonight).

## Not done, named honestly

- The four missing verifiers (sellable, installable-fast, procurement-passable, owned) have no
  schema anywhere in this repo. Inventing their evidence format is real design work, not a
  10-minute extension, and is not attempted in this ticket.
- No signing layer. Claims in the schema above are as trustworthy as `pi-session` branch claims
  are today — real, but not cryptographic. Whether that gap needs closing is a founder call
  against actual incident history, not a default "add Sigstore" because a proposal named it.
- The 8-week rollout, Postgres, OPA, and a 5-service fleet are explicitly not started here.
