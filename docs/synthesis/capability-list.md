# The Complete Capability List — every capability the estate can grant, one row each

**Written 2026-09-23. The flat, exhaustive ledger — all repos, not idp alone, not grouped**
**into branches.** This is the raw data behind the Factory Inventory (doc 1). Where the Inventory
groups capabilities into 11 branches for the architect, *this* list is the **full enumeration**:
one line per capability, with its class, its source repo, and its state. Nothing is summarised
away.

**Classes:** perceive · act · surface · memory · compute · safety · make
**States:** current · incubating · deprecated · built · built-elsewhere · gap

---

## A. Hermes-agent tools — 126 capabilities (the largest single surface)

Source: `hermes-agent/tools/*.py`. State: `deprecated` (the repo is archived; the live tree is
hermes-v2), but every tool here is a *capability the estate has already built* — it remains
grantable the moment a branch chooses to carry it forward.

| # | Capability | Class | State |
|---|---|---|---|
| 1 | annotate_preview_tool | perceive | deprecated |
| 2 | ansi_strip | act | deprecated |
| 3 | apply_layout_tool | act | deprecated |
| 4 | approval | safety | deprecated |
| 5 | async_delegation | act | deprecated |
| 6 | audio_container | surface | deprecated |
| 7 | binary_extensions | act | deprecated |
| 8 | blueprints | act | deprecated |
| 9 | bot_mode_probe | act | deprecated |
| 10 | browser_camofox | act | deprecated |
| 11 | browser_camofox_state | act | deprecated |
| 12 | browser_cdp_tool | act | deprecated |
| 13 | browser_dialog_tool | act | deprecated |
| 14 | browser_supervisor | act | deprecated |
| 15 | browser_tool | act | deprecated |
| 16 | browser_use_cli | act | deprecated |
| 17 | budget_config | safety | deprecated |
| 18 | checkpoint_manager | memory | deprecated |
| 19 | clarify_gateway | perceive | deprecated |
| 20 | clarify_tool | perceive | deprecated |
| 21 | close_preview_tool | act | deprecated |
| 22 | close_terminal_tool | act | deprecated |
| 23 | code_execution_tool | act | deprecated |
| 24 | computer_use_tool | act | deprecated |
| 25 | credential_files | safety | deprecated |
| 26 | cronjob_tools | act | deprecated |
| 27 | daemon_pool | compute | deprecated |
| 28 | debug_helpers | act | deprecated |
| 29 | delegate_tool | act | deprecated |
| 30 | delegation_live_log | act | deprecated |
| 31 | delegation_output_schema | act | deprecated |
| 32 | desktop_ui | surface | deprecated |
| 33 | discord_tool | surface | deprecated |
| 34 | drive_preview_tool | perceive | deprecated |
| 35 | env_passthrough | compute | deprecated |
| 36 | env_probe | compute | deprecated |
| 37 | fal_common | make | deprecated |
| 38 | feishu_doc_tool | surface | deprecated |
| 39 | feishu_drive_tool | surface | deprecated |
| 40 | file_operations | act | deprecated |
| 41 | file_state | act | deprecated |
| 42 | file_tools | act | deprecated |
| 43 | flux3_video_tool | make | deprecated |
| 44 | focus_pane_tool | act | deprecated |
| 45 | fuzzy_match | perceive | deprecated |
| 46 | homeassistant_tool | act | deprecated |
| 47 | hook_output_spill | act | deprecated |
| 48 | image_generation_tool | make | deprecated |
| 49 | image_source | perceive | deprecated |
| 50 | interrupt | safety | deprecated |
| 51 | kanban_tools | act | deprecated |
| 52 | lazy_deps | compute | deprecated |
| 53 | managed_tool_gateway | act | deprecated |
| 54 | mcp_dashboard_oauth | safety | deprecated |
| 55 | mcp_oauth | safety | deprecated |
| 56 | mcp_oauth_manager | safety | deprecated |
| 57 | mcp_schema_cache | act | deprecated |
| 58 | mcp_stdio_watchdog | compute | deprecated |
| 59 | mcp_tool | act | deprecated |
| 60 | memory_tool | memory | deprecated |
| 61 | microsoft_graph_auth | safety | deprecated |
| 62 | microsoft_graph_client | surface | deprecated |
| 63 | neutts_synth | make | deprecated |
| 64 | open_preview_tool | act | deprecated |
| 65 | openrouter_client | compute | deprecated |
| 66 | osv_check | safety | deprecated |
| 67 | patch_parser | act | deprecated |
| 68 | path_security | safety | deprecated |
| 69 | plugin_guard | safety | deprecated |
| 70 | process_registry | act | deprecated |
| 71 | project_tools | act | deprecated |
| 72 | react_to_message_tool | surface | deprecated |
| 73 | read_extract | perceive | deprecated |
| 74 | read_preview_tool | perceive | deprecated |
| 75 | read_terminal_tool | perceive | deprecated |
| 76 | read_window_tool | perceive | deprecated |
| 77 | registry | act | deprecated |
| 78 | schema_sanitizer | safety | deprecated |
| 79 | self_repo_guard | safety | deprecated |
| 80 | send_message_tool | surface | deprecated |
| 81 | session_search_tool | memory | deprecated |
| 82 | setup_mcp_tool | act | deprecated |
| 83 | shell_heredoc | act | deprecated |
| 84 | skill_ledger | memory | deprecated |
| 85 | skill_linter | safety | deprecated |
| 86 | skill_manager_tool | act | deprecated |
| 87 | skill_provenance | memory | deprecated |
| 88 | skill_usage | memory | deprecated |
| 89 | skillevaluator_scan | safety | deprecated |
| 90 | skills_ast_audit | safety | deprecated |
| 91 | skills_guard | safety | deprecated |
| 92 | skills_hub | act | deprecated |
| 93 | skills_sync | act | deprecated |
| 94 | skills_sync_client | act | deprecated |
| 95 | skills_tool | act | deprecated |
| 96 | slash_confirm | safety | deprecated |
| 97 | spill_safety | safety | deprecated |
| 98 | subagent_worktree | act | deprecated |
| 99 | terminal_hints | act | deprecated |
| 100 | terminal_tool | act | deprecated |
| 101 | thread_context | memory | deprecated |
| 102 | threat_patterns | safety | deprecated |
| 103 | tirith_security | safety | deprecated |
| 104 | todo_tool | act | deprecated |
| 105 | tool_backend_helpers | act | deprecated |
| 106 | tool_output_limits | act | deprecated |
| 107 | tool_result_storage | memory | deprecated |
| 108 | tool_search | act | deprecated |
| 109 | tour_tool | act | deprecated |
| 110 | transcription_tools | perceive | deprecated |
| 111 | tts_streaming | make | deprecated |
| 112 | tts_text_normalize | make | deprecated |
| 113 | tts_tool | make | deprecated |
| 114 | url_safety | safety | deprecated |
| 115 | video_generation_tool | make | deprecated |
| 116 | vision_tools | perceive | deprecated |
| 117 | voice_mode | surface | deprecated |
| 118 | wake_word | perceive | deprecated |
| 119 | web_tools | act | deprecated |
| 120 | website_policy | safety | deprecated |
| 121 | working_diff | act | deprecated |
| 122 | write_approval | safety | deprecated |
| 123 | x_search_tool | perceive | deprecated |
| 124 | xai_http | make | deprecated |
| 125 | xai_video_tools | make | deprecated |
| 126 | yuanbao_tools | surface | deprecated |

