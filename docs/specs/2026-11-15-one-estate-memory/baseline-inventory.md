# W0 baseline — authority, components, surfaces, owners

Requirement: FR-001. Cases: MEM-001-POS, MEM-001-NEG. Generated 2026-11-15 from the live checkout and host.
Machine record: `baseline-inventory.json` (same directory). No operational claim is made here.

## Authority

- Canonical issues: `chidionyema/idp#6164` (OPEN), `chidionyema/idp#7955` (OPEN).
- Substrate: `docs/decisions/0048-the-estate-runs-on-one-node-with-an-admission-list.md`. OKE is retired; ARM k3s is the declared home, not an operating claim.
- idp revision measured: `306ce092530f4f35b85cafb48b7129670c53fa51`.

## Components (installed revisions, sha256)

| id | path | owner | sha256 (prefix) | bytes |
|---|---|---|---|---|
| memory-door | `platform/estate/memory/door.py` | platform/estate/memory | `009dcf808982` | 13172 |
| memory-mcp | `mcp/plugins/estate_memory.py` | mcp/plugins | `a45a8e5e5702` | 28608 |
| plan-lock | `platform/estate/memory/plan.py` | platform/estate/memory | `13e71d316b0b` | 54642 |
| brief | `bin/estate-brief` | platform/estate/memory | `a38315264ef7` | 5632 |

Successor pointer: `chidionyema/idp#8156` adds a graph-lessons section to the brief (measured 7512 bytes on the lane); it was not merged at the measured revision.

## External stores observed on this host

| path | owner | sha256 (prefix) | bytes |
|---|---|---|---|
| `~/.estate/memory/memory.db` | memory-door | `0c1a1fc8e4cf` | 704512 |
| `~/.estate/graph/estate-graph/.growmos/entities.jsonl` | estate-graph | `ebb0b2f74814` | 5327387 |
| `~/.estate/packs/registry.json` | estate-session | `8fed518d92bd` | 6827 |
| `~/Documents/code/crew/STATE.md` | crew | `ce05b91a2326` | 15929 |

These are host observations; CI does not assert their presence.

## Surfaces

| class | route | status |
|---|---|---|
| opencode | `~/.config/opencode/plugin/estate-memory.js` | present |
| claude_code | `~/.claude/settings.json SessionStart -> estate-session` | present |
| codex | — | no memory injection found in this pass |
| gemini_cli | — | no memory injection found in this pass |

## Unresolved (explicit)

- Independent builder reviewer: no owner. The authorized session-start route was not exposed (sb absent; sessions MCP lists/reads only).
- Codex and Gemini memory injection: no owner. No installed hook or plugin was found that writes or injects memory for these surfaces.
- Graph to memory-door drain: owned by `estate-graph-drain`, currently broken. Log `2026-11-15T21:06:11Z ingest_rc=2 Connection refused` via `GROWMOS_BASE_URL=http://127.0.0.1:4000`.

## Obsolete routes

- `oke` (any path segment beginning `oke`, `oke-`, `oke_`) is refused: ADR 0048 retired OKE. A runbook that still says OKE is history, not authority.

## Bound acceptance

- `MEM-001-POS`: a planned memory path selects the current owner and the named installed revision (sha256 matches the file on disk).
- `MEM-001-NEG`: an OKE route is refused and an unknown owner is refused; neither is admitted.
