# The estate snapshot is mandatory: no agent proceeds without it

Founder, 2026-09-03 04:1xZ, in the Kimi lane session, verbatim: "soryr that does not nake sense
and nno sgaebt can proceed withoit it furthernoe i need to know exactly what is conteibs".

Plain reading, as a ruling:

1. **No agent may start work without the estate snapshot.** A session that cannot read it at
   start is blind and does not proceed; it says `BLOCKED: estate snapshot unreadable` and why.
   A stale cache is not the snapshot.
2. **The founder must be able to see exactly what the snapshot contains.** Its shape is written
   down here and kept current by the test that grades it, never explained from memory.

## What the snapshot is

One document, version 1, produced by the estate MCP server's `get_estate_state` tool and read by
every session's SessionStart hook (`estate-state-relay.py`), which caches it in the session's
estate folder as `estate-state.json` and marks it stale after 30 minutes. Contents, from the
document generated 2026-09-03T03:49:22Z:

| Section | Field | What it holds |
|---|---|---|
| overview | `freeze` | whether a change freeze is active |
| overview | `rulings` | every standing founder ruling, by id (57 today, R1 to R74) |
| overview | `sessions` | every agent session: id, lane, what it is doing, what blocks it, last handoff time (8 today) |
| overview | `board` | open board items (0 today) |
| runtime | `surfaces` | each founder-facing surface with its measured verdict, the URL probed, the HTTP answer and the time (5 today: signoz, healthchecks, llm, screen, published-paths) |
| runtime | `clusters` | each cluster with role, overall state and every Flux row: kind, name, namespace, ready, revision, since (1 cluster, 80 rows today) |
| delivery | `main_sha` | the commit each repo's main is at |
| delivery | `failed_runs` | failed CI runs on main (0 today) |
| delivery | `open_p0` | open P0 items (0 today) |
| security | `open_findings` | open security findings (0 today) |
| docs_apis | `standards_page`, `runbooks_index`, `diagrams` | where the standards page, runbook index and diagrams live |

It does **not** hold any secret, vault field, key or token; it does not hold per-PR state, pod
logs or metrics. Those are separate MCP tools (`get_workload_state`, `get_workload_logs`).

## What was wrong tonight

The session's restart hook printed `[estate-state] BLIND: get_estate_state could not be read
(TimeoutError)` and the session carried on from a cached copy. Under this ruling that is a stop,
not a warning. The gate is the relay itself: when the read fails, the relay must refuse the
session, not print a line nobody reads (LAW 28, LAW 44).

## Next version, planned 2026-09-03 04:2xZ, awaiting the founder's go

Founder: "it could contain more useful info" and "and any recent decision or changes". Seven
additions to the same document, same tool:

1. Vendor roots: each SEED secret's last-set time and the last apply run's verdict per vendor, in the vendor's words.
2. Router lanes: each model alias with its last measured answer and time.
3. Open pull requests per repo, with check state and merge state.
4. The founder's open blockers: every action sent to him and not yet answered, and the word each waits for.
5. Last apply run: the failing step and its line.
6. Incidents in the last 24 hours, with their signature.
7. Recent decisions and changes: founder rulings and decision records made in the last 24 hours, and every merge to main in that window (repo, commit, title), so a session knows what moved since the last time anyone looked.

Gate: the start-up relay refuses a blind session. Budget: the producer run stays under two minutes.