---

## B. Hermes-config skills — 30 capabilities

Source: `hermes-config/skills/`. State: `current` (the live skill registry).

| # | Capability | Class | State |
|---|---|---|---|
| 127 | apple | surface | current |
| 128 | autonomous-ai-agents | act | current |
| 129 | canvas-design | make | current |
| 130 | creative | make | current |
| 131 | crew | act | current |
| 132 | data-science | act | current |
| 133 | devops | act | current |
| 134 | dogfood | act | current |
| 135 | dropped-ball-prevention | safety | current |
| 136 | email | surface | current |
| 137 | estate-ground-truth-probe | perceive | current |
| 138 | external-audience-writing | make | current |
| 139 | frontend-design | make | current |
| 140 | github | act | current |
| 141 | lux-proof-driven-development | safety | current |
| 142 | mcp-builder | act | current |
| 143 | media | make | current |
| 144 | mlops | act | current |
| 145 | note-taking | memory | current |
| 146 | productivity | act | current |
| 147 | research | perceive | current |
| 148 | safe-commit-protocol | safety | current |
| 149 | security-best-practices | safety | current |
| 150 | skill-creator | act | current |
| 151 | smart-home | act | current |
| 152 | social-media | surface | current |
| 153 | software-development | act | current |
| 154 | supervised-process-contract | safety | current |
| 155 | task-resilience | safety | current |
| 156 | yuanbao | surface | current |

