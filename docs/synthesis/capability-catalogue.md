# Capability Catalogue — every capability an agent can be granted, and what is missing

**Written 2026-09-23 (measured, not inherited).** This is the *grantable* view of the estate's
capability surface, for a builder that assembles agents — corporate and personal — against a
single catalogue. It merges the five disjoint inventories that already exist on disk into one
table, and it is the prerequisite the consolidation needs: **before we build a "grant any
capability" interface, we enumerate the capabilities.**

It is the companion to `2026-09-20-full-capability-map.md`. The map answers *"what exists,
categorised by where it runs."* This catalogue answers *"what can an agent be granted, from
which source, and where are the holes."* The map is an inventory; this is the order surface.

## State vocabulary (same as the map, applied per-row)

| State | Means |
|---|---|
| **live** | running, wired, observed |
| **wired** | connected to something that runs; will fire |
| **built** | exists, tested, not connected to anything that runs |
| **built-elsewhere** | exists per its own docs/ticket, but **not present in this checkout** — verify before granting |
| **missing** | not found anywhere; a capability a 2100-agent brain plausibly needs that the estate has not built |

---

## 0. How to read the Class column

Every capability gets exactly one class, so a builder can grant along an axis a client
understands:

- **perceive** — the agent senses: vision, hearing, reading.
- **act** — the agent does: run, type, click, control.
- **surface** — the agent reaches a person through a channel.
- **memory** — the agent remembers.
- **compute** — the agent chooses where it runs.
- **safety** — the agent is constrained and audited.
- **make** — the agent produces media (image/voice/video).

---

## 1. Perceive (the eyes)

| Capability | What it does | Source | State |
|---|---|---|---|
| Vision / screenshot | read the screen, screenshot + OCR + coordinates | `hermes-agent/tools/vision_tools.py`, `computer_use/` (8 files incl. `vision_routing.py`, `cua_backend.py`) | built |
| Camera / computer-use | drive a real desktop via computer-use agent (`cua_backend`) | `hermes-agent/tools/computer_use/` | built |
| Browser (see + act) | 6 browser tools + CamouFox stealth + CDP | `hermes-agent/tools/browser_tool.py`, `browser_cdp_tool.py`, `browser_camofox.py`, `browser_supervisor.py`, `browser_use_cli.py`, `browser_dialog_tool.py` | built |
| Voice intake / transcription | speech → text (Whisper etc.) | `hermes-agent/tools/transcription_tools.py` | built |
| Wake-word | on-device wake detection (`hey_hermes.onnx` + tflite) | `hermes-agent/tools/wake_word.py`, `wakewords/` | built |
| Biometric speaker verification | refuse a cold/hoarse/imposter voice | `mums-concierge` (voice gate) | **built-elsewhere** |
| Document read | Feishu docs/drive, Microsoft Graph, file read | `hermes-agent/tools/feishu_doc_tool.py`, `feishu_drive_tool.py`, `microsoft_graph_client.py`, `file_tools.py` | built |
| Web search | X search, open web tools, SERP | `hermes-agent/tools/web_tools.py`, `x_search_tool.py` | built |

---

## 2. Act (the hands)

| Capability | What it does | Source | State |
|---|---|---|---|
| Code execution | run code in guarded environments | `hermes-agent/tools/code_execution_tool.py` | built |
| Terminal / shell | shell with heredoc, hints, output limits | `hermes-agent/tools/terminal_tool.py`, `shell_heredoc.py`, `terminal_hints.py`, `tool_output_limits.py` | built |
| File operations | read/write/move files, working-diff | `hermes-agent/tools/file_operations.py`, `working_diff.py`, `patch_parser.py` | built |
| OS input injection | **type/clicks at the OS level** — macOS Quartz + Windows SendInput | `sovereign/sentinel/src/input/macos.rs` (184), `windows.rs` (151), `keys.rs` (136) | built |
| GUI automation | screenshot → intent → coordinates → injected input | `sovereign/vision_brain/` (planner + Anthropic/local backends) | built |
| Browser operator (real profile) | Playwright against Nunn's *own* Chrome, vision click + screenshot receipt | `mums-concierge/browser_operator.py` | **built-elsewhere** |
| Cron / scheduling | scheduled jobs | `hermes-agent/tools/cronjob_tools.py` | built |
| Kanban / todos | task boards, todo lists | `hermes-agent/tools/kanban_tools.py`, `todo_tool.py` | built |
| Delegation / sub-agents | delegate, subagent worktrees, async delegation | `hermes-agent/tools/delegate_tool.py`, `async_delegation.py`, `subagent_worktree.py` | built |
| Smart-home control | Home Assistant | `hermes-agent/tools/homeassistant_tool.py` | built |
| Project / workspace | project_tools, apply-layout, focus-pane | `hermes-agent/tools/project_tools.py`, `apply_layout_tool.py`, `focus_pane_tool.py` | built |

---

## 3. Surface (the reach — where agents meet people)

