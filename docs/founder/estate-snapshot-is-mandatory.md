# The estate snapshot is mandatory, and no agent proceeds without it

Founder, 2026-09-03 04:1xZ, in the Kimi lane session, verbatim: "soryr that does not nake sense
and nno sgaebt can proceed withoit it furthernoe i need to know exactly what is conteibs."

Plain reading, as a ruling:

1. **No agent may start work without the estate snapshot.** A session that cannot read it at
   start is blind and does not proceed; it says `BLOCKED: estate snapshot unreadable` and why.
   A stale cache is not the snapshot.
2. **He can see exactly what the snapshot contains, whenever he asks.** Its shape is written
   down here and kept current by the test that grades it, never explained from memory.

## What the snapshot is

One document, version 1, produced by the estate MCP server's `get_estate_state` tool and read by
every session's start-up hook (`estate-state-relay.py`), which caches it in the session's
estate folder as `estate-state.json` and marks it stale after 30 minutes. Contents, from the
document generated 2026-09-03T03:49:22Z:

| Section | Field | What it holds |
|---|---|---|
| overview | `freeze` | whether a change freeze is active |
| overview | `rulings` | every standing founder ruling, by number (57 today, the first to the seventy-fourth) |
| overview | `sessions` | every agent session: number, lane, what it is doing, what blocks it, last handoff time (8 today) |
| overview | `board` | open board items (0 today) |
| runtime | `surfaces` | each founder-facing surface with its measured verdict, the URL probed, the HTTP answer and the time (5 today: signoz, healthchecks, llm, screen, published-paths) |
| runtime | `clusters` | each cluster with role, overall state and every Flux row: kind, name, area of the cluster, ready, revision, since (1 cluster, 80 rows today) |
| delivery | `main_sha` | the commit each repository's main is at |
| delivery | `failed_runs` | failed CI runs on main (0 today) |
| delivery | `open_p0` | open P0 items (0 today) |
| security | `open_findings` | open security findings (0 today) |
| docs_apis | `standards_page`, `runbooks_index`, `diagrams` | where the standards page, runbook index and diagrams live |

It does **not** hold any secret, vault field, key or token; it does not hold pod logs or metrics.
Those are separate MCP tools (`get_workload_state`, `get_workload_logs`).

## What was wrong tonight

The session's restart hook printed `[estate-state] BLIND: get_estate_state could not be read
(TimeoutError)` and the session carried on from a cached copy. Under this ruling that is a stop,
not a warning. The gate is the guard hook itself: when the read fails, the first tool call is
refused, not a line printed that nobody reads (the law that an instrument nobody reads is not an
instrument, and the law that a rule without a protocol is a wish).

## Version 2, built 2026-09-03 on the founder's word (04:2xZ)

Founder: "it could contain more useful info" and "and any recent decision or changes." Seven
additions inside the same five tabs, served by the same `get_estate_state` tool of the same estate
MCP server; nothing about how a session fetches it changed. Every new field comes from a file the
producer workflow fetched; a source it could not read is a `BLIND` line in the run and an empty or
`UNKNOWN` field in the document, never a green row.

| Section | Field | What it holds |
|---|---|---|
| security | `vendor_roots` | each vendor with a SEED secret: the secret's name, when it was last set, and the last apply run's verdict for that vendor in the vendor's own words (`ok`, `FAIL` with the refusing URL and HTTP answer, or `UNKNOWN` when the seeder did not name it) |
| runtime | `router_lanes` | every model alias in the router config with one measured call of one token: `ok`, `FAIL` with the HTTP answer, or `UNKNOWN` when the probe key is not allowed on that lane; each with its time and duration |
| delivery | `open_prs` | open pull requests across idp, crew, prospector, hermes-v2 and claude-guards: number, title, branch, draft, check counts (ok, fail, pending, newest run per check), merge state, last update |
| overview | `founder_blockers` | every live session whose Blocked line waits on the founder, with the words it waits for; and every open `founder-request` issue |
| delivery | `last_apply` | the newest oke-check run that ran the vendor seeder: run number, URL, time, conclusion, every failed step by job, and every `FAIL` or `BLIND` verdict line of its log |
| runtime | `incidents` | rows of the crew incident ledger that are open or were detected or resolved in the last 24 hours, with their classes |
| overview | `decisions` | founder rulings dated in the last 24 hours and every commit to `docs/decisions` or `docs/founder` in idp and crew in that window |
| delivery | `changes` | every merge to main across the five repositories in the last 24 hours: repository, short commit hash, title, time, newest first |

Measured on the first local build, 2026-09-03 04:44Z: the two refused vendor roots (deepseek set
20:38Z, kimi set 21:20Z, both `FAIL` with the vendor's 401 in the row) and the dead `kimi` router
lane (`FAIL` 500, the same words the founder's aider session saw) are named in the document
without anyone re-running apply. That is the field test the ruling asked for.

Producer: `.github/workflows/estate-state.yml`, one App-token fetch step and one router probe
step (`bin/idp-router-lanes`), parsed by `bin/idp-estate-state-build`; shapes in
`platform/estate-state/schema.json`; graded by
`tests/test_incident_estate_snapshot_names_what_moved_and_what_waits.py`. The fetch step ran in
12 seconds locally and the probe in under a minute, inside the two-minute budget.

Gate, next: the guard hook refuses the first tool call of a blind session instead of printing a
line (claude-guards `opa-hook.py` and its policies, separate change).
