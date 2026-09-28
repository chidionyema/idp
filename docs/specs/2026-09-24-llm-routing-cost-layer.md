# LLM Routing & Cost Layer — Full End-to-End Rebuild Specification
Version: 1.0
Status: Authoritative — supersedes all prior fragments
Saved: 2026-09-24
Scope: All LLM traffic from all agent harnesses, all providers, all environments (laptop and cluster), including normal operation and emergency change.

## SPIFFE/SPIRE State (as of 2026-09-24)

SPIRE IS deployed and running in the cluster.

- **Namespace**: `spire-mgmt`
- **HelmRelease**: `platform/spire/helmrelease.yaml` — `spire` chart v0.30.1, `spire-crds` v0.6.1
- **Flux Kustomization**: `clusters/oke/platform.yaml` → `spire` row, `suspend: false` (ACTIVE)
- **Health check**: waits on `HelmRelease/spire` in `spire-mgmt`
- **Depends on**: `scheduling`, `backstage-namespace`
- **Proof**: `platform/spire/proof.yaml` and `proof-cronjob.yaml` — automated verification

**What SPIRE is NOT yet doing**: issuing SVIDs to workloads that would replace the env-var-based provider keys. The trust-debt register (below) captures this.

The spec's §10 item "Pod env contains provider keys" → "Workload-identity broker (SPIFFE, IRSA, or estate equivalent)" is the work item that wires SPIRE SVIDs to the litellm router and other workloads.

---

## 0. How to read this document
This is the single source of truth for the routing and cost layer. It contains:

The axioms that constrain every design decision (§2)
The anti-patterns that have caused the current outage and must never return (§3)
The target architecture, component by component (§4)
Every data flow, normal and emergency (§5)
The zero-trust break-glass path (§6)
The identity and policy plane (§7)
The phased execution plan (§8)
The acceptance criteria that define "done" (§9)
The trust-debt register — what we know is not yet zero trust (§10)
Risks (§11), out-of-scope (§12), and a single-page owner checklist (§13)

If a decision elsewhere contradicts this document, this document wins.

## 1. Context

### 1.1 What exists today

**Router.** LiteLLM proxy at llm.mumchimp.com, running in the idp-router pod on OKE, managed by Flux from platform/llm/config.yaml.

**Harnesses.** Pi, Cline, Claude Code, Aider, OpenCode. Each with its own config file schema (models-store.json, .aider.conf.yml, cline_config.json, etc.), each with its own model-name catalog, each independently maintained.

**Secrets.** Provider keys scattered across Bitwarden, GitHub repo secrets, ~/.pi/agent/auth.json, and dotfiles. No single source of truth.

**Ledger.** ~/.estate/efficiency-ledger.jsonl on the founder's laptop. Orphaned. No active writer. 72 stale rows from an old session.

**Cost visibility.** None. The efficiency mechanisms run inside the router but write to a filesystem the founder cannot see (the pod's container FS, not the laptop's).

### 1.2 What's broken

- **Translation tables.** Agent model names (MiniMax-M2.7) don't match router aliases (minimax_m27). Every new provider or harness release requires editing both sides.
- **Per-tool config maintenance.** Pi needs one patch, Cline another, Aider a third. Any new harness is a new maintenance burden.
- **Provider keys in agents.** Pi's auth.json contains the raw MiniMax key. Any leaked config is leaked spend.
- **No enforcement.** An agent that hardcodes api.anthropic.com bypasses the router entirely. Nothing stops it.
- **Ledger on the wrong layer.** The router writes to its own container FS. The laptop-local JSONL is stale and unwatched.
- **Emergency change latency.** PR → CI → Flux round-trip is minutes to hours. At 3am with money burning, that is unacceptable.

### 1.3 What "done" looks like