| Capability | What it does | Source | State |
|---|---|---|---|
| Voice out (TTS) | text → speech, streaming, NuTTS synth | `hermes-agent/tools/tts_tool.py`, `tts_streaming.py`, `tts_text_normalize.py`, `neutts_synth.py` | built |
| Voice mode | full duplex voice session | `hermes-agent/tools/voice_mode.py` | built |
| Discord | Discord bot channel | `hermes-agent/tools/discord_tool.py` | built |
| Feishu | Feishu docs + drive | `hermes-agent/tools/feishu_doc_tool.py`, `feishu_drive_tool.py` | built |
| Microsoft Graph | email/calendar/files via Graph | `hermes-agent/tools/microsoft_graph_client.py`, `microsoft_graph_auth.py` | built |
| Send message | generic send/announce | `hermes-agent/tools/send_message_tool.py`, `react_to_message_tool.py` | built |
| X (Twitter) | X search + post | `hermes-agent/tools/x_search_tool.py` | built |
| SMS fan-out + DTMF (OOB approval) | Twilio SMS + phone DTMF confirmation | `sovereign/concierge/oob.py`, `sentinel/src/approval.rs` | built |
| Twilio / WhatsApp webhook | voice/webhook entry for a personal agent | `mums-concierge/voice_endpoints.py`, `request_auth.py` | **built-elsewhere** |
| Telegram | gateway exists; operator shell | `idp/platform/otto-gateway`, `hermes-operator`, `idp/platform/jit` | built |
| **Email (first-class)** | send/read/triage as a *tool* (not via Graph) | — | **missing** |
| **Calendar / scheduling** | first-class calendar tool | — | **missing** |
| **SMS / phone (grantable)** | SMS as a grantable tool (exists only inside Concierge) | — | **missing** |
| **Slack / Teams** | corporate chat | — | **missing** |
| **Notion / Linear / Jira** | corporate work + knowledge | — | **missing** |

---

## 4. Memory (the brain's persistence)

| Capability | What it does | Source | State |
|---|---|---|---|
| Memory provider(s) | memory_tool + provider system (40+ tests) | `hermes-agent/tools/memory_tool.py`, `plugins/memory/` | built |
| estate_memory MCP | `remember` / `recall`, one memory for every agent | `idp/mcp/plugins/estate_memory.py` | built |
| growmos knowledge graph | cross-repo typed memory (entities/relations/provenance) | `estate-graph/`, per-repo `.growmos/` | **live** |
| hermes memory subsystem | 98 memory-related files | `hermes-agent/` | built |
| hermes-v2 memory | architect's own store | `hermes-v2/` | built |
| decision log / prompt ledger | shared research trail, one close-per-prompt | `crew/`, `claude-guards/prompt-ledger.py`, `decision-log.py` | **live** |

> **Founder decision needed (open):** four memory systems exist (estate_memory MCP, hermes,
> growmos, hermes-v2). Does the builder expose "pick a memory backend" as a *grantable choice*
> per agent, or fold them into **one** shared brain? This catalogue lists all four until that is
> decided — it is the single biggest "one of each layer" violation in the capability surface
> (AGENTS.md law 6).

---

## 5. Compute (where the agent runs)

| Capability | What it does | Source | State |
|---|---|---|---|
| 12 execution arenas | local, docker, modal, managed_modal, daytona, vercel_sandbox, singularity, ssh, base, file_sync, modal_utils | `hermes-agent/tools/environments/` (12 files) | built |
| kronos rings 0–4 | Firecracker VM, Wasm fuel, eBPF, vsock+Vault, SQLite ledger | `kronos/crates/ring{0..4}-*` | built (Linux/K8s only) |
| devcontainer / systemd-run / vCluster / k3d / colima / gVisor | additional sandboxes | `agent-guard/sandbox/`, `idp/platform/sandbox/`, `idp/platform/gvisor-runtime/` | mixed; colima **live** |

> The map's verdict stands: 4 sandbox systems (12 backends + kronos + devcontainer + vcluster)
> should be **1 entry rule**, not a client choice. The builder exposes *one* "where does it run"
> grant; the arena is resolved underneath.

---

## 6. Safety (what makes it safe to grant anything at all)

| Capability | What it does | Source | State |
|---|---|---|---|
| Guardian 3-tier engine | autonomous / human-confirm / founder-gate risk tiers | `mums-concierge/guardian_engine.py` (30 tests) | **built-elsewhere** |
| Budget + rate gates | daily $, per-minute rate, approval thresholds | `sovereign/sentinel/src/guardrails/mod.rs` | built |
| Semantic boundary | intent vs allowed-action boundary | `sentinel/src/guardrails/mod.rs` L23-31 | built |
| Out-of-band approval | human confirms from phone (SMS/DTMF) | `sentinel/src/approval.rs`, `concierge/oob.py` | built |
| Hash-chained audit ledger | SQLite WAL + tamper verification | `sentinel/src/ledger/` | built |
| Credential vault | Keychain / Credential Manager | `sentinel/src/` | built |
| Aevum | Ed25519 + ML-DSA-65, COSE_Sign1, RFC 3161, hash-chained | `idp/platform/observability/aevum.yaml`, `.aevum/local.jsonl` | built (ledger empty) |
| JIT broker | one named write at a time, founder approves by phone | `idp/platform/jit/` | built |
| Guard / policy | 5 implementations (see map) | `idp/bin/*-gate`, `claude-guards/` | **live** |
| Threat detection / policy | threat_patterns, Tirith, path/url/website policy | `hermes-agent/tools/threat_patterns.py`, `tirith_security.py`, `path_security.py`, `url_safety.py`, `website_policy.py` | built |
| Approval / write gate | approval, slash-confirm, write-approval | `hermes-agent/tools/approval.py`, `slash_confirm.py`, `write_approval.py` | built |
| Multi-tenant isolation | tenant-scoped subjects `tasks.<tenant>.<slug>` | `agent-foundry/af/bus.py`, ORDER.md §4 | built (not operating) |

