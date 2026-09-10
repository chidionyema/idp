# SPEC — MUM-286: Backstage sessions board

**Author:** direct-executor (pi-crew run `team_20260910163921_20949e8b3ce3b3e3`).
**Branch:** `feat/mum-286-sessions-board` off `origin/main` (commit `92149bd0`,
"fix(otto): the memory backfill outlasts a brief hindsight outage, and re-runs").

## Why this exists

Founder narrowing for MUM-286 (after the ops Health page `/ops` shipped):
the Backstage home module grows a **session board** that lists the founder's
recent agent sessions — one Backstage surface for "what did I ask the agents
lately", rendered from the catalogue the estate already publishes. No second
file format, no second scan of `~/.claude`, no second MCP server.

## Seam (re-verified 2026-09-10)

Verified before any code was written:

- `catalog/catalog-info.yaml` carries 50 `kind: Resource` rows whose
  `estate/path` is under `~/.claude/state/prompt-ledger/`. Each row carries
  `metadata.name` starting with `claude-state-prompt-ledger-`, the
  `estate/coupling: anthropic`, `estate/kind: ledger`, and a numeric
  `estate/rows` annotation. Confirmed by
  `grep -c "estate/path: '~/.claude/state/prompt-ledger'"` = 76 (50 files
  plus the family envelope and 25 short-form repetitions).
- `bin/catalog-gen` is the only generator of those rows. It is the law-39
  one-shot that turns the inventory into Backstage entities; nothing else
  emits ledgers.
- `mcp/plugins/estate_*.py` are datasette hooks registered through
  `register_mcp_tools(datasette, mcp)`, the same mechanism datasette-mcp uses
  for its built-in tools. They run inside the existing `estate-mcp` server
  (one Datasette process, `--plugins-dir /app/plugins`); ADR 0006 forbids a
  second server.
- `backstage/packages/app/src/modules/home/` is the home module and
  `Investigate.tsx` shows the proxy/fetch pattern. The page sits beside
  `/ops`, `/reports`, `/investigate`, `/showcase`, `/tools`.

Constraint note re. item 4 of the brief: the brief says "the proxy route for
estate MCP is configured in `backstage/app-config.yaml` under the existing
MCP-server integration". The seam check found it is **not** configured. The
page therefore reads the session rows through Backstage's native catalog
client (`catalogApiRef`, used by `useDoors.ts`, `useEstate.ts`, `useOpenReds.ts`
and the Ops/Showcase/EstateHome tests). This is one of the two "doors" the
brief invited (the other being the MCP-over-HTTP route), and it bypasses any
need to add a new proxy route. The MCP plugin ships anyway so non-Backstage
MCP callers (Telegram/hermes/k8sgpt) can list sessions over the existing
`mcp.${ESTATE_ZONE}/estate/mcp` lane.

## Deliverable surface

| Layer | File | Role |
|---|---|---|
| MCP tool | `mcp/plugins/estate_sessions.py` | Adds `list_sessions` and `get_session(name)` datasette hooks. Reads `catalog/catalog-info.yaml` once per call. Returns rows whose `estate/path` is under `~/.claude/state/prompt-ledger/`. |
| Tests | `tests/test_estate_sessions.py` | Pytest with `monkeypatch`d `ESTATE_CATALOG_PATH`; reads fixture `tests/fixtures/sessions/catalog-info.yaml`. |
| Fixture | `tests/fixtures/sessions/catalog-info.yaml` | 3 sample session rows + 1 non-session row to prove the filter. |
| Page | `backstage/packages/app/src/modules/home/Sessions.tsx` | The Backstage page at `/sessions`; renders the list with a refresh button. Mirrors `Investigate.tsx` style. |
| Page test | `backstage/packages/app/src/modules/home/Sessions.test.tsx` | Backstage `renderInTestApp` with a `catalogApiMock`; asserts the rows render and a click handler triggers refresh. |
| Hook | `backstage/packages/app/src/modules/home/useSessions.ts` | Thin hook around `catalogApiRef.getEntities({ filter })`. |
| Home module | `backstage/packages/app/src/modules/home/homeModule.tsx` | Adds `sessionsPage` at `/sessions`. |
| Toolkit | `backstage/app-config.yaml` | Adds `/sessions` to the home toolkit so it appears beside `/ops`. |

## Data shape (catalogue row -> Sessions page card)

```yaml
metadata:
  name: claude-state-prompt-ledger-...
  annotations:
    estate/coupling: anthropic
    estate/kind: ledger
    estate/path: ~/.claude/state/prompt-ledger/<file>.jsonl   # LA W 46 already pre-homed
    estate/rows: '17'
spec:
  type: ledger
```

The page renders one card per row:

| field | source |
|---|---|
| `session_id` | suffix of `metadata.name` after `claude-state-prompt-ledger-` (path-encoded, decoded) |
| `path` | `metadata.annotations.estate/path` |
| `row_count` | `metadata.annotations.estate/rows` |
| `last_updated` | file mtime (`os.path.getmtime`) where readable; `null` when missing or unreadable |
| `lifecycle` | `experimental` (Backstage vocabulary, mapping `dev` env → `experimental`) |

## MCP `list_sessions` shape

```json
{
  "available": true,
  "stale": false,
  "count": 50,
  "sessions": [
    {
      "session_id": "private-tmp-claude-501-Users-chidionyema-<uuid>-scratchpad",
      "name": "claude-state-prompt-ledger-...",
      "path": "~/.claude/state/prompt-ledger/...jsonl",
      "row_count": 17,
      "last_updated": "2026-09-10T17:42:01Z",
      "lifecycle": "experimental"
    }
  ]
}
```

Envelope shape mirrors `estate_state.py` (available/stale/error) so a caller
in front of either tool reads the same code path.

## `get_session(name)` MCP tool

Returns one row matching `metadata.name`. Missing rows return
`{"available": false, "error": "..."}` (same envelope, no crash). Refused
when name has a `/` so the catalogue can't be path-traversed.

## CI gates touched

- `python3 bin/idp-ruff` — ruff E9,F,B,S, ignore S603,S607, per-file-ignores
  `tests/*:S101` (the project policy).
- `bin/test-executes-gate` — the test-execution rule.
- Nothing new added to `rules.yaml`; nothing in `bin/` was a new file.

## Failure modes named up front

- Catalog missing: returns `available: false`, `error: "no catalog at ..."`.
  Same posture as `estate_state.py:62` (CP3 acceptance: a missing estate-state
  is stale + unavailable, never fabricated).
- Row missing on `get_session`: `available: false`, `error: "no session ..."`.
- Catalogue file unreadable (OSError): caught and returned as an envelope with
  `error`. Never raises to the caller.

## Out of scope

- No new proxy route in `backstage/app-config.yaml`.
- No new MCP server, no new catalogue generator.
- No schema change to `catalog/catalog-info.yaml`; the rows are read as-is.