A founder who can:
- Add a model by adding one Bitwarden entry and (at most) one ExternalSecret manifest. No harness-side action.
- Add a harness by running estate-execute <name>. No routing-layer code.
- Query cost by harness, model, and token, in real time, from a laptop.
- Apply an emergency change in seconds, from a hardware-key tap, scoped to one verb, expiring automatically.
- Sleep at night knowing no agent holds a provider key and no agent can reach a provider directly.

## 2. Design axioms

Non-negotiable. Any solution that violates one is rejected.

- **A1** — The router is the only egress. Every LLM call from every harness passes through llm.mumchimp.com. Enforced at the network layer, not by configuration.
- **A2** — No translation tables. The router never maps agent-supplied model names to provider model names. Routing is by wildcard prefix or capability tier.
- **A3** — Agents are protocol clients, not configuration owners. A harness knows only: a base URL, one token, and the OpenAI wire format. It does not know providers, credentials, or model catalogs.
- **A4** — Secrets flow one direction. Bitwarden → ExternalSecrets → pod environment. Agents never see provider keys. Humans never paste credentials into CI, GitHub Secrets, or dotfiles.
- **A5** — The ledger is a database, not a file. Cost, tokens, model, harness, tenant are written to Postgres by the router at call time. No JSONL. No laptop-local artifacts. No per-tool ledger writers.
- **A6** — One control plane. Models are managed in LiteLLM. Nothing else enumerates models. Harness configs are derived from GET /v1/models.
- **A7** — One measurement plane. The instrument that routes is the instrument that observes. Exactly one source of truth for "what happened." No shadow ledgers, no local fallbacks, no forks.
- **A8** — No standing credentials. Every privileged action is authenticated per-request, authorized per-request, and carried by a JIT-issued, single-purpose, TTL-bounded capability. No long-lived admin keys. No saved sessions.
- **A9** — Break-glass is additive and time-boxed. Emergency change can add or override, never delete. Every emergency entry has a TTL and expires automatically.
- **A10** — Three surfaces only. Every change to the routing layer lands in one of: the router (§4.2), the secret bridge (§4.1), or the wrapper (§4.6).

## 3. Anti-patterns explicitly rejected

| Anti-pattern | Why it fails | Axiom violated |
|---|---|---|
| MiniMax-M2.7 → minimax_m27 translation dict | N×M matrix. Drifts on every release. Silent 404s. | A2 |
| Per-tool config patchers | Each is separate code, separate schema, separate breakage. | A3, A10 |
| Agent-side ledger writers | One writer per harness = one bug per harness. | A5 |
| Env vars as the only enforcement | Hardcoded provider URL ignores them. | A1 |
| Provider keys in agent auth files | Any leaked config = leaked spend. | A4 |
| ~/.estate/efficiency-ledger.jsonl as live state | Local file, wrong layer, orphaned writer. | A5, A7 |
| Asking a human for a connection string | The pod already has DATABASE_URL composed at boot. | A4 |
| Standing admin keys for break-glass | "Emergency" becomes "the way it works." | A8 |
| Destructive break-glass (delete a callback) | Turns a tourniquet into a blindfold. | A9 |
| Shadow ledger during router outage | Forks the measurement plane; unreconcilable. | A7 |
| Hot path with no git-path equivalent | Becomes shadow infrastructure. | A9, A10 |

## 4. Target architecture

```
HUMAN/FOUNDER
  Hardware key → PDP → JIT capability → one verb → expires
         ↓
IDENTITY & POLICY PLANE (PDP, OIDC, audit)
         ↓ issues
BREAK-GLASS (additive, TTL, reaper, git-correspondence)
         ↓
AGENT HARNESSES (pi | cline | claude-code | aider | opencode)
  spawned by estate-execute
  env: BASE_URL=llm.mumchimp.com/v1  KEY=$ESTATE_AGENT_KEY
  no provider keys. egress locked.
         ↓ OpenAI wire format
ROUTER (LiteLLM, wildcards, tiers)
  Governance callbacks (cache, ceiling, compaction, …)
  Ledger → Postgres + Langfuse + OTel
  keys from pod env (ExternalSecret ← Bitwarden)
         ↓
UPSTREAM PROVIDERS (api.minimax.io | api.deepseek.com | …)
```

