# ESTATE MAP — must-read before any agent session

**Canonical path:** `~/Documents/code/idp/docs/ESTATE_MAP.md`
**Served at:** `http://127.0.0.1:4300/map` (estate-bus, loopback)
**Rule:** if a fact here disagrees with reality, fix this file in the same lane that discovered it.

## 1. What the estate is

A deterministic control plane above replaceable model workers. Models (Gemini/AI Studio, Claude,
Codex, DeepSeek, MiniMax/Z.ai) execute; the estate owns state, authority, gates and receipts.
A model is never the source of truth.

## 2. Topology

```
agents (DSH / Codex / Claude / AI Studio)
        │  read at boot
        ▼
  AGENTS.md  ──►  SESSION_PREFLIGHT.md  ──►  estate-bus :4300
        │                                        │
        │                                        ├─ /preflight  live state
        │                                        ├─ /map        this document
        │                                        ├─ /state      disk/repos/lanes
        │                                        └─ /artifacts  landed artifacts
        ▼
  pennyd :4200 (router)  ──►  providers (groq, zai, deepseek, openrouter, gemini, minimax)
        │
        ▼
  repos: idp · argon · argon-sync   ──►  lane/* branches ──► Greenlane
        │
        ▼
  surfaces: :3000 (#projector/#omega) · :4090 control 302 · :4101 ICP · :3080 DSH
```

## 3. Ports (verified 2026-11-12)

| Port | Process | Role |
|---:|---|---|
| 3000 | `vite` in `~/Documents/code/argon` | Founder surface: `#projector`, `#omega`, fleet |
| 3080 | DSH standalone | This agent's Web GUI |
| 3081 | `approval-inbox.py` | Approval inbox |
| 4001 | `estate_live_surface_server.py` | AURA live surface / realtime publish |
| 4090 | `omega-codex-live.py` | Control plane; 302 → 3000 (hash preserved) |
| 4101 | `tools/local-switch.mjs` | ICP cockpit + monitor + metrics |
| 4200 | `pennyd` | Model router; OpenAI-compatible `/v1/chat/completions` |
| 4222 / 8222 | nats-server | Event bus / monitoring |
| 4319 | `tsx server.ts` (argon) | Argon backend |
| 8002 | `local_store.py` | Memory store |
| 8080 | `genesis-cockpit.py` | Genesis cockpit |
| 8099 | `otto.ingress` | Telegram ingress (Otto) |
| 8770 | Python service | Estate worker (entrypoint not yet labelled) |
| 8789 | `inboxd-worker` | Inbox daemon |
| 20241 | cloudflared | Tunnel metrics |

## 4. Repositories

| Repo | Path | Purpose | Current |
|---|---|---|---|
| idp | `~/Documents/code/idp` | Platform: governance, Greenlane, memory door, ops | `lane/disk-delete-only` @ 296b50756, dirty 7 |
| argon | `~/Documents/code/argon` | Founder surface, projector, agent console | `lane/genesis-port` @ 8838e85, dirty 8 |
| argon-runtime | `~/.estate/argon` | Live runtime copy (dist, .genesis) | `main` @ da1536c, dirty 155 |
| argon-sync | `~/Documents/code/argon-sync` | Sync/transport lane | present |
| estate-secrets | `~/Documents/code/estate-secrets` | SOPS/age vault | present |

**Never push to `main`/`master` directly.** All work lands on `lane/*`; Greenlane is the only writer.

## 5. Data stores

| Store | Path | Holds |
|---|---|---|
| estate.db | `~/.estate/estate.db` | WWFD memory, step_runs, tickets, policy state |
| memory door | `idp/platform/estate/memory/door.py` | local-first facts; `door.recall/post` |
| ICP DB | `~/.estate/state/icp-cockpit.sqlite` | packets, grants, seals, audit |
| landed ledger | `~/.estate/state/landed_artifacts.jsonl` | artifact → repo/branch/SHA |
| preflight | `~/.estate/state/SESSION_PREFLIGHT.md` | compiled boot state |
| secrets vault | `estate-secrets/secrets/` | sops/age encrypted; mirror `~/.estate/secrets` |

## 6. Agents and their wiring

| Agent | Boot context | Model route | Limits |
|---|---|---|---|
| DSH (this) | `AGENTS.md` + preflight block | `deepseek-flash` via DSH | tool timeout, sandbox |
| Codex | `AGENTS.md`; `~/.codex/config.toml` | `gpt-6.1-sol`, effort high/low | session rollout jsonl |
| Claude | `CLAUDE.md` / project settings | provider | no repo-wide default |
| AI Studio | bundle endpoint only; no disk | Gemini | cannot push to GitHub |
| Otto | `AGENTS.md` + Telegram ingress | pennyd | one poller only |

**Every local agent must read `AGENTS.md` (and therefore the preflight block) before acting.**
A cloud agent must fetch `http://127.0.0.1:4300/preflight` through a tunnel; it cannot read disk.

## 7. Surfaces

| Surface | URL | Truthfulness |
|---|---|---|
| Face & Fleet | `http://127.0.0.1:3000/#projector` | **golden replay of 3 signed INS fixtures** — labelled NOT LIVE STREAM |
| Omega Codex | `http://127.0.0.1:3000/#omega` | live server-backed |
| Control plane | `http://127.0.0.1:4090/` | 302 → 3000, hash preserved |
| ICP cockpit | `http://127.0.0.1:4101/` | live packets/grants/receipts |
| DSH | `http://127.0.0.1:3080` | this session |
| Estate bus | `http://127.0.0.1:4300/` | preflight/map/state/artifacts |

### Tunnel status (2026-11-12)

The named tunnel connector is registered (4 connections). `llm.mumchimp.com` returns 200, so the
path works. `estate-bus.mumchimp.com` has **no DNS record** yet; `cloudflared tunnel route dns`
failed with an authentication error and no API token was found in the secrets store.

Required record (one, proxied):

```
estate-bus.mumchimp.com  CNAME  d77a438e-996e-4eac-9c1b-96b3dc07d9f1.cfargotunnel.com
```

Until then the bus is loopback-only and cloud agents stay blind.

## 8. Laws

1. Ring-0 (`policy.seal.toml`) is immutable to agents; boot asserts its SHA-256.
2. `main` is written only by Greenlane; agents use `lane/*`.
3. A completion claim needs a machine-generated receipt (`bin/estate-receipt`); `[unsupported-report]` locks the session.
4. Disk below 1500 MB halts non-reclaim work; below 2000 MB reclaim wins.
5. At most one poller per Telegram bot (Otto).
6. Secrets never enter a transcript; redact before render.

## 9. Verify (copy-paste)

```bash
df -m /System/Volumes/Data | tail -1
curl -s http://127.0.0.1:4300/health
curl -s http://127.0.0.1:4300/preflight
curl -s http://127.0.0.1:4200/v1/models -H "Authorization: Bearer $PENNYD_KEY" | head -c 200
git -C ~/Documents/code/argon status --short | head
```

## 10. Known drift (fix in lanes, not by hand on main)

- `argon-runtime` is 155 files dirty; it is a runtime, not a source of truth.
- `pennyd` health reports `ok=false`, `chain_break_at=25` — investigate before routing critical work.
- Port 8770 process is unl abelled; assign an owner.
- Cloud agents have no bus access; `4300` is loopback until tunnelled with auth.
