# The Factory Inventory — a thorough, measured record of everything the estate has grown so far

**Document 1 of 3. Written 2026-09-23, for the consultant architect. Companion: the**
**Programme (doc 2) and the Factory Contract (doc 3).**

The purpose of this document is **not** to editorialise. It is to hand the architect a
**complete, measured inventory** — every repository, every capability, every currently-named
"branch" — organised by a single organising law so the architect can *shape the product* from
fact, not from a summary.

Every number and path below was measured this session against the checked-out tree. Where a
repo exists on GitHub but **not** on this checkout, or exists only as a skeleton, that is
stated — an inventory that omits its own gaps is not an inventory.

---

## 0. The organising law (one paragraph, then facts)

The estate is a **fractal factory**: one kind of thing — a *factory*, which takes an order and
produces a result — recursing at every scale, where the result it produces is itself a factory.
Over time the one seed has grown **branches** (voice, web, evals, sandboxes, memory, compute,
workforce, platform, products), and these branches *look* like a fixed stack of layers, but that
is an appearance of the moment, not the law. The law is: **every branch produces, grades, and
sheds its own output.** An agent, a swarm, the Concierge, and later a robot or a pair of glasses
are all *orders placed against the branches* — nothing more.

This document is therefore organised as **the branch-tree the seed has grown so far**, each
branch marked with its `current` / `incubating` / `deprecated` state, and each row naming the
repository that carries it. The architect reads downward and sees both the fractal and the
inventory at once.

---

## 1. The complete repository inventory (65 repos, measured)

Column key: **py/rs/ts** = source-file counts (depth-bounded where noted). **State** = what the
repo *is* in the branch-tree.

| Repo | Language | Size (measured) | What it is in the tree | State |
|---|---|---|---|---|
| `idp` | Python | platform root, ~380 bin scripts | the platform: portals, MCP doors, gates, workflows, docs | current |
| `crew` | Python | coordination repo | shared coordination + verify.d + issue board | current |
| `zeroedge` / `zeroedge-repo` | Python | 27 py, proto+schema | cost/routing optimizer (off unless ZEROEDGE_URL set) | incubating |
| `estate-secrets` | Shell | vault | SOPS+age secrets store | current |
| `hermes-agent` | Python | 4,481 py (archived) | the largest agent runtime (superseded) | deprecated |
| `prospector` | Python | 255 py | research-pack seller; voice gate Python half | current (money rail 503) |
| `estate-guards` | Python | scripts submodule | pre-push/CI guards | current |
| `ironcage` | Rust | 7 rs, crates: ledger/api/inference/verifier/kernel | provable research engine (MCTS + formal) | incubating |
| `hermes-config` | Python | 227 py, 30 skills | skills/memories/prompts/simulators | current |
| `sentinel-loop` | Python | 61 py | loop spec + cockpit | built |
| `acg` | Python | 20 py | asymmetric compute grid (CPU/spot/free-API inference) | current |
| `estate-graph` | Python | growmos | model-agnostic knowledge graph | current |
| `agent-guard` | Python | containment | subprocess containment (reap, launchd-lint, load-probe) | current |
| `survival-stack` | JS | serverless | failover, cold-start-from-phone, degraded mode | current |
| `hermes-v2` | Python | 29 py | "The Architect": watches prod, opens PRs | current |
| `sovereign` | Rust+Py | sentinel + vision_brain | personal agent scaffold; OS input injection; OOB approval | current |
| `agent-foundry` | Python | 26 files | **the seed expression**: order→decompose→manifest→run | current |
| `haworks-platform` / `haworks` | C# | microservices | .NET 9 microservices | built |
| `kronos` | Rust | 23 rs, 5 rings | five-ring isolation kernel (private) | incubating (Linux/K8s) |
| `maestro` | Python | 10 py | requirements/board engine | built |
| `mumchimp-medusa` | TS | commerce | Medusa commerce | built |
| `agent-workforce` | Python | 12 py | crewAI 1.9.3 crew (no deploy/merge hands) | incubating |
| `hermes-operator` | Python | 3 py | Telegram ops shell, daemon control, remote coding | current |
| `estate-core` / `estate` | Python | 11 py | laws, guards, checkpoints, job definitions | current |
| `mums-concierge` | Python | private; 18 modules, 295 tests | consent-gated personal agent for Nunn | **built-elsewhere** |
| `research-engine` | Python | 0 files (skeleton) | research dept as a service (SPEC-v1 CP1) | incubating (empty) |
| `lux` / `lux-popdd` / `popdd-ts` | TS+Py | proof | proof-driven dev + chain-of-custody | current |
| `claude-observability-plugin` | Python | plugin | Langfuse plugin for Claude Code | current |
| `verdict` | TS | Next.js | auth/payments/moderation/judges | built |
| `ecommerce*` / `ebookStore` / `portfolio-site` / `cv` | TS/C# | client sites | client-facing products | built |
| `company-root-vault` | Python | vault | company root vault (private) | current |
| `QAlgo` / `Q` / `signalengine` | Python | algo | quant/trading algorithms | built |
| `AuthService` / `crux` / `nethermind` / `merkleroot` / `Sharp-Architecture` / `TechMastery.MarketPlace` / `Home` / `Web` / `Cosmonaut` / `QTrader` | C#/JS | sundry | assorted products & starters | built |
| `ci-reach-heal-probe` | — | dead | one-off probe, proved healer worked, 2026-08-23 | deprecated (delete blocked) |
| `nextjs*` / `test` / `glustack-` / `alwayson` / `tailwind-*` | TS | starters | starter templates | built |