### 4.1 Secret bridge — Bitwarden → ExternalSecrets → pod env

**Owner:** platform/secrets/, platform/human-vault-bridge/

**Current state (2026-09-24):**
- Bitwarden Secrets Manager is the vault source for all vendor keys (store_default: human-vault)
- ExternalSecrets syncs every 1 minute from Bitwarden into cluster namespaces (llm, dagster, otto-gateway, etc.)
- ClusterSecretStore `human-vault` is deployed and active (Flux Kustomization `human-vault` + `human-vault-bridge`)
- One manifest per vendor per namespace, rendered from platform/vendors/consoles.yaml (Helm chart, no committed files)
- **Problem:** Consoles.yaml had 35 targets missing the `entry` field — fixed 2026-09-24 in PR #3928

**Still missing:**
- SEED_GROQ_API_KEY, SEED_CEREBRAS_API_KEY, SEED_NVIDIA_API_KEY, SEED_SAMBANOVA_API_KEY, SEED_COHERE_API_KEY, SEED_TYPESAFE_API_KEY — no repository secrets set
- SEED_MINIMAX_API_KEY, SEED_DEEPSEEK_API_KEY, SEED_GEMINI_API_KEY, SEED_KIMI_API_KEY — repository secrets set but keys are invalid/expired
- These must be set in Bitwarden (the source) AND the Bitwarden entry names must match the `bw` field in consoles.yaml

**Trust debt:** Pod env vars are standing credentials. SPIRE is deployed but not yet wired to issue workload identities that would replace env-var-based keys.

### 4.2 Router — LiteLLM with wildcard passthrough

**Owner:** platform/llm/config.yaml

**Wildcard routes:**
```yaml
model_list:
  - model_name: "minimax/*"
    litellm_params:
      model: "openai/*"
      api_base: "https://api.minimax.io/v1"
      api_key: "os.environ/MINIMAX_API_KEY"
  - model_name: "deepseek/*"
    litellm_params:
      model: "deepseek/*"
      api_base: "https://api.deepseek.com/v1"
      api_key: "os.environ/DEEPSEEK_API_KEY"
  - model_name: "anthropic/*"
    litellm_params:
      model: "anthropic/*"
      api_key: "os.environ/ANTHROPIC_API_KEY"
  - model_name: "openai/*"
    litellm_params:
      model: "openai/*"
      api_key: "os.environ/OPENAI_API_KEY"
  - model_name: "openrouter"
    litellm_params:
      model: "openai/nvidia/nemotron-3.5-lightning:free"
      api_base: "https://openrouter.ai/api/v1"
      api_key: "os.environ/OPENROUTER_API_KEY"
```

**Tier aliases:**
```yaml
  - model_name: "tier-fast"
    litellm_params: { model: "minimax/MiniMax-M2.7-highspeed" }
  - model_name: "tier-code"
    litellm_params: { model: "deepseek/deepseek-coder" }
  - model_name: "tier-frontier"
    litellm_params: { model: "anthropic/claude-sonnet-4" }
```

**Status:** Wildcard routing partially implemented. OpenRouter lane is live. Default/fast lanes point to MiniMax but MINIMAX_API_KEY is invalid. DeepSeek is invalid. Gemini is shape mismatch. The OPENROUTER_API_KEY was seeded 2026-09-24 and is the immediate working path.

### 4.3 Governance callbacks

**Owner:** platform/llm/efficiency_gateway.py, platform/llm/request_ceiling.py

Nine mechanisms on every routed call: cache, compaction, deduplication, ceiling, orphan removal, gisting, schema compression, observability hits, attribution.

Attribution reads `response.model` — the provider's canonical name from the response body. Never the agent-supplied string.

