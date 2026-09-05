# Otto capability inventory: every iota, built first

Founder, 2026-09-05: "we need to dig up every single iota of capability even potential not yet
built but more important what is built", "no inch given", "every iota". Records:
`~/.claude/docs/founder/2026-09-05T2224Z-what-else-is-left-all-gates-on-pr-3f4054b0.md`,
`~/.claude/docs/founder/2026-09-05T2238Z-lastly-can-you-ensire-we-aewnot-building-cpbolit-a8454faf.md`.

This file is the one list. It was assembled on 2026-09-05 from four read-only audits, each row
carrying a file receipt a buyer's engineer can open: the `otto/` packages in hermes-v2 (main
17aa95e), the hermes-agent fork that is the Otto container image, the idp platform under
`platform/`, `mcp/` and `backstage/`, and the crew board (crew#717, #768, #773, #770, #758,
#682). Nothing here is quoted from memory.

## How to read a row

| Status | Meaning |
|---|---|
| **LIVE** | On the door's live request path today: Telegram update → `otto/ingress/worker.py` → `otto/boot/pipeline.py::answer_envelope` → reply. Proven by tests and by the door's log. |
| **BUILT** | Code and tests exist on main, but nothing on the live path imports it yet. Wiring is a spec step, not a build. |
| **IN THE IMAGE** | Ships inside the fork (`/app/hermes-agent` in the Otto container). Enabled means the fork's default toolset carries it; the door does not call it until spec step 1 lands. |
| **IN THE IMAGE, KEY NEEDED** | Same, and it stays dark until one credential is minted (R52: one root per provider, code mints the rest). |
| **PLATFORM** | An idp workload, route, secret or page that exists on the cluster and serves Otto. |
| **GRADED** | A crew#717 row with a recorded pass or fail from the 2026-08-31 audits. |
| **POTENTIAL** | Designed on the board, not yet built. |

The spec that moves BUILT and IN THE IMAGE rows to LIVE is `docs/specs/otto-door-hands-and-senses.md`
(main 4177b3a2). Execution claim: crew#768, comment 5555267239. One executor.

## The marketing list, plain English

What Otto is today, and what it becomes the day each spec step lands. Every line maps to rows
below with a receipt.

### Senses

- **Reads every Telegram message on one hardened door**, two bots, webhook self-healed every five minutes, two replicas, never a single point of failure. LIVE. `platform/otto-gateway/deployment.yaml:22`, `registration-reconciler.yaml:258`.
- **Hears voice notes** and transcribes them on the pod, no cloud, eight speech-to-text providers behind one registry (local faster-whisper, Groq, OpenAI, Mistral, xAI, ElevenLabs, DeepInfra). IN THE IMAGE. `hermes-agent/tools/transcription_tools.py:379`. Wired to the door at spec step 3.
- **Speaks back** through eleven text-to-speech providers, the free Edge voice first, ElevenLabs, OpenAI, MiniMax, Gemini and local Piper among the rest. IN THE IMAGE. `hermes-agent/tools/tts_tool.py:780`. Step 3.
- **Sees photos and screenshots** on the router's vision lane. IN THE IMAGE and PLATFORM (`platform/llm/config.yaml` vision row). Step 4.
- **Understands video** clips. IN THE IMAGE, opt-in toolset `video`. `hermes-agent/toolsets.py:140`.
- **Always-on wake word** ("Hey Hermes"), three on-device engines, and a push-to-talk voice mode. IN THE IMAGE. `hermes-agent/tools/wake_word.py:67`, `tools/voice_mode.py:1`.
- **Never learns your voiceprint.** A voice principal is refused by design. BUILT. `otto/surface/identity.py`.
- **Ambient trust class**: what a camera or a passing microphone hears is never an instruction. BUILT. `otto/surface/envelope.py`.

### Hands

- **Runs a terminal, reads and writes files, patches code, searches a tree.** IN THE IMAGE. `hermes-agent/toolsets.py:193, 224`. Step 1 puts these behind the tool gateway.
- **Searches the web and reads any page**, Exa key present. IN THE IMAGE, enabled. `toolsets.py:109`.
- **Drives a headless browser**: navigate, click, type, screenshot, run scripts. IN THE IMAGE. `toolsets.py:205`.
- **Drives a desktop in the background** without stealing the cursor. IN THE IMAGE, KEY NEEDED (cua-driver). `toolsets.py:183`.
- **Generates images** on the router's image lane and through FAL, OpenAI or xAI. IN THE IMAGE and PLATFORM. `toolsets.py:146`, `platform/llm/config.yaml` image row.
- **Generates video**, text-to-video, image-to-video, keyframes, continuation. IN THE IMAGE, KEY NEEDED. `toolsets.py:152, 164`.
- **Writes Python that calls its own tools**, for work no single tool covers. IN THE IMAGE. `toolsets.py:293`.
- **Spawns sub-agents** with their own context, in the background, and collects them. IN THE IMAGE. `hermes-agent/tools/delegate_tool.py:3597`.
- **Schedules itself**: "remind me every hour" becomes a listed, pausable job. IN THE IMAGE. `toolsets.py:217`, `cron/scheduler.py:128`.
- **Ships code**: clone, branch, commit, pull request, review, merge, with a GitHub App token that expires in an hour. PLATFORM and IN THE IMAGE. `platform/hermes-agent/gateway.yaml:100`, skills `github/*`.
- **Delegates coding to other agents**: Claude Code, Codex, OpenCode, Cursor, Gemini, on the founder's Mac over Tailscale. IN THE IMAGE and PLATFORM. `platform/hermes-agent/estate.yaml:6`, `mac-run-key.yaml:10`.
- **Controls a smart home** (Home Assistant, Philips Hue) and **plays music** (Spotify). IN THE IMAGE, KEY NEEDED. `toolsets.py:308, 375`, skill `smart-home/openhue`.
- **Reads and triages email, drafts replies, never sends without asking.** IN THE IMAGE. skills `email/*`, `productivity/google-workspace`.
- **Works documents**: Word, Excel, PowerPoint, PDF, OCR, Notion, Airtable, Obsidian, Box, Google Workspace. IN THE IMAGE. skills `productivity/*`.
- **Eighty-two skills** in all, from arXiv research to Manim videos to weekly reviews, each a vetted playbook the agent reads on demand. IN THE IMAGE. `hermes-agent/skills/`.
- **Writes its own skills** from a proven approach, gated behind a pull request. IN THE IMAGE, enabled. `config.yaml skills.skill_auto_creation_requires_pr: true`.

### Judgment and trust

- **Every tool call passes one gateway**: schema validated, tiered T0 to T3, taint-capped, audited, and the human is asked only for what cannot be undone. LIVE. `otto/gateway/core.py:109`. ADR 0024.
- **Denials are structured, never exceptions**; a refused call says why. LIVE. `otto/gateway/denial.py:14`.
- **Four model lanes, distinct families by construction**: judgment, bulk, verify, deep. A lane that shares a family with its checker refuses to boot. LIVE. `otto/router/config.py:259`.
- **Every claim carries a confidence and a verdict; an unverified claim is rendered with a warning prefix.** LIVE. `otto/router/render.py:15`.
- **Budgets per lane and per task, in dollars, with a hard stop.** LIVE. `otto/router/budget.py:18`; `config.yaml limits.budget_hard_stop: true`.
- **A verification plane with its own credentials**: Ed25519-signed verdicts, single-use nonces, forged or replayed verdicts rejected, a false-success corpus at zero leakage. BUILT. `otto/verify/verifier.py`. crew#768 CP3.
- **Smart approvals**: dangerous commands detected, low-risk ones auto-approved by a second model, a permanent allowlist. IN THE IMAGE, enabled. `hermes-agent/tools/approval.py:3322`.
- **Loop guard**: repeated failing tool calls stop the turn. IN THE IMAGE. `hermes_cli/config_defaults.py:697`.
- **A regression gate on every prompt change**: 41-case core suite plus a 15-item false-success set. BUILT. `otto/router/evals.py`, `otto/evals/gate.py:25`.

### Memory

- **Two-tier memory**: a synchronous fast recall inside the answer deadline, an asynchronous long-term store (Hindsight) written behind. LIVE. `otto/memory/fast_recall.py:77`, `otto/memory/hindsight.py:140`.
- **Hybrid retrieval**: pgvector embeddings (1536 dims) fused with full text by reciprocal rank. BUILT, store deployed. `otto/memory/config.py`, `platform/otto-gateway/memory-store-job.yaml:39`.
- **Provenance on every fact**, tiered, with a taint note on anything sourced from untrusted input. LIVE. `otto/memory/models.py:32`, `fast_recall.py:56`.
- **Hygiene**: time-to-live, dedup, and a cap on how much one run may delete. BUILT. `otto/memory/config.py` hygiene fields.
- **Eight pluggable long-term memory backends** (Hindsight, Honcho, Mem0, OpenViking, ByteRover, Holographic, Supermemory, RetainDB). IN THE IMAGE. `hermes-agent/plugins/memory/`.
- **Recalls its own past conversations** and keeps a user profile. IN THE IMAGE, enabled. `toolsets.py:254`, `config.yaml memory.user_profile_enabled`.
- **Context compaction** at a token threshold, native where the model supports it. IN THE IMAGE. `hermes-agent/agent/native_compaction.py:119`.
- **One conversation thread across turns on the door.** POTENTIAL, spec step 8.

### Reach

- **Telegram**, LIVE. **Agent-to-agent protocol** on port 9900, enabled. `hermes-agent/plugins/platforms/a2a/adapter.py:338`.
- **Twenty more surfaces in the image**, each an adapter with an env-var switch: WhatsApp (Cloud API and Baileys), Slack, Discord, Signal, iMessage (BlueBubbles), email (IMAP/SMTP), SMS (Twilio), Matrix, Mattermost, Microsoft Graph webhooks (Teams, Outlook), generic HMAC webhooks (GitHub, Stripe, Jira), Home Assistant, DingTalk, Feishu, WeCom, Weixin, QQ, Yuanbao, and an OpenAI-compatible HTTP API. IN THE IMAGE. `hermes-agent/gateway/platforms/`, `toolsets.py:516-646`. Order of enablement: spec step 9.
- **The portal**: an Investigate page that asks HolmesGPT the same questions Otto answers on Telegram; founder tiles with live pod state; a one-button parity run. PLATFORM. `backstage/packages/app/src/modules/home/Investigate.tsx:1`, `backstage/templates/founder-actions/otto-parity/template.yaml:1`.
- **Web chat on the portal** (`POST /surface/web`), then Slack, WhatsApp, email, a voice session, glasses. POTENTIAL, spec step 9 and crew#770 H1 to H2.

### Operations

- **Asks the platform about itself** through one MCP server: inventory, state, workload logs, HolmesGPT investigations, read-only SQL, board issues, permanent memory. PLATFORM. `mcp/plugins/*.py`, `mcp/agentgateway.yml:19-101`.
- **Every turn is a trace**: OpenTelemetry to the estate collector, five day-0 metrics (cost per lane, verdicts, budget, taint hits, latency), boot refuses without a collector. LIVE. `otto/obs/core.py:305`. GRADED: 5163 traces on 2026-08-31.
- **A fifteen-minute answer probe on every model lane** and a five-minute webhook reconciler, both emitting metrics. PLATFORM. `answer-probe.yaml:187`, `registration-reconciler.yaml:258`.
- **Replays any task from the event spine alone**, no database needed. BUILT. `otto/spine/replay.py`.
- **Onboards a new service in six steps** with a signed inventory, budgets, catalogue entity and a coverage gate that refuses a dark service. BUILT. `otto/onboard/core.py`.
- **Lives in a fenced namespace**: both-ways default deny, seven named exceptions, quota, one replica always up. PLATFORM. `platform/otto-gateway/network-policy.yaml`, `availability.yaml:3`.
- **Reads its own namespace and nothing else.** GRADED: kube-system secrets refused, 2026-08-31. `platform/hermes-agent/rbac.yaml:13`.
- **Survives the founder's Mac being closed.** PLATFORM: the gateway runs on the cluster, not the laptop (crew#516).
- **A sandbox for the terminal that cannot see a secret.** POTENTIAL, spec step 6.

## Counts, from the tables below

| Source | Rows | LIVE | BUILT | Enabled in image | Key needed |
|---|---|---|---|---|---|
| `otto/` packages | 128 (9 are test harness) | 56 | 62 | | |
| Fork toolsets | 32 base + 27 platform bundles | | | 20 in the default set | 15 |
| Fork skills | 82 | | | 82 | per skill |
| Fork surfaces | 22 adapter files, 21 surfaces | 1 (Telegram) | | 2 (Telegram, A2A) | 19 |
| Platform objects serving Otto | 36 | | | | |
| Board rows crew#717 | 56 | | | | 19 graded, 37 never graded |


---

# A. The `otto/` packages on hermes-v2 main (every function, its test, and whether the live door calls it)

## A.1 Capabilities by package

| Capability | File:Line | Tested | Live Telegram Path |
|---|---|---|---|
| **boot** |
| Answer-envelope pipeline: recall memory, route to model, render claims, store fact | boot/pipeline.py:356 (`answer_envelope`) | tests/boot/test_pipeline.py | yes |
| In-process tool registry assembly (note-taking tool) w/ 12-tool cap enforcement | boot/pipeline.py:264 (`build_registry`), 111 (`_note_handler`) | tests/boot/test_pipeline.py | yes |
| Router construction wired to LiteLLM provider + budget ledger + policy config | boot/pipeline.py:121 (`_router`) | tests/boot/test_pipeline.py | yes |
| `/think` prefix routes to deep (reasoning) lane by explicit operator opt-in | boot/pipeline.py:235 (`route_hint`) | tests/boot/test_pipeline.py, tests/cp5/test_reasoning_lane_ux.py | yes |
| Obs handles boot (metrics/tracing) for the boot component | boot/pipeline.py:278 (`ObsHandles`), 289 (`boot_obs_handles`) | tests/boot/test_pipeline.py | yes |
| Chat-id extraction from native Telegram event | boot/pipeline.py:330 (`extract_chat_id`) | tests/boot/test_pipeline.py | yes |
| Legacy webhook update processing (surface normalization → answer) | boot/pipeline.py:516 (`process_update`) | tests/boot/test_pipeline.py | built, not wired |
| Legacy Telegram delivery (send answer back via Bot API) | boot/pipeline.py:588 (`deliver`) | tests/boot/test_pipeline.py | built, not wired |
| Fail-closed boot config: required bot token (loud refusal if unset) | boot/config.py:31,44 (`read_token`) | tests/boot/test_config.py | built, not wired |
| Fail-closed operator chat-id allowlist (YAML-loaded, required) | boot/config.py:74 (`read_chat_allowlist`) | tests/boot/test_config.py | built, not wired |
| Optional HTTP bind port w/ range validation, default 8080 | boot/config.py:113 (`read_port`) | tests/boot/test_config.py | built, not wired |
| Configurable Telegram API base URL (test seam) | boot/config.py:133 (`read_api_base`) | tests/boot/test_config.py | built, not wired |
| Telegram Bot API HTTP transport (send_message, long-poll) | boot/transport.py | tests/boot/test_app.py | built, not wired |
| Legacy webhook HTTP server (`build_server`) — route since REMOVED per its own docstring | boot/server.py:1 (docstring), only `GET /healthz` served | tests/boot/test_server_routes.py | built, not wired (route removed) |
| `/healthz` liveness endpoint | boot/server.py | tests/boot/test_server_routes.py | built, not wired |
| Presence/long-poll offset tracking for legacy Telegram getUpdates loop | boot/presence.py | tests/boot/test_app.py | built, not wired |
| Legacy process entrypoint wiring config+transport+server | boot/__main__.py, boot/app.py | tests/boot/test_main.py | built, not wired |
| `BootRefused` structured fail-closed error type | boot/errors.py | tests/boot/test_config.py | built, not wired |
| **evals (CP0 harness)** |
| Property-based (non-LLM-judge) scoring of eval items | evals/scoring.py | tests/cp0/test_scoring.py | built, not wired |
| Eval item/report Pydantic models | evals/models.py | tests/cp0/test_models.py | built, not wired |
| Baseline-vs-candidate suite runner | evals/runner.py | tests/cp0/test_runner.py | built, not wired |
| Deterministic sha256-stamped report (wall-clock redacted from hash) | evals/report.py:32 (`REPORT_PATH_ENV_VAR`) | tests/cp0/test_report.py | built, not wired |
| Regression gate: configurable pass/fail thresholds vs. baseline | evals/gate.py:25 (`GATE_CONFIG_ENV_VAR`) | tests/cp0/test_gate.py | built, not wired |
| `otto eval` CLI (run/diff/report) | evals/cli.py | tests/cp0/test_cli.py | built, not wired |
| **gateway (Tool Gateway)** |
| Envelope model + taint-capped `effective_tier` computation | gateway/core.py:30 (`Envelope`), 100 (`_effective_tier`) | tests/cp2/step_defs/test_cp2_gateway_core.py | yes |
| `ToolGateway.call`: schema validate → tier check → human-gate → execute → audit | gateway/core.py:109 (`call`) | tests/cp2/step_defs/test_cp2_gateway_core.py | yes |
| Structured (never-exception) denial responses w/ reasons | gateway/core.py:201 (`_deny`), gateway/denial.py:14 (`DenialReason`), 24 (`Denial`) | tests/cp2/step_defs/test_cp2_gateway_core.py | yes |
| Human-gate protocol hook (approval token) for T3/opted-in T2 tools | gateway/core.py:61 (`HumanGate`), 53 (`ApprovalToken`) | tests/cp2/step_defs/test_cp2_gateway_core.py | yes |
| Tool registry with constitution hard cap (12 tools) | gateway/registry.py:79 (`ToolRegistry`), gateway/errors.py:12 (`ToolCapacityExceeded`) | tests/cp2/step_defs/test_cp2_gateway_core.py | yes |
| Tier enum (T0–T3, ordered) + `ToolSpec` (schema, irreversible flag) | gateway/registry.py:22 (`Tier`), 49 (`ToolSpec`) | tests/cp2/step_defs/test_cp2_gateway_core.py | yes |
| Duplicate-tool / schema-violation registration guards | gateway/errors.py:22,29 | tests/cp2/step_defs/test_cp2_gateway_core.py | yes |
| In-memory audit emitter for every gateway call | gateway/audit.py:21 (`AuditEvent`), 40 (`InMemoryAuditEmitter`) | tests/cp2/step_defs/test_cp2_gateway_core.py | yes |
| Configurable max-tools/taint-ceiling/human-gate-tiers via env | gateway/config.py:43 (`GatewayConfig`) | tests/cp2/step_defs/test_cp2_gateway_core.py | yes (config consumed at registry construction) |
| **ingress (Universal Event Gateway)** |
| Worker: JetStream pull consumer loop dispatching to `_handle` | ingress/worker.py:68 (`Worker`), 130 (`_handle`) | tests/ingress/test_worker_answers.py | yes |
| Worker publishes audit events to spine subjects after answering | ingress/worker.py (uses `otto.spine.subjects`, `Bus`) | tests/ingress/test_worker_answers.py | yes |
| Outbound channel plugin protocol + Telegram/HTTP plugin implementations | ingress/plugins.py:53 (`ChannelPlugin`), 100 (`TelegramPlugin`), 153 (`HttpPlugin`), 189 (`default_plugins`) | tests/ingress/test_routes.py | yes |
| `OutboundNotSupported` structured refusal for unsupported channel replies | ingress/plugins.py:46 | tests/ingress/test_routes.py | yes |
| Per-tenant channel outbound secret resolution from env (`OTTO_CHANNEL_SECRET_*`) | ingress/secrets.py:24 (`SecretNotFound`), 44 (`env_var_name`), 56 (`EnvSecretResolver`) | tests/ingress/test_store_and_secrets.py | yes |
| Channel binding model + token fingerprinting (credential never stored raw) | ingress/store.py:93 (`fingerprint`), 107 (`ChannelBinding`) | tests/ingress/test_store_and_secrets.py | yes |
| SQLite channel-binding store (test/dev backing store) | ingress/store.py:181 (`SqliteChannelBindingStore`) | tests/ingress/test_store_and_secrets.py | yes |
| Postgres channel-binding store (production backing store, `%s`-dialect SQL) | ingress/pg_store.py | tests/ingress/test_store_and_secrets.py (via shared contract) | yes (used by worker via `ChannelBindingStore` protocol at deploy time) |
| Fail-closed DB-not-configured refusal at boot (401s every event otherwise) | ingress/pg_store.py:100 (`DatabaseNotConfigured`) | tests/ingress/test_store_and_secrets.py | yes |
| DSN assembly from env + password-from-file (never Secret-as-env-var) | ingress/pg_store.py:110 (`dsn_from_env`) | tests/ingress/test_store_and_secrets.py | yes |
| Inbound event door (`EventGateway`): verify credential, build `TaskEnvelope`, publish | ingress/gateway.py:84 (`EventGateway`) | tests/ingress/test_gateway.py | built, not wired (strict def: not imported by worker.py) |
| JetStream event publisher (`EventPublisher`/`JetStreamPublisher`) | ingress/publisher.py:25,32 | tests/ingress/test_gateway.py | built, not wired |
| Inbound HTTP server routing by channel path segment | ingress/server.py:30 (`channel_from_path`), 92 (`build_server`) | tests/ingress/test_routes.py, tests/ingress/test_entrypoint.py | built, not wired |
| Process entrypoint wiring gateway+worker+pg store, configurable port | ingress/__main__.py:50 (`PORT_ENV`), 58 (`port_from_env`) | tests/ingress/test_entrypoint.py | built, not wired |
| **memory** |
| Two-tier memory: synchronous fast-recall read path | memory/fast_recall.py:77 (`recall`) | tests/cp4/test_l2_sync_recall.py | yes |
| Fast-recall degrades explicitly when unconfigured (no crash, no memory) | memory/fast_recall.py:59 (`configured`) | tests/cp4/test_cp4_hardening.py | yes |
| Tainted-recall marker on results sourced from untrusted input | memory/fast_recall.py:56 (`TAINT_NOTE`), 67 (`_render`) | tests/cp4/test_cp4_hardening.py | yes |
| libpq env-var presence probe (`PGHOST`/`PGDATABASE`/`PGSERVICE`/`PGURI`) | memory/fast_recall.py:50 (`_LIBPQ_ENV`), 64 | tests/cp4/test_cp4_hardening.py | yes |
| Async "hindsight" write-behind memory client (recall/retain over HTTP) | memory/hindsight.py:140 (`recall`), 171 (`retain`) | tests/boot/test_memory_hindsight.py | yes |
| Timeout-swallowing recall (overrun never blocks the answer) | memory/hindsight.py:120 (`_post`), 96 (`_timeout`) | tests/boot/test_memory_hindsight.py | yes |
| Fact/Provenance models with tier validation | memory/models.py:32 (`Provenance`), 64 (`Fact`), 21 (`ProvenanceError`) | tests/cp4/test_cp4_memory_engine.py | yes |
| Fact storage call from pipeline after answering | boot/pipeline.py:181 (`_store_fact`) | tests/cp4/test_cp4_memory_engine.py | yes |
| LiteLLM-backed embedding provider w/ configurable url/model/timeout/dims | memory/embeddings_litellm.py:142 (`provider_from_env`), 171 (`_build`) | tests/cp4/test_embedding_lane.py | built, not wired (imported by backfill/db, not by pipeline's live recall path) |
| DB URL resolution indirected through a configurable env-var-name field | memory/db.py:28 (`database_url_env` lookup) | tests/cp4/test_cp4_memory_engine.py | built, not wired |
| Reciprocal-rank-fusion + candidate-pool retrieval config | memory/config.py (RRF/top_k/candidate_pool fields) | tests/cp4/test_dangling_reference.py | built, not wired (config object; consumer is embeddings/retrieval, not live sync path) |
| TTL / hygiene batch deletion with max-deletion-fraction safety cap | memory/config.py (`hygiene_max_deletion_fraction`, `default_ttl_days`) | tests/cp4/test_cp4_hardening.py | built, not wired |
| Bulk backfill of facts into hindsight (paged, timeout-bounded) | memory/backfill.py | tests/cp4/test_cp4_memory_engine.py | built, not wired |
| Dangling-embedding-reference detection/repair | memory/config.py + memory/db.py (referenced by) tests/cp4/test_dangling_reference.py | tests/cp4/test_dangling_reference.py | built, not wired |
| **obs** |
| `instrument(component, config)` — fail-closed OTLP boot (LAW 50: no dark boot) | obs/core.py:305 (`instrument`) | tests/cp6obs/step_defs/test_cp6_observability.py | yes |
| `ObsBootError` refusal when no OTLP endpoint configured in otlp mode | obs/core.py:76 | tests/cp6obs/step_defs/test_cp6_observability.py | yes |
| Five day-0 metrics: cost/lane, verdicts, budget consumption, taint hits, task latency | obs/config.py:28 (`MetricNames`) | tests/cp6obs/step_defs/test_cp6_observability.py | yes |
| Task context / trace propagation (ULID + traceparent envelope keys) | obs/core.py:95 (`TaskContext`), obs/config.py:20-21 | tests/cp6obs/step_defs/test_cp6_observability.py | yes |
| ULID-based OTel span/trace ID generator | obs/core.py:139 (`UlidIdGenerator`) | tests/cp6obs/step_defs/test_cp6_observability.py | yes |
| In-memory test-mode exporters (`OTTO_OBS_MODE=test`) | obs/config.py:16-17 (`MODE_TEST`) | tests/cp6obs/step_defs/test_cp6_observability.py | yes |
| Per-metric-name override via `OTTO_OBS_METRIC_<FIELD>` | obs/config.py:34 (`MetricNames.from_env`) | tests/cp6obs/step_defs/test_cp6_observability.py | yes |
| Coverage window / eval-coverage check (used by onboarding gate) | obs/config.py:64 (`coverage_window_seconds`); `obs.coverage.check_coverage` (referenced by onboard/core.py) | tests/onboard/step_defs/test_onboarding.py | built, not wired (onboarding-only consumer) |
| **onboard** |
| `otto onboard <service>` CLI: 6-step admission ticket workflow | onboard/core.py, onboard/cli.py | tests/onboard/step_defs/test_onboarding.py | built, not wired |
| Register tools → sign inventory (Ed25519) → allocate budgets → stamp traces → write Backstage catalog entity → fail-closed coverage gate | onboard/core.py (six-step sequence) | tests/onboard/step_defs/test_onboarding.py | built, not wired |
| Staged `.pending` manifest promotion (nothing half-onboarded) | onboard/manifest.py | tests/onboard/step_defs/test_onboarding.py | built, not wired |
| Backstage catalog entity writer | onboard/catalog.py | tests/onboard/step_defs/test_onboarding.py | built, not wired |
| Manifest directory override via env, default `~/.otto` state dir | onboard/cli.py:29 (`MANIFEST_DIR_ENV`), onboard/core.py:61-64 | tests/onboard/step_defs/test_onboarding.py | built, not wired |
| Structured onboarding errors (fail-closed at each step) | onboard/errors.py | tests/onboard/step_defs/test_onboarding.py | built, not wired |
| **router** |
| Lane-based routing (judgment/bulk/verify/deep) w/ route-table matching | router/core.py:89 (`Router`), router/config.py:199 (`_default_routes`) | tests/cp5/step_defs/test_cp5_network_and_contract.py | yes |
| Distinct-model-family guard (fail-closed if judgment shares family w/ bulk or verify) | router/config.py:259 (`__post_init__`), 46 (`_DEFAULT_MODEL_FAMILIES`) | tests/cp5/step_defs/test_cp5_network_and_contract.py | yes |
| Per-lane daily budget + per-task cost cap ledger | router/budget.py:18 (`BudgetLedger`) | tests/cp5/test_provider_completion_budget.py | yes |
| Bounded retries by failure class (5xx/timeout), egress-denial never retries | router/config.py:133 (`RetryPolicy`) | tests/cp5/step_defs/test_cp5_network_and_contract.py | yes |
| Universal JSON provider-response contract normalization | router/contract.py:215 (`normalise_provider_output`), 106 (`extract_json_object`) | tests/cp5/step_defs/test_cp5_router_structured_outputs.py | yes |
| Confidence-token normalization/spelling tolerance | router/contract.py:37 (`normalise_confidence`) | tests/cp5/test_confidence_spelling.py | yes |
| Claim/ProposedAction structured parsing from provider output | router/contract.py:69 (`Claim`), 80 (`ProposedAction`), 173/195 (`_parse_claims`/`_parse_actions`) | tests/cp5/step_defs/test_cp5_router_structured_outputs.py | yes |
| LiteLLM HTTP provider client + max-tokens cap (8192 default) | router/providers.py:26,43 (`_max_tokens`), `LiteLLMClient` | tests/cp5/test_live_minimax.py | yes |
| Reasoning ("deep"/kimi) lane reachable only via explicit `/think` prefix | boot/pipeline.py:235 (`route_hint`); router/config.py `_DEFAULT_LANE_MODELS["deep"]` | tests/cp5/test_reasoning_lane_ux.py | yes |
| `⚠ unverified:` claim marker — unmarked only when VERIFIED + evidence | router/render.py:9 (`UNVERIFIED_PREFIX`), 15 (`render_claim`) | (no dedicated test file found) | yes |
| ULID generation without third-party dependency | router/ulid.py:1 (`new_ulid`), 20 (`is_ulid`) | (no dedicated test file found) | yes |
| Mechanical (non-model) groundedness check via casefold token overlap | router/grounding.py:1 (`GroundingCheck`), `supports`/`is_grounded` | tests/cp5/test_grounding_casefold.py | built, not wired (not imported by pipeline.py/worker.py; only router/evals.py & router/__init__.py re-export) |
| Router-scoped EvalGate: 41-case core suite, P6 merge-word gate | router/evals.py:1 (`_core_suite`), `EvalGate` | tests/cp5/step_defs/test_cp5_network_and_contract.py | built, not wired |
| In-process eval CLI (`eval diff`/`eval run --suite core`) | router/evals.py (`run_eval_cli`) | (no dedicated test file found) | built, not wired |
| Hot-reloadable versioned-YAML routing policy loader | router/config.py:272 (`from_policy_dict`) | tests/cp5/step_defs/test_cp5_network_and_contract.py | yes (invoked at boot construction time, not per-message) |
| **spine** |
| JetStream bus connect/publish/consume (4 streams: TASKS/AUDIT/VERDICTS/METRICS) | spine/bus.py:51 (`OTTO_NATS_URL` default), `Bus` class | tests/cp1/step_defs/test_cp1_spine_and_measurement.py | yes |
| Subject taxonomy (`otto.*.v1.>`) | spine/subjects.py | tests/cp1/step_defs/test_cp1_spine_and_measurement.py | yes |
| Strict/frozen `TaskEnvelope` w/ two-source taint-cap rule, `canonical_json` | spine/envelope.py (`TaskEnvelope`, `Tier`, `TrustTag`) | tests/cp1/step_defs/test_cp1_spine_and_measurement.py | yes |
| Duplicate-window dedup config for JetStream publishes | spine/bus.py:62 (`OTTO_JETSTREAM_DUPLICATE_WINDOW_SECONDS`, default 7200) | tests/cp1/test_durable_pull_guard.py | yes |
| `otto replay` — pure JetStream reconstruction (no Postgres) | spine/replay.py | tests/cp1/step_defs/test_cp1_spine_and_measurement.py | built, not wired |
| Spine CLI (bus admin/replay entrypoints) | spine/cli.py | tests/cp1/step_defs/test_cp1_spine_and_measurement.py | built, not wired |
| Component lifecycle helpers (start/stop hooks) | spine/lifecycle.py | tests/cp1/step_defs/test_cp1_spine_and_measurement.py | built, not wired |
| Transactional outbox pattern (ADR-0012 D1 ported to asyncpg) | spine/outbox.py:53 (`OTTO_POSTGRES_DSN` default) | tests/cp1/step_defs/test_cp1_spine_and_measurement.py | built, not wired |
| CP1 eval runner/report plumbing (distinct from otto.evals and router.evals) | spine/eval_runner.py | tests/cp1/step_defs/test_cp1_spine_and_measurement.py | built, not wired |
| Signed capability inventory (Ed25519), `OTTO_INVENTORY_KEY_PATH`/`OTTO_STATE_DIR` | spine/inventory.py:109,112 | tests/cp1/test_inventory_signature.py | built, not wired (reused by onboard/core.py) |
| **surface** |
| Neutral `SurfaceEnvelope` normalized from native channel events | surface/envelope.py | tests/cp2b/test_envelope_trust_gate.py, tests/cp2b/step_defs/test_cp2b_surface_contract.py | built, not wired |
| `TrustClass` (OPERATOR/UNTRUSTED/AMBIENT); AMBIENT never instruction-bearing | surface/envelope.py | tests/cp2b/test_envelope_trust_gate.py | built, not wired |
| `SurfaceAdapter` Protocol for channel-native → neutral normalization | surface/adapter.py | tests/cp2b/test_surface_unit.py | built, not wired |
| Capability negotiation with explicit (never silent) degradation | surface/adapter.py, surface/renderer.py | tests/cp2b/step_defs/test_cp2b_surface_contract.py | built, not wired |
| No-voiceprint rule: voice/audio/biometric principal sources always refused | surface/identity.py | tests/cp2b/test_envelope_trust_gate.py | built, not wired |
| Response renderer (neutral → channel-appropriate output) | surface/renderer.py | tests/cp2b/test_surface_unit.py | built, not wired |
| Telegram surface binding (chat-id allowlist → principal) | surface/bindings/telegram.py | tests/cp2b/test_surface_unit.py | built, not wired (module-level import into pipeline.py, used only in legacy process_update/deliver) |
| HTTP surface binding | surface/bindings/http.py | tests/cp2b/test_surface_unit.py | built, not wired |
| **verify (Verification Plane, CP3)** |
| Ed25519-signed verdicts, single-use nonce, claim_hash binding | verify/verifier.py, verify/model.py | tests/cp3/step_defs/test_cp3_verification_plane.py | built, not wired |
| Hard/soft verdict distinction (soft insufficient for T2/T3) | verify/model.py | tests/cp3/step_defs/test_cp3_verification_plane.py | built, not wired |
| Read-only prover ServiceAccounts (write denied by credential itself) | verify/credentials.py | tests/cp3/step_defs/test_cp3_verification_plane.py | built, not wired |
| Deterministic per-claim-type checkers (rerun_tests/artifact_hash/state_read/source_fetch/cross_model) | verify/verifier.py | tests/cp3/step_defs/test_cp3_verification_plane.py | built, not wired |
| Zero-width code point detection/refusal in claims | verify/verifier.py | tests/cp3/test_zero_width_observations.py | built, not wired |
| False-success eval corpus (15 known-bad items, 0% leakage bar) | verify/eval_hook.py | tests/cp3/test_falsification_set.py | built, not wired |
| Verifier signing identity loaded from `OTTO_VERIFIER_KEY_PATH` | verify/identity.py:22 (`DEFAULT_KEY_PATH_ENV`) | tests/cp3/step_defs/test_cp3_verification_plane.py | built, not wired |
| Verdict ledger (append-only record of verification outcomes) | verify/ledger.py | tests/cp3/step_defs/test_cp3_verification_plane.py | built, not wired |
| Verify-plane bus wiring (JetStream verdicts stream) | verify/bus.py | tests/cp3/step_defs/test_cp3_verification_plane.py | built, not wired |
| Structured verifier error taxonomy | verify/errors.py | tests/cp3/step_defs/test_cp3_verification_plane.py | built, not wired |
| **tests (harness capabilities)** |
| BDD step-definition harness (Gherkin-style CP1/CP2/CP2b/CP3/CP5/CP6/onboard/demo scenarios) | tests/cp1/step_defs/, tests/cp2/step_defs/, tests/cp2b/step_defs/, tests/cp3/step_defs/, tests/cp5/step_defs/, tests/cp6obs/step_defs/, tests/onboard/step_defs/, tests/demo/step_defs/ | n/a (is the test suite) | n/a |
| Ephemeral local `nats-server` fixture (binary discovery via `GOBIN`/`GOPATH`) | tests/cp1/conftest.py:60-70 | n/a | n/a |
| Ephemeral local Postgres socket fixture (`OTTO_PG_SOCKET_BASE`) | tests/cp1/conftest.py:241 | n/a | n/a |
| Live-network opt-in gate for real-provider tests (`OTTO_CP5_LIVE=1`) | tests/cp5/conftest.py:44 | tests/cp5/test_live_minimax.py | n/a |
| CP4 test-Postgres bindir override (`OTTO_CP4_TEST_PG_BINDIR`) | tests/cp4/conftest.py:38 | n/a | n/a |
| Pinned-requirements integrity check | tests/integration/test_requirements_pinned.py | n/a | n/a |
| Full-assembly smoke test (imports every package together) | tests/integration/test_smoke_assembly.py | n/a | n/a |
| Manifest-claims-every-file completeness check (demo W3) | tests/demo/test_manifest_claims_every_file.py | n/a | n/a |
| Tenant-required / compute-is-channel-blind cross-cutting tenancy guards | tests/tenancy/test_tenant_is_required.py, tests/tenancy/test_compute_is_channel_blind.py | n/a | n/a |

## A.2 Every environment variable and flag the packages read

| Variable | Default | Where Read |
|---|---|---|
| `OTTO_TELEGRAM_BOT_TOKEN` | none (required, refuses) | boot/config.py:31 |
| `OTTO_BOOT_CONFIG` | none (required, refuses) | boot/config.py:32 |
| `OTTO_BOOT_PORT` | 8080 | boot/config.py:33 |
| `OTTO_BOOT_TELEGRAM_API_BASE` | `https://api.telegram.org` | boot/config.py:34 |
| `OTTO_GATEWAY_MAX_TOOLS` | 12 | gateway/config.py:18,53 |
| `OTTO_GATEWAY_TAINT_CEILING` | `"T1"` | gateway/config.py:19,57 |
| `OTTO_INGRESS_DB_HOST` | none (required) | ingress/pg_store.py:39 |
| `OTTO_INGRESS_DB_PORT` | `"5432"` | ingress/pg_store.py:40,47 |
| `OTTO_INGRESS_DB_NAME` | none (required) | ingress/pg_store.py:41 |
| `OTTO_INGRESS_DB_USER` | none (required) | ingress/pg_store.py:42 |
| `OTTO_INGRESS_DB_PASSWORD_FILE` | none | ingress/pg_store.py:45 |
| `OTTO_CHANNEL_SECRET_<ref>` (dynamic prefix) | none per-key | ingress/secrets.py:44 |
| `OTTO_INGRESS_PORT` | 8080 | ingress/__main__.py:50-51 |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | none (required in otlp mode; boot refuses without it) | obs/config.py:14 |
| `OTTO_OBS_MODE` | `"otlp"` | obs/config.py:15-17,70 |
| `OTTO_OBS_METRIC_COST_BY_LANE` | `"otto.cost.usd"` | obs/config.py:28,40 |
| `OTTO_OBS_METRIC_VERDICTS` | `"otto.verdicts"` | obs/config.py:29,40 |
| `OTTO_OBS_METRIC_BUDGET_CONSUMPTION` | `"otto.budget.consumed"` | obs/config.py:30,40 |
| `OTTO_OBS_METRIC_TAINT_HITS` | `"otto.taint.hits"` | obs/config.py:31,40 |
| `OTTO_OBS_METRIC_TASK_LATENCY` | `"otto.task.latency_ms"` | obs/config.py:32,40 |
| `OTTO_MEMORY_DATABASE_URL_ENV_NAME` | `"OTTO_MEMORY_DATABASE_URL"` | memory/config.py:115 |
| `OTTO_MEMORY_DATABASE_URL` (name indirected via above) | none | memory/db.py:28 |
| `OTTO_MEMORY_EMBEDDING_DIM` | 1536 | memory/config.py:116 |
| `OTTO_MEMORY_RETRIEVAL_TOP_K` | 8 | memory/config.py:117 |
| `OTTO_MEMORY_RETRIEVAL_CANDIDATE_POOL` | 40 | memory/config.py:118 |
| `OTTO_MEMORY_EMBEDDING_DEADLINE_S` | 2.0 | memory/config.py:119 |
| `OTTO_MEMORY_RRF_K` | 60 | memory/config.py:120 |
| `OTTO_MEMORY_DEFAULT_TTL_DAYS` | 90 | memory/config.py:121 |
| `OTTO_MEMORY_HYGIENE_BATCH_SIZE` | 500 | memory/config.py:122 |
| `OTTO_MEMORY_DEDUP_LOOKBACK_DAYS` | 365 | memory/config.py:123 |
| `OTTO_MEMORY_HYGIENE_MAX_DELETION_FRACTION` | 0.2 | memory/config.py:124-126 |
| `OTTO_MEMORY_CONTEXT_BUDGET_TOKENS` | 2000 | memory/config.py:127 |
| `OTTO_MEMORY_CONTEXT_CHARS_PER_TOKEN` | 4.0 | memory/config.py:128 |
| `OTTO_MEMORY_MIGRATIONS_DIR` | `""` | memory/config.py:129 |
| `OTTO_MEMORY_EMBEDDING_URL` | none (unset → no embedding provider, lexical-only fallback) | memory/embeddings_litellm.py:43,151 |
| `OTTO_MEMORY_EMBEDDING_MODEL` | none | memory/embeddings_litellm.py:45,152 |
| `OTTO_MEMORY_EMBEDDING_API_KEY` | none | memory/embeddings_litellm.py:48,179 |
| `OTTO_MEMORY_EMBEDDING_TIMEOUT_S` | 1.5 | memory/embeddings_litellm.py:51-52,174 |
| `OTTO_MEMORY_HINDSIGHT_URL` | none (required for hindsight calls) | memory/hindsight.py:44 |
| `OTTO_MEMORY_BANK` | `"hermes"` | memory/hindsight.py:46-47 |
| `OTTO_MEMORY_RECALL_TIMEOUT_S` | 10.0 | memory/hindsight.py:60,62 |
| `OTTO_MEMORY_RETAIN_TIMEOUT_S` | 5.0 | memory/hindsight.py:61,63 |
| `OTTO_MEMORY_BACKFILL_PAGE_SIZE` | 200 | memory/backfill.py:56-57 |
| `OTTO_MEMORY_BACKFILL_TIMEOUT_S` | 60.0 | memory/backfill.py:58-59 |
| `PGHOST` / `PGDATABASE` / `PGSERVICE` / `PGURI` | none (presence-only probe) | memory/fast_recall.py:50,64 |
| `OTTO_ONBOARD_MANIFEST_DIR` | none | onboard/cli.py:29 |
| `OTTO_ONBOARD_DIR` | none | onboard/core.py:61 |
| `OTTO_STATE_DIR` | `~/.otto` (onboard) / `~/.otto/cp1` (spine inventory) | onboard/core.py:64; spine/inventory.py:112 |
| `OTTO_ROUTER_MAX_TOKENS` | 8192 | router/providers.py:26,43 |
| `LITELLM_API_KEY` | `""` (falls back to key file) | router/providers.py:87 |
| `LITELLM_BASE_URL` | `https://llm.mumchimp.com/v1` | router/providers.py:26,97 |
| `OTTO_ROUTER_MAX_RETRIES_5XX` | 1 | router/config.py:73,140 |
| `OTTO_ROUTER_MAX_RETRIES_TIMEOUT` | 1 | router/config.py:74,145 |
| `OTTO_ROUTER_TIMEOUT_SECONDS` | 120.0 | router/config.py:75,150 |
| `OTTO_ROUTER_TIMEOUT_CHARGE_USD` | 0.01 | router/config.py:79,155 |
| `OTTO_ROUTER_ON_BUDGET_EXHAUSTED` | `"queue_and_notify"` | router/config.py:72,225 |
| `OTTO_ROUTER_GROUNDING_MIN_OVERLAP` | 0.5 | router/config.py:83,231 |
| `OTTO_ROUTER_UNGROUNDED_RATE_BAR` | 0.05 | router/config.py:84,236 |
| `OTTO_ROUTER_LANE_<NAME>_MODEL` | per-lane (judgment=anthropic/claude, bulk=minimax, verify=google/gemini, deep=kimi) | router/config.py:34-39,181-183 |
| `OTTO_ROUTER_BUDGET_<NAME>_USD` | judgment=15.0, bulk=5.0, verify=3.0, deep=10.0 | router/config.py:17,184-186 |
| `OTTO_ROUTER_TASK_CAP_<NAME>_USD` | judgment=0.80, bulk=0.10, verify=0.10, deep=0.50 | router/config.py:18-23,187-190 |
| `OTTO_ROUTER_PRICE_<NAME>_PER_1K_USD` | 0.001 | router/config.py:80,191-193 |
| `OTTO_NATS_URL` | `nats://127.0.0.1:4222` | spine/bus.py:51 |
| `OTTO_JETSTREAM_DUPLICATE_WINDOW_SECONDS` | 7200 | spine/bus.py:62 |
| `OTTO_INVENTORY_KEY_PATH` | none | spine/inventory.py:109 |
| `OTTO_POSTGRES_DSN` | `postgresql://localhost:5432/otto` | spine/outbox.py:53 |
| `OTTO_VERIFIER_KEY_PATH` | none (required) | verify/identity.py:22 |
| `OTTO_EVAL_REPORT_PATH` | none | evals/report.py:32,190 |
| `OTTO_EVAL_GATE_CONFIG` | none | evals/gate.py:25,57 |
| `OTTO_NATS_SERVER_BIN` / `GOBIN` / `GOPATH` | none / none / `~/go` | tests/cp1/conftest.py:60,69-70 |
| `OTTO_PG_SOCKET_BASE` | system tempdir | tests/cp1/conftest.py:241 |
| `OTTO_CP5_LIVE` | unset (opt-in `"1"`) | tests/cp5/conftest.py:44 |
| `OTTO_CP4_TEST_PG_BINDIR` | none | tests/cp4/conftest.py:38 |
---

# B. The fork image (`/app/hermes-agent` in the Otto container)

That's a minor point, not blocking. Now compiling the final markdown report.

---

Repo: chidionyema/hermes-agent, the NousResearch fork that is the production image. Line numbers verified against the working tree on 2026-09-05.

## B.1. Toolsets (`toolsets.py`)

### B.1a. Base capability toolsets

| Toolset | Capability (plain English) | Tools | Env/key needed | toolsets.py line |
|---|---|---|---|---|
| `web` | Web search + page content extraction | web_search, web_extract | none built-in; backend picked via web_search_registry plugin (e.g. Exa needs `EXA_API_KEY`) | 109 |
| `search` | Web search only, no scraping | web_search | same as above | 115 |
| `x_search` | Search X/Twitter posts via xAI's built-in tool | x_search | `XAI_API_KEY` or SuperGrok OAuth sign-in | 121 |
| `vision` | Image analysis/description | vision_analyze | vision-capable model or vision provider configured | 134 |
| `video` | Video understanding (opt-in, not in default toolset) | video_analyze | video-analysis provider configured | 140 |
| `image_gen` | Image generation | image_generate | an image_gen_registry provider configured (e.g. `FAL_KEY`, `OPENAI_API_KEY`, xAI) | 146 |
| `video_gen` | Video generation (text/image/reference-to-video) | video_generate, xai_video_edit, xai_video_extend | video_gen_registry provider (xAI creds or FAL) | 152 |
| `bfl` | Black Forest Labs FLUX 3 video gen via Nous tool gateway (submit/poll) | bfl_flux3_text_to_video, bfl_flux3_image_to_video, bfl_flux3_keyframes_to_video, bfl_flux3_video_continuation, bfl_flux3_get_result, bfl_flux3_prompting_guide | Nous sign-in (bearer credential); gated by `check_bfl_requirements()` in tools/flux3_video_tool.py:804 | 164 |
| `computer_use` | Background desktop control (screenshots/mouse/keyboard) via cua-driver, no cursor stealing | computer_use | cua-driver binary installed locally; gated by `check_computer_use_requirements` in tools/computer_use_tool.py:25 | 183 |
| `terminal` | Shell/process execution and management | terminal, process | none (dangerous-command approval applies) | 193 |
| `skills` | View/create/manage skill documents | skills_list, skill_view, skill_manage | none | 199 |
| `browser` | Browser automation (navigate/click/type/scroll/iframes) + web_search | browser_navigate, browser_snapshot, browser_click, browser_type, browser_scroll, browser_back, browser_press, browser_get_images, browser_vision, browser_console, browser_cdp, browser_dialog, browser_exec, web_search | headless browser runtime (Playwright/browser-use/camofox) | 205 |
| `cronjob` | Create/list/update/pause/resume/remove/trigger scheduled tasks | cronjob | none | 217 |
| `file` | Read/write/patch (fuzzy match)/search files | read_file, write_file, patch, search_files | none | 224 |
| `tts` | Text-to-speech (Edge free, ElevenLabs, OpenAI, xAI, etc.) | text_to_speech | provider-specific key (`ELEVENLABS_API_KEY`, `OPENAI_API_KEY`, `XAI_API_KEY`, `MISTRAL_API_KEY`, `GEMINI_API_KEY`, `DEEPINFRA_API_KEY`; Edge/local/piper/kittentts/neutts are free) | 230 |
| `todo` | Task planning/tracking for multi-step work | todo | none | 236 |
| `memory` | Persistent memory across sessions (notes + user profile) | memory | memory provider config (builtin, or a plugin like hindsight/honcho/mem0) | 242 |
| `context_engine` | Runtime tools exposed by the active pluggable context engine | (dynamic, provider-supplied) | depends on engine plugin | 248 |
| `session_search` | Search/recall past conversations with summarization | session_search | none | 254 |
| `project` | Desktop Projects — create/switch named workspaces (GUI only) | project_list, project_create, project_switch | desktop GUI session | 260 |
| `desktop_ui` | Desktop GUI affordances — in-app terminal/browser panes, pane focus, reactions | read_terminal, close_terminal, open_preview, close_preview, read_preview, drive_preview, annotate_preview, read_window_below, focus_pane, react_to_message, setup_mcp, tour | desktop GUI session | 275 |
| `clarify` | Ask the user clarifying questions (multiple-choice/open-ended) | clarify | none | 287 |
| `code_execution` | Run Python scripts that call tools programmatically | execute_code | none | 293 |
| `delegation` | Spawn subagents with isolated context | delegate_task | none | 299 |
| `homeassistant` | Home Assistant smart home control/monitoring | ha_list_entities, ha_get_state, ha_list_services, ha_call_service | `HASS_TOKEN` (+ `HASS_URL`); gated by tools/homeassistant_tool.py:346-347 | 308 |
| `kanban` | Kanban multi-agent coordination (worker actions: complete/block/review/comment/attach; orchestrator: list/unblock) | kanban_show, kanban_list, kanban_complete, kanban_block, kanban_request_review, kanban_request_changes, kanban_heartbeat, kanban_comment, kanban_create, kanban_link, kanban_unblock, kanban_attach, kanban_attach_url, kanban_attachments | `HERMES_KANBAN_TASK` env set (dispatcher-spawned worker) | 314 |
| `discord` | Discord read/participate (fetch messages, search members, threads) | discord | `DISCORD_BOT_TOKEN` | 336 |
| `discord_admin` | Discord server management (channels/roles, pin, assign roles) | discord_admin | `DISCORD_BOT_TOKEN` | 342 |
| `yuanbao` | Yuanbao platform tools — group info, members, DM, stickers | yb_query_group_info, yb_query_group_members, yb_send_dm, yb_search_sticker, yb_send_sticker | `YUANBAO_APP_ID`/`YUANBAO_APP_SECRET` (+ `YUANBAO_BOT_ID`) | 348 |
| `feishu_doc` | Read Feishu/Lark document content | feishu_doc_read | `FEISHU_APP_ID`/`FEISHU_APP_SECRET` | 360 |
| `feishu_drive` | Feishu/Lark document comment ops (list/reply/add) | feishu_drive_list_comments, feishu_drive_list_comment_replies, feishu_drive_reply_comment, feishu_drive_add_comment | `FEISHU_APP_ID`/`FEISHU_APP_SECRET` | 366 |
| `spotify` | Native Spotify playback/search/playlists/albums/library | spotify_playback, spotify_devices, spotify_queue, spotify_search, spotify_playlists, spotify_albums, spotify_library | Spotify OAuth (`hermes auth login spotify`; optional `HERMES_SPOTIFY_CLIENT_ID`) | 375 |

### B.1b. Meta / scenario / posture toolsets

| Toolset | Capability | Tools/composition | Env/key needed | Line |
|---|---|---|---|---|
| `debugging` | Debugging/troubleshooting kit | terminal, process + includes `web`, `file` | none | 387 |
| `safe` | Safe kit, no terminal access | includes `web`, `vision`, `image_gen` | image_gen provider key for image_gen part | 393 |
| `coding` | Coding posture (CLI/TUI/desktop/ACP default in a code workspace) — files, terminal, search, web docs, skills, todo, delegate, vision, browser | web_search, web_extract, terminal, process, read_file, write_file, patch, search_files, vision_analyze, skills_list, skill_view, skill_manage, browser_*, todo, memory, session_search, clarify, execute_code, delegate_task | none; marked `"posture": True` (auto-selected by agent/coding_context.py, not user-configurable) | 408 |
| `hermes-acp` | Editor integration (VS Code/Zed/JetBrains) — coding tools, no messaging/audio/clarify | same core-coding set minus clarify | none | 441 |
| `hermes-api-server` | OpenAI-compatible HTTP API — full agent tools, no interactive UI tools | core coding set + tts, memory, cronjob, homeassistant, delegate_task, etc. | none | 461 |
| `hermes-cli` | Full interactive CLI toolset (all default core tools + cron) | `_HERMES_CORE_TOOLS` (defined toolsets.py:31-92) | none | 499 |
| `hermes-cron` | Default cron worker toolset | `_HERMES_CORE_TOOLS` | none | 505 |
| `hermes-telegram` | Telegram bot — full personal-use access | `_HERMES_CORE_TOOLS` | `TELEGRAM_BOT_TOKEN` | 516 |
| `hermes-discord` | Discord bot — full access | `_HERMES_CORE_TOOLS` + discord, discord_admin | `DISCORD_BOT_TOKEN` | 522 |
| `hermes-whatsapp` | WhatsApp (Baileys bridge) bot | `_HERMES_CORE_TOOLS` | WhatsApp session/QR pairing | 531 |
| `hermes-slack` | Slack bot — full workspace access | `_HERMES_CORE_TOOLS` | `SLACK_BOT_TOKEN` | 537 |
| `hermes-signal` | Signal bot (encrypted messaging) | `_HERMES_CORE_TOOLS` | `SIGNAL_HTTP_URL`, `SIGNAL_ACCOUNT` (signal-cli daemon) | 543 |
| `hermes-bluebubbles` | BlueBubbles iMessage bot | `_HERMES_CORE_TOOLS` | `BLUEBUBBLES_SERVER_URL`, `BLUEBUBBLES_PASSWORD` | 549 |
| `hermes-homeassistant` | Home Assistant event monitoring/control bot | `_HERMES_CORE_TOOLS` | `HASS_TOKEN`, `HASS_URL` | 555 |
| `hermes-email` | Email bot (IMAP/SMTP) | `_HERMES_CORE_TOOLS` | `EMAIL_IMAP_HOST`, `EMAIL_SMTP_HOST` (+ creds) | 561 |
| `hermes-mattermost` | Mattermost bot | `_HERMES_CORE_TOOLS` | `MATTERMOST_TOKEN`, `MATTERMOST_URL` | 567 |
| `hermes-matrix` | Matrix bot (decentralized encrypted messaging) | `_HERMES_CORE_TOOLS` | `MATRIX_ACCESS_TOKEN` or `MATRIX_PASSWORD` + `MATRIX_HOMESERVER` | 573 |
| `hermes-dingtalk` | DingTalk enterprise messaging bot | `_HERMES_CORE_TOOLS` | `DINGTALK_CLIENT_ID`, `DINGTALK_CLIENT_SECRET` | 579 |
| `hermes-feishu` | Feishu/Lark enterprise messaging bot | `_HERMES_CORE_TOOLS` + feishu_doc_read, feishu_drive_* | `FEISHU_APP_ID`, `FEISHU_APP_SECRET` | 585 |
| `hermes-weixin` | Weixin (personal WeChat via iLink) bot | `_HERMES_CORE_TOOLS` | `WEIXIN_TOKEN`, `WEIXIN_ACCOUNT_ID` | 597 |
| `hermes-qqbot` | QQ messaging via Official Bot API v2 | `_HERMES_CORE_TOOLS` | `QQ_APP_ID`, `QQ_CLIENT_SECRET` | 603 |
| `hermes-wecom` | WeCom (enterprise WeChat) bot | `_HERMES_CORE_TOOLS` | `WECOM_BOT_ID`, `WECOM_SECRET` | 609 |
| `hermes-wecom-callback` | WeCom self-built-app callback bot | `_HERMES_CORE_TOOLS` | `WECOM_CALLBACK_CORP_ID`, `WECOM_CALLBACK_CORP_SECRET` | 615 |
| `hermes-yuanbao` | Yuanbao 元宝 messaging bot | `_HERMES_CORE_TOOLS` + yb_* tools | `YUANBAO_APP_ID`/`YUANBAO_APP_KEY`, `YUANBAO_APP_SECRET` | 621 |
| `hermes-sms` | SMS bot via Twilio | `_HERMES_CORE_TOOLS` | `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN` | 634 |
| `hermes-webhook` | Webhook toolset — receive/process external events, deliberately constrained (no local exec) | `_HERMES_WEBHOOK_SAFE_TOOLS` (web_search, web_extract, vision_analyze, clarify; toolsets.py:97-105) | route-level HMAC `secret` in config.yaml `platforms.webhook.extra.routes` | 640 |
| `hermes-gateway` | Union of every messaging-platform toolset | includes all `hermes-*` bundles above | union of all above | 646 |

## B.2. Platforms (`gateway/platforms/*.py`)

| File | Surface it connects | Config/env needed |
|---|---|---|
| `ADDING_A_PLATFORM.md` | (docs, not code) — guide for adding a new adapter | n/a |
| `__init__.py` | Package init/exports for platform adapters | n/a |
| `_http_client_limits.py` | Shared httpx client connection-limit config for all adapters | n/a (internal infra) |
| `api_server.py` | OpenAI-compatible HTTP API (`/v1/chat/completions`, `/v1/responses`, `/api/sessions/*`, `/v1/models`, `/v1/capabilities`) | HTTP server bind config; optional API-key auth |
| `base.py` | `BasePlatformAdapter` — shared interface all adapters (Telegram, Discord, WhatsApp, Weixin, etc.) implement | n/a (abstract base) |
| `bluebubbles.py` | Apple iMessage via a local BlueBubbles macOS server (webhook + REST) | `BLUEBUBBLES_SERVER_URL`, `BLUEBUBBLES_PASSWORD`, `BLUEBUBBLES_WEBHOOK_HOST/PORT` |
| `helpers.py` | Shared adapter helpers (dedup, batch aggregation, markdown stripping, thread tracking) | n/a (internal infra) |
| `media_cache.py` | Shared mime↔extension mapping for inbound media across all adapters | n/a (internal infra) |
| `msgraph_webhook.py` | Microsoft Graph change-notification webhook ingress (e.g. Teams/Outlook events) | `MSGRAPH_WEBHOOK_ENABLED`, `MSGRAPH_WEBHOOK_PORT`, `MSGRAPH_WEBHOOK_CLIENT_STATE`, `MSGRAPH_WEBHOOK_ACCEPTED_RESOURCES` |
| `qqbot/` (adapter.py, chunked_upload.py, constants.py, crypto.py, keyboards.py, onboard.py, utils.py) | QQ messaging via Official QQ Bot API v2 (WebSocket gateway + REST) | `QQ_APP_ID`, `QQ_CLIENT_SECRET`; `QQBOT_HOME_CHANNEL` |
| `signal.py` | Signal messenger via a local signal-cli daemon (SSE inbound, JSON-RPC outbound) | `SIGNAL_HTTP_URL`, `SIGNAL_ACCOUNT` (signal-cli daemon running) |
| `signal_format.py` | Shared markdown→Signal bodyRanges formatting helper | n/a (internal infra) |
| `signal_rate_limit.py` | Process-wide token-bucket limiter for Signal attachment sends | n/a (internal infra) |
| `webhook.py` | Generic inbound webhook adapter (GitHub/GitLab/JIRA/Stripe etc.) → agent prompt, HMAC-verified | per-route `secret` (HMAC) in `config.yaml` `platforms.webhook.extra.routes` |
| `webhook_filters.py` | Route-local filters/script transforms for the webhook adapter | n/a (internal infra) |
| `weixin.py` | Personal WeChat via Tencent iLink Bot API (long-poll + encrypted media CDN) | `WEIXIN_TOKEN`, `WEIXIN_ACCOUNT_ID`, `WEIXIN_BASE_URL` |
| `whatsapp_cloud.py` | Official Meta WhatsApp Business Cloud API (Graph API + signed webhook) | `WHATSAPP_CLOUD_PHONE_NUMBER_ID`, `WHATSAPP_CLOUD_ACCESS_TOKEN`, `WHATSAPP_CLOUD_APP_ID/SECRET`, `WHATSAPP_CLOUD_VERIFY_TOKEN`, webhook host/port |
| `whatsapp_common.py` | Shared behavior mixin (allow-list/mention/quoted-reply/formatting) for both WhatsApp adapters | n/a (internal infra) |
| `yuanbao.py` | Yuanbao WebSocket gateway (Tencent internal messaging) — auth, heartbeat, send/receive | `YUANBAO_APP_ID`, `YUANBAO_APP_SECRET`, `YUANBAO_BOT_ID`, `YUANBAO_WS_URL`, `YUANBAO_API_DOMAIN` |
| `yuanbao_media.py` | Yuanbao COS upload / media download / TIM media message builder | inherits Yuanbao creds |
| `yuanbao_proto.py` | Pure-Python Yuanbao WebSocket protobuf frame codec | n/a (internal infra) |
| `yuanbao_sticker.py` | Yuanbao TIMFaceElem sticker support | inherits Yuanbao creds |

Note: several other messaging surfaces (Telegram, Slack, Mattermost, Matrix, DingTalk, WeCom, Email, SMS, WhatsApp/Baileys, Home Assistant, Discord, Feishu, A2A) are wired via `plugins/platforms/*` rather than `gateway/platforms/*` — see the "plugins" row in Section 4.

## B.3. Skills (every directory under `skills/`)

| Skill | One-liner |
|---|---|
| apple/apple-notes | Manage Apple Notes via memo CLI: create, search, edit |
| apple/apple-reminders | Apple Reminders via remindctl: add, list, complete |
| apple/findmy | Track Apple devices/AirTags via FindMy.app on macOS |
| apple/imessage | Send and receive iMessages/SMS via the imsg CLI on macOS |
| autonomous-ai-agents/claude-code | Delegate coding to Claude Code CLI (features, PRs) |
| autonomous-ai-agents/codex | Delegate coding to OpenAI Codex CLI (features, PRs) |
| autonomous-ai-agents/computer-use | Drive the desktop in the background without stealing focus |
| autonomous-ai-agents/hermes-agent | Use, configure, theme, extend, and orchestrate Hermes Agent |
| autonomous-ai-agents/merge-reconciler | Neutral third-party resolution of agent merge conflicts |
| autonomous-ai-agents/opencode | Delegate coding to OpenCode CLI (features, PR review) |
| creative/architecture-diagram | Dark-themed SVG architecture/cloud/infra diagrams as HTML |
| creative/ascii-art | ASCII art: pyfiglet, cowsay, boxes, image-to-ascii |
| creative/ascii-video | ASCII video: convert video/audio to colored ASCII MP4/GIF |
| creative/baoyu-infographic | Infographics: 21 layouts x 21 styles |
| creative/claude-design | Design one-off HTML artifacts (landing, deck, prototype) |
| creative/comfyui | Generate images, video, and audio via diffusion workflows |
| creative/design-md | Author/validate/export Google's DESIGN.md token spec files |
| creative/excalidraw | Hand-drawn Excalidraw JSON diagrams (arch, flow, seq) |
| creative/humanizer | Humanize text: strip AI-isms and add real voice |
| creative/manim-video | Manim CE animations: 3Blue1Brown math/algo videos |
| creative/p5js | p5.js sketches: gen art, shaders, interactive, 3D |
| creative/popular-web-designs | 54 real design systems (Stripe, Linear, Vercel) as HTML/CSS |
| creative/pretext | Build creative browser demos with DOM-free text layout |
| creative/sketch | Throwaway HTML mockups: 2-3 design variants to compare |
| creative/songwriting-and-ai-music | Songwriting craft and Suno AI music prompts |
| creative/touchdesigner-mcp | Control TouchDesigner via twozero MCP |
| devops/sdlc-review | Review Kanban handoffs and route verified outcomes |
| email/email-inbox-triage | Triage an inbox: prioritize threads, draft replies safely |
| email/himalaya | Himalaya CLI: IMAP/SMTP email from terminal |
| github/codebase-inspection | Inspect codebases w/ pygount: LOC, languages, ratios |
| github/github-auth | GitHub auth setup: HTTPS tokens, SSH keys, gh CLI login |
| github/github-code-review | Review PRs: diffs, inline comments via gh or REST |
| github/github-issue-to-pr | Carry a GitHub issue to a verified PR with honest CI state |
| github/github-issues | Create, triage, label, assign GitHub issues via gh or REST |
| github/github-pr-workflow | GitHub PR lifecycle: branch, commit, open, CI, merge |
| github/github-repo-management | Clone/create/fork repos; manage remotes, releases |
| media/gif-search | Search/download GIFs from Tenor via curl + jq |
| media/songsee | Audio spectrograms/features (mel, chroma, MFCC) via CLI |
| media/youtube-content | YouTube transcripts to summaries, threads, blogs |
| mlops/evaluation/evaluating-llms-harness | lm-eval-harness: benchmark LLMs (MMLU, GSM8K, etc.) |
| mlops/evaluation/weights-and-biases | W&B: log ML experiments, sweeps, model registry, dashboards |
| mlops/huggingface-hub | HuggingFace hf CLI: search/download/upload models, datasets |
| mlops/inference/llama-cpp | llama.cpp local GGUF inference + HF Hub model discovery |
| mlops/inference/serving-llms-vllm | vLLM: high-throughput LLM serving, OpenAI API, quantization |
| note-taking/obsidian | Read, search, create, and edit notes in the Obsidian vault |
| productivity/airtable | Airtable REST API via curl: records CRUD, filters, upserts |
| productivity/box | Box manages cloud files, sharing, search, and metadata |
| productivity/document-to-action-items | Extract cited obligations, deadlines, tasks from documents |
| productivity/docx | Create, read, edit, template, and review Word .docx files |
| productivity/google-workspace | Gmail, Calendar, Drive, Docs, Sheets via gws CLI or Python |
| productivity/maps | Geocode, POIs, routes, timezones via OpenStreetMap/OSRM |
| productivity/meeting-action-items | Turn meeting notes into cited decisions, owners, tickets |
| productivity/nano-pdf | Edit text in existing PDFs via natural-language prompts |
| productivity/notion | Notion API + ntn CLI: pages, databases, markdown, Workers |
| productivity/ocr-and-documents | Extract text from PDFs/scans (pymupdf, marker-pdf) |
| productivity/pdf | Create, read, merge, fill, and secure PDF files |
| productivity/powerpoint | Create, read, edit .pptx decks with python-pptx |
| productivity/product-price-monitor | Watch product, flight, or listing prices; alert on target |
| productivity/session-librarian | Organize sessions by prompt: find, rename, archive, prune |
| productivity/teams-meeting-pipeline | Teams meeting summaries, job replay, Graph subscriptions |
| productivity/weekly-review-planning | Weekly reset: commitments, stalled work, next-week plan |
| productivity/xlsx | Create, read, edit Excel .xlsx workbooks and CSVs |
| research/arxiv | Search arXiv papers by keyword, author, category, or ID |
| research/blocked-page-recovery | Recover blocked/paywalled/WAF'd pages via fallbacks |
| research/blogwatcher | Monitor blogs and RSS/Atom feeds via blogwatcher-cli tool |
| research/competitor-news-monitor | Watch named companies for material news; cited digests |
| research/grounded-citations | Ground answers and documents in cited, verifiable sources |
| research/llm-wiki | Karpathy's LLM Wiki: build/query interlinked markdown KB |
| research/research-paper-writing | Write ML papers for NeurIPS/ICML/ICLR: design→submit |
| smart-home/openhue | Control Philips Hue lights, scenes, rooms via OpenHue CLI |
| social-media/xurl | X/Twitter via xurl CLI: raw post search, posting, DM, media |
| software-development/dogfood | Exploratory QA of web apps: find bugs, evidence, reports |
| software-development/hermes-agent-skill-authoring | Author in-repo SKILL.md files: frontmatter and structure |
| software-development/inspecting-hermes-desktop-dom | Read the live Hermes desktop DOM/CSS over CDP |
| software-development/node-inspect-debugger | Debug Node.js via --inspect + Chrome DevTools Protocol CLI |
| software-development/plan | Write a markdown plan to .hermes/plans/; no execution |
| software-development/python-debugpy | Debug Python: pdb REPL + debugpy remote (DAP) |
| software-development/requesting-code-review | Pre-commit review: security scan, quality gates, auto-fix |
| software-development/simplify-code | Parallel 4-agent cleanup of recent code changes |
| software-development/spike | Throwaway experiments to validate an idea before build |
| software-development/systematic-debugging | 4-phase root cause debugging: understand bugs before fixing |
| software-development/test-driven-development | TDD: enforce RED-GREEN-REFACTOR, tests before code |

(`skills/index-cache/` holds cached JSON indexes of external skill catalogs — anthropic/openai/lobehub skills — not itself a skill.)

## B.4. Other features (`gateway/run.py`, `cli.py`, `agent/`, `tools/`)

| Feature | What it does | File:line receipt |
|---|---|---|
| Sessions/compaction — native compaction | Detects models with native context-management APIs and applies threshold-based compaction | `agent/native_compaction.py:119` (`native_compaction_context_management`), threshold resolver at `:85` |
| Sessions/compaction — context compressor | Default `ContextEngine` implementation; summarizes/DAG-constructs conversation history at token thresholds | `agent/context_compressor.py` (large file; hygiene/timeout guards e.g. `:77`, `:87`) |
| Sessions/compaction — session persistence | Session DB, forking, lineage, message history | `gateway/session.py` (184KB) |
| Memory providers — abstract interface | `MemoryProvider(ABC)` — pluggable memory backends registered via `register_memory_provider` | `agent/memory_provider.py:104` |
| Memory providers — bundled implementations | Hindsight (knowledge graph + entity resolution), Honcho (dialectic Q&A/peer cards), Mem0, OpenViking, ByteRover, Holographic, Supermemory, RetainDB | `plugins/memory/hindsight/__init__.py:1`, `plugins/memory/honcho/__init__.py:1`, `plugins/memory/mem0/`, `plugins/memory/openviking/`, `plugins/memory/byterover/`, `plugins/memory/holographic/`, `plugins/memory/supermemory/`, `plugins/memory/retaindb/` |
| Voice mode | Push-to-talk audio capture (sounddevice) + STT dispatch + TTS playback for CLI | `tools/voice_mode.py:1` |
| Wake word | Always-on hotword listener ("Hey Hermes"), 3 on-device engines, shared by CLI/TUI/desktop | `tools/wake_word.py:67` (`WakeWordInUse`), `:191` (`load_wake_word_config`) |
| TTS providers | Central registry; builtins: edge, elevenlabs, openai, minimax, xai, mistral, gemini, neutts, kittentts, piper, deepinfra | `tools/tts_tool.py:780` (`BUILTIN_TTS_PROVIDERS`); registration API `agent/tts_registry.py:69` |
| STT providers | Central registry; builtins: local, local_command, groq, openai, mistral, xai, elevenlabs, deepinfra | `tools/transcription_tools.py:379` (`BUILTIN_STT_PROVIDERS`); registration API `agent/transcription_registry.py:58` |
| Cron jobs | Job scheduling (SQLite-backed), execution, failure summarization, blueprint/suggestion catalogs | `cron/scheduler.py:128` (`_connect`), `cron/jobs.py`, `cron/executions.py`, `tools/cronjob_tools.py:1` |
| Delegation/subagents | `delegate_task` tool spawns isolated-context subagents; background/async variant returns a handle immediately | `tools/delegate_tool.py:3597` (`delegate_task`); async registry `tools/async_delegation.py:1`; lifecycle API `agent/subagent_lifecycle.py:1` |
| MCP client | Connects to external MCP servers (stdio/HTTP-StreamableHTTP/SSE), discovers tools, registers them into the tool registry; config under `mcp_servers:` in config.yaml | `tools/mcp_tool.py:1` (module docstring), `MCPServerTask` class `:2349`, cached tool wrapper `:7013` |
| Approvals / smart approvals | Dangerous-command detection, per-session approval state, CLI/gateway prompting, auxiliary-LLM auto-approval of low-risk commands, permanent allowlist | `tools/approval.py:1` (module docstring), `_smart_approve` at `:3322` |
| Budget / loop hard stop | Tool-loop guardrails: soft warnings + opt-in hard stop after repeated failed/non-progressing tool calls; per-turn runaway caps (max_web_searches, max_subagents) | `hermes_cli/config_defaults.py:694-716` (`tool_loop_guardrails`, `hard_stop_enabled` at `:697`) |
| Tool-result size budget | Per-tool char budgets (result size, turn budget, preview size) governing when large tool output is persisted vs inlined | `tools/budget_config.py:1` |
| Skill auto-creation | `skill_manage` tool action `create` — agent writes new `SKILL.md` + supporting files into `~/.hermes/skills/` from a proven approach | `tools/skill_manager_tool.py:1-14` (module docstring, action list) |
| User profile | Builtin memory store's user-profile flag, distinct from general memory; toggled per-agent/per-review-agent | `agent/agent_init.py:1812` (`_user_profile_enabled = False`), `:1836` (`get_builtin_memory_store_flags`) |
| Context engine (pluggable) | Abstract base for context management strategies; default is the built-in `ContextCompressor`; selectable via `context.engine` in config.yaml | `agent/context_engine.py:89` (`class ContextEngine(ABC)`) |
| A2A adapter | Agent-to-Agent protocol v1.0 — inbound: exposes Hermes as an A2A agent; outbound: 5 client tools to call other agents | `plugins/platforms/a2a/adapter.py:338` (`class A2AAdapter(BasePlatformAdapter)`); plugin docstring `plugins/platforms/a2a/__init__.py:1` |
| Plugins system | Plugin loader/registry (`PluginContext.register_platform`, `register_tool`, `register_tts_provider`, `register_memory_provider`, etc.); bundled plugin categories: browser, context_engine, cron_providers, dashboard_auth, disk-cleanup, google_meet, hermes-achievements, image_gen, kanban, memory, model-providers, observability, platforms (a2a/discord/feishu/homeassistant/…), security-guidance, spotify, teams_pipeline, video_gen, web | `plugins/memory/__init__.py:560` (`register_memory_provider`), plugin dirs listed via `ls plugins/` |

## B.5. What `/Users/chidionyema/dev/code/hermes-v2/config.yaml` actually enables

Read directly from `config.yaml` (131 lines):

```
memory: { memory_enabled: true, user_profile_enabled: true, provider: hindsight }
skills: { skill_auto_creation: true, skill_auto_creation_requires_pr: true }
approvals: { smart_approvals: true, always_ask: [...], never_ask: [...] }
limits: { max_cost_usd_per_task: 5, budget_hard_stop: true }
platforms: { telegram: {...}, a2a: { enabled: true, extra: { port: 9900 } } }
plugins: { enabled: [sovereign, guide] }
compression: { threshold_tokens: 150000, context_timeout_seconds: 300 }
```

No `toolsets:`, `tools:`, `mcp_servers:`, `auto_tts:`, or `vision:` keys are present, so those areas run on hermes-agent's built-in defaults.

| Row from sections 1-4 | Enabled / Disabled here | Basis |
|---|---|---|
| **Toolsets** — no explicit `toolsets`/`disabled_toolsets` override | Enabled: default `_HERMES_CORE_TOOLS` set for whichever platform bundle is active (telegram → `hermes-telegram`, a2a → `a2a` plugin toolset). This includes: web, terminal, file, vision, image_gen, bfl (schema present), skills, browser, tts, todo, memory, session_search, clarify, execute_code, delegate_task, cronjob, homeassistant (schema present), kanban (schema present), computer_use (schema present) | `hermes_cli/config_defaults.py:12` default `"toolsets": ["hermes-cli"]`, `:351` `"disabled_toolsets": []`; toolsets.py:31-92 `_HERMES_CORE_TOOLS`; config.yaml has no override |
| `homeassistant` toolset | Disabled at runtime | No `HASS_TOKEN`/`HASS_URL` in `.env` → `tools/homeassistant_tool.py:346-347` gate returns False |
| `bfl` (FLUX3 video) | Disabled at runtime | `auth.json` `providers: []`, no Nous credential → `check_bfl_requirements()` fails (tools/flux3_video_tool.py:804) |
| `computer_use` | Disabled at runtime (schema present, functionally gated) | Depends on local cua-driver install, not configured in config.yaml/.env |
| `x_search` | Disabled | Not in `_HERMES_CORE_TOOLS`/not added by any config.yaml toolset entry; also no `XAI_API_KEY` in `.env` |
| `discord`, `discord_admin` | Disabled | Platform not configured; no `DISCORD_BOT_TOKEN` in `.env` |
| `spotify` | Disabled | Toolset not added; no Spotify OAuth performed |
| `feishu_doc`, `feishu_drive`, `yuanbao` | Disabled | Platforms not configured; no `FEISHU_*`/`YUANBAO_*` in `.env` |
| `web`/`search` | Enabled, backed by Exa | `EXA_API_KEY` present in `.env`; used by `plugins/web/exa/provider.py` |
| **Platforms** — `telegram` | Enabled | `platforms.telegram` block in config.yaml; `TELEGRAM_BOT_TOKEN`, `TELEGRAM_ALLOWED_USER_IDS`, `TELEGRAM_HOME_CHANNEL` all present in `.env` |
| **Platforms** — `a2a` | Enabled | `platforms.a2a: { enabled: true, extra: { port: 9900 } }` in config.yaml |
| **Platforms** — bluebubbles, signal, weixin, whatsapp_cloud, webhook, msgraph_webhook, qqbot | Disabled | Not present under `platforms:` in config.yaml; none of their env vars (`BLUEBUBBLES_*`, `SIGNAL_*`, `WEIXIN_TOKEN`, `WHATSAPP_CLOUD_*`, `QQ_*`) are in `.env` |
| **Platforms** — discord, slack, mattermost, matrix, dingtalk, wecom, sms, email (plugin-based) | Disabled | Not under `platforms:` in config.yaml; corresponding env vars absent from `.env` |
| **MCP servers** | None configured | No `mcp_servers:` key in config.yaml — MCP client code loads but connects to nothing |
| **auto_tts** | Disabled (default) | Default `"auto_tts": False` (`hermes_cli/config_defaults.py:1780`); config.yaml does not override |
| **Vision** | Enabled (default core tool) | `vision_analyze` is in `_HERMES_CORE_TOOLS`; config.yaml sets no override |
| **Memory provider** | Hindsight, local-embedded mode | config.yaml `memory.provider: hindsight`; `hermes-v2/hindsight/config.json`: `{"mode": "local_embedded", "llm_provider": "ollama", "llm_model": "qwen2.5-coder:7b", "bank_id": "hermes"}` — no cloud `HINDSIGHT_API_KEY` needed |
| **User profile** | Enabled | config.yaml `memory.user_profile_enabled: true` |
| **Skill auto-creation** | Enabled, PR-gated | config.yaml `skills.skill_auto_creation: true`, `skill_auto_creation_requires_pr: true` |
| **Smart approvals** | Enabled | config.yaml `approvals.smart_approvals: true`, with explicit `always_ask` (gh pr merge, git push, rm -rf) and `never_ask` (gh issue list/view, git log/status/diff) overrides |
| **Budget hard stop** | Enabled | config.yaml `limits: { max_cost_usd_per_task: 5, budget_hard_stop: true }` |
| **Plugins** | `sovereign`, `guide` enabled (local, non-bundled plugins) | config.yaml `plugins.enabled: [sovereign, guide]`; found at `/Users/chidionyema/dev/code/hermes-v2/plugins/sovereign/plugin.yaml` ("Sovereign Bus session control ... shells to `$IDP/bin/sb --json`") and `.../plugins/guide/plugin.yaml` ("/guide: Otto teaches the founder what the Architect can do, built from what is on disk") |
| **Compaction threshold** | 150,000 tokens (custom, tuned down from a prior 200k incident) | config.yaml `compression.threshold_tokens: 150000`, `context_timeout_seconds: 300` |
---

# C. The platform: what idp runs for Otto

## C. Estate MCP server tools (what Otto can ask the platform)

| Tool | Receipt | Answers |
|---|---|---|
| `get_estate_inventory` | mcp/plugins/estate_inventory.py:184 | Every catalogue entity, owner, repo |
| `get_estate_state` | mcp/plugins/estate_state.py:107 | The estate as one document with an availability envelope |
| `get_workload_state` | mcp/plugins/workload_state.py:236 | "Why is X down": catalogue entry, desired vs actual, metrics |
| `get_workload_logs` | mcp/plugins/workload_logs.py:169 | Last N raw log lines for a workload |
| `ask_holmes` | mcp/plugins/estate_holmes.py:160 | A free-text investigation by HolmesGPT over the cluster |
| `remember` / `recall` | mcp/plugins/estate_memory.py:245, 267 | Write and read the estate's permanent memory (Hindsight) |
| `list_databases`, `get_database_schema`, `execute_sql` | mcp/agentgateway.yml:19-21 | Read-only SQL over the catalogue database |
| GitHub `issues` toolset | mcp/agentgateway.yml:101 | Read the board's issues |

## C. otto-gateway namespace (the door)

| Kind | Name | Receipt | Does |
|---|---|---|---|
| Deployment | otto-gateway | platform/otto-gateway/deployment.yaml:22 | `python -m otto.ingress`, 2 replicas, critical priority, spread across nodes; init container seeds channel bindings |
| HTTPRoute | otto-gateway | httproute.yaml:19 | `otto.<zone>/webhook/*` → the door, one path for every channel |
| ExternalSecret | otto-gateway-channels | external-secret.yaml:33 | Two Telegram bots' tokens and webhook secrets on one door |
| ExternalSecret | otto-gateway-router | external-secret.yaml:82 | Router key, allowlist minimax, gemini, deepseek, embed |
| NetworkPolicy ×7 | default-deny, dns, edge ingress, observability, event bus, database, memory, llm | network-policy.yaml | Both-ways deny plus named exceptions; no internet egress, no MCP egress |
| PodDisruptionBudget | otto-gateway | availability.yaml:3 | One replica always up |
| Job | otto-memory-store | memory-store-job.yaml:39 | pgvector + full-text fast-recall store backfilled from Hindsight |
| CronJob | otto-registration-reconciler | registration-reconciler.yaml:258 | Every 5 min re-points both bots' webhooks at the door, emits metrics |
| CronJob | otto-answer-probe | answer-probe.yaml:187 | Every 15 min a real completion on every router lane, grades non-empty |
| Env | judgment=deepseek, bulk=gemini, verify=gemini, memory recall 30s, embed 1536-dim, OTLP to SigNoz | deployment.yaml:153-234 | |

## C. hermes-agent namespace (the old agent, the fork's gateway, no Telegram since 2026-09-05)

| Kind | Name | Receipt | Does |
|---|---|---|---|
| Deployment | hermes-agent-gateway | platform/hermes-agent/gateway.yaml:205 | The fork's gateway plus Tailscale sidecar; A2A port 9900 |
| Generator | GitHub App installation token | gateway.yaml:100 | Fresh `estate-agents` app token every refresh: contents, pull requests, issues write |
| ExternalSecret | hermes-agent-env | gateway.yaml:50 | The agent's whole environment; Telegram keys renamed DISABLED |
| ExternalSecret | hermes-agent-mcp | mcp-key.yaml:10 | `ESTATE_MCP_KEY` into the estate MCP server |
| ExternalSecret | hermes-agent-langfuse | langfuse-key.yaml:9 | Otto's own trace project |
| ExternalSecret | hermes-agent-mac-run | mac-run-key.yaml:10 | SSH key to the founder's Mac (`mac-run`, `cursor-agent`) |
| ExternalSecret | hermes-agent-tailscale | tailscale.yaml:16 | Tailnet membership |
| PVC | hermes-agent-data 5Gi | gateway.yaml:178 | state.db, sessions, memories, cron jobs |
| ConfigMap | hermes-agent-estate | estate.yaml:6 | Lanes watch/work/evolution/sunday on; bench and screenshot off; dispatch runtimes mac-run, cursor, gemini, opencode, codex; $5 per task cap |
| RBAC | hermes-agent-reader | rbac.yaml:13 | Read pods, logs, events, deployments in own namespace only |

## C. Backstage portal

| Surface | Receipt | Does |
|---|---|---|
| `/investigate` page | backstage/packages/app/src/modules/home/Investigate.tsx:1 | Ask HolmesGPT from the portal, the twin of `ask_holmes` on Telegram |
| Founder tiles | backstage/founder/catalog-info.yaml:437, 526, 564, 583 | Telegram bot link, Otto entity with live pod state, door health, Cursor worker |
| Platform entity | backstage/platform/catalog-info.yaml:843 | hermes-agent layer with SigNoz logs and Langfuse traces links |
| Founder action | backstage/templates/founder-actions/otto-parity/template.yaml:1 | Button that runs every advertised Otto ability for real and reports green/red |

## C. Router lanes on the cluster (platform/llm/config.yaml)

minimax (MiniMax-M2), gemini (2.5-flash), default (2.5-pro), fast (2.5-flash), embed (gemini-embedding-001, 1536), vision (2.5-flash), image (gemini-3.1-flash-image, generation), kimi (alias → moonshot kimi-k3), deepseek. Measured 2026-09-05 22:20Z with Otto's key: deepseek and minimax return tool calls.

## C. Decisions and specs on main that bind Otto

0006 one MCP; 0011 Claude is a router lane; 0017 Bitwarden is the human door; 0021 two hats; 0022 voice-first, nothing deleted; 0024 Otto runs every tool, asks only for the unundoable; 2026-09-03 hermes-v2 rides the hermes-agent row; 2026-09-04 judgment lane, kimi alias, MCP key fingerprint; specs otto-five-capabilities-finished, hosted-session-memory, otto-door-hands-and-senses.

---

# D. The board: graded rows and the checkpoints that define done

## D. crew#717 — Otto superpowers, 33 checkpoints, last graded status per row

Status = the LAST graded mention across the three audit comments of 2026-08-31 (09:03Z baseline; 10:56–11:14Z rerun; 12:34–12:38Z fixed-grader rerun). "Never graded" = no comment mentions the row.

| Row | Plain-English capability | Status as recorded |
|---|---|---|
| CP1 `web-search-answers` | Web search/extract tool with a search key | Never graded |
| CP2 `browser-opens-backstage` | Headless browser opens Backstage/Langfuse/Healthchecks/shop | Never graded |
| CP3 `vision-lane-answers` | Router lane carries images sent by founder | Never graded (vision proved later, hermes-v2 PR #86, 2026-09-05) |
| CP4 `video-lane-answers` | Analyses a video clip | Never graded |
| CP5 `voice-roundtrip` | Transcribes Telegram voice notes, replies as audio | Never graded (see `tts-edge-answers`) |
| CP6 `x-search-or-declared-off` | X/Twitter search when key exists, else declared off | Never graded |
| CP7 `dispatches-a-drill` | Runs estate workflows (oke-check, catalogue drills) with pod token | Never graded |
| CP8 `sa-writes-own-namespace` | Write RBAC in Otto's own namespace only | Never graded |
| CP8 `sa-blind-elsewhere` | Service account cannot read secrets outside its namespace | "kube-system secrets now refused — the RBAC lockdown holds", 2026-08-31 |
| CP9 `cronjob-roundtrip` | "remind me every hour" becomes a listed, pausable job | Never graded |
| CP10 `code-exec-runs` | code_execution runs a script calling many tools | Never graded |
| CP11 `delegation-runs` | Subagents through the router for long jobs | Never graded |
| CP12 `image-gen-answers` | Image generation | Never graded |
| CP12 `video-gen-or-declared-off` | Video generation or declared off | Never graded |
| CP13 `computer-use-over-mac-run` | computer_use over mac-run onto the founder's laptop | Never graded |
| CP14 `session-search-answers` | Recall over Otto's own past conversations | Never graded |
| CP15 `consult-answers` | "consult" skill: ask a second model when stuck | Never graded |
| CP16 `todo-clarify-present` | todo tool for multi-step work; clarify only when needed | Never graded |
| CP17 `skills-all-vetted` | All 25 shipped skills have a description and a VETTED row | Never graded |
| CP18 `incident-lane-roundtrip` | incident-triage / post-mortem / verify-to-prod from Telegram | Never graded |
| CP19 `board-write` | Reads/writes the crew board | Never graded |
| CP20 `cost-report-answers` | "what did we spend today" from the spend ledger | Never graded |
| CP21 `webhook-receives` | hermes-webhook receives estate alerts | Never graded |
| CP22 `tirith-scans` | tirith + osv security scans on what Otto touches | Never graded |
| CP23/31 `state-backup-fresh` | State volume and hindsight Postgres backed up on a schedule | Never graded |
| CP24 `email-reads` | Reads/drafts on the founder's mailbox, send always asks | Never graded |
| CP25 `homeassistant-or-declared-off` | Home Assistant if on the tailnet | Never graded |
| CP26 `second-channel-answers` | One more channel than Telegram | Never graded |
| CP27 `otto-emits-traces` | Every turn a Langfuse trace | "otto-emits-traces (5163 traces)" ok, 2026-08-31 12:34Z |
| CP28 demo Tools page | One Telegram message per superpower, on a Backstage Tools page | Never graded |
| CP29 hindsight visible to estate | `get_workload_state app=hindsight` finds it | body 2026-08-30: "answers found:false today" |
| CP30 `memory-recalls-across-days` | A fact stored one day is recalled the next | Never graded |
| CP32 | Otto survives the Mac being closed | Never graded |
| CP33 `estate-state-read-at-start` | Gateway log shows `estate-state: READ` at boot | FAIL 2026-08-31 12:34Z: "no such code anywhere" |
| `gateway-ready` | Deployment rolls out, replica ready | ok 2026-08-31 10:56Z |
| `key-usable` | Exec into the running pod works | ok 12:34Z |
| `key-direct` | SSH from Otto to the founder's Mac | "answered its hostname" ok 12:34Z |
| `tailnet-up` | Pod on the Tailscale tailnet | ok 12:34Z |
| `mac-run-hostname` | mac-run executes on the founder's Mac | ok 12:34Z |
| `git-in-pod` | git and gh authenticated in the pod | "live gh login" ok 12:34Z |
| `hindsight-answers` | Memory API answers | "200" ok 12:34Z |
| `cron-lanes-installed` | Watch/work/evolution cron lanes | "jobs=9" ok 12:34Z |
| `model-lane-is-router` | Model calls go through the estate router | ok 12:34Z |
| `repo-workspace` | Clone, branch, push with a token | "dry-run ok" 12:34Z |
| `sa-reads-own-namespace` | Read-only RBAC in own namespace | green 10:56Z |
| `memory-survives-restart` | State persists across a pod restart | ok 12:34Z |
| `memory-volume-bound` | 50Gi state claim bound | green 10:56Z |
| `memory-hindsight-answers` | Long-term memory backend answers | ok 12:34Z |
| `langfuse-key-mounted` | Langfuse key in the pod | ok 12:34Z |
| `api-answers` | Router API responds | green 09:03Z |
| `kubeconfig` | Usable kubeconfig | green 09:03Z |
| `bindings-outside-namespace` | No RBAC outside own namespace | green 10:56Z |
| `toolsets-available` | Configured toolsets load | ungraded output 10:56Z |
| `no-restart-loop` | restarts=0 | ok 09:03Z and 10:56Z |
| `tts-edge-answers` | Text-to-speech via edge-tts | FAIL 12:34Z (voice landed later, hermes-v2 PR #87, 2026-09-05) |
| `estate-mcp-answers` | MCP handshake with the pod's key | FAIL 12:34Z (estate MCP named in config, hermes-v2 PR #79, 2026-09-05) |

## D. crew#768 — Build Spec v1.0 checkpoints

| CP | Demands |
|---|---|
| CP1 | Spine and measurement: JetStream subjects, outbox relay, eval corpus and runner, capability inventory, `otto replay` |
| CP2 | Tool gateway, authority tiers, sandbox: schema validation, tier enforcement, taint tracking, egress control, red-team suite |
| CP3 | Verification plane: separate credentials, signed verdicts, forged/replayed/absent verdicts rejected, false-success eval at zero leakage |
| CP4 | Memory and context engine: pgvector hybrid retrieval, provenance-enforced facts, hygiene job, budgets and compaction |
| CP5 | Router and structured outputs: lane policy, budget guards, universal response contract, unverified-claim rendering |
| CP6 | Hardening and phone-first: chaos pass (daemon kill, NATS partition), weekly digest, a week operable from Telegram alone |
| CP7 | Constitution P1 to P8 verified under adversarial test |

## D. crew#773 — Spec v1.1 checkpoints

| CP | Demands |
|---|---|
| CP1 | Channel plane: adapter registry and capability negotiation |
| CP2 | Voice in: transcription pipeline, Telegram voice notes first |
| CP3 | Voice out: synthesis and the no-voiceprint rule |
| CP4 | Vision: image_in day 0, `ambient` classification |
| CP5 | Conversational presence: one conversation across surfaces keyed on founder identity |
| CP6 | Observability: voice, vision, presence spans reach the collector |
| CP7 | Constitution extended: no-voiceprint and ambient rules under red-team |

## D. crew#770 — roadmap, potential (founder start word 2026-08-31: "may as well just build the whole roadmap")

| Item | Capability |
|---|---|
| H0 platform | Build Spec v1 phases 0–5; eval corpus 40–60 tasks + 10 false-success; decisions on bulk model, secrets, traces, gVisor; Meta Wearables toolkit preview; glasses hardware |
| H1.1 voice interaction plane | LiveKit Agents self-hosted; STT→router→TTS cascade ≤800ms, barge-in; T0 read-only; SIP phone number |
| H1.2 companion app | Native iOS/Android: chat+voice, push, T2/T3 approval cards, passkey-bound identity |
| H1.3 glasses surface | Ray-Ban Display preview: glanceable cards, voice loop, Neural Band approvals, `ambient` capture |
| H1.4 Spec v1.1 | Channel plane, identity plane, presence kernel, `ambient` trust class |
| H2.1 channel rollout | email in/out → WhatsApp → Slack/Discord → iMessage, each with eval and red-team |
| H2.2 presence kernel | One conversation across glasses, desk, kitchen voice |
| H2.3 twin stage 1 | Drafts as the founder, T1 only, style eval |
| H2.4 vision stage 1 | Images and frames as task inputs with provenance; printed-text injection in red-team |
| H3 twin stage 2 and 3 | Approved sends; disclosed autonomy for low-stakes classes after 30 clean days |
| H3 ambient Otto | Morning brief on lens, context nudges, end-of-day review, tells never acts |
| H3 second glasses platform | Android XR as an adapter |
| H3 capture ethics runbook | Consent, retention, UK recording law |
| H4 embodiment R0–R2 | Simulated/teleoperated → constrained actuation → verification plane with its own sensors |
| H5 beyond | Every model release = router row + eval; GPU pool + local vLLM lane; skill economy via PRs; Otto as chief of staff; interop watch-brief |

## D. crew#758 — Backstage is the one door

| CP | Otto on Backstage | Status |
|---|---|---|
| CP1 | Otto in the catalogue with Langfuse and SigNoz links | |
| CP2 | Release from Backstage, deploy-when-green button | |
| CP3 | Every workload entity shows logs and traces | "CP3 landed and released", idp PR 1081 merged 2026-08-31 |
| CP4 | Coverage measured from the backends into the warehouse | |
| CP5 | Generated self-service audit page | |

## D. crew#682 — Slack is the machine alert channel

| CP | Demands |
|---|---|
| CP1 | One Slack root; `#alerts-p1`, `#alerts-p2`, `#alerts-noise` by code; founder in every channel |
| CP2 | Flux Provider + Alert and Alertmanager receiver to Slack |
| CP3 | Telegram only for P1 and founder lines; every red has an owner; unowned 10 min escalates to Telegram P1 page |
| CP4 | Runbook and a daily synthetic P1 drill |
| CP5 | Every alert thread and page lands in the collector; weekly grading |

## D. Other open Otto tickets

862 why is Otto not working · 819 a paying customer onboards themselves · 734 P0 green baseline and Otto lockdown · 763 crew agents run in pods like Otto · 798 Slack by purpose · 736 unbreakable release contract · 755 release word from Telegram · 761 Otto total coverage from the backend · 278 Otto must be trustworthy · 756 DSPy on every prompt surface · 290 continuity through any single loss · 491 memory to a real vector/graph provider · 496 incident 2026-08-27 refusals · 671 Telegram surface polish · 684 ops dashboard and Tools page · 764 picture evidence before UI release · 529 independent certification of the gateway · 840 staged approvals as durable state with a signed Telegram button · 767 agent SSO account with kill switch. Closed: 213 Sovereign Bus, 561 parity list in the cluster.

---

# E. Potential, in one place

Everything designed and not yet built, each with the ticket that owns it. A row leaves this
section only when a QA session ticks its box on a green run.

| Capability | Owner | What exists today |
|---|---|---|
| Fork tools behind the door's gateway (terminal, files, web, browser, code, delegation, cron, skills) | spec step 1, crew#768 CP2 | tools in the image, gateway live with one tool |
| Tool loop inside the provider client | spec step 2, crew#768 CP5 | `LiteLLMClient` sends one message, no tools |
| Voice in and out on Telegram | spec step 3, crew#773 CP2, CP3, ADR 0022 | faster-whisper, edge-tts, ffmpeg in the image; binding is text only |
| Photo to vision lane | spec step 4, crew#773 CP4 | vision lane on the router; binding drops photos |
| Door pod holds the fork's environment, the MCP key, a state volume, wider egress | spec step 5 | secrets exist in hermes-agent namespace, not mounted on the door |
| Sandbox namespace for the terminal, no secrets, one-hour token | spec step 6, crew#768 CP2 sandbox row | none |
| Typing, progress edits, deferred replies, interrupt | spec step 7 | none |
| One conversation thread per principal with compaction | spec step 8, crew#773 CP5 | `otto/spine` envelopes, no thread table |
| Portal web chat, Slack, WhatsApp, email, voice session | spec step 9, crew#758, crew#682, crew#770 H1.1, H2.1 | adapters in the image, `platforms.telegram` only |
| Verification plane on the live path (signed verdicts before T2/T3) | crew#768 CP3 | BUILT, `otto/verify/`, not imported by the worker |
| Chaos pass, weekly digest, a week operable from the phone alone | crew#768 CP6 | none |
| Constitution P1 to P8 under adversarial test | crew#768 CP7, crew#773 CP7 | eval corpus and false-success set BUILT |
| Web search, browser, video, X search, image and video generation graded on the board | crew#717 CP1, CP2, CP4, CP6, CP12 | all in the image, never graded |
| Cron round trip, code execution, delegation, consult, todo, session search graded | crew#717 CP9, CP10, CP11, CP14, CP15, CP16 | in the image, never graded |
| Incident lane, board write, cost report, webhook receive, security scans | crew#717 CP18 to CP22 | webhook adapter and skills in the image; cost ledger LIVE in `otto/router/budget.py` |
| State backups on a schedule | crew#717 CP23/31 | none recorded |
| Email, Home Assistant, a second channel | crew#717 CP24, CP25, CP26 | adapters in the image, keys absent |
| Estate state read at boot | crew#717 CP33 | FAIL 2026-08-31: no such code |
| Live voice session under 800 ms with barge-in, a phone number | crew#770 H1.1 | none |
| Native companion app with approval cards and passkeys | crew#770 H1.2 | none |
| Glasses surface, ambient capture, Neural Band approvals | crew#770 H1.3, H3 | `ambient` trust class BUILT |
| Twin stages: drafts as the founder, approved sends, disclosed autonomy | crew#770 H2.3, H3 | none |
| Embodiment R0 to R2 | crew#770 H4 | none |
| GPU pool and a local vLLM lane; a skill economy through pull requests | crew#770 H5 | vLLM and llama.cpp skills in the image |
| Staged approvals as durable state with a signed Telegram button | crew#840 | human gate LIVE in `otto/gateway/core.py:61`, token protocol only |
| Otto as a paying customer's self-service assistant | crew#819 | onboarding CLI BUILT |

## Method

Four read-only audits ran on 2026-09-05 between 22:10Z and 22:45Z: one over `otto/` on
hermes-v2 origin/main 17aa95e (every package, every test directory, every `os.environ` read),
one over the fork checkout (`toolsets.py`, `gateway/platforms/`, `skills/`, `tools/`, `agent/`,
`plugins/`, `config.yaml`, `.env` names only), one over idp `platform/`, `mcp/`, `backstage/`
and `docs/decisions/`, and one over the crew board's issue bodies and comments. A row's status
was decided by import: LIVE means `otto/ingress/worker.py` or `otto/boot/pipeline.py` reaches
it; anything else on main is BUILT. Enabled in the image means the fork's default toolset or
`config.yaml` carries it with its credential present. Nothing was graded by running it; the
board rows carry the last recorded grade and its date. The next grade comes from the proof
table in `docs/specs/otto-door-hands-and-senses.md`, quoted from the door's log.
