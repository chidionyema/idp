# Takeover plan — crew#973 / Deploy River + Three Planes Observatory

**For the next agent picking this up.** Read this file before anything else; it captures
the verified state of the repo, the gap between the prior session's transcript and
what is actually true, and the precise pickup point.

**Board row:** crew#973. **Spec:** `docs/specs/2026-09-23-deploy-river.md` — read it
first; it has the vision, the laws, the data plane, the build slices, and the honesty
ledger. This file is the *pickup brief*, not the vision.

## Verified state of the repo (read, do not trust the transcript)

| Path | Bytes | Lines | State |
|---|---|---|---|
| `docs/specs/2026-09-23-deploy-river.md` | 9 917 | ~155 | present, complete CP1–CP6 spec |
| `bin/estate-deploy-recorder` | 11 096 | 283 | **BROKEN — syntax error at line 283** |
| `mcp/plugins/deploy_journeys.py` | 6 718 | 167 | present, looks clean |
| `tests/test_deploy_journeys.py` | 6 362 | 175 | present, but cannot run (recorder won't import) |

Verified command and its actual output, just before this handover:

```
$ python3 -m pytest tests/test_deploy_journeys.py -q
E   File "/Users/roseonyema/Documents/code/idp/bin/estate-deploy-recorder", line 283
E       }
E       ^
E   SyntaxError: unmatched '}'
1 error in 8.55s
```

The prior session's transcript (Cline) reported "ALL PASS" with a one-line edit
(`editor +6 -5 lines`) that **never landed in the file**. Take the transcript's
self-reports as unverified claims; the file system is the only truth.

## The exact bug to fix first (the entire pickup point for CP1)

`bin/estate-deploy-recorder`, line 283:

```python
280: if __name__ == "__main__":
281:     sys.exit(main())
282:
283:     }
```

Line 283 is a stray `}` — the residue of a partial edit on `lone_journey`. The
function `lone_journey` ends correctly at line 200-something above; the orphan `}`
left here makes the module unimportable. Delete line 283.

Expected after the fix:
```
$ python3 -m pytest tests/test_deploy_journeys.py -q
... 9 passed in 0.5s
```

Nine tests cover what CP1 owes (per the spec's build-slice row):

- `test_recorder_joins_pr_and_gates_into_one_journey` — one journey per PR, stages in
  order, conclusion-less check = `pending` not `pass`
- `test_recorder_is_idempotent` — re-running over the same sources writes the same rows,
  never doubled
- `test_recorder_blind_writes_nothing` — `gh` refusing is BLIND, exit 2, no writes
- `test_recorder_unclaimed_sha_gets_unknown_pr_stage` — a sha no PR claims is named
  `unknown`, never invented
- `test_recorder_flux_events_land_as_cluster_stages` — `FLUX_EVENTS_PATH` rows become
  cluster stages
- `test_plugin_lists_and_fetches_the_journey` — abbreviated sha resolves, events in
  `seq` order
- `test_plugin_names_a_miss` — `journey: null` + named `error` for a sha nobody recorded
- `test_plugin_blind_when_the_store_is_missing` — `available: false`, never an empty
  fleet
- `test_plugin_refuses_an_empty_sha`

Once those nine tests are green, CP1's "done means" line in the spec's build-slice
table is satisfied:

> `CP1 | deploy_journeys ledger: recorder + MCP tools | get_deploy_journey(<sha>) returns a real push→merge chain on this repo`

Verification (do not skip):
```bash
RECORDER_PR_LIMIT=50 python3 bin/estate-deploy-recorder --json   # writes to catalog/estate.db
python3 -c "import sqlite3; c=sqlite3.connect('catalog/estate.db'); print(c.execute('SELECT COUNT(*) FROM deploy_journeys').fetchone()[0])"
```

## The architecture the next five CPs sit on top of

The spec depends on these existing components. The next agent must understand each
before touching the River code:

| Component | Path | Why it matters |
|---|---|---|
| HUD architecture | `docs/specs/2026-09-20-fleet-2100-hud-architecture.md` | laws for both pages: information is ambient until interrogated, voice is routed by spatial intent, chrome is eliminated, transcript never hidden |
| Three.js lineage | `backstage/packages/app/src/modules/room/ui/FleetReactorApp.tsx` | the existing full-bleed WebGL room; both new scenes live inside it |
| Voice engine | `backstage/plugins/fleetview-backend/src/voice.py` | the BACKEND side; the SPA hook is `useEstateVoice` in `packages/app/src/modules/home/` |
| Estate MCP | `mcp/plugins/` (extend; do not add a second server, ADR 0006) | the new `deploy_journeys.py` is already shaped to plug into this. The River and Observatory read over MCP, never over a second door |
| Ledger | `catalog/estate.db` | one store per THE HEADLINE; new tables `deploy_journeys` / `deploy_journey_events` are already in the recorder |

## The five remaining CPs — the actual scope of "the next agent's day"

| CP | What it lands | Acceptance test (from the spec) |
|---|---|---|
| CP2 | `/fleetview/river` scene — comet for a commit, gate rings over the river, red gates crack, rejection basin, Andon ambient light | a live push visibly flies; a forced failure visibly cracks its gate |
| CP3 | Narration engine — templates over the ledger, deterministic text from real timestamps, sovereign voice on :8899 | story mode speaks a real deploy, timestamps correct |
| CP4 | Time-scrub + gate holograms + Holmes interrogation | "why did this fail" answers from a real red run, by voice |
| CP5 | `/fleetview/planes` Three Planes Observatory — three concentric rings, live data from jev_decisions, red-team catalog, Aevum receipts | jev decisions, judge drift and Aevum seals all animate in one view |
| CP6 | Voice steering both pages — spatial target-lock | "tell the one on the left to stop" reaches the right session |

**CP2 is the smallest standalone slice.** If the next agent has limited time, CP2
gives the founder something to look at and unblocks all later CPs.

## Pattern the recorder already establishes (so CP2–CP6 don't drift)

The recorder's design choices are load-bearing for the rest. Read the docstrings in
`bin/estate-deploy-recorder` and `mcp/plugins/deploy_journeys.py` — they are the laws:

1. **One store per THE HEADLINE.** No second database. The River reads `catalog/estate.db`
   the same way the recorder writes it.
2. **`available: false` ≠ empty fleet.** A broken reader and an unread story must never
   look the same. The MCP envelope's `available` flag is the bit the renderer is
   allowed to show "we don't know"; the `error` field is the bit the renderer must
   surface.
3. **Templates over ledger, not LLM over vibes.** Narration is deterministic from real
   timestamps. LLMs answer *questions about* the journey (Holmes, CP4), never narrate
   the journey.
4. **BLIND has a name and an exit code.** `BlindError`, stderr, exit 2. The Cline
   transcript correctly writes `BLIND estate-deploy-recorder: gh pr refused: …` and
   exits 2. Keep this convention for every new component.
5. **The MCP plugin's module-level alias trick.** `mcp/plugins/deploy_journeys.py`
   binds `_envelope_list_deploy_journeys = list_deploy_journeys` *outside* the
   `register_mcp_tools` function because the inner `@mcp.tool()` decorators create
   same-named locals which would shadow the module-level functions (measured on
   `estate_sessions.py` 2026-09-13 — the tool answered with the repr of its own
   coroutine). Copy this exact shape into any new MCP tool.

## Where the visible gap is drawn (per the honesty ledger)

The spec's "honesty ledger" section says the Universal Write Boundary is drawn as a
crack in the Observatory ring because it *is* one — `platform/idp_agent/engine.py:311`
writes straight to disk via `open().write()`, bypassing every gate in Plane 3. The
new MCP tools in this PR close one part of the gap (ledger-mediated writes for deploy
journeys) but do not close it. CP5 must render the gap visibly, not hide it.

## Files the next agent will likely create

Approximate shape (CP2 ships first):

```
backstage/packages/app/src/modules/fleetview/river/         # the new page
  index.tsx              # the route handler
  scene/                 # Three.js pieces, mirrors room/ui/FleetReactorApp.tsx
  data/                  # MCP client; reads get_deploy_journey + list_deploy_journeys
mcp/plugins/fleet_narration.py   # CP3: template engine, deterministic from ledger rows
backstage/packages/app/src/modules/fleetview/observatory/  # CP5
backstage/packages/app/src/modules/fleetview/voice/        # CP6: spatial target-lock
```

Each new component ships with its own tests and its own proof, exactly as CP1 does.

## Single short checklist for the next agent

1. `git pull` (or verify the four files above match the table's bytes/lines).
2. Delete line 283 of `bin/estate-deploy-recorder`.
3. `python3 -m pytest tests/test_deploy_journeys.py -q` → expect `9 passed`.
4. Run the recorder once against this repo: `python3 bin/estate-deploy-recorder` — read
   what it writes; that is the data shape CP2 will render.
5. Read `docs/specs/2026-09-23-deploy-river.md` end to end.
6. Read `backstage/packages/app/src/modules/room/ui/FleetReactorApp.tsx` — that's the
   WebGL lineage the River scene extends.
7. Start CP2 with `backstage/packages/app/src/modules/fleetview/river/` mirroring
   FleetReactorApp's full-bleed pattern; the spec's CP2 row is the acceptance test.