### 4.4 Ledger — Postgres via LiteLLM native callback

**Owner:** platform/llm/config.yaml

**Status:** Postgres callback configured. DATABASE_URL composed at boot from LITELLM_DB_PASSWORD. No JSONL writer should be active.

```yaml
litellm_settings:
  success_callback: ["langfuse", "postgres", "otel"]
  failure_callback: ["langfuse", "postgres"]
```

**Verification:** `psql $DATABASE_URL -c "SELECT count(*) FROM litellm_spend WHERE created_at > now() - interval '1 hour'"` should return a growing number.

### 4.5 Egress lock

**Owner:** platform/network/agent-egress.yaml

Default deny. Explicit allows: llm.mumchimp.com, github.com, pypi.org, registry.npmjs.org.

Explicit denies: api.minimax.io, api.deepseek.com, api.anthropic.com, api.openai.com, api.groq.com, openrouter.ai.

**Status:** Not yet verified on laptop.

### 4.6 Agent wrapper

**Owner:** bin/estate-execute

Before spawning: export base URLs, single token, harness tag. Strip provider keys. Apply egress lock.

### 4.7 Observability

**Owner:** platform/observability/

Langfuse for traces; Postgres for aggregate cost queries.

## 5. Data flows

### 5.1 Normal call (harness → provider)
```
Harness (spawned by estate-execute)
  env: OPENAI_BASE_URL=https://llm.mumchimp.com/v1
      OPENAI_API_KEY=$ESTATE_AGENT_KEY
  no provider keys in scope
  egress locked to llm.mumchimp.com
  ↓
Router
  receives {model: "minimax/MiniMax-M2.7", messages: [...]}
  wildcard match: minimax/* → api_base api.minimax.io/v1
  strip prefix: "MiniMax-M2.7"
  apply: cache, ceiling, compaction, dedup, …
  attach: MINIMAX_API_KEY from pod env
  forward
  ↓
MiniMax API
  ↓
Router callbacks fire
  success_callback: langfuse, postgres, otel
  postgres row: {model: response.model, tokens, cost, harness_tag, …}
  ↓
Harness receives OpenAI-format response
```

### 5.2 Founder adds a model
1. Founder adds key to Bitwarden.
2. Founder adds one ExternalSecret manifest to platform/secrets/ (or reuses an existing provider key — no action).
3. Flux reconciles; pod restarts with new env var.

### 5.3 Emergency change
See §6.

## 6. Break-glass / emergency change path

### Design rules
- **R1** — Two paths, one state. Hot path overrides git for its TTL. When TTL expires, effective state reverts to git automatically.
- **R2** — Every hot change is a row in estate_breakglass. Auditable.
- **R3** — Hot path is additive or overriding only. No deletes.
- **R4** — No single entry lasts more than 24h. Default TTL: 2h. Egress allowances: 30m max.
- **R5** — Hot path is logged loudly. Never silent.
- **R6** — Every verb has a git equivalent. If a break-glass verb does not correspond to a change that can be made via git, the verb is not allowed to exist.

### CLI surface
```
estate-break-glass <surface> <verb> [args] --ttl <duration> --reason <string>

Surfaces: route | key | egress | wrapper | harness | pr
Common flags: --ttl (required, max 24h), --reason (required, min 20 chars), --dry-run
```

## 7. Identity and policy plane

**Owner:** platform/identity/

Zero trust: no privileged action is carried by a standing credential.

Components:
- Identity provider: GitHub App (idp-github-app) + hardware-key attestation
- PDP (Policy Decision Point): evaluates each request
- Capability token: signed JWT — sub, aud, verb, surface, args_hash, iat, exp
- Admission checks: every privileged endpoint accepts only PDP-issued tokens

**SPIFFE state:** SPIRE IS deployed and running (namespace spire-mgmt, HelmRelease spire v0.30.1, active). Workload identity issuance to litellm router and other workloads is the §10 trust-debt item.

