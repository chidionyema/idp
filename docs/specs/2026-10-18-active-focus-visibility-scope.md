# Scope: Active Focus job-plane visibility (spec #6227)

Date: 2026-10-18 · Claim: chidionyema/idp#6228 · Agent: estate-agent

## Question

Spec #6227 asks for Active Focus to be visible on the job plane. What exists, what is
missing, and what is the smallest path to the founder watching the focus controller decide,
live, on /fleet?

## What exists (measured this session)

- **Controller** — `platform/active-runtime/src/focus/active-focus-controller.ts` (339 lines):
  the decision logic (AWAIT_APPROVAL, ticket creation, consume/expire, resume). Complete, unit
  tested (`test_harness.py` covers ticket lifecycle).
- **Store** — `approval_tickets` (schema.sql §11): ticket_id, agent_id, tool_name,
  target_resource, status, expires_at, resume_data. The live decision is fully row-expressible.
- **Counting** — `/harness/stats` counted pending approvals as a bare integer; FleetView
  forwarded it; **nothing rendered it** — no frontend consumed `/fleetview/harness` at all
  (rg over `backstage/packages/app/src/`: zero hits before this session).
- **Decision stream** — `fleetview serve.py` already streams `type: approval` events over
  NATS (`subscribe_approvals`), a second, push-shaped channel the panel does not use yet.

## The gap, in one line

The focus controller decides; the decision is stored; nothing shows the decision happening.
A count cannot show who awaits, on what, until when — and a stale count is indistinguishable
from a live one (AGENTS.md §3: narrating instead of proving).

## What landed (this session, on lane fix/agent-attribution)

1. `/harness/stats` now returns `store.pending_ticket_details` — the live pending tickets
   (agent, tool, target, created, expiry), filtered `status='pending' AND expires_at > NOW()`,
   capped at 20 — with a contract gate (`test_harness_stats.py`) proven able to fail by
   stripping the expiry filter.
2. `/fleet` gains an **Active focus** panel (`EstateHarness.tsx`): renders the deciding
   tickets (who: what on which target — awaits until), active runs, per-agent write
   attribution; a degraded memory server shows its reason, never a bare zero.

## Remaining rungs (out of this lane, in order)

1. **Voice** — the panel is visual; the founder hears nothing. A pending ticket should speak
   (or arrive in the voice turn) per the voice-first law: "awaiting your approval: atlas
   wants db_drop on prod/events, for the next 15 minutes." The NATS approval stream
   (`serve.py` approvals_adapter) is the natural source; the voice plane consumes it.
2. **Push, not poll** — the panel polls at 10s; the NATS stream already carries the same
   events. Switching the panel to the stream removes the poll and the staleness window.
3. **Decision outcomes** — approved/rejected land in `approval_tickets.status`; the panel
   should show the last decision and its latency (ticket created → consumed), making the
   focus controller's throughput measurable, not just its queue depth.
4. **Agent-plane attribution parity** — `resume_data` carries the suspended run; surfacing
   which run/session a ticket belongs to links the focus decision to the session board.

## Deliberately not in scope

- A second reader of the harness tables (AGENTS.md §6: one of each layer) — all reads stay
  behind the unified-memory-server's HTTP API.
- Any change to the focus controller itself: its decisions are correct and tested; the gap
  was visibility, not judgement.