---

## 2. The branch-tree — every branch the seed has grown, with its current output

This is the *factory* view. Each branch is one recurring family; the rows are the
implementations that family has produced, marked `current` / `incubating` / `deprecated` /
`built` / `gap`. This is the inventory grouped so the architect can see, per capability, what
produces it *today* and what is being grown or shed.

### Branch: Harness (the agent's runtime)
| Output | Repo | State |
|---|---|---|
| Claude Code + 31 hooks, 77 guards | `claude-guards/`, `~/.claude` | **current** |
| pi harness (2 extensions, no block hook) | `~/.pi/agent` | incubating |
| hermes-agent runtime (6,251 files) | `hermes-agent/` | deprecated |
| crewAI workforce | `agent-workforce/` | incubating |
| subprocess containment | `agent-guard/` | current |

### Branch: Voice & Speech
| Output | Repo | State |
|---|---|---|
| Rust deterministic voice gate | `idp/platform/voice-gate/` | **current** |
| Python deny gate (live publish) | `prospector/voice_gate/` | current |
| TTS + NuTTS + streaming | `hermes-agent/tools/tts_*.py` | current |
| Transcription | `hermes-agent/tools/transcription_tools.py` | current |
| Wake-word (`hey_hermes`) | `hermes-agent/tools/wake_word.py` | current |
| Duplex voice mode | `hermes-agent/tools/voice_mode.py` | current |
| Biometric speaker verification | `mums-concierge/` | **gap (built-elsewhere)** |

### Branch: Web & Browser (the eyes + hands on the web)
| Output | Repo | State |
|---|---|---|
| 6 browser tools + CamouFox + CDP | `hermes-agent/tools/browser_*.py` | **current** |
| Computer-use (CUA) | `hermes-agent/tools/computer_use/` | current |
| Vision (screenshot→intent→coords) | `sovereign/vision_brain/` | current |
| OS input injection (Quartz/SendInput) | `sovereign/sentinel/src/input/` | current |
| DOM-strip / scrape / extract | `agent-foundry/af/nodes.py` | current |
| Web search (X, open web) | `hermes-agent/tools/web_tools.py`, `x_search_tool.py` | current |
| Browser operator on a real Chrome profile | `mums-concierge/browser_operator.py` | **gap (built-elsewhere)** |

