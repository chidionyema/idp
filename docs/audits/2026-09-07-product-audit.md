# Product Audit v2 — 2026-09-07

Owner: chidionyema. Scope: every capability in this estate, against the commercial
opportunity the platform-engineering market actually buys. v2 supersedes v1: the v1
inventory stopped at the 23 selectable platform features and 8 product candidates.
This version adds the **pipeline work that is 80% done and not yet operationalized**
(the Model Forge, Edge Runtime, Research Engine, Agent Workforce, Cyrus, Otto
capabilities, Voice Gate, zero-trust boundary, two-hats tenant split, vendor key
activation, backstage-as-a-product, self-service golden paths, hosted session memory,
client-context ingest), and adds the **combinations that compose multiple blocks
into a single sale**, plus the **install UX, point-of-sale motion and integration
surface** the v1 audit did not address.

Read-only audit. No code was changed. Sourced from `README.md`, `docs/explanation/`,
`docs/specs/`, `docs/decisions/`, `platform/features/features.yaml`,
`catalog/ports.yaml`, `docs/audits/2026-09-06-portal-audit.md`, `docs/SHOWCASE.md`,
`SALVAGE.md`, the `forge/`, `sovereign/`, `platform/*` trees, and four batches of
market research (full source list at the end).

---

## TL;DR

This estate is not "a collection of unfinished platforms." It is **two parallel agent
stories running on a single IDP substrate**:

1. The **frontier-agent story**: Hermes-v2 / Otto / Sovereign / Cyrus / MCP, on the LLM
   gateway, doing judgment and orchestration.
2. The **small-model story**: Model Forge + Edge Runtime, training 0.6B–1.7B models on
   Modal for narrow classification, deploying on the ARM64 nodes as the fallback or
   the only option.

Both stories are 80% done. Neither is packaged. **What the estate has is more than
what it sells, and what it sells is less than what it has.** That is the problem and
that is the opportunity.

The headline findings of this v2 audit:

- **8 v1 product candidates still hold.** They were the right list. They are not
  enough. The v1 audit stopped at the platform boundary; this version pulls the
  pipeline into the room.
