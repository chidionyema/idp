# Product Audit — 2026-09-07

Owner: chidionyema. Scope: every capability in this estate, against the commercial
opportunity the platform-engineering market actually buys. Output of a read-only audit;
no code was changed. Findings sourced from this repo's `README.md`, `docs/explanation/`,
`platform/features/features.yaml`, `catalog/ports.yaml`, `docs/audits/2026-09-06-portal-audit.md`,
`docs/SHOWCASE.md`, `SALVAGE.md`, and four batches of market research.

---

## TL;DR

This estate is not "a collection of unfinished platforms." It is a single, internally
consistent platform with **23 selectable features** (per `platform/features/features.yaml`),
4 products already running on it, and at least **8 distinct commercial products** inside
its borders that could be sold separately today. What it does not have is product
packaging: each candidate product is described in the catalogue as "everything the X
repository holds," which is not packaging, it is a confession of where the work is.

The market window is open. IDP is $10B now, $30B+ by 2031. Backstage is the only
CNCF-graduated platform, and Spotify just split its commercial features out into a
paid product. The buyers are not asking "do you have a portal?" — they are asking
"can you tell me what is running, what it costs, and prove it is safe." This estate
already answers every one of those questions. The work is the packaging.

---

## 1. What we have

The estate has three layers: a **platform** (the IDP substrate), **products** (code that
runs on the platform), and **capabilities** (functions that may be sold either with the
platform or as their own thin wrapper).

### 1.1 Platform (the IDP substrate)

The substrate is one thing, not a list. Per `README.md` and `docs/explanation/architecture-overview.md`,
every layer is one instance and lives in `idp`:

| Layer | What it does | Where |
|---|---|---|
| Catalogue as source of truth | One inventory, two renderers (Backstage + Datasette), switch-only fallback | `bin/catalog-gen`, `bin/db-gen`, `backstage/` |
| Identity (SSO + SPIRE + Tailscale) | Federated login, workload identity, tailnet | `platform/spire`, `platform/identity` |
| Edge & DNS (Traefik + external-dns) | One published URL, TLS, cert renewal | `platform/edge`, `platform/dns` |
| Secrets (External Secrets over OCI Vault) | Static + dynamic, no in-cluster `Secret` literals | `platform/secrets`, `platform/secret-store` |
| Model routing (LiteLLM) | Per-lane budgets, spend breaker, no provider lock-in | `platform/llm` |
| Traces & audit (Langfuse + OTel) | Every model call, cost, prompt is a trace | `platform/observability`, `platform/observability-collector` |
| Scheduling (Dagster) | Scheduled jobs, success-fail pings | `platform/scheduling` |
| CI & supply chain (GitHub Actions + Flux + syft/grype) | SBOM, CVE scan, license gate | `bin/supply-chain` |
| Chaos & drills | What breaks first, measured | `platform/chaos`, `platform/drills` |
| Policy (Kyverno + Rego) | License, placement, capacity admitted by the plane | `policy/*.rego`, `bin/idp-rules` |
| Agent interface (MCP + Sovereign Bus) | One door per agent, audited, governed | `mcp/`, `sovereign/` |

The header rule from `README.md` is the load-bearing one: *"We are selling this. Buy the
mature platform. Do not stitch one."* `prospector`, `hermes-v2`, `consultd`, `kimi_bridge`,
`board_serve`, `sovereign-cockpit` are products that run on the platform; they carry no
copy of any platform layer. Every layer listed above is "one of" each row on the standards
page, lives in `idp`, and is reused by every product that lands.

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
because nobody wrote product copy.** They are not "less real" than prospector; they are
just less packaged.

### 1.3 Capabilities (commercializable on their own)

The `platform/features/features.yaml` register lists 23 selectable features; each is a
swappable tier of a platform capability. A subset of them is already product-shaped —
already proved under load, already governed by the platform, already documented. They
are listed below in the order they map to commercial products in Section 3.

