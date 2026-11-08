# The catalogue — what we sell

This is the buyer's index to every product, feature and bundle the estate ships.
Every page below follows the same shape: the problem first, what you get, how it
works, why us, pricing, and how to start.

The full register of everything built, product or not, with who it is useful for: [capabilities.md](./capabilities.md).

## Products

| Product | What it is | Tier |
|---|---|---|
| [The Platform](./products/platform.md) | The whole IDP, sold as a managed deployment | Strategic |
| [FleetView](./products/fleetview.md) | One live board for every AI agent you run, with stop/approve/steer from the page | 2 weeks |
| [Voice Gate](./products/voice-gate.md) | Deterministic prose linter for house voice | Ship now |
| [Otto Assistant](./products/otto-assistant.md) | A personal agent that lives in your chat | Ship now |
| [Inventory + Dual-Renderer](./products/inventory-dual-renderer.md) | One source, two renderers, runtime-separated fallback | Ship now |
| [MCP Gateway](./products/mcp-gateway.md) | One policed door for every tool an agent can reach | 90 days |
| [Spend-bounded LLM Gateway](./products/llm-gateway.md) | An LLM router that cannot lose you money | 90 days |
| [Model Forge](./products/model-forge.md) | A tiny-model factory for narrow tasks | 90 days |
| [Edge Runtime](./products/edge-runtime.md) | Private inference on cheap hardware | 90 days |
| [Zero-Trust Boundary](./products/zero-trust.md) | Calico policy-only, audit-first enforcement | 6 months |
| [Secrets Bridge](./products/secrets-bridge.md) | Bitwarden bridges to OCI Vault for workloads | 6 months |
| [Compliance Pack](./products/compliance-pack.md) | SBOM + license + placement gates as a CI image | 6 months |
| [Agent Workforce + Research Engine](./products/agent-workforce.md) | Self-hosted engineering operations automation | 6 months |
| [Vendor Key Activation](./products/vendor-key-activation.md) | A vendor pastes one key; the platform does the rest | 6 months |

## Bundles

A bundle is what we sell when one product alone is not the story. Every bundle is
cheaper than the sum of its parts and tells a single, end-to-end story a buyer can
take to their board.

| Bundle | The story the buyer tells their board |
|---|---|
| [AI-Safe Portal](./bundles/ai-safe-portal.md) | "We shipped AI to production in week 4, with every call traced, every action governed, every $ capped, every voice reviewed." |
| [Private Inference Stack](./bundles/private-inference.md) | "We pay frontier rates for judgment, cents per hour for narrow classification, and we hold the artifacts." |
| [Compliance-as-Code](./bundles/compliance-as-code.md) | "What runs, in whose pocket, with what licenses, with what CVEs, on a clock." |
| [Zero-Trust Estate](./bundles/zero-trust-estate.md) | "Every pod's traffic is enforced by the network; every tenant is in its own lane; every drill proves the SLO." |
| [Engineering Operations Automation](./bundles/eng-ops.md) | "Linear tickets turn into PRs without a person; CI red turns into triage without a person; research runs on a clock without a person." |

## Genesis Assurance — product-first commercial roadmap (pre-product)

**Founder decision — 8 November 2026.** Our first commercialisation target is **Genesis Assurance: independently verifiable autonomous execution, machine-directed decisions and prevention of recurrent failure classes**. It is **not for sale yet**. Build the narrowest useful product, dogfood it through real off-host estate operation, measure an independently replicated advantage, then pilot and commercialise. Funding applications are subordinate to engineering proof. **The estate is tenant zero and its 2026 IDP incident archive is a valuable research corpus, not live operating evidence.**

