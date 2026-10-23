# 0038 — One scene contract, one path: `estate.scene.frame` replaces the cinema cue

Date: 2026-10-23
Status: accepted
Related: 0037 (deterministic twin), 0039 (one mouth), 0040 (placement),
`docs/specs/2026-10-23-estate-as-movie-director-engine.md` §5.2

---

## Context

The estate has a cinema channel today, and it is the weakest link in the chain.

Measured on 2026-10-23:

- `estate.cinema.cue` is published on **core NATS, ephemeral** — a cue published while the page
  is closed is gone (`fleetview_backend/nats_adapter.py:32`, `subscribe_cues` `:336`);
- it has **no JSON schema**: `platform/event-bus/contract/` holds exactly three schemas today
  (`estate.agent.event.json`, `estate.commerce.order_paid.json`, `estate.news.story.json`), and
  none of them describes a cue;
- the only consumer is one branch of one page: `FleetReactorApp.tsx:1587`;
- nothing calls the director: `platform/voice-router/deploy/director.yaml` says, in its own
  header, *"No Service is declared: nothing calls the director."*

So the estate has a topic, a schema-less payload, an ephemeral transport and one consumer — the
shape of a thing that was started and never finished.

The film needs more than a cue. A frame has to carry the **cast** (who is on stage, where, in
what state), the **shot** (which camera move, on whom, and why), the **line** (what is said, and
the id of the row that says it may be said), the **directive** (what the founder asked, who, and
what happened to it) and the **interruption** (what was dropped and why). Building that as an
extension of the ad-hoc cue would give the estate two scene-ish channels — the duplication AGENTS.md
§6 forbids.

## Decision

**One contract, `estate.scene.frame`, in the contract directory, on JetStream. The
`estate.cinema.cue` topic is retired in the same change.**

- Subject: `estate.scene.<room>.frame`. **JetStream, not core NATS** — a frame the page missed
  must be recoverable, and a cut that arrives late is worse than no cut.
- Schema file: `platform/event-bus/contract/estate.scene.frame.json`, enforced by the same CI
  check that enforces `estate.agent.event.json`.
- The frame carries: `at`, `seq` (monotonic per room), `room`, `cast[]`, `shot`, `line` (with
  `source.id`), `directive`, `interrupted`.
- `estate.cinema.cue` is **deleted**, not deprecated alongside. One path, in the same change, in
  one commit. The page's `type === 'cue'` branch goes with it.
- The Director's **only** egress is this stream. It has no client for `/nudge`, no write path to
  a session and no secret — it proposes; the estate's existing `/nudge` door acts.

### Why one contract and not two

A cue ("cut to X, say Y") and a scene ("here is the stage, here is the shot, here is the line,
here is the directive") are the same fact at two resolutions. Keeping both means two consumers of
truth, two failure modes, and a page that has to reconcile them. One contract at scene
resolution can express a cue as a degenerate scene, so nothing is lost.

The `seq` field is what makes a whole-scene snapshot safe on the wire: the page drops
out-of-order frames rather than rendering a cut that has already been superseded.

## Consequences

**Positive.** The scene becomes schema'd, replayable and auditable like the event spine. The
page has one input. The cue's ephemeral transport and missing schema go away.

**Negative, accepted.**

1. **The page's cue branch breaks mid-change.** Accepted: one commit changes the contract, the
   backend and the page together. A half-landed change shows no film, which is a louder and
   cheaper failure than a wrong film.
2. **The frame is bigger than a cue.** Acceptable on a LAN; the cast list is small (one entry per
   live session) and frames are coalesced per session by the existing coalescer.
3. **`estate.cinema.cue` may have consumers outside this repo.** Measured: one consumer in this
   repo. The consultant greps the estate before deleting, and the deletion happens in the same
   change as the new contract.

## Enforcement

- The contract file exists and is enforced (law RG4).
- A grep for `estate.cinema.cue` in the estate returns **nothing** after the change.
- The page has exactly one branch that turns a frame into a picture (law RI1).
- The Director's process holds no credential and opens no client to `/nudge` (law RG1) — a
  reviewer reads its imports and finds only the bus and the schema.
