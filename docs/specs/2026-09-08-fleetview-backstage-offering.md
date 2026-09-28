# FleetView: the live agent-session board, on Backstage, sold as an offering

Founder, 2026-09-08 19:35Z: "there was a dashboard screen where I could monitor the agent
sessions in real time, that is a super marketable product, we are sitting on gold and do not
even know we have it." 19:50Z: "needs to be exponentially better and on Backstage, but we need
this developed as an offering." Record:
`~/.claude/docs/founder/2026-09-08T1935Z-hidden-gems-the-cockpit-and-the-inventory-pipeline-a92d5ead.md`.

## What exists today (measured 2026-09-08)

`sovereign/cockpit`: a stdlib HTTP server and one HTML page on the Mac, loopback port 8788,
polling every 3 seconds. Doors: `/api/sessions`, `/api/status`, `/api/inbox`, `/api/config`,
and `stop | approve | deny | steer` on one session. Sessions come from Temporal workflows through
`sovereign/engine/client.py` (`list_sessions`). Telegram Mini App auth. 37 unit tests, green.
Its launchd job is not loaded; the log stopped 2026-08-28 14:44 (BrokenPipeError) when the
engine moved to the cluster (commit c2733b99). No marketing page. Started by hand on
2026-09-08 it served one session, status `unknown`, and a red "integrity check required" line.

So the gold is the idea and the contract (presence, decisions, inbox, four signals), not the
page. The page is rebuilt where the founder and a buyer already look: the Backstage portal.

## What "exponentially better" means, in numbers a test can grade

| today | FleetView |
|---|---|
| one runtime (sovereign sessions) | every agent runtime in the estate on one board: Claude Code sessions, DeepSeek lanes, Cyrus, Otto, Dagster runs, GitHub Actions bots |
| one machine, loopback | on the portal, behind the estate's OIDC, any device |
| 14 fields, no history | each session tied to its pull requests, its traces (Langfuse), its spend (LiteLLM), its ticket (Linear/GitHub), and its checkpoint file; 30 days of history with replay |
| stop/approve/deny/steer on one session | the same four signals on any session, from the page, with an audit row for each press |
| a red line that says run a terminal command | an alert that names the session, the reason and the one button that fixes it; no terminal, ever (LAW 31, R75) |
| poll every 3 s | server push; a change reaches the page under 3 s; first paint under 2 s |
| single tenant | tenant-scoped: a customer sees their fleet only (decision 0021) |

## Architecture: two Backstage plugins, one data contract

- `backstage/plugins/fleetview-backend`: a backend plugin with one job: turn every runtime into
  the same session record. Adapters: `sovereign` (Temporal, existing client), `claude-code`
  (the checkpoint and transcript files the estate already writes, read through the estate MCP
  server, never the filesystem from the portal), `cyrus` (its own session API), `dagster` (the
  GraphQL runs endpoint the entity provider already talks to), `github-actions` (runs by bot
  actor). Enrichers: Langfuse trace by session id, LiteLLM spend by tag, PRs by branch,
  Linear issue by key in the branch name. One SSE stream `/api/fleetview/stream`; one REST
  read `/api/fleetview/sessions`; one signal door `/api/fleetview/sessions/:id/:signal` that
  writes an audit row before it acts.
- `backstage/plugins/fleetview`: the frontend. A fleet page (`/fleet`) with the board, a
  session drawer, and the four signal buttons. A card on every catalog entity that is an
  agent (`spec.type: agent`) showing its live sessions. Uses `custom-entity-extensions` for the
  card slot, as the "On the cluster" card branch already does.
- The session record is one JSON schema, `backstage/plugins/fleetview-backend/schema/session.json`,
  versioned; every adapter's output is validated against it in CI. The schema is the offering's
  integration surface: a customer with their own runtime writes one adapter.

Rejected: keep the Python cockpit and iframe it into Backstage (second login, second server,
no tenant scope, no entity linkage; the stitching the headline forbids). Rejected: a Grafana
dashboard on the traces (read-only, no signals, no entity linkage).

## Checkpoints, each with the command that says it is done

CP1 The contract. Schema, backend plugin skeleton, sovereign and dagster adapters, `/sessions`
    and `/stream`. Done: `curl -s $PORTAL/api/fleetview/sessions | jq length` is 1 or more on
    the cluster, and the `fleetview-backend` tests are green.
CP2 The board. Frontend plugin, `/fleet` page, drawer, live update. Done: the founder opens
    `$PORTAL/fleet`, sees a session that is running right now, and its state changes on the page
    without a reload; `features/fleetview/cp2_board.feature` passes in CI against the preview.
CP3 The signals. Stop, approve, deny, steer from the page with an audit row. Done: pressing
    Stop ends a real sovereign session within 5 s (`bin/sb show <id> --json` reads stopped) and
    `SELECT * FROM fleetview_audit ORDER BY at DESC LIMIT 1` names the press.
CP4 Every runtime. Claude Code, Cyrus, GitHub Actions adapters; Langfuse, LiteLLM, PR and
    Linear enrichers. Done: a Claude Code session, a Cyrus run and a bot PR all appear on one
    board with a trace link, a spend figure and a PR link each.
CP5 The offering. Tenant scope, 30-day history and replay, alerting through the existing
    Alertmanager route, marketing page live, demo and onboarding pages (LAW 32), a customer
    adapter guide. Done: a second tenant account sees none of the estate's sessions; the
    `docs/marketing/products/fleetview.md` page is in the catalogue index; `bin/law32-gate`
    is green.

## Two weeks, ten DeepSeek lanes

Days 1–3: CP1 (two lanes: schema and backend, adapters). Days 2–6: CP2 (two lanes: page,
card). Days 4–8: CP3 (one lane) and CP4 adapters (three lanes, one per runtime). Days 7–11:
CP4 enrichers (two lanes). Days 9–14: CP5 (all lanes). Each lane is one branch, one PR, merged
when green by the merge-when-green workflow that already exists. Optimised: CP1's schema is the
only serial step; everything after it is parallel by adapter.

## The offering

Name: FleetView (the name already exists in the estate's agent registry). Sold inside the
Platform plans and standalone. Standalone: the Team plan price, $24,000 a year, for up to ten
agent runtimes; Enterprise includes it. What the buyer says to their board: "Every AI agent we
run is on one screen, with its cost, its trace and its pull request, and I can stop any of them
from my phone."