| # | Capability | File path | Why it is product-shaped |
|---|---|---|---|
| 1 | **Voice Gate (deterministic prose linter)** | `platform/voice-gate/` | Python half merged; Rust half port 8420, 12 tests pass. Works on commit-time, not at inference. |
| 2 | **Sovereign Bus / MCP gateway** | `mcp/`, `sovereign/` | One door, consensus-gated, audited, governed. Not a stub. |
| 3 | **LLM gateway with spend discipline** | `platform/llm/` | LiteLLM with per-lane budgets, $176M tokens tracked before $0/minimax row bug; spend breaker on. |
| 4 | **Traces & audit (Langfuse + OTel)** | `platform/observability/` | Already shipping; OTel collector as fallback when Langfuse is down. |
| 5 | **Inventory + dual renderers** | `bin/catalog-gen`, `bin/db-gen` | Two renderers, one source, runtime-separated fallback. |
| 6 | **Policy-as-code (Rego + conftest)** | `policy/*.rego`, `bin/idp-rules` | License, placement, capacity gates with fixtures. |
| 7 | **Secrets bridge (Bitwarden → OCI Vault)** | `platform/human-vault-bridge` | Unique; bridges a personal vault to a workload-grade vault via External Secrets. |
| 8 | **Webhooks → worktrees (Cyrus)** | `platform/cyrus/` | Linear/GitHub in, worktree + engine + PR out. Per its README, holds no cluster verbs. |
| 9 | **Workflow engine (Temporal / Windmill)** | `platform/temporal/` | One tier suspends (Temporal), the other selects (Windmill). Choose at deploy time, not at runtime. |
| 10 | **Agent memory (Hindsight API)** | per features.yaml | Per-session persistence, configurable. |
| 11 | **Supply-chain audit (SBOM + grype)** | `bin/supply-chain` | Per-build SBOM, license gate, vulnerability report. |
| 12 | **Healthchecks + drill-grade SLOs** | `bin/placement-audit` | Heartbeat, placement probe, drill gate. |

The other 11 features in `features.yaml` (chaos, autoscaling, dev-loop, staging, etc.)
are platform capabilities that **sell with the platform, not as products.** They belong
on the platform price page as a tier knob.

---

## 2. What the market buys

From four batches of web research (12 sources in total; full source list at the end):

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

---

## 3. The product packaging

Eight product candidates, ranked by how far each is from being packageable today.
"Tier 0" ships in 30 days with the work mostly done; "Tier 3" is a 6–12 month effort.

### Tier 0 — ship within 30 days

**Product 1 — Voice Gate.** A deterministic, version-controlled prose linter that a
team runs in CI to enforce house voice on every commit and PR. Domain: editorial teams,
marketing orgs at SaaS companies, content publishers with brand-voice guidelines.
- What the buyer gets: a binary or container, a `voice-policy.yaml`, a CI step, a
  pre-commit hook. Detection rules cover "assistant residue," cadence, banned tokens,
  punctuation density. 12 tests pass; Rust half is on `fix/cyrus-webhook-routes`.
- Pricing motion: per-language (EN/ES/JA pre-bundled), $50/seat/mo for teams, custom
  for publishers with 100+ authors. Below Veldica on UX, above them on being commit-time
  not inference-time.
- One founder note already on record: one engine, deterministic gate only, no semantic
  tier. That is the product strategy.

**Product 2 — Inventory + dual-renderer.** A drop-in Backstage + Datasette pattern that
takes one YAML/JSON source and serves it two ways. Domain: platform teams at
$20M-$200M ARR SaaS companies that have outgrown a wiki and don't want to be a Backstage admin.
- What the buyer gets: an inventory format, two renderers, the failover contract,
  the upgrade contract. The failover was the bug that was in Datasette; it is fixed.
- Pricing motion: per-tenant subscription. The two-renderer fallback is the differentiator:
  competitor portals go down with their runtime; this estate's fallback has a separate
  runtime by design.

### Tier 1 — ship within 90 days