---

## C. MCP plugins — 15 estate doors

Source: `idp/mcp/plugins/*.py`. State: `current` (built and served).

| # | Capability | Class | State |
|---|---|---|---|
| 157 | estate_executor | act | current |
| 158 | estate_simulate | act | current |
| 159 | estate_guards | safety | current |
| 160 | estate_memory | memory | current |
| 161 | estate_sessions | memory | current |
| 162 | estate_holmes | perceive | current |
| 163 | estate_inventory | perceive | current |
| 164 | estate_state | perceive | current |
| 165 | estate_twin | perceive | current |
| 166 | workload_logs | perceive | current |
| 167 | workload_state | perceive | current |
| 168 | voice | surface | current |
| 169 | jev | perceive | current |
| 170 | deploy_journeys | act | current |
| 171 | __init__ | — | (package) |

---

## D. Sovereign — the personal-agent scaffold

Source: `sovereign/`. State: `current` (Rust sentinel + Python vision_brain).

| # | Capability | Class | State |
|---|---|---|---|
| 172 | OS input injection — macOS Quartz | act | current |
| 173 | OS input injection — Windows SendInput | act | current |
| 174 | key-combo parser | act | current |
| 175 | vision_brain planner (screenshot→intent) | perceive | current |
| 176 | vision_brain Anthropic backend | perceive | current |
| 177 | OOB phone approval (SMS + DTMF) | safety | current |
| 178 | semantic boundary enforcement | safety | current |
| 179 | daily budget gate | safety | current |
| 180 | per-minute rate limit | safety | current |
| 181 | hash-chained ledger | memory | current |
| 182 | tamper verification | safety | current |
| 183 | SQLite WAL store | memory | current |
| 184 | credential vault (Keychain/CredMgr) | safety | current |
| 185 | approval threshold eval | safety | current |

---

## E. agent-foundry — the seed expression (8 nodes + order)

Source: `agent-foundry/af/`. State: `current`.

| # | Capability | Class | State |
|---|---|---|---|
| 186 | order (goal → N bots) | act | current |
| 187 | army (assemble DAG) | act | current |
| 188 | nodes (DOM-strip, extract, math-check, alert) | act | current |
| 189 | worker (poison-pill, NAK, dead-letter, ack) | act | current |
| 190 | bus (tenant-scoped NATS subjects) | compute | current |
| 191 | meter (task_executions metering) | memory | current |
| 192 | serve (in-cluster seam) | compute | current |
| 193 | db (tenants + task_executions rows) | memory | current |

---

## F. Execution arenas — 12 compute environments

Source: `hermes-agent/tools/environments/`. State: `current` (fold to 1 entry rule).

| # | Capability | Class | State |
|---|---|---|---|
| 194 | local arena | compute | current |
| 195 | docker arena | compute | current |
| 196 | modal arena | compute | current |
| 197 | managed_modal arena | compute | current |
| 198 | daytona arena | compute | current |
| 199 | vercel_sandbox arena | compute | current |
| 200 | singularity arena | compute | current |
| 201 | ssh arena | compute | current |
| 202 | base arena | compute | current |
| 203 | file_sync arena | compute | current |
| 204 | modal_utils arena | compute | current |
| 205 | (environments __init__) | — | (package) |