This roadmap is a **commercial projection of existing engineering authorities**, not a new project tracker, execution engine, failure-class register or release approval. One underlying task has one owner and one source of evidence: [Genesis FLOW](https://github.com/chidionyema/argon/issues/47), [IDP FLOW](https://github.com/chidionyema/idp/issues/7771), [FCR and decision assurance](https://github.com/chidionyema/idp/issues/7452), [Science](https://github.com/chidionyema/idp/issues/7372), [method selection](https://github.com/chidionyema/idp/issues/7342), [verification engine](https://github.com/chidionyema/idp/issues/7263), [remote agent admission](https://github.com/chidionyema/idp/issues/7794), [Founder Surface](https://github.com/chidionyema/argon/issues/62), [commercial-readiness plans](https://github.com/chidionyema/idp/issues/7516).

### Release waves — order is non-negotiable; disjoint engineering may proceed in parallel

| Wave | Deliverable (minimum) | Closure evidence; no substitutes |
|---|---|---|
| **P0 — operational foundation** | A remotely hosted, authenticated, cost-bounded FLOW mission works with the founder's laptop **off**. Old OKE paths are excluded; trusted DoF/Greenlane and reviewer have a working, authorized repair path. | Real cloud workflow/run ID, exact deployed source/plan SHA, independent user-facing effect, durable replay/rollback and Founder Surface readback. **Not fulfilled by** a source branch, green CI, transport HTTP 200, design or issue update. Dependencies: [#7800](https://github.com/chidionyema/idp/issues/7800), [#7334](https://github.com/chidionyema/idp/issues/7334), [#7771](https://github.com/chidionyema/idp/issues/7771), [#7794](https://github.com/chidionyema/idp/issues/7794). |
| **P1 — commercial product wedge** | A product-shaped **failure prevention and verifiable-yield loop**: authenticated incident/instruction → decision provenance (including mundane micro-decisions) → class retrieval/causal hypotheses → machine-selected permitted task → real off-host agent launch → independently verified effect → FCR correction/adoption → real-time founder/customer projection. Reflexive Integrity governs rule changes **before, during and after** establishment. | One real known IDP failure class reproduced as a failing test, corrected at root cause, intercepted in a second independently admitted agent/provider with no repeated investigation; distinct independent verifier; no false ACK/green; class and decision audit log; no duplicate scheduler/bus. Existing [#7452](https://github.com/chidionyema/idp/issues/7452), [#7263](https://github.com/chidionyema/idp/issues/7263), [#7481](https://github.com/chidionyema/idp/issues/7481), [#7771](https://github.com/chidionyema/idp/issues/7771). |
| **P2 — independent comparative proof** | Existing Genesis Science preregisters baseline, intervention, holdout, falsifiers, budget, uncertainty, independent assessor and analysis plan. Replay a curated, provenance-preserving set of past IDP failures across different failure classes; compare **current conventional workflow** vs Genesis under matched conditions and real cost limits, not against a deliberately broken straw-man. | Reproducible paired evaluations with hidden holdout cases and no training/test leakage, independent replication, uncertainty intervals/effect sizes, negative/ablation tests identifying which mechanism generated improvement. Primary measures: **verified completion rate, recurrence rate, p50/p95 time to verified yield, founder interventions, unauthorized or false-positive effects, total cost per successful mission**. Pre-register a decision-relevant minimum improvement and sample size/power analysis **before** observing the holdout; do not invent a lift. Safety regressions veto promotion even if speed improves. Owner [#7372](https://github.com/chidionyema/idp/issues/7372), method owner [#7342](https://github.com/chidionyema/idp/issues/7342), FCR [#7452](https://github.com/chidionyema/idp/issues/7452). |
| **P3 — independent customer deployment** | A documented portable API/SDK, clean tenant-isolated deployment, supported installation/upgrade/rollback, real observability and incident response, license/SBOM, GDPR/retention/export, quotas and metered per-customer costs. Preserve independence of operator, reviewer and customer. | A second clean tenant or external design partner executes the same end-to-end live canary without founder credentials, home machine, estate-only GitHub names or synthetic demonstrations; independent penetration/isolation/restore checks and prospective reliability observation. The existing estate is **tenant zero**, not evidence of general portability. |
| **P4 — commercial validation** | Obtain an independently identified design partner, validate the buyer's loss/cost problem, paid-pilot terms, support capacity, unit economics and pricing hypothesis. Reuse existing storefront and billing only when independently certified, not the dead-cluster claims in the September inventory. | Signed pilot or genuine customer commitment; observed customer use, retention and correct cash receipts, gross margin after measured support, inference, hosting and recovery costs. No commercial valuation from agent count, PRs, marketing impressions or estimated ARR. |
| **P5 — funding / growth option** | Evaluate UK innovation competitions, grants, research collaboration and small finance **using the P1/P2 proof**, not as a substitute for it. Make no assumption a particular competition remains open or qualifies; verify current official eligibility, award cap, match-funding and deadlines at application time. | Application only when novel mechanism, independent benchmark, UK SME eligibility, available match funding and defensible use of proceeds are established. Maintain a short reusable evidence dossier; applications must **not** interrupt P0–P2 delivery. **No unapproved capital expenditure or recurring infrastructure** is authorized by this roadmap. |

### Product boundary and permanent constraints

**First sell the independently demonstrated assurance wedge**, not an unverified entire autonomous estate. Possible later SKUs: developer SDK / CI assurance, enterprise agent governance, managed FLOW/failure-prevention fabric, and a full portable Genesis platform—each separately certified. Open-source foundations are welcome where licensed, secure and cheaper to maintain; do not reimplement a broker, solver, scheduler, identity provider, workflow runtime or independent verifier to support this product.

**Nonnegotiable invariants:** zero **unapproved** incremental recurring infrastructure spend; no production/recovery dependency on laptops, local services or founder attendance; no OKE resurrection; no self-review/forgeable authority; no certification from unsigned/self-reported receipts; no new blocking law without a proven bounded remediation path; no 'proven never fails again' claim outside specified tested failure models. The historical [capability inventory](./capabilities.yaml) is a **dated 2026-09-08 snapshot** and its old 'on cluster' statements are not current health claims or market-ready certifications.

### Decision and scientific feedback loop

For every product feature or process improvement: **before** acting record the minimum user problem, authority, relevant existing components, expected causal mechanism, alternative/cheaper approach, dependencies, irreversible risks, intended test and predicted cost. **During** implementation, inherit Reflexive Integrity / DoF / FLOW and preserve decision receipts. **After**, independently test the negative case, compare pre-registered baseline against deployed reality and adopt verified lessons in the existing FCR/agent onboarding. Wrong decisions create a decision-process regression, not just a code patch. Scale scrutiny to risk; deterministic micro-decisions are batched under an authenticated plan, not converted into founder-interrupting ceremonies.

**Priority controller:** P0/P1 operating yield before new SKUs; P2 benchmark begins in parallel only once the testbed is real; P3 packaging can parallelize non-privileged documentation/SDK quality work without claiming release; P4 and P5 depend on P1/P2 evidence. If key proof cannot be obtained, publish the **exact falsifier, unknown and owned next action**, rather than widening scope or declaring a milestone accomplished.

**Commercial roadmap status: SOURCE PROPOSAL / UNVERIFIED**. This section records intent and acceptance criteria only. The actual code, independent tests, production health, customer demand and funding are not established by this document.

## How to start

Every product above has three ways in:

1. **Run the install wedge** — a single image, `idp/quickstart`, that runs the
   platform on a fresh k3d cluster in 30 minutes. The drill is the demo; the
   screenshot is the case study.
2. **Read the showcase** — `/showcase` on the install wedge renders the live
   estate bar, the per-system health donuts, and the buyer sandbox launch
   button. The showcase is the page a buyer's engineer opens first.
3. **Call us** — for the platform itself, for the bundles, and for any product
   that needs a tenant, a SOC 2 conversation, or a procurement-grade security
   one-pager.

The drill runs hourly. The receipts land in the collector. The case study is
the dogfood chain: we ship every product here because we use every product here.