## 8. Implementation plan

### Step 0 — Bleed stop
- [ ] Add "postgres" to success_callback and failure_callback in platform/llm/config.yaml. DONE (already configured).
- [ ] Verify Flux reconciliation and pod restart.
- [ ] Send one request through llm.mumchimp.com. Confirm one row in litellm_spend.

### Step 1 — Ledger cutover
- [ ] Confirm Postgres rows accumulate for every routed call.
- [ ] Archive ~/.estate/efficiency-ledger.jsonl (rename to .archived).
- [ ] Delete efficiency_gateway.py's local JSONL writer. Retain in-memory mechanisms.
- [ ] Add per-mechanism metadata to Postgres rows.

### Step 2 — Wildcard routing
- [ ] Replace model list in platform/llm/config.yaml with wildcard blocks for every active provider.
- [ ] Remove all specific model-name entries and all translation aliases.
- [ ] Verify: curl -X POST https://llm.mumchimp.com/v1/chat/completions -d '{"model":"minimax/MiniMax-M2.7","messages":[{"role":"user","content":"OK"}]}' returns 200.

### Step 3 — Secret bridge
- [ ] ExternalSecrets ↔ Bitwarden wired. DONE for openrouter/exa/cursor/telegram/stripe/google_oauth. IN PROGRESS for minimax/deepseek/gemini/kimi (invalid keys). MISSING for groq/cerebras/nvidia/sambanova/cohere/typesafe (no repository secrets).
- [ ] Provider keys evicted from every other surface.
- [ ] Verify: pod env contains MINIMAX_API_KEY etc.; no other surface does.

### Step 4 — Agent wrapper
- [ ] Modify bin/estate-execute: export base URLs and single agent key.
- [ ] Fetch /v1/models and regenerate harness-specific config files.
- [ ] Inject harness and tenant tags.
- [ ] Strip provider keys from child env.

### Step 5 — Egress lock
- [ ] Define NetworkPolicy for the cluster agent arena.
- [ ] Define macOS firewall rules for laptop agents.
- [ ] Verify: from inside the arena, api.minimax.io fails; llm.mumchimp.com succeeds.

### Step 6 — Identity plane and break-glass CLI
- [ ] Provision PDP (or extend existing OIDC/App flows).
- [ ] Wire hardware-key attestation.
- [ ] Implement estate-break-glass with JIT capability issuance.
- [ ] Wire SPIRE SVIDs to replace pod env vars as the long-term fix for A4 trust debt.
- [ ] Ship the reaper and git drift detector.
- [ ] Retire standing credentials.

### Step 7 — Tier aliases and cost query tool
- [ ] Add tier-fast, tier-code, tier-frontier to router config.
- [ ] Ship estate-cost CLI with --by-harness, --by-model, --since, --mechanisms.

## 9. Acceptance criteria

1. `psql $DATABASE_URL -c "SELECT count(*) FROM litellm_spend WHERE created_at > now() - interval '1 hour'"` returns a growing number during active sessions.
2. `rg "api\.(minimax|deepseek|anthropic|openai)\.(io|com)" ~/.pi ~/.aider* ~/.config/cline ~/.config/opencode ~/.claude` returns nothing (or only URLs inside comments).
3. `rg "MiniMax-M2\.7|minimax_m27|minimax_json" platform/llm/` returns nothing.
4. From inside the agent arena: curl -m 5 https://api.minimax.io/v1/models fails; curl -m 5 https://llm.mumchimp.com/v1/models succeeds.
5. Adding a model requires only a Bitwarden entry plus at most one ExternalSecret manifest. No harness-side action.
6. Every harness in {pi, cline, aider, opencode, claude-code} launched via estate-execute produces Postgres rows tagged with the correct harness_tag.
7. `estate-cost --by-harness --since 24h` returns real cost and token totals.
8. No process writes to ~/.estate/efficiency-ledger.jsonl (file archived, writer deleted).
9. `estate-break-glass route add ... --ttl 5m` applies a route in under 5s, and the route disappears within 90s of TTL expiry.
10. `estate-break-glass active` shows zero entries during steady state.
11. Unplugging every long-lived credential from the founder's laptop and tapping the hardware key still allows a break-glass operation to succeed.
12. No standing admin credential is accepted by any privileged endpoint.