---

## G. Security & isolation kernels

Source: `kronos/`, `ironcage/`, `agent-guard/`. State: `incubating` (Linux/K8s only).

| # | Capability | Class | State |
|---|---|---|---|
| 206 | kronos ring0 — Firecracker/KVM | safety | incubating |
| 207 | kronos ring1 — Wasmtime/WASI fuel | safety | incubating |
| 208 | kronos ring2 — eBPF/Tetragon | safety | incubating |
| 209 | kronos ring3 — vsock + Vault egress | safety | incubating |
| 210 | kronos ring4 — SQLite+SHA-2 ledger | safety | incubating |
| 211 | kronos kernel — orchestrator/budget | safety | incubating |
| 212 | ironcage verifier | safety | incubating |
| 213 | ironcage inference | compute | incubating |
| 214 | ironcage ledger | memory | incubating |
| 215 | ironcage api | surface | incubating |
| 216 | agent-guard containment (reap/lint/probe) | safety | current |
| 217 | gVisor runtime + cells | safety | current |
| 218 | devcontainer sandbox | safety | current |
| 219 | colima container VM | compute | current |

---

## H. Concierge & personal-agent capabilities (built-elsewhere)

Source: `mums-concierge/` (not in this checkout). State: `built-elsewhere`.

| # | Capability | Class | State |
|---|---|---|---|
| 220 | voice webhook (Twilio/WhatsApp + Whisper) | surface | built-elsewhere |
| 221 | request_auth (HMAC) | safety | built-elsewhere |
| 222 | guardian_engine (3-tier risk) | safety | built-elsewhere |
| 223 | browser_operator (real Chrome profile) | act | built-elsewhere |
| 224 | biometric speaker verification | safety | built-elsewhere |
| 225 | cost gate | safety | built-elsewhere |
| 226 | currency gate (GBP→config) | safety | built-elsewhere |
| 227 | kill gate (/kill persists) | safety | built-elsewhere |

---

## I. The gaps — capabilities no branch produces yet

Measured, not speculative. These complete the list by naming what is **absent**.

| # | Capability | Class | State |
|---|---|---|---|
| 228 | first-class email (send/read/triage) | surface | gap |
| 229 | calendar / scheduling | surface | gap |
| 230 | SMS / phone (grantable) | surface | gap |
| 231 | Slack / Teams | surface | gap |
| 232 | Notion / Linear / Jira | surface | gap |
| 233 | payments / billing rail | act | gap (rail 503) |
| 234 | self-description schema (capability.yaml across repos) | safety | gap (only agent-foundry has it) |
| 235 | grant operation (capabilities: []) | act | gap |
| 236 | multi-tenant isolation (operating) | safety | gap (specced, not running) |

---

## J. Totals

| Group | Count |
|---|---|
| A — Hermes tools | 126 |
| B — Skills | 30 |
| C — MCP plugins | 15 |
| D — Sovereign | 14 |
| E — agent-foundry | 8 |
| F — Arenas | 12 |
| G — Security/isolation | 14 |
| H — Concierge (built-elsewhere) | 8 |
| I — Gaps | 9 |
| **Total capabilities enumerated** | **236** |

---

## The one honest caveat

This list is exhaustive **to the capability-name level** of the repos on this checkout. It is not
yet exhaustive to the *leaf* (every tool has sub-methods; every skill has sub-steps; every MCP
plugin exposes multiple functions — `estate_executor` alone exposes 13 verbs). The leaf-level
enumeration is exactly what the `capability.yaml` self-description schema (Factory Contract,
doc 3) exists to produce: once every repo declares its outputs, this list becomes a machine-
emitted fact at any depth, instead of a hand-completed table. Until then, **236 named
capabilities is the measured floor, not the ceiling.**

---

*This is the complete capability list. It is the raw data for the consultant — pair it with the
Factory Inventory (grouping), the Programme (strategy), and the Contract (schema), and it becomes
the full brief.*