**Product 3 — MCP Gateway.** The Sovereign Bus, packaged as a hardened proxy in front
of an enterprise's MCP servers. Domain: enterprises that have already deployed agents
and need a single audited, governed door. Permit.io ships this at $25/mo entry; their
enterprise path goes 4-figure/mo. Our differentiator is "the door carries identity (SPIRE)
+ policy (Kyverno/Rego) + a budget, not just an OAuth proxy."
- What the buyer gets: agentgateway deployment, SPIRE-issued workload identity, the
  policy bundle, the Sovereign Bus for fan-out.
- Pricing motion: per-agent-per-month, like Permit but priced for the governance row.

**Product 4 — Spend-bounded LLM gateway.** LiteLLM, hardened, with the per-lane budget
breakers and the spend dashboard. Domain: SaaS scaleups with an LLM rollout that needs
an audit story. OpenRouter (credit/marketplace) and Portkey (per-log) are the comps.
- What the buyer gets: gateway, the spend breaker, the trace pipeline, the cost-per-team
  view.
- Pricing motion: by token volume, with a floor. The differentiator is "we cannot lose
  you money" — the budget is enforced at the proxy, not at the bill.

### Tier 2 — ship within 6 months

**Product 5 — Secrets Bridge.** The `human-vault-bridge` packaged: a Bitwarden-side
operator plus an ESO bridge to OCI Vault (or any Vault). Domain: enterprises where
operators hold shared credentials in Bitwarden and workloads need them as Kubernetes
secrets. This is a thin product, but the pattern is unique.
- Pricing motion: per-seat (Bitwarden side) + per-workload (bridge side).

**Product 6 — Compliance Pack.** The Rego rules + conftest + license/placement/capacity
gates, packaged as a CI image: `bin/idp-rules run --plane ci`. Domain: any company that
needs SBOM + license + placement evidence for SOC 2 / ISO 27001 / vendor security review.
Styra DAS competes here; our version is not UI-grade, but it is "you don't have to stand
up Styra."
- Pricing motion: per repo, per org.

**Product 7 — Workflow Tier Chooser.** Temporal or Windmill, pick at deploy, off by
default. Domain: teams that have outgrown CronJobs. Already a feature; needs a price.

### Tier 3 — strategic, 6-12 months

**Product 8 — The Platform itself.** The IDP-as-a-Service: catalogue, identity, edge,
secrets, model routing, traces, scheduling, supply chain, policy, agent interface —
sold as a managed deployment on a tenant's cluster (or ours). This is the highest ceiling
and the longest cycle. It is also the "mature platform, do not stitch one" the headline
already calls out.

**Strategic product — Hermes-class.** A Telegram-in, multi-channel-out executive agent
that owns the founder/CEO surface. The product already exists for the founder; packaging
it for sale is "find 10 founders who want this and prove it on their behalf." Not a
mass-market product. Founder-distributed.

---

## 4. Gaps per product

These are the gaps that block each product from being saleable. None of them is a
"no." They are all "yes, but you need to do X first."

### 4.1 Cross-cutting gaps (block every product)

- **No customer-facing docs.** `docs/explanation/` is internal/operator-focused; there
  is no "getting started" page a buyer can read without already knowing the estate.
- **No pricing page, anywhere.** Features have tiers; nothing has a $ sign anywhere a
  customer can see it.
- **No trial.** Nothing to "try before you buy." The platform demos are inward-facing.
- **No sales motion.** No pitch decks, no case studies (real or synthetic), no ROI
  calculator, no procurement-grade security one-pager.
- **No support tiering.** No tier-1/2/3 split; no SLA definition; no on-call rotation
  outside the founder.
- **No certification.** Not SOC 2 Type II, no ISO 27001. Buyers larger than $50M ARR
  will be told "we cannot close you today" without these.
- **No multi-tenant billing.** Lago commerce is deployed per the platform, but it is
  not wired to a customer-facing signup → invoice → payment loop.
- **No product copy.** 9 of 13 catalogue entries are "Everything the X repository holds."
  Product pages cannot be written from that text.