- **5 new product candidates emerge** when you look at the pipeline: Model Forge as
  a service, Edge Runtime as a service, the Otto assistant as a product (not just
  the founder's bot), the zero-trust boundary as a service, and the agent workforce
  + research engine as a packaged automation platform.
- **3 combinations compose into the highest-margin sale**: the **AI-safe portal**
  (Platform + Voice Gate + MCP gateway + LLM gateway), the **private inference
  stack** (Model Forge + Edge Runtime + LiteLLM with abstain), and the
  **compliance-as-code bundle** (Platform + Trivy + Rego + License gate + Placement).
- **Install UX is the single biggest gap.** The estate has the bits; it has no
  *one thing a buyer installs and runs in 30 minutes.* That is the wedge that turns
  13 catalogue entries into 13 product pages.
- **Market nous is the second biggest gap.** The buyer-facing copy, the demo
  video, the security one-pager, the ROI calculator, the case study, the
  procurement-grade FAQ — none exist. The estate's foundation is solid; the
  surface a buyer meets is still a link farm in some places.

The market window is open. IDP is $10B now, $30B+ by 2031. Backstage is the only
CNCF-graduated platform, and Spotify just split its commercial features out into a
paid product. The buyers are not asking "do you have a portal?" — they are asking
"can you tell me what is running, what it costs, and prove it is safe." This estate
already answers every one of those questions. The work is the packaging.

---

## 1. What we have — the platform, the products, and the pipeline

The estate has four layers. The v1 audit covered the first two; v2 adds the third and
the fourth.

### 1.1 Platform (the IDP substrate)

Per `README.md` and `docs/explanation/architecture-overview.md`, every layer is one
instance and lives in `idp`:

| Layer | What it does | Where |
|---|---|---|
| Catalogue as source of truth | One inventory, two renderers (Backstage + Datasette), switch-only fallback | `bin/catalog-gen`, `bin/db-gen`, `backstage/` |
| Identity (SSO + SPIRE + Tailscale) | Federated login, workload identity, tailnet | `platform/spire`, `platform/identity`, `platform/tailscale` |
| Edge & DNS (Traefik + external-dns) | One published URL, TLS, cert renewal | `platform/edge`, `platform/dns` |
| Secrets (External Secrets over OCI Vault + Bitwarden bridge) | Static + dynamic, no in-cluster `Secret` literals, human-in-the-loop door | `platform/secrets`, `platform/secret-store`, `platform/human-vault-bridge`, `platform/human-vault` |
| Model routing (LiteLLM) | Per-lane budgets, spend breaker, no provider lock-in | `platform/llm` |
| Traces & audit (Langfuse + OTel) | Every model call, cost, prompt is a trace | `platform/observability`, `platform/observability-collector` |
| Scheduling (Dagster) | Scheduled jobs, success-fail pings | `platform/scheduling` |
| CI & supply chain (GitHub Actions + Flux + syft/grype) | SBOM, CVE scan, license gate | `bin/supply-chain` |
| Chaos & drills | What breaks first, measured | `platform/chaos`, `platform/drills` |
| Policy (Kyverno + Rego) | License, placement, capacity admitted by the plane | `policy/*.rego`, `bin/idp-rules`, `platform/kyverno` |
| Agent interface (MCP + Sovereign Bus) | One door per agent, audited, governed | `mcp/`, `sovereign/`, `platform/agentgateway` |

The header rule from `README.md` is the load-bearing one: *"We are selling this. Buy
the mature platform. Do not stitch one."* `prospector`, `hermes-v2`, `consultd`,
`kimi_bridge`, `board_serve`, `sovereign-cockpit` are products that run on the
platform; they carry no copy of any platform layer.

### 1.2 Products (code that runs on the platform)

Per `catalog/ports.yaml` and the catalogue entries observed:

| Product | Port | Description (literal catalogue text) | Status |
|---|---|---|---|
| **prospector** | 3000, 5291, 8080, 8443, 8611 | "finds and qualifies prospects" | The only product with a real description. Three repos (engine, store-api, store-web). |
| **hermes-v2** | (per `platform/otto-gateway/`) | "agent that acts for the founder from anywhere: Telegram in, PR or run out" | Telegram in, SOPS/Flux out. Production for the founder. |
| **prospector-live** | — | "Everything the prospector-live repository holds and runs" | Generic; not a packaged product page. |
| **claude** | — | "Everything the claude repository holds and runs" | Generic. |
| **lux** | — | "Everything the lux repository holds and runs" | Generic. |
| **popdd-py**, **popdd-ts** | — | "Everything the X repository holds and runs" | Generic. |
| **sentinel-loop** | — | "Everything the sentinel-loop repository holds and runs" | Generic. |
| **signalengine** | — | "Everything the signalengine repository holds and runs" | Generic. |
| **vault-201** | — | "Everything the vault-201 repository holds and runs" | Generic. |
| **estate** | — | "Everything the estate repository holds and runs" | Generic. |
| **consultd** | 8765 | (no entry seen) | Per `catalog/ports.yaml`, a service on the platform. |
| **kimi_bridge** | 8766, 8767 | (no entry seen) | Bridges to a model. |
| **board_serve** | 8787 | (no entry seen) | Board-meeting surface. |
| **sovereign-cockpit** | 8788 | (no entry seen) | The control plane for agents. |

What this table says, plainly: **9 of 13 products have a 12-word catalogue description
because nobody wrote product copy.** They are not "less real" than prospector; they
are just less packaged.

### 1.3 Pipeline work that is 80% done and not yet operationalized

This is the new section v2 adds. Every item below is a real, partly-implemented
capability whose packaging is the work, not its construction.

| # | Pipeline item | Where it lives | What is done | What is not |
|---|---|---|---|---|
| **P1** | **Model Forge** | `forge/`, spec `docs/specs/2026-09-06-model-forge-edge-runtime.md` | Modal launcher (`modal_app.py`), Unsloth LoRA trainer (`train.py`), dataset collector (`collect_ci_runs.py`), `task.yaml` schema, first task `ci-flake-triage` (crew#885), example-classify task, export to GHCR as OCI artifact, Langfuse trace | The held-out eval gate is built; production traffic has not run yet. The first real task (`ci-flake-triage`) is in a fixture, not on the queue. |
| **P2** | **Edge Runtime** | same spec | Rust service spec, ARM64 image pipeline (already builds `linux/arm64`), GGUF `q4_k_m` export, OpenAI-compatible endpoint contract | Not deployed; no production traffic; no benchmark on the A1 node yet. |
| **P3** | **Cyrus** | `platform/cyrus/` | A worktree+engine+PR agent that picks up Linear/GitHub issues; pod deployed; per its README, holds no cluster verbs; four walls documented (config path, loopback bind, webhook routes, identity) | Per the README, four walls were measured broken in the running pod; the fix is in `fix/cyrus-webhook-routes` but the empirical proof (a real Linear ticket turning into a PR) is not yet on the log. |
| **P4** | **Agent Workforce** | `platform/agent-workforce/` | crewAI cronjob, persistent volume, `agent-workforce-data` PVC, no Role or RoleBinding (correctly: no agent touches the cluster again), `AGENT_WORKFORCE_STORAGE_DIR` | The cronjob is wedged. Per the portal-100 spec, "crew is not taking its queue" — 1788 min waiting. Root cause not yet identified. |
| **P5** | **Research Engine** | `platform/research-engine/` | Cronjob with pull-secret, namespace, ExternalSecret | I have not read its HANDOFF; per the layout, it is a recurring research job. Whether it produces an artifact or just stores results needs review. |
| **P6** | **Otto five capabilities** | `docs/specs/otto-five-capabilities-finished.md` | Edge-TTS voice replies (built, off by default), screenshot handler (template only, flag decorative), bench (name only), speech-to-text (built, broken in cluster — `faster-whisper` not in image), vision (built, mis-pointed, fix merged in hermes-v2 #86, not yet proved) | None of the five are operationally finished; STT is the only one with a clear blocker. |
| **P7** | **Voice Gate** | `platform/voice-gate/` | Python half merged on prospector main; Rust half port 8420, 12 tests pass, branch `fix/cyrus-webhook-routes` pushed | The Rust half is in a branch; not on main; no customer-facing install path. |
| **P8** | **Zero-trust boundary** | `docs/specs/zero-trust-boundary.md`, `platform/calico/` | 154 NetworkPolicy objects exist; `bin/idp-ci` refuses a namespace without both-ways default-deny; Calico manifests in repo | No enforcement agent in cluster (only flannel). Measured RED on 2026-09-05: a pod in a fenced namespace reached the internet and a cross-namespace pod. Calico policy-only mode is the planned fix. |
| **P9** | **Two-hats tenant split** | `docs/specs/two-hats-tenant-split.md`, decision 0021 | `TaskEnvelope.tenant_id` is end-to-end; gateway stamps by binding; `estate/plane: control\|tenant` field to be added; `bin/idp-tenant-split` gate spec'd | Six changes in order, none complete. The first change (customer bot becomes a tenant of its own) is a one-row YAML edit. |
| **P10** | **Vendor key activation** | `docs/specs/vendor-key-activation.md` (336 lines) | Vendor key lifecycle, console-onboarding, seed-vault-road, per-vendor `ExternalSecret` pattern | The spec exists. No vendor has been onboarded through this path end-to-end with the gate green. |
| **P11** | **Backstage-as-a-product** | `docs/specs/backstage-as-a-product.md` | CP1 (showcase as in-house page) through CP8 (login-drill default paths) all written as ordered checkpoints | Not started. 43 of 52 founder surfaces are level-1 (link only); 64 of 64 platform layers are level-1 on the card. |
| **P12** | **Self-service golden paths** | `docs/specs/self-service-golden-paths.md` | The spec defines the paths a buyer walks in the portal to enable a feature | The portal already has scaffolder buttons (`backstage/templates/founder-actions/`, 29 generated); the spec refines the path UX. |
| **P13** | **Hosted session memory** | `docs/specs/hosted-session-memory.md` | `claude-mem` server runtime, shared Postgres, LiteLLM-routed compression model, no client-local storage | Status: planned in `features.yaml`. Floor typed. No pod. |
| **P14** | **Client-context ingest** | `docs/specs/client-context-ingest-and-session-runtime.md` | The four context kinds (estate, catalog, constraint, workaround), MCP resource serving, snapshot producer, memory store | Status: planned in `features.yaml`. Floor typed. The door, the snapshot producer and the memory store it reads are already running under `[mcp]`. |
| **P15** | **Drills** | `platform/drills/`, `bin/portal-freshness-drill`, `bin/door-probe` | Hourly drills, receipts to the collector, freshness gate in `bin/idp-verify` | The drill is run hourly; the freshness gate is new; some drills are row-only (`bin/idp-verify` refuses those). |

The pattern is the same in every row: the spec exists, the code is partly written,
the gate is designed, and the proof — the live log line, the green drill, the held-out
eval — is what's missing. **The estate has 15 pipeline items in this state.** None of
them is more than 6 weeks from "finished." All 15 are saleable on their own.

### 1.4 Capabilities (commercializable on their own)

The `platform/features/features.yaml` register lists 23 selectable features; each is
a swappable tier of a platform capability. A subset of them is already product-shaped —
already proved under load, already governed by the platform, already documented. They
are listed below in the order they map to commercial products in Section 3.

| # | Capability | File path | Why it is product-shaped |
|---|---|---|---|
| 1 | **Voice Gate (deterministic prose linter)** | `platform/voice-gate/` | Python half merged; Rust half port 8420, 12 tests pass. Works on commit-time, not at inference. |
| 2 | **Sovereign Bus / MCP gateway** | `mcp/`, `sovereign/`, `platform/agentgateway` | One door, consensus-gated, audited, governed. Not a stub. |
| 3 | **LLM gateway with spend discipline** | `platform/llm/` | LiteLLM with per-lane budgets, $176M tokens tracked before $0/minimax row bug; spend breaker on (rewritten 2026-09-04, the original measured nothing and stopped nothing). |
| 4 | **Traces & audit (Langfuse + OTel)** | `platform/observability/` | Already shipping; OTel collector as fallback when Langfuse is down. |
| 5 | **Inventory + dual renderers** | `bin/catalog-gen`, `bin/db-gen` | Two renderers, one source, runtime-separated fallback. The fallback was the bug that was in Datasette; it is fixed. |
| 6 | **Policy-as-code (Rego + conftest)** | `policy/*.rego`, `bin/idp-rules` | License, placement, capacity gates with fixtures. |
| 7 | **Secrets bridge (Bitwarden → OCI Vault)** | `platform/human-vault-bridge` | Unique; bridges a personal vault to a workload-grade vault via External Secrets. |
| 8 | **Webhooks → worktrees (Cyrus)** | `platform/cyrus/` | Linear/GitHub in, worktree + engine + PR out. Per its README, holds no cluster verbs. |
| 9 | **Workflow engine (Temporal / Windmill)** | `platform/temporal/` | One tier suspends (Temporal), the other selects (Windmill). Choose at deploy time, not at runtime. |
| 10 | **Agent memory (Hindsight API)** | per features.yaml | Per-session persistence, configurable. |
| 11 | **Supply-chain audit (SBOM + grype)** | `bin/supply-chain` | Per-build SBOM, license gate, vulnerability report. |
| 12 | **Healthchecks + drill-grade SLOs** | `bin/placement-audit` | Heartbeat, placement probe, drill gate. |
| 13 | **Model Forge (small-model factory)** | `forge/`, `docs/specs/2026-09-06-model-forge-edge-runtime.md` | Modal + Unsloth + Qwen3 0.6B/1.7B; OCI artifact; first task `ci-flake-triage`. |
| 14 | **Edge Runtime (private inference on ARM64)** | same spec | Rust service, OpenAI-compatible endpoint, GGUF `q4_k_m`, abstain signal. |
| 15 | **Zero-trust boundary (Calico policy-only)** | `docs/specs/zero-trust-boundary.md`, `platform/calico/` | Turns on 154 dormant NetworkPolicy objects with one CNI sidecar. The smallest change that closes the defect. |
| 16 | **Two-hats tenant split** | `docs/specs/two-hats-tenant-split.md`, decision 0021 | The control-plane vs. tenant-plane boundary, end-to-end. |
| 17 | **Vendor key onboarding** | `docs/specs/vendor-key-activation.md` | A vendor pastes one key at one console; the gate refuses everything else. |
| 18 | **Hosted session memory (claude-mem)** | `docs/specs/hosted-session-memory.md` | Server-side, shared Postgres, no client-local storage. |
| 19 | **Client-context ingest** | `docs/specs/client-context-ingest-and-session-runtime.md` | The four context kinds served as MCP resources. |
| 20 | **Drills as features** | `platform/drills/` | What breaks first, measured, on a clock. The drill is the SLO. |
| 21 | **Backstage-as-a-product (level-3/4 surfaces)** | `docs/specs/backstage-as-a-product.md` | 43 link-only founder surfaces + 64 link-only platform layers become interactive, level-3/4. |
| 22 | **Self-service golden paths** | `docs/specs/self-service-golden-paths.md` | The path a buyer walks to enable a feature. |
| 23 | **Otto five capabilities** | `docs/specs/otto-five-capabilities-finished.md` | TTS, STT, vision, screenshot handler, bench — five pieces of the assistant. |
| 24 | **Agent Workforce (crewAI automation)** | `platform/agent-workforce/` | A queue-fed agent workforce, persistent memory, no cluster writes. |
| 25 | **Research Engine** | `platform/research-engine/` | A recurring research job. |

Six more product candidates than v1 found, because v1 stopped at the platform
boundary and did not pull the pipeline into the room.

The other features in `features.yaml` (chaos, autoscaling, dev-loop, staging, etc.)
are platform capabilities that **sell with the platform, not as products.** They
belong on the platform price page as a tier knob.

---

## 2. What the market buys

From four batches of web research (12 sources in total; full source list at the end).

### 2.1 Market sizes that matter

| Market | Size 2026 | Source | CAGR |
|---|---|---|---|
| Platform engineering / IDP | **$10.4B** | Mordor Intelligence | 24.8% → $31.6B by 2031 |
| Platform engineering / IDP (alt) | $8.9B | SNS Insider | 21.3% → $50B by 2035 |
| MCP gateway segment | small, immature | Agentery | — |
| Policy-as-code | — | — | — |
| LLM gateway | — | — | — |

The two IDP estimates diverge by analyst, not by definition. Both put the market at
$10B+ in 2026 and $30B+ by 2031. Build-vs-buy TCO ranges (per Zuplo / developerportalcost):
custom $200K–$2M 3-yr; Backstage self-hosted $300K–$1M 3-yr; commercial SaaS $12K–$300K.
The mid-market buyer's choice is increasingly "Backstage-as-a-Service," not "build it."

### 2.2 The three buying motions buyers use

1. **Replace an internal Backstage build.** Two-thirds of new portal deals are a
   self-hosted Backstage that has been in production for 6–18 months and is hitting the
   wall of: catalog drift, auth integration, ticket backlog. The buyer is a platform
   engineering lead; the sale needs SOC 2, K8s-native, no per-seat.
2. **Buy an IDP for compliance.** A SaaS scaleup needs an audit story for SOC 2,
   ISO 27001, "what is running in prod, who owns it, what did we ship this week." They
   don't want to be a Backstage admin. The buyer is a CTO/Head of Platform who has
   4 hours a week for this problem.
3. **Wrap an AI rollout in something safe.** The current buying cycle is
   "we just bought an LLM API and now compliance is asking us to prove nothing leaked
   and the spend was sane." The buyer is a security engineering lead. They need
   trace + cost + audit, not chat.

The estate already answers all three. None of them is a single product page today.

### 2.3 What the adjacent comparables cost

| Adjacent | Vendor | Public pricing | Where this estate fits |
|---|---|---|---|
| Hosted Backstage | Roadie, Spotify Portal, Red Hat Dev Hub | Per-seat, public | Our platform is sellable against this |
| MCP gateway | Permit.io | $25/mo entry, custom Enterprise | Our Sovereign Bus is an enterprise MCP gateway without the SaaS wrapper |
| LLM gateway | OpenRouter, Portkey, Helicone | Credit / per-log / cloud | Our LiteLLM is on-prem + budget-graded — competing on cost discipline, not feature count |
| OPA enterprise | Styra DAS | AWS Marketplace, no public list | Our Rego + conftest is governance, not Styra-grade UI; below them on UX, above them on integrated |
| Bitwarden-to-K8s | (Bitwarden Secrets Manager + ESO) | Per-user Bitwarden | Our `human-vault-bridge` is the only "personal vault bridges to workload vault" pattern in market |
| Workflow engine | Temporal ($100/mo entry, Enterprise custom) / Windmill ($1/mo + $170/mo Enterprise) | Both public | We ship both, choose at deploy, off by default — a "you don't pay until you turn it on" model |
| LLM observability | Langfuse Cloud Enterprise $2,499/mo + unit pricing | $8/100k units | We already self-host; the gap is a customer-facing Langfuse dashboard |
| Prose linter / house-voice | StyleMCP, Slop Sentry, Veldica | Per seat | Our Voice Gate is deterministic and Rust-deployable; market is nascent |
| Tiny-model serving | vLLM, llama.cpp, Modal, Ollama | Mix of OSS + per-GPU-hour | Our Forge + Edge Runtime competes on **task-specific distillation**, not on raw serving — different product |
| Workflow agents | Lindy, Relay, n8n + AI | Per seat / per run | Our Cyrus is "self-hosted, cluster-aware, holds no cluster verbs" — different product |
| Compliance audits | Drata, Vanta, Secureframe | Per-employee / per year | Our Compliance Pack is the engineering layer (CI image, Rego), not the GRC layer (dashboards). They could be a pair. |

---

## 3. The product packaging — 13 candidates, in 4 tiers

Eight candidates from v1 still hold. Five new ones emerge from the pipeline. They
are listed below by tier of ship-readiness. "Tier 0" ships in 30 days with the work
mostly done; "Tier 3" is a 6–12 month effort.

### Tier 0 — ship within 30 days

**Product 1 — Voice Gate.** A deterministic, version-controlled prose linter that a
team runs in CI to enforce house voice on every commit and PR. Domain: editorial teams,
marketing orgs at SaaS companies, content publishers with brand-voice guidelines.
- What the buyer gets: a binary or container, a `voice-policy.yaml`, a CI step, a
  pre-commit hook. Detection rules cover "assistant residue," cadence, banned tokens,
  punctuation density. 12 tests pass; Rust half is on `fix/cyrus-webhook-routes`.
- Pricing motion: per-language (EN/ES/JA pre-bundled), $50/seat/mo for teams, custom
  for publishers with 100+ authors. Below Veldica on UX, above them on being
  commit-time not inference-time.
- One founder note already on record: one engine, deterministic gate only, no
  semantic tier. That is the product strategy.

**Product 2 — Inventory + dual-renderer.** A drop-in Backstage + Datasette pattern that
takes one YAML/JSON source and serves it two ways. Domain: platform teams at
$20M-$200M ARR SaaS companies that have outgrown a wiki and don't want to be a Backstage admin.
- What the buyer gets: an inventory format, two renderers, the failover contract,
  the upgrade contract. The failover was the bug that was in Datasette; it is fixed.
- Pricing motion: per-tenant subscription. The two-renderer fallback is the
  differentiator: competitor portals go down with their runtime; this estate's
  fallback has a separate runtime by design.

**Product 3 — Otto Assistant.** The Hermes/Otto runtime, packaged as a personal
assistant that lives in a Telegram chat (or any channel the buyer chooses). Domain:
founder/CEO/exec operators who want one chat to run their platform.
- What the buyer gets: an agent runtime (the Sovereign Bus), a channel binding,
  the LLM gateway with their budgets, the spend breaker, the trace pipeline, the
  Memory (Hindsight) for cross-session recall. Five capabilities per
  `docs/specs/otto-five-capabilities-finished.md` — TTS, STT, vision, screenshot,
  bench — are all built, four need proof.
- Pricing motion: per-assistant subscription; per-token volume through the gateway.
  The closest comparable is Lindy or Relay; ours is on-prem and cluster-aware.

### Tier 1 — ship within 90 days

**Product 4 — MCP Gateway.** The Sovereign Bus, packaged as a hardened proxy in front
of an enterprise's MCP servers. Domain: enterprises that have already deployed agents
and need a single audited, governed door. Permit.io ships this at $25/mo entry; their
enterprise path goes 4-figure/mo. Our differentiator is "the door carries identity
(SPIRE) + policy (Kyverno/Rego) + a budget, not just an OAuth proxy."
- What the buyer gets: agentgateway deployment, SPIRE-issued workload identity, the
  policy bundle, the Sovereign Bus for fan-out.
- Pricing motion: per-agent-per-month, like Permit but priced for the governance row.

**Product 5 — Spend-bounded LLM gateway.** LiteLLM, hardened, with the per-lane budget
breakers and the spend dashboard. Domain: SaaS scaleups with an LLM rollout that needs
an audit story. OpenRouter (credit/marketplace) and Portkey (per-log) are the comps.
- What the buyer gets: gateway, the spend breaker, the trace pipeline, the cost-per-team
  view.
- Pricing motion: by token volume, with a floor. The differentiator is "we cannot
  lose you money" — the budget is enforced at the proxy, not at the bill.

**Product 6 — Model Forge as a Service.** The `forge/` pipeline as a hosted product.
Domain: platform teams at SaaS scaleups that want narrow task classification without
paying frontier rates per call. The estate's first task — CI flake triage — is a
real example: a 0.6B LoRA reads the failed step's log tail and says "flake" or "real,"
abstains below 0.80 confidence, and pays cents per run on Modal instead of dollars
per call on the router.
- What the buyer gets: a task schema (`task.yaml`), a dataset collector
  (`collect_ci_runs.py`), the trainer (`train.py`), the artifact format, the
  evaluation gate, the OCI artifact push, the Langfuse trace, and the Edge Runtime
  to deploy it.
- Pricing motion: per-task training fee + per-1k-inference fee. Below Modal's raw GPU
  rate by bundling the eval/artifact path; above the frontier-call rate by being
  the *only* product that ships the held-out eval gate.
- Differentiator: **task-specific distillation with a refusal gate.** Modal and
  Unsloth are tools, not products. The product is the workflow: examples in, eval
  gate, abstain signal, OCI artifact.

**Product 7 — Edge Runtime as a Service.** The Rust ARM64 service that loads a GGUF
and answers single-task inferences with an abstain signal. Domain: any enterprise
that wants private, on-prem inference for narrow tasks. The closest comp is Ollama or
llama.cpp, but ours is purpose-built for the Forge's artifact format and exposes an
abstain signal so the buyer can fall back to the router.
- What the buyer gets: the binary, the OCI artifact pull, the OpenAI-compatible
  endpoint, the abstain signal, the LiteLLM `abstain_below` integration.
- Pricing motion: per-node-per-month; per-token on the served model.

### Tier 2 — ship within 6 months

**Product 8 — Zero-trust boundary as a Service.** Calico policy-only mode installed
beside flannel, turning on the 154 dormant NetworkPolicy objects with the audit log
captured first and the enforcement gated to the policies that actually permit real
traffic. Domain: any enterprise running k8s that wants Zero Trust without a CNI
migration.
- What the buyer gets: a one-CNI-sidecar install (Calico policy-only), the audit
  run, the gate, the policy bundle, the drills (`platform/drills/`), the live
  enforcement proof.
- Pricing motion: per-cluster-per-month; per-policy-row beyond a floor.
- Differentiator: the audit step. Most "zero trust in a day" pitches skip the audit
  and risk an estate-wide outage on the cutover. This estate's spec is "log-only
  posture for one full day, then enforce." That is the sale.

**Product 9 — Secrets Bridge (Bitwarden → Vault).** The `human-vault-bridge`
packaged: a Bitwarden-side operator plus an ESO bridge to OCI Vault (or any Vault).
Domain: enterprises where operators hold shared credentials in Bitwarden and
workloads need them as Kubernetes secrets. This is a thin product, but the pattern
is unique.
- Pricing motion: per-seat (Bitwarden side) + per-workload (bridge side).

**Product 10 — Compliance Pack.** The Rego rules + conftest + license/placement/capacity
gates, packaged as a CI image: `bin/idp-rules run --plane ci`. Domain: any company that
needs SBOM + license + placement evidence for SOC 2 / ISO 27001 / vendor security review.
Styra DAS competes here; our version is not UI-grade, but it is "you don't have to stand
up Styra."
- Pricing motion: per repo, per org.

**Product 11 — Agent Workforce + Research Engine.** A packaged automation platform:
crewAI cronjob for the queue, persistent memory for the recall, the Research Engine
for the periodic jobs. Domain: platform teams that want a self-hosted Lindy/Relay
without giving a vendor access to their repo and cluster. Per the portal-100 spec,
the agent-workforce cronjob is wedged (1788 min waiting) — this product cannot
ship until that is fixed.
- Pricing motion: per-agent-per-month; per-task execution.

### Tier 3 — strategic, 6-12 months

**Product 12 — The Platform itself.** The IDP-as-a-Service: catalogue, identity,
edge, secrets, model routing, traces, scheduling, supply chain, policy, agent
interface — sold as a managed deployment on a tenant's cluster (or ours). This is
the highest ceiling and the longest cycle. It is also the "mature platform, do not
stitch one" the headline already calls out.
- Two-hats pattern: founder is both estate superadmin and customer zero
  (decision 0021, `docs/specs/two-hats-tenant-split.md`).
- Pricing motion: annual subscription, tiered by node size and feature tier.

**Product 13 — Vendor Key Activation.** The vendor key lifecycle
(`docs/specs/vendor-key-activation.md`) packaged as a service for vendors who want to
sell into our catalogue. Domain: AI vendors who want a one-line onboarding into the
estate, with a key minted by the platform rather than pasted at a console.
- Pricing motion: per-vendor activation fee; per-call volume.

---

## 4. Combinations that compose

Three product pairs compose into a sale that is more than either alone. These are
the bundles with the highest margin and the strongest "one story" for the buyer.

### 4.1 The AI-safe portal

**Components:** Platform + Voice Gate + MCP Gateway + LLM gateway + Spend breaker.
**Story the buyer tells their board:** "We shipped AI to production in week 4, with
every call traced, every action governed, every $ capped, and every output's voice
reviewed."
**Margin:** highest. Each component is a product on its own; the bundle is sold as
the "AI rollout done right" SaaS for mid-market companies.
**Buyer:** a security engineering lead at a SaaS scaleup.

### 4.2 The private inference stack

**Components:** Model Forge + Edge Runtime + LiteLLM with abstain signal.
**Story the buyer tells their board:** "We pay frontier rates for judgment, cents
per hour for narrow classification, and we hold the artifacts in our own registry."
**Margin:** high. The product is the workflow (examples in, eval gate, OCI artifact,
Rust deployment), not the tools.
**Buyer:** a platform team at a SaaS scaleup with an LLM rollout.

### 4.3 The compliance-as-code bundle

**Components:** Platform + Trivy + Rego rules + License gate + Placement gate +
Supply-chain audit.
**Story the buyer tells their board:** "What runs, in whose pocket, with what
licenses, with what CVEs, on a clock."
**Margin:** medium. Competes with Styra DAS on UX, beats it on integrated cost
(bundle of the platform + the rules + the drills).
**Buyer:** a CTO/Head of Platform at a $20M-$200M ARR SaaS company that needs SOC 2
or ISO 27001 evidence.

### 4.4 The Zero-Trust estate

**Components:** Platform + Calico policy-only + Two-hats tenant split + Drills.
**Story the buyer tells their board:** "Every pod's traffic is enforced by the
network, not the application; every tenant is in its own lane; every drill proves
the SLO."
**Margin:** medium. The audit step (one full day of log-only posture) is the
differentiator.
**Buyer:** a security engineering lead at any enterprise running k8s.

### 4.5 The engineering operations automation

**Components:** Cyrus + Research Engine + Agent Workforce + Forge (CI flake triage
task).
**Story the buyer tells their board:** "Linear tickets turn into PRs without a
person; CI red turns into triage without a person; research runs on a clock without
a person."
**Margin:** high. The product is the integration; each piece is already partly
shipped (Cyrus pod exists; agent-workforce is wedged; Forge first task is in a
fixture).
**Buyer:** a CTO at a fast-moving SaaS scaleup with 20+ engineers.

### 4.6 The dogfood chain

The estate itself is a customer of every product above. Voice Gate lints portal
copy (Lane 7 of the portal-100 spec). The Forge trains a CI-flake-triage model that
runs in `bin/idp-ci`. Cyrus picks up Linear tickets and runs a Forge task. Drills
prove every product's SLO. The dogfood story is the most credible sales story a
buyer can be told: **we ship this because we use this.**

---

## 5. The install UX — what a buyer meets on day one

The v1 audit identified "no customer-facing docs" and "no trial" as cross-cutting
gaps. v2 turns those into a concrete install path.

### 5.1 What day one looks like for a buyer today

**Today**, the install path is:
1. The buyer reads `README.md`. It is 80% operator-focused.
2. The buyer finds the platform GitHub repo and reads `docs/explanation/`.
3. The buyer asks: "How do I run this on my cluster?"
4. There is no answer in 30 minutes. The answer is: read `bin/idp-up`, read the
   `bin/catalog-gen` and `bin/db-gen` adapters, read the inventory spec, install
   Backstage and Datasette, configure SSO, point the inventory at your YAML.
5. The buyer gives up at step 4 or hires the founder.

**The wedge**: a buyer-installable image that runs the platform on a fresh k3d
cluster in 30 minutes, with SSO pre-wired, one sample tenant, and the showcase
page rendering live.

### 5.2 What day one should look like (the install wedge)

The install wedge is a single image — `idp/quickstart` — that:

1. **Spins up a k3d cluster** with the platform pre-installed.
2. **Pre-wires SSO** with a Keycloak realm reachable through the portal
   (`docs/decisions/0013-customer-identity-is-keycloak-and-the-realm-is-code.md`).
3. **Seeds one sample tenant** with 10 platform-layer entities and 10 founder-surface
   entities, each at level 3–4 (drawn, interactive, not link-only) — the showcase
   is the buyer's first impression.
4. **Lands a `/showcase` page** with the live estate bar (entities ELITE/GAP/BLIND),
   per-system health donuts, the five Otto LIVE capabilities, and the **buyer
   sandbox launch button** (CP2 of `docs/specs/backstage-as-a-product.md`).
5. **Runs a drill** in the first 60 seconds: `login-drill.yml` against the
   buyer's `/showcase`, `/tools`, `/ops` paths. Screenshot evidence lands in
   the collector.
6. **Prints the next 5 commands** the buyer runs to enable the next feature
   (`docs/specs/self-service-golden-paths.md`).

**The drill is the demo.** The buyer does not read a pitch deck; the buyer presses
the button and sees the donut render. The drill runs hourly; the screenshots are
the case study.

### 5.3 Connecting to existing client systems

The wedge above runs on k3d. The real buyer has an existing cluster, an existing
identity provider, an existing secret store, an existing CI, an existing trace
backend. The platform must integrate with what is already there. The integration
surface:

| System the buyer has | What the platform integrates with | Where |
|---|---|---|
| AWS / GCP / Azure / OCI | Kustomize overlays for the cluster; per-cloud secrets; per-cloud identity | `platform/oci/`, `bin/idp-migrate-domain` |
| Okta / Auth0 / Google / Azure AD | OIDC at the gateway (`docs/decisions/0007`); no local password | `platform/identity/` |
| HashiCorp Vault / AWS Secrets Manager / Doppler / Bitwarden | External Secrets Operator with a vendored backend | `platform/secrets/`, `platform/human-vault-bridge/` |
| GitHub Actions / GitLab CI / CircleCI | The platform's supply chain runs on the buyer's CI; SBOM + grype + license gate | `bin/supply-chain` |
| Datadog / Honeycomb / Grafana Cloud / New Relic | OTel collector as the platform's trace surface; SigNoz optional | `platform/observability/` |
| Linear / Jira / GitHub Issues | Cyrus is the bridge — Linear/GitHub in, worktree+engine+PR out | `platform/cyrus/` |
| OpenAI / Anthropic / Google / DeepSeek / Kimi / local Ollama | LiteLLM as the model router; per-lane budgets | `platform/llm/` |
| Slack / Telegram / Discord / Email | Apprise in `platform/notify/` as the unified notifier | `platform/notify/`, `platform/notify/apprise-api.yaml` |
| Postgres / MySQL / SQLite | Lago commerce, the estate DB, the catalogue DB — all backends supported | `platform/commerce/`, `bin/db-gen` |
| A buyer's existing Backstage | The dual-renderer pattern: the buyer's Backstage + Datasette as the fallback | `bin/catalog-gen`, `bin/db-gen` |

The integration surface is broad, but each row is one integration point with one
gate. The buyer does not need a "connector library" — they need a one-line config
change to point the platform at what they already have.

### 5.4 First-time user experience (the 30-minute walk)

The install wedge above is the first 30 minutes. The next 30 minutes are:

1. **Add the buyer's first platform-layer entity** (their main service). The
   scaffolder template dispatches a GitHub Action that opens a PR to their repo
   with `catalog-info.yaml` + `kubernetes-label-selector` annotation. The PR
   lands via Flux; the entity appears on `/showcase` within 10 minutes.
2. **Connect their existing identity provider.** One command, one config file,
   one OIDC client secret. The buyer uses their own login.
3. **Enable one feature** from the self-service golden paths (`docs/specs/
   self-service-golden-paths.md`). The default is "vulnerability scanning" —
   it is the lowest-risk, highest-value, single-flag turn-on (`bin/idp-features
   plan` shows the floor; the buyer approves the plan).
4. **Run the drill.** `login-drill.yml` against the buyer's paths. The drill
   runs hourly from now on.
5. **Hand off.** The buyer has a working portal, a working drill, one feature
   turned on. The next 30 minutes are on the buyer's schedule.

---

## 6. Point-of-sale thinking — the surface a buyer meets

The estate's foundation is solid. The surface a buyer meets is the install wedge
above; the surface a buyer reads is the procurement-grade FAQ, the security
one-pager, the case study, the demo video, and the pricing page. None of these
exist yet. v2 maps what each must say.

### 6.1 The pricing page

The estate has tiered features. It does not have dollar signs. **Each product in
Section 3 needs a one-page pricing sheet with three tiers (Solo / Team /
Enterprise) and one "Contact us" row for the platform itself.** The pricing page is
not a number; it is a sentence. The sentence is: "you can start free, you can grow
into a number, you can call us for the platform."

### 6.2 The demo video

A 90-second video: the install wedge above, in real time, with no narration but
with the drill receipts on screen. The drill is the demo. The screenshot is the
case study. **The buyer does not read a pitch deck; the buyer presses the button
and sees the donut render.**

### 6.3 The security one-pager

A single page a buyer's CISO can read in 5 minutes:
- The catalog is the asset, the portal is a renderer (architecture-overview.md).
- The boundary is enforced by the infrastructure, never by the application
  (decision 0023).
- One credential is one tenant's; the operator's road never widens the customer's
  (decision 0021).
- The platform never holds a human's password (decision 0007).
- The spend breaker is on; the audit log is on; the drill is on.
- **No, we are not yet SOC 2 Type II.** (Honest. The roadmap says when.)

### 6.4 The case study

The first case study is the estate itself. The dogfood story is more credible than
a customer story at this stage. The case study is:
- "We run this platform. 408 catalog entities. 376 ELITE, 19 GAP, 13 BLIND.
  The drill runs hourly. The spend breaker tripped once, on a $0/minimax row bug
  we fixed in two hours. The zero-trust boundary is being installed this quarter."
- The numbers are real; the receipts are in the collector; the founder is the
  reference.

### 6.5 The procurement-grade FAQ

The buyer will ask the same ten questions every time. They need written answers:
- "Where is the data?" (Answered: in the buyer's cluster.)
- "Who has access?" (Answered: SPIRE-issued workload identity, OIDC for humans.)
- "How do you handle a CVE?" (Answered: Trivy Operator + grype + supply-chain
  workflow + `bin/estate-security-scan`.)
- "What is your SLA?" (Honest: we do not have one yet. The drill is the closest
  proxy; the SLO is the drill's `max_age_hours`.)
- "Can I export my data?" (Yes; the catalogue is YAML, the trace is OTel, the
  spend is Langfuse. All export.)
- "What is the upgrade path?" (Flux Kustomizations; suspend is the switch; never
  a destructive change.)
- "What happens if you go down?" (The two-renderer fallback. Backstage is node,
  Datasette is python; both run on different runtimes.)
- "Can I run this on-prem?" (Yes; the install wedge runs on k3d, the production
  estate runs on Oracle OKE A1 ARM64.)
- "Can I bring my own model?" (Yes; LiteLLM alias, per-lane budget.)
- "What does it cost?" (See pricing page; for the platform, Contact us.)

### 6.6 The marketing posture

What the buyer hears, in one sentence per buyer persona:

- **Platform engineering lead**: "The portal is one runtime, the fallback is
  another runtime, and they share no dependencies. The drill is the SLO."
- **CTO at a SaaS scaleup**: "We give you a portal that proves what is running,
  who owns it, and what it costs. The audit log is the answer to your auditor."
- **Security engineering lead at a company rolling out AI**: "Every model call is
  traced, every $ is capped, every action is governed, every output is linted for
  voice. The MCP gateway is one door; the LLM gateway is one router; the spend
  breaker is one switch."
- **Founder / CEO who wants an assistant**: "The Otto assistant runs your platform
  from a chat. Five capabilities, all built, the spend breaker is on, the trace
  is in the collector."

---

## 7. Gaps per product — and the cross-cutting gaps that block all of them

### 7.1 Cross-cutting gaps (block every product)

- **No customer-facing docs.** `docs/explanation/` is internal/operator-focused;
  there is no "getting started" page a buyer can read without already knowing the
  estate.
- **No install wedge.** No `idp/quickstart` image; no 30-minute demo path.
- **No pricing page, anywhere.** Features have tiers; nothing has a $ sign anywhere
  a customer can see it.
- **No trial.** Nothing to "try before you buy." The platform demos are inward-facing.
- **No sales motion.** No pitch decks, no case studies (real or synthetic), no ROI
  calculator, no procurement-grade security one-pager.
- **No support tiering.** No tier-1/2/3 split; no SLA definition; no on-call rotation
  outside the founder.
- **No certification.** Not SOC 2 Type II, no ISO 27001. Buyers larger than $50M ARR
  will be told "we cannot close you today" without these.
- **No multi-tenant billing.** Lago commerce is deployed per the platform, but it is
  not wired to a customer-facing signup → invoice → payment loop.
- **No product copy.** 9 of 13 catalogue entries are "Everything the X repository
  holds." Product pages cannot be written from that text.

### 7.2 Per-product gaps

| Product | Top three blockers |
|---|---|
| Voice Gate | (1) License choice (BSL vs source-available); (2) a `voice-policy.yaml` example set a buyer can fork; (3) Cloudflare/Worker or CLI distribution path |
| Inventory + dual-renderer | (1) Container packaging of `bin/catalog-gen` + `bin/db-gen` + a docker-compose for a buyer; (2) auth integration; (3) upgrade contract documentation |
| Otto Assistant | (1) STT fix (add `faster-whisper` to image); (2) prove the five capabilities end-to-end with live log lines; (3) customer-facing install path |
| MCP Gateway | (1) Tenant split (one customer cannot see another's tool list); (2) policy bundle in a vendored format a buyer signs once; (3) SOC 2 |
| Spend-bounded LLM gateway | (1) The "$0/minimax" row bug in `platform/llm/` documented; (2) a price sheet by token band; (3) audit-log export |
| Model Forge | (1) First production task (`ci-flake-triage`) on the queue, not a fixture; (2) held-out eval gate proved live; (3) customer-facing install path |
| Edge Runtime | (1) Benchmark on the A1 ARM64 node; (2) LiteLLM `abstain_below` integration; (3) customer-facing install path |
| Zero-trust boundary | (1) Calico policy-only installed in log-only posture; (2) one full day of would-be-denied flows captured; (3) allow rules merged before enforcement flips |
| Secrets Bridge | (1) Bitwarden-side operator docs that an ops team can follow; (2) namespace isolation; (3) audit log |
| Compliance Pack | (1) Stand the rules in an operator-friendly distribution; (2) one CVE/license/placement report out of the box; (3) a CI image that drops into GitHub Actions |
| Agent Workforce + Research Engine | (1) Unwedge the agent-workforce cronjob (root cause the queue consumer); (2) read the Research Engine HANDOFF; (3) ship a self-hosted Lindy/Relay with the wedge |
| The Platform | (1) Tenant isolation (multiple customers on shared infra); (2) SOC 2 + ISO 27001; (3) the AI guardrail that says "we don't add features a buyer asks for in week 1" |
| Vendor Key Activation | (1) First vendor onboarded through the gate end-to-end; (2) the gate green in CI; (3) the console-side onboarding doc |

### 7.3 Coupling opportunities

Three product pairs compose into a sale that is more than either alone:

- **AI-safe portal:** Platform + Voice Gate + LLM gateway + MCP gateway.
- **Private inference stack:** Model Forge + Edge Runtime + LiteLLM with abstain.
- **Compliance-as-a-service:** Platform + Compliance Pack + Supply-chain audit.

Three more combinations, from the v2 pipeline:

- **Zero-Trust estate:** Platform + Calico policy-only + Two-hats tenant split +
  Drills.
- **Engineering operations automation:** Cyrus + Research Engine + Agent Workforce
  + Forge (CI flake triage).
- **Dogfood chain:** every product, sold to the buyer as "we ship this because we
  use this."

---

## 8. Recommendations, ordered by effort and revenue impact

These are the actions to take, not the products to build. The build is implied.

1. **Stop describing products as "everything the X repository holds."** One person,
   two days. Result: 13 catalogue entries become readable, and the sales team knows
   the room.
2. **Pick one Tier 0 product to ship.** Voice Gate is the smallest surface area
   and the lowest risk. If Voice Gate doesn't ship in 30 days, the platform itself
   doesn't ship in 6 months.
3. **Build the install wedge.** One image, one command, 30 minutes from `docker
   run` to a working portal. The drill is the demo. The screenshot is the case
   study. **The wedge is the wedge.**
4. **Stand a `pricing/` folder with one page per product.** Even "Contact us" is a
   pricing page; what is not there cannot be sold.
5. **Decide the license posture for Tier 0/1 products now.** Source-available (BSL,
   AGPL) vs. fully OSS. The decision shapes the sales motion for every product
   after this.
6. **Write one customer-facing "getting started" doc per product.** Use the
   engineering README as input; "what you ship on Monday" as the output. Three
   docs, three weeks.
7. **Take the Compliance Pack to one prospect for free, on the condition they write
   the case study.** It is the cheapest market-test we have; the rego bundle
   already exists.
8. **Unwedge the agent-workforce cronjob.** Root-cause before restart (LAW 6); the
   whole Engineering Operations Automation bundle is blocked on this.
9. **Add `faster-whisper` to the hermes-agent image.** STT is the only Otto
   capability with a clear blocker; one line in `hermes-v2/Dockerfile:57`. Then
   prove all five capabilities with live log lines.
10. **Ship the zero-trust boundary in log-only posture for one day, then enforce.**
    The audit step is the differentiator; skipping it is the outage.
11. **Take the Model Forge first task (`ci-flake-triage`) from fixture to
    production queue.** One Forge run on real estate data; one held-out eval; one
    OCI artifact push; one Edge Runtime deployment; one abstain signal in the
    router.
12. **Stop standing up products the buyer will not turn on.** The "every feature
    is on by default" posture in `features.yaml` is a developer ergonomics
    posture, not a sales posture. A buyer with a 90-day onboarding window wants
    the equivalent of "lights-on for week 1, then turn things on as you trust them."

---

## 9. Verifications

Every claim in this audit can be cross-checked against the artifacts below. None of
those are the audit itself; they are the load-bearing sources.

```
# Platform layers
ls platform/{llm,observability,observability-collector,spire,identity,edge,dns,secrets,secret-store,scheduling,cyrus,hermes-agent,vendor*}/

# The capability register
cat platform/features/features.yaml | grep '^  - name:'

# Architecture overview
cat docs/explanation/architecture-overview.md | sed -n '1,30p'

# Pipeline items v2 added
ls forge/                                    # Model Forge + Edge Runtime
ls platform/cyrus/                           # Cyrus webhook agent
ls platform/agent-workforce/                 # Agent Workforce (wedged)
ls platform/research-engine/                 # Research Engine
ls platform/human-vault-bridge/              # Bitwarden → OCI Vault bridge
ls platform/calico/                          # Zero-trust boundary (Calico)
ls sovereign/otto/                           # Otto assistant runtime

# Specs v2 added
cat docs/specs/2026-09-06-model-forge-edge-runtime.md | sed -n '1,50p'
cat docs/specs/two-hats-tenant-split.md | sed -n '1,40p'
cat docs/specs/zero-trust-boundary.md | sed -n '1,40p'
cat docs/specs/otto-five-capabilities-finished.md | sed -n '1,30p'
cat docs/specs/backstage-as-a-product.md | sed -n '1,30p'
cat docs/specs/2026-09-06-portal-100.md | sed -n '1,30p'

# Decisions v2 added
ls docs/decisions/002{1,2,3,4,5}-*.md

# Product catalog states
cat catalog/ports.yaml
# expected entries: prospector-store-web, prospector-engine, prospector-store-api,
# consultd, kimi_bridge, board_serve, sovereign-cockpit

# Voice Gate state
ls platform/voice-gate/
git -C platform/voice-gate log --oneline | head
cat platform/voice-gate/HANDOFF.md | head

# Market research sources — see Sources section, end of document.
```

---

## Sources

**IDP market & pricing:**
- https://www.mordorintelligence.com/industry-reports/platform-engineering-and-internal-developer-platform-idp-market
- https://www.snsinsider.com/reports/internal-developer-platform-market-10643
- https://zuplo.com/learning-center/developer-portal-cost-build-vs-buy-analysis
- https://developerportalcost.com/

**IDP vendor landscape:**
- https://www.ciopages.com/buyer-guides/internal-developer-platform
- https://www.youngju.dev/blog/culture/2026-05-16-internal-developer-platforms-2026-backstage-port-opslevel-cortex-compass-roadie-deep-dive.en
- https://www.qovery.com/blog/backstage-alternatives-developer-portals-buyers-guide

**MCP / agent gateways:**
- https://agent.security/pricing
- https://tetrate.io/faq
- https://pincrs.com/market/mcp-gateway-enterprise
- https://www.digitalapi.ai/blogs/mcp-gateway

**LLM gateways:**
- https://aicost.ai/ai-cost-guides/calc/router-compare
- https://futurepicker.com/en/portkey-vs-litellm-vs-openrouter-vs-helicone-llm-gateway-2026/
- https://rikuq.com/blog/infra/portkey-vs-helicone-vs-litellm-vs-openrouter/

**Observability:**
- https://langfuse.com/pricing
- https://langfuse.com/pricing-self-host
- https://langfuse.com/enterprise

**Policy-as-code:**
- https://www.styra.com/enterprise-opa-platform/
- https://openpolicyagent.org/
- https://docs.ops0.com/docs/billing

**Workflow engines:**
- https://temporal.io/pricing
- https://www.windmill.dev/pricing
- https://comparetiers.com/compare/temporal-vs-windmill

**Secrets + Bitwarden:**
- https://external-secrets.io/latest/provider/bitwarden-secrets-manager/
- https://bitwarden.com/help/secrets-manager-kubernetes-operator/
- https://iancloud.ai/blog/kubernetes-secret-management-external-secrets-sops-vault-2026
- https://scopir.com/posts/kubernetes-secrets-management-tools-2026/

**Voice / prose linters:**
- https://stylemcp.com/
- https://slopsentry.ai/
- https://veldica.com/prose-linter
- https://synthquery.com/product/brand-voice

**Workflow / agent runtime:**
- https://docs.temporal.io/ai
- https://temporal.io/blog/building-ai-agents-that-overcome-the-complexity-cliff
- https://temporal.io/blog/temporal-agent-harness-durable-agent-infrastructure

**Backstage catalog:**
- https://backstage.io/docs/features/software-catalog/
- https://github.com/backstage/community-plugins/issues/2461
- https://backstage.spotify.com/docs/portal/core-features-and-plugins/catalog
