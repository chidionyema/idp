# A live, model-agnostic laptop-to-cluster session-sync capability

**Status:** scoped, not built. Per DoD v3, nothing here may be called `DONE:` until an
independent check runs against it.
**Opened:** 2026-09-15
**Door (from the UI):** none yet — the door this unblocks is FleetView's `/fleets` panel
showing live `sessions`/`stream` data for every coding-agent vendor in use (Claude Code,
`.pi`, Gemini, any future one), not just the two that already work.
**Law:** ADR 0006 (one estate graph, no second store), THE HEADLINE (build once, model
agnostic — "never script what a proven platform already solves," and never bake one vendor's
local file format into a product meant to serve any of them), LAW 46 (no ledger path-leak),
the 2026-09-15 DoD v3 standing rule (no self-declared done, no stub presented as done).
**Extends:** `catalog/estate.db` (schema only), `mcp/plugins/estate_sessions.py` (already
model-agnostic — confirmed, not touched by this ticket), `bin/catalog-gen`'s `fold_families`
(read, not changed by this ticket — its LAW 46 regression stays authoritative).
**Blocks:** the `sessions`/`stream` claude-code (and `.pi`, and any future vendor) rows on
FleetView's PR idp#3518, currently honestly marked `Not done:` for exactly this reason.

## Why this is a ticket and not a PR

Founder, 2026-09-15, after FleetView's `mutations` and `sessions` endpoints were first found
to have laptop-only stubs: "look i dont want any fucking stubs, get shit done" — then, when a
fix was proposed that parsed Claude Code's own local `prompt-ledger/*.jsonl` file format
directly: "this is idiotic, nothing claude-code specific should exist, we are building
enterprise model agnostic, gut it out." Both corrections are right, and they point at the same
gap: the estate has never built a live, vendor-agnostic path for what's happening in a coding
session on someone's laptop to become queryable, in-cluster, as data. What exists today
(`mcp__estate__list_sessions`/`get_session`, `mcp/plugins/estate_sessions.py`) is already
correctly vendor-agnostic in its *filtering* (`SESSION_STORE_ROOTS` treats `.claude`, `.pi`,
`.gemini` identically) — but nothing publishes fresh, per-event session data into anything
cluster-reachable. `bin/catalog-gen`'s `fold_families` intentionally collapses what does reach
the catalogue into one summary row per family, specifically to fix a real portal-noise and LAW
46 path-leak defect (founder, 2026-09-07) — a decision this ticket does not revisit.

That is real, unscoped infrastructure work — a live sync daemon, a schema for full-fidelity
session events distinct from the folded catalogue summary, and redaction reused (not
reinvented) from LAW 46's existing protections. It does not belong stitched into a deployment
PR under time pressure; a rushed version of it is exactly the kind of thing that would either
leak a path LAW 46 already fixed once, or quietly re-introduce a vendor-specific shim disguised
as "generic."

## What "model agnostic" means here, concretely

Any vendor whose local session-store format is added to `SESSION_STORE_ROOTS` must work through
one, single sync mechanism and one schema — not per-vendor code paths in `fleetview-backend` or
anywhere else. Today's `.claude`/`.pi`/`.gemini` list is the full set of vendors already treated
identically at the filter layer; the sync daemon this ticket scopes must preserve that, not
special-case any one of them.

## The shape of the fix (scoped, not built)

1. Two new `estate.db` tables, canonical and provider-agnostic — additive schema only, via the
   estate MCP server's schema path (ADR 0006), kept separate from the catalogue's folded
   summary rows so LAW 46's existing regression test keeps covering the surface it was written
   for:
   ```sql
   sessions(id, provider, model, created_at, metadata_json)
   session_events(id, session_id, seq, type, payload_json, ts)
   ```
   Every runner/adapter (see below) writes here directly; nothing downstream ever reads a
   vendor's own local file format again.
2. One sync mechanism (a daemon or scheduled job, following whatever pattern this repo already
   uses for laptop-side jobs — `platform/scheduling/one-scheduler.yaml` per AGENTS.md) that
   watches every root in `SESSION_STORE_ROOTS` uniformly and writes new events into the table
   above, reusing LAW 46's redaction logic rather than re-implementing it.
3. `fleetview-backend`'s `sessions`/`stream` endpoints read from `live_session_events` in
   `estate.db` (already mounted in-cluster per idp#3518) instead of any local file, for every
   vendor uniformly — no `if vendor == "claude"` anywhere in that code path.
4. Independent verification once built: a real event written by a real session on a laptop
   shows up in `estate.db` and is served by `fleetview-backend` in-cluster, confirmed by
   something other than the builder (qa-agent or a live query), per DoD v3 check 4.

## Not done, named honestly

- No code exists yet for any of the four steps above. This ticket records scope and rationale
  only.
- Sizing: this is a new sync daemon plus a schema plus a redaction-reuse pass plus an
  in-cluster read path — a multi-session build, not a same-night wiring fix, which is why it
  was pulled out of idp#3518 rather than rushed into it.
- Whether this is worth building now, versus FleetView shipping with `sessions`/`stream`
  correctly scoped to what's real today (`sovereign`, pi, gemini) and an honest "not yet" for
  the rest, is a founder prioritization call, not inferred scope.