## 10. Trust-debt register

| Item | Nature of debt | Trigger to pay down |
|---|---|---|
| Pod env contains provider keys (A4) | Mounted env vars are standing credentials for the pod's lifetime | **SPIRE IS DEPLOYED** — wire SVIDs to litellm router and other workloads (Step 6) |
| ExternalSecrets operator has a standing Bitwarden credential | Operator credential is a standing secret | Bitwarden supports workload identity for the operator |
| Laptop harness runs with a static ESTATE_AGENT_KEY | Static token in env | Per-session virtual key issuance via PDP |
| Postgres read credentials for estate-cost | Currently static | JIT-issued read tokens (§7) |
| Langfuse credentials | Static | Same PDP path |
| LLM provider keys read from pod env at call time | Standing for pod lifetime | Workload-identity broker |

None of these blocks the rebuild. All are documented. All are scheduled.

## 11. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Wildcard routing breaks a provider with non-standard model-name semantics | Test each provider's wildcard before merging |
| ExternalSecrets/Bitwarden operator goes down | Pod retains last-mounted env until restart. Acceptable. |
| Postgres callback writes on the hot path | LiteLLM batches async. Monitor pod CPU. |
| Egress lock breaks a legitimate tool | Whitelist is explicit and reviewed. |
| PDP is on the critical path for break-glass | If down, break-glass falls back to standing credentials with loud warning. |
| Reaper fails silently | Per-entry TTL enforced at read time. Drift detector alerts. |
| Hot path becomes the default path | R4 TTL ceiling, R5 loud logging, R6 git equivalence, reaper. |
| SPIRE wired but not verified | Proof cronjob (platform/spire/proof-cronjob.yaml) validates SVID issuance. |

## 12. Out of scope

- Provider selection policy (which model is "best" for a task)
- Prompt-level optimizations inside harnesses
- Fine-tuning, embeddings, batch jobs
- Kubernetes and Flux rebuild

## 13. Owner checklist

**Today (bleed stop)**
- [ ] §8 Step 0 — Postgres callback confirmed. One row verified.
- [ ] §8 Step 1 — Local JSONL archived, writer deleted.
- [ ] §8 Step 2 — Wildcards replace all specific routing.
- [ ] VALIDATE: router completes with openrouter lane (nvidia/nemotron-3.5-lightning:free) — THIS IS THE WORKING PATH TODAY.

**This week**
- [ ] §8 Step 3 — Fix invalid keys in Bitwarden (MINIMAX/DEEPSEEK/GEMINI/KIMI). Set repository secrets for missing keys (GROQ/CEREBRAS/NVIDIA/SAMBANOVA/COHERE/TYPESAFE).
- [ ] §8 Step 4 — estate-execute wrapper exports base URL, single key, harness tag; strips provider keys.
- [ ] §8 Step 5 — Egress lock active on cluster and laptop.

**This month**
- [ ] §8 Step 6 — Identity plane live; break-glass CLI ships; SPIRE SVIDs wired to litellm; standing credentials retired.
- [ ] §8 Step 7 — Tier aliases defined; estate-cost shipped.
- [ ] §9 Acceptance criteria 1–12 verified.
- [ ] §10 Trust-debt reviewed and scheduled.

**Steady state**
- [ ] §6.4 estate-break-glass active returns zero during normal operation.
- [ ] §6.3 Reaper and drift detector run without incident.
- [ ] Daily ledger sanity, weekly break-glass log, monthly trust-debt review.