---

## 7. Make (the media the agent produces)

| Capability | What it does | Source | State |
|---|---|---|---|
| Image generation | text → image | `hermes-agent/tools/image_generation_tool.py` | built |
| Video generation | text → video (flux3, xai video) | `hermes-agent/tools/flux3_video_tool.py`, `xai_video_tools.py`, `video_generation_tool.py`, `xai_http.py` | built |
| TTS synthesis | NuTTS + streaming voice | `hermes-agent/tools/neutts_synth.py`, `tts_streaming.py` | built |

---

## 8. The doors (how a builder reaches all of the above)

| Door | Tools exposed | Source | State |
|---|---|---|---|
| estate_mcp (15 plugins) | `estate_executor`, `estate_memory`, `estate_state`, `estate_twin`, `estate_holmes`, `estate_inventory`, `estate_sessions`, `estate_guards`, `estate_simulate`, `voice`, `jev`, `workload_state`, `workload_logs`, `deploy_journeys` | `idp/mcp/plugins/` | built |
| LiteLLM router | one router key per identity (the model door) | `idp/platform/llm/` | **live** |
| 30 skill domains | research, data-science, devops, mlops, frontend/creative, media, email, social, smart-home, apple, github, security, yuanbao, + meta-skills (skill-creator, mcp-builder, safe-commit-protocol, supervised-process-contract) | `hermes-config/skills/` | built |
| agent-foundry | order → decompose → manifest → run (8 nodes: army, nodes, worker, bus, meter, order, serve, db) | `agent-foundry/af/` | built |

---

## 9. The capability classes, counted

| Class | Rows | Mostly | Biggest hole |
|---|---|---|---|
| perceive | 8 | built | biometric speaker-verify is **built-elsewhere** |
| act | 12 | built | browser-operator (real profile) is **built-elsewhere** |
| surface | 15 | built, but… | **5 missing**: email, calendar, SMS, Slack/Teams, Notion/Linear/Jira |
| memory | 6 | live/built | **4 systems where law 6 wants 1** — founder decision open |
| compute | 3 | built | 4 sandbox systems where the map wants 1 entry rule |
| safety | 12 | live/built | Aevum ledger empty; multi-tenant isolation built-not-operating |
| make | 3 | built | nothing missing |
| doors | 4 | live/built | agent-foundry built, never wired to the live bus |

---

## 10. The honest verdict

1. **The estate already has a world-class capability surface.** ~140 Hermes tools, the full
   `sovereign/` personal-agent scaffold (OS input injection, OOB approval, budget/audit), the
   `mums-concierge` consent stack, 30 skills, 12 arenas, 4 memory systems, 15 MCP doors. The
   "need more" is mostly **not** more capabilities.

2. **The real gap is grantability.** None of the ~190 capabilities above register as a typed,
   grantable row in one builder. `agent-foundry` exposes 8 nodes. The catalogue above is the
   missing registry — each row is a capability a client could be granted, and today every one of
   them is granted only by hand-wiring code.

3. **The genuine "need more"** — the rows a 2100-agent brain demands that the estate has not
   built — is a short, honest list: **first-class email, calendar, SMS, Slack/Teams,
   Notion/Linear/Jira.** Five integrations. Everything else the estate already has, scattered.

4. **Two things need a founder decision, and block the builder:**
   - **Memory**: one shared brain, or pick-a-backend per agent? (4 systems today.)
   - **`mums-concierge` is not in this checkout.** Its capabilities (biometric voice gate, browser
     operator, guardian engine, Twilio/WhatsApp) are judged **built-elsewhere**. Before the
     builder can grant them, either fetch the repo into the estate root or re-mark them
     "verify before grant."

---

## 11. Next step, offered

Wire the catalogue as the source of truth for a grant model: add a `capabilities: [...]` field
to the `agent-foundry` order object, where each entry is `{ name, class, scope, mode }` and
`name` resolves against the rows above. The builder then grants *any* row to *any* agent,
corporate or personal, through one schema'd, audited operation — and the catalogue is what makes
"grant any capability" a typed fact instead of prose.

This document is read-only evidence. Confirm and I'll turn it into the grant-model ADR + the
foundry order-schema change.