### 4.2 Per-product gaps

| Product | Top three blockers |
|---|---|
| Voice Gate | (1) License choice (BSL vs source-available); (2) a `voice-policy.yaml` example set a buyer can fork; (3) Cloudflare/Worker or CLI distribution path |
| Inventory + dual-renderer | (1) Container packaging of `bin/catalog-gen` + `bin/db-gen` + a docker-compose for a buyer; (2) auth integration; (3) upgrade contract documentation |
| MCP Gateway | (1) Tenant split (one customer cannot see another's tool list); (2) policy bundle in a vendored format a buyer signs once; (3) SOC 2 |
| Spend-bounded LLM gateway | (1) The "$0/minimax" row bug in `platform/llm/` documented; (2) a price sheet by token band; (3) audit-log export |
| Secrets Bridge | (1) Bitwarden-side operator docs that an ops team can follow; (2) namespace isolation; (3) audit log |
| Compliance Pack | (1) Stand the rules in an operator-friendly distribution; (2) one CVE/license/placement report out of the box; (3) a CI image that drops into GitHub Actions |
| Workflow Tier Chooser | (1) Pick Temporal or Windmill in the Backstage template; (2) per-tier doc + cost; (3) the workflow-engine addon for the platform price sheet |
| The Platform | (1) Tenant isolation (multiple customers on shared infra); (2) SOC 2 + ISO 27001; (3) the AI guardrail that says "we don't add features a buyer asks for in week 1" |

### 4.3 Coupling opportunities

Three product pairs compose into a sale that is more than either alone:

- **AI-safe portal:** Platform + Voice Gate + LLM gateway + MCP gateway.
  The story a buyer tells their board: "we shipped AI to production in week 4, with
  every call traced, every action governed, every $ capped, and every output's voice
  reviewed." This is the highest-margin bundle.
- **Developer growth:** Platform + prospector. "What runs in prod, plus who buys what
  next." Useful for companies that sell to developers, niche but recurring.
- **Compliance-as-a-service:** Platform + Compliance Pack + Supply-chain.
  "What runs, in whose pocket, with what licenses, with what CVEs." An audit firm re-sells
  this; we don't need to be in the audit business.

---

## 5. Recommendations, ordered by effort and revenue impact

These are the actions to take, not the products to build. The build is implied.

1. **Stop describing products as "everything the X repository holds."** One person, two
   days. Result: 13 catalogue entries become readable, and the sales team knows the room.
2. **Pick one Tier 0 product to ship.** Voice Gate is the smallest surface area and the
   lowest risk. If Voice Gate doesn't ship in 30 days, the platform itself doesn't ship
   in 6 months.
3. **Stand a `pricing/` folder with one page per product.** Even "Contact us" is a
   pricing page; what is not there cannot be sold.
4. **Decide the license posture for Tier 0/1 products now.** Source-available (BSL, AGPL)
   vs. fully OSS. The decision shapes the sales motion for every product after this.
5. **Write one customer-facing "getting started" doc per product.** Use the engineering
   README as input; "what you ship on Monday" as the output. Three docs, three weeks.
6. **Take the Compliance Pack to one prospect for free, on the condition they write the
   case study.** It is the cheapest market-test we have; the rego bundle already
   exists.
7. **Stop standing up products the buyer will not turn on.** The "every feature is on by
   default" posture in `features.yaml` is a developer ergonomics posture, not a sales
   posture. A buyer with a 90-day onboarding window wants the equivalent of
   "lights-on for week 1, then turn things on as you trust them."

---

## 6. Verifications

Every claim in this audit can be cross-checked against the artifacts below. None of
those are the audit itself; they are the load-bearing sources.

```
# Platform layers
ls platform/{llm,observability,observability-collector,spire,identity,edge,dns,secrets,secret-store,scheduling,cyrus,hermes-agent,vendor*}/

# The capability register
cat platform/features/features.yaml | grep '^  - name:'

# Architecture overview
cat docs/explanation/architecture-overview.md | sed -n '1,30p'

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
