# FleetView triage and focus: needs-attention and the merged session timeline

Founder, prior session: "the whole fview needs thinking aboutt", "bleeding edge", "innovative",
"code is cheap, the other stuff is where we need to invest in" -- FleetView's UI and interaction
should not read as a plain CRUD table. This is the triage-and-focus delta: it does not invent a
new signal, it makes the signals the board already measures (`state`, `isStale`, notes, nudge
audit rows, the receipt verdict) impossible to miss and easy to act on from one place.

Door (from the UI): Backstage -> `/fleets` -> the "Needs attention" panel above the session
table, and each row's "Focus" fold (click a session's Focus summary to open it).

## What exists on main today that this reuses, unchanged

| already built | file | this delta's use of it |
|---|---|---|
| `isStale(session, now)` | `fleetBoard.ts` | the "stale" half of `needsAttention` |
| `state === 'failed'` | `fleetBoard.ts` `Session` type | the "failed" half of `needsAttention` |
| `signals_for(session_id)` | `fleetview-backend/src/signals.py` | the nudge audit trail; no new store |
| `check_receipts_batch` / `POST /check-receipts` | `fleetview-backend/src/evals.py`, `routes.py` | the per-session receipt verdict, called as a batch of one |
| notes (`GET/POST /notes`) | `fleetview-backend/src/routes.py` | one half of the merged timeline |
| the inline author `<input>` on each row | `Fleet.tsx` | replaces `window.prompt()` for Nudge's author |

Nothing here is a new heuristic. `needsAttention` and `timelineFor` are pure functions over
rows the board already fetches; the only new backend surface is a read-only GET that exposes an
audit trail `signals.py` was already writing.

## The three pieces

**1. `GET /api/fleetview/signals?session_id=`** (`routes.py` `signals_envelope`, `serve.py`
`signals_get`) -- read-only, always 200, `{"signals": [...]}`, empty list for a session with
none. Same contract shape as the existing `/notes` GET.

**2. `needsAttention(sessions, now)`** (`fleetBoard.ts`) -- ranks `failed` sessions ahead of
`stale` ones, each group newest-`updated_at`-first. Feeds `Board.attention`, rendered as the
"Needs attention" panel (`data-testid="needs-attention"`) above the table -- triage order, not
table order. Empty is the healthy answer: no panel renders.

**3. `timelineFor(notes, signals)`** (`fleetBoard.ts`) -- merges the two already-fetched,
already-tested row sets into one chronologically-ascending list, copying every field verbatim
(no synthesized field). Rendered inside each row's Focus fold, opened on demand
(`onToggle`), alongside an auto-fetched receipt verdict from the existing `/check-receipts`
route. An unreadable Langfuse renders `Receipt: unavailable`, never a fabricated pass/fail --
the estate's "never fabricate a mapping" rule, applied to the one new render path that touches
an external system.

`sendNudge`'s `window.prompt()` fallback is gone; the author name now comes from the same inline
`<input>` the Focus fold already offered for notes. A Nudge with no name filled in shows "Add
your name in Focus above first" instead of silently no-op'ing or popping a browser dialog Focus
can't lay out or test around.

## Checkpoint, and the command that says it is done

Done: every test below is green, run from this worktree.

- Backend, the new route: `bin/idp-exec bash -c 'python -m pytest sovereign/tests/bdd/test_fleetview_signals.py -q'`
  -- 8 passed.
- Backend, the fleetview suite unaffected: `python -m pytest sovereign/tests/bdd/test_fleetview_*.py -q`
  -- 61 passed, 1 xfailed, 4 failed. The 4 are pre-existing: `test_fleetview_cp1.py` and
  `test_fleetview_cp2.py` import `sovereign.engine.client`, which imports `temporalio`
  (`sovereign/requirements.txt:1`, not installed in this environment); neither file was touched
  by this delta.
- Frontend, the two changed modules: `yarn workspace app run test src/modules/home/fleetBoard.test.ts --watchAll=false`
  (37 passed) and `yarn workspace app run test src/modules/home/Fleet.test.tsx --watchAll=false`
  (29 passed) -- covering `needsAttention`, `timelineFor`, the needs-attention panel, the Focus
  fold's merged timeline and receipt fetch, and the no-`window.prompt` Nudge path (including the
  blank-name case).
- Frontend, no regression on the estate-graph page built earlier in this effort:
  `yarn workspace app run test src/modules/home/EstateMap.test.tsx --watchAll=false` -- 4 passed.

## What this explicitly does not touch

`spend.py`, `mutations.py`, `mutations.ts`, `useMutations.ts`, `Ops.tsx`, `estateGraph.ts`,
`useEstateGraph.ts` -- concurrent sessions' territory in this same worktree. This delta's diff
is seven files: `routes.py`, `serve.py`, `test_fleetview_signals.py`, `Fleet.tsx`,
`Fleet.test.tsx`, `fleetBoard.ts`, `fleetBoard.test.ts`.