### Branch: Evals, Judges & Verifiers (the self-critic)
| Output | Repo | State |
|---|---|---|
| judge-drift | `idp/platform/eval/judge_drift.py` | **current** |
| pareval (bootstrap CI) | `idp/platform/eval/pareval_*.py` | current |
| red-team loop | `idp/platform/eval/red_team_*.py` | current |
| otto verify (13 modules) | `hermes-v2/otto/verify/` | current |
| consultd (second mind, cascade) | `claude-estate/scripts/consultd.py` | current |
| prm_grader | `idp/bin/prm_grader.py` | current |
| 407 BDD scenarios | `idp/features/` | current |
| crew verify.d (20 steps) | `crew/scripts/verify.d/` | current |
| lux / popdd proof-of-chain | `lux/`, `lux-popdd/`, `popdd-ts/` | current |
| 5 judge planes (107 files) | idp, hermes-agent, hermes-v2, hermes-config, prospector | 5 impls → 1 factory (architect decision) |

### Branch: Sandbox & Isolation (the boundary)
| Output | Repo | State |
|---|---|---|
| 12 execution arenas | `hermes-agent/tools/environments/` | **current entry rule (fold to 1)** |
| kronos rings 0–4 | `kronos/` | incubating (Linux/K8s only) |
| ironcage verifier/kernel | `ironcage/crates/` | incubating |
| devcontainer / systemd-run / vCluster / k3d / gVisor / colima | `agent-guard/`, `idp/platform/` | mixed |

### Branch: Trace & Observability (the record)
| Output | Repo | State |
|---|---|---|
| Aevum (PQ-signed, hash-chained) | `idp/platform/observability/aevum.yaml` | **current (ledger must wire)** |
| Langfuse tracing | `idp/platform/`, `claude-observability-plugin/` | current |
| span-retention | `idp/platform/eval/span_retention*.py` | current |
| ClickHouse twin TTL | `idp/bin/idp-clickhouse-twin-ttl` | current |
| estate-twin (ACTUAL vs DECLARED) | `idp/bin/estate-twin-runtime`, `mcp/plugins/estate_twin.py` | current (unwired — wire it) |
| decision log / prompt ledger | `crew/`, `claude-guards/` | current |

### Branch: Memory & Knowledge
| Output | Repo | State |
|---|---|---|
| growmos knowledge graph | `estate-graph/`, per-repo `.growmos/` | **current** |
| estate_memory MCP | `idp/mcp/plugins/estate_memory.py` | current |
| hermes memory (98 files) | `hermes-agent/` | deprecated |
| hermes-v2 memory | `hermes-v2/` | current |
| estate.db | `idp/catalog/estate.db` | current |
| *(open founder decision: one brain vs pick-backend)* | — | **gap** |

### Branch: Compute & Models
| Output | Repo | State |
|---|---|---|
| LiteLLM router (one key/identity) | `idp/platform/llm/` | **current** |
| ACG (asymmetric compute grid) | `acg/` | current |
| ZeroEdge (routing optimizer) | `zeroedge/`, `zeroedge-repo/` | incubating |
| efficiency gateway / token killer | `idp/platform/llm/`, `platform/efficiency/` | current |

### Branch: Workforce, Swarms & Agents (orders against the branches)
| Output | Repo | State |
|---|---|---|
| agent-foundry (the seed expression) | `agent-foundry/` | **current** |
| hermes-v2 (architect, PRs from phone) | `hermes-v2/` | current |
| hermes-operator (Telegram ops shell) | `hermes-operator/` | current |
| sovereign (personal scaffold) | `sovereign/` | current |
| mums-concierge (consent-gated personal) | `mums-concierge/` | **gap (built-elsewhere)** |
| research-engine | `research-engine/` | incubating (empty) |

### Branch: Platform & Delivery (the rails)
| Output | Repo | State |
|---|---|---|
| Flux GitOps + image-automation | `idp/clusters/`, `platform/image-automation/` | **current** |
| build-multiarch / deploy-when-green | `idp/.github/workflows/` | current |
| secrets (SOPS+age, vault bridge) | `estate-secrets/`, `idp/platform/human-vault-bridge/` | current |
| identity (SPIRE, jit-broker) | `idp/platform/spire/`, `platform/jit/` | current |
| doors (MCP 15 plugins, Backstage, NATS) | `idp/mcp/plugins/`, `idp/backstage/` | current |
| executor daemon | `idp/mcp/plugins/estate_executor.py` | built (daemon not started on this box) |
| survival-stack / lifeboat | `survival-stack/`, `idp/platform/lifeboat/` | current |
| estate-core / estate-guards | `estate-core/`, `estate-guards/` | current |

### Branch: Products (business-facing instances)
| Output | Repo | State |
|---|---|---|
| prospector (research packs) | `prospector/` | current (money rail 503) |
| verdict (auth/payments/judges) | `verdict/` | built |
| mumchimp-medusa | `mumchimp-medusa/` | built |
| haworks-platform | `haworks-platform/` | built |
| maestro / sentinel-loop | `maestro/`, `sentinel-loop/` | built |
| ecommerce / ebookStore / portfolio / cv | multiple | built |
| QAlgo / Q / signalengine | `QAlgo/`, `Q/`, `signalengine/` | built |

---

## 3. The gaps — capabilities no branch produces yet (the architect's build list)

Measured, not speculative. These are the rows a 2100-agent world — corporate + personal, then
robots and glasses — requires that **no current branch produces**:

1. **First-class Email** (send/read/triage) — only via Microsoft Graph.
2. **Calendar / scheduling** — none.
3. **SMS / phone (grantable)** — only inside `mums-concierge`, not grantable.
4. **Slack / Teams** — corporate chat: none.
5. **Notion / Linear / Jira** — corporate work + knowledge: none.
6. **Payments / billing rail** — `estate.commerce.order_paid` exists; rail 503.
7. **A self-description schema** — only `agent-foundry` ships `capability.yaml`; the other 64
   repos do not, so discovery is manual, not machine. **Architect priority #1.**
8. **A grant operation** — `agent-foundry` order has no `capabilities: [...]` field yet, so no
   branch output can be *granted* through one typed, audited step.
9. **Multi-tenant isolation (operating)** — specced (`tasks.<tenant>.<slug>`) but not running;
   the corporate-vs-personal boundary is described, not enforced.
10. **Biometric speaker-verification + browser-operator** — both live in `mums-concierge`, which
    is not in this checkout. Fetch it, or mark "verify before grant".

---

## 4. The discovery mechanism (how this inventory stays true without re-reading 65 repos)

The estate already owns the instruments; the architect's job is to wire them into one
self-refreshing registry:

| Instrument | Discovers | State |
|---|---|---|
| `gh repo list chidionyema` | full repo set (65) | current |
| growmos graph | typed entities + provenance | current |
| Backstage catalog + `bin/catalog-gen` | component/domain entities | current |
| `capability.yaml` (per repo) | a repo's self-declared factory outputs | **only agent-foundry has it — the gap** |
| estate_mcp inventory/state/twin | runtime actual-vs-declared | built |

**The single most important architectural move in this document:** define the `capability.yaml`
schema so every repo *declares its own branch and outputs*, and a collector rolls them into the
registry. Then this inventory is produced by the platform itself, every hour, instead of written
by hand — which is the fractal factory doing to its *own description* what it does to everything
else: producing it, rather than maintaining it.

---

*This is document 1 of 3 (the inventory for the consultant). Document 2 is the Programme (the
spiral and the factory as its constraint); document 3 is the Factory Contract (the schema and
the order language).*
