# The autonomous company, graded: what converges, what this estate already runs, what to build now

Founder record: `~/.claude/docs/founder/2026-09-08T2342Z-and-this-also-link-tickets-inclning-code-nt-760a5bba.md`
("do extensive grounded research and see what is already out there and where academic and industry
future plans converge but can be fully productionised now"). Board row: MUM-289, linked to MUM-287
and MUM-288. Companion spec: `2026-09-08-estate-world-model-simulate-before-execute.md`.

The pasted blueprint: NATS JetStream and Temporal as the nervous system; Protobuf typed contracts
with constrained decoding so agents can only emit valid actions; OPA and Z3 gates; Firecracker and
WASM sandboxes; SPIFFE/SPIRE identity; TigerBeetle ledger and macaroons for spend; six departments
(Legal/GRC, Treasury/FP&A, Customer Ops, InfoSec/Red team, Agent Ops, Executive PMO); twenty
research lanes; OKE with Workload Identity; a Go/Rust/Python/TS-WASM language doctrine; a genesis
monorepo. This spec grades every component three ways: what the estate runs today (measured
2026-09-09), what the mature industry tool is and its maturity, and what the peer-reviewed
literature measured. The verdict column is the deliverable.

## 1. Convergence map

Maturity: **production** (GA, multi-vendor, used in anger), **emerging** (shipping, one vendor or
pre-1.0), **research** (papers only).

| Blueprint component | Estate today | Mature tool, maturity | Literature | Verdict |
|---|---|---|---|---|
| Durable execution for agents | Temporal: 6 deployments in `temporal`, sovereign-worker running 12 days | Temporal; OpenAI Agents SDK integration GA 2026-03-23. Production | Every agent vendor made durable execution first-party in 2026 | **Have it.** Every long agent run is a Temporal workflow; nothing else retries |
| Event bus | NATS `event-bus/nats-0` Running; Sovereign Bus debounces to agents (ADR 0006) | NATS 2.12 JetStream. Production | — | **Have it.** One bus; no second broker |
| Typed action contracts | None. MCP tools take JSON Schema | MCP spec 2026-07-28: JSON Schema 2020-12 output schemas, gRPC transport emerging | Kästner et al. ICSE 2026: formal specs on tool sequence via annotated MCP metadata, no numbers yet | **Build now, as MCP output schemas, not Protobuf.** Protobuf is a second contract language for one server |
| Constrained decoding | None | vLLM structured outputs (XGrammar). Production | Progent: policies over tool name and arguments cut attack success 39.9% to 1.0%, utility held | **Build now** at the LiteLLM proxy: `response_format` json_schema for every tool call that changes state |
| Policy gate on tool calls (OPA) | Kyverno 14 ClusterPolicies, conftest 8 rego files, `bin/idp-rules` | OPA and Kyverno as policy decision point. Production (Styra wound down, OPA stays CNCF) | Progent, AgentSpec (over 90% unsafe executions blocked, under 1 ms), ShieldAgent | **Have the engine; build the tool-call gate.** The world model spec is that gate |
| SMT/Z3 proofs | None | Google's Z3-backed CEL verifier, Aug 2026. Emerging | SMT on arbitrary agent actions: research only | **Reject for now.** Revisit when an invariant outgrows rego |
| Firecracker sandboxes | gVisor cell `otto-gvisor-sandbox`, `bin/gvisor-cell-gate` | Firecracker and gVisor both production; k8s agent-sandbox CRD "not yet production-ready" | — | **Have it (gVisor).** Firecracker is a second sandbox for no new property on OKE |
| WASM tool sandboxes | None | wasmtime/Spin. Emerging for agent tools | — | **Defer.** gVisor covers the threat; WASM is a language-doctrine choice, not a security one |
| Workload identity | SPIRE server, `spire-system`; OKE Workload Identity | SPIRE graduated CNCF; Google Agent Identity built on SPIFFE. Production | — | **Have it.** Every agent pod gets a SPIFFE ID; no API key in a pod |
| Spend ledger | Budget keys in `AGENTS.md` toml, LiteLLM max_budget | TigerBeetle 0.17.x, production pre-1.0 | — | **Defer.** LiteLLM enforces the ceiling today; a double-entry ledger arrives with the first paying tenant |
| Capability tokens (macaroons) | JIT broker `jit`, `bin/idp-jit-grants`, TTL ceiling, no standing tokens (WJ.5) | IETF draft-niyikiza-oauth-attenuating-agent-tokens, Biscuit. Emerging | CaMeL: capability separation, provable on 77% of tasks | **Have the property; keep the broker.** Adopt the IETF format when it leaves draft |
| Human approval door | Telegram door, `otto-gateway`, decision 0024 | Shipped default in every 2026 agent vendor | Agent Laboratory: quality acceptable only with human feedback per stage | **Have it.** Every `execute_change` UNSAFE/UNKNOWN routes here |
| Digital twin / simulate first | None (see companion spec) | Kubernetes server dry-run GA | Cloud-OpsBench snapshot twin: Top-1 0.73 reproducible; AIOpsLab live mitigation ceilings 59%; ITBench 11.4% on real SRE | **Build now**: MUM-288 |
| Red team lane | Trivy operator, chaos-mesh, fence drills | Promptfoo, Garak. Production | The Attacker Moves Second: adaptive attacks push 12 "near zero" defenses above 90%; only architectural isolation survives | **Build now**: an adversarial drill in Dagster against the tool gate, graded pass^k |
| Multi-agent departments | `.claude/agents` roster, 13 agents | CrewAI, AutoGen, MetaGPT. Emerging | MAST: 7 frameworks fail 41 to 86.7%; best fix (objective verification) recovers only +15.6%; TheAgentCompany best 30.3% | **Reject as an org chart.** Departments are verifiers on one agent's output, not more agents |
| Scheduler | Dagster, `bin/idp-one-scheduler` | — | — | **Have it.** Research lanes are Dagster jobs |
| A2A / inter-agent protocol | None | A2A v1.0 to Agentic AI Foundation Aug 2026. Emerging | — | **Defer** until a second vendor's agent needs to call ours |

## 2. Productionise now: five things, each with its estate row

1. **Simulate before execute** (MUM-288). Server dry-run plus the four graders, propose/execute
   pair on the estate MCP server. Literature ceiling says live mitigation stays human-gated:
   `UNSAFE` and `UNKNOWN` route to the Telegram door.
2. **Constrained tool calls at the proxy.** Every state-changing MCP tool declares an output
   schema; LiteLLM enforces `response_format` for those calls. Progent's result is the reason:
   gating on name and arguments is the one defense class that held under adaptive attack.
   Row: `llm/config.yaml`, one rule in `rules.yaml` (a state-changing tool with no schema is refused).
3. **Planner and reader separation** (CaMeL). The engine that reads untrusted text (Linear issue
   bodies, web pages, logs) never holds the grant that executes. Today Cyrus reads and acts with one
   identity. Row: Cyrus runs as reader; execute goes through the broker with the planner's SPIFFE ID.
   Accept the measured utility cost of about seven points.
4. **Grade with pass^k and adversarial re-tests.** tau-bench: 90% pass@1 is 57% pass^8; SWE-ABS
   shows test-based pass rates are inflated. Row: `bin/idp-verify-drill` reruns every agent drill
   eight times and reports pass^8; the flake protocol applies to the drill, not the verdict.
5. **Adversarial red-team drill in Dagster.** AgentDojo's 629 injection cases run nightly against
   the tool gate; a rise in attack success is a `MEASURED_FAIL` on the security policy page.

## 3. Rejected, with the sentence that rejects each

- **Z3 as the safety proof**: the invariants are in Kyverno and rego; a second engine drifts.
- **Protobuf contracts**: MCP output schemas are the contract this server already speaks.
- **Firecracker**: gVisor already holds the sandbox row; a second runtime is stitching.
- **TigerBeetle now**: no tenant spends through us yet; the LiteLLM ceiling is the ledger.
- **Six departments as six agent teams**: MAST and TheAgentCompany measure multi-agent orgs failing
  most of the time; each department becomes a verifier, below.
- **Twenty research lanes**: research-engine and Dagster run lanes today; twenty charters with no
  measured output is the "we could also use X" the headline forbids. Lanes open one at a time,
  each with a pass^k target.
- **Standing admin identity on OKE**: WJ.5, decision 0025.
- **Language doctrine (Go/Rust/Python/TS-WASM)**: the estate is Python and TypeScript; a doctrine
  that adds two toolchains for no measured property is a cost, not a standard.
- **Genesis monorepo**: `idp` is the monorepo; there is no second platform.

## 4. Department gap list, mapped onto the roster in `.claude/agents`

Each blueprint department becomes a verifier that grades one agent's output. None becomes a team.

| Blueprint department | Roster today | Gap | Verifier it becomes |
|---|---|---|---|
| Legal / GRC | `legal`, `ai-act-gate`, `security-policy-gate` | No licence gate on agent-written dependencies at PR time | `conftest test policy/fixtures/sell-blocking.json` runs on every agent PR |
| Treasury / FP&A | `finance`, LiteLLM budgets | No per-run cost on the PR | receipt-auditor adds the run's USD from Langfuse to the PR body |
| Customer Ops | `sales`, `ux`, Telegram door | No tau-bench style dual-control drill | one Dagster drill: a scripted customer on the Telegram door, graded pass^8 |
| InfoSec / Red team | Trivy, chaos-mesh, `idp-fence-enforcement` | No prompt-injection drill | section 2 item 5 |
| Agent Ops | `operations`, FleetView (MUM-287) | No pass^k in FleetView | FleetView shows pass^8 per agent per drill |
| Executive PMO | `ceo`, `pm-agent`, `qa-agent`, Linear | Linear to Cyrus loop blocked on OAuth consent | FOUNDER ACTION already on MUM-284 |

## 5. Phasing, tied to the board

| Phase | Ticket | Ships |
|---|---|---|
| 0 | MUM-284 | Cyrus receives Linear webhooks with the OAuth application (one founder consent) |
| 1 | MUM-288 | `simulate_change` / `execute_change` with the twelve edge cases pinned |
| 2 | MUM-289 | Constrained tool calls at the proxy; reader/planner split for Cyrus; pass^8 in drills |
| 3 | MUM-287 | FleetView shows proposals, verdicts and pass^8 per agent |
| 4 | new row when phase 2 is measured | Adversarial red-team drill nightly in Dagster |

## 6. Sources

Industry: NATS 2.12 release notes; Temporal and OpenAI Agents SDK GA announcement 2026-03-23; MCP
specification 2026-07-28; vLLM structured outputs documentation; OPA project status after Styra;
Google Z3-backed CEL verifier announcement, Aug 2026; kubernetes-sigs/agent-sandbox README;
SPIFFE/SPIRE graduation; TigerBeetle releases; IETF draft-niyikiza-oauth-attenuating-agent-tokens;
Biscuit; A2A v1.0 transfer to the Agentic AI Foundation, Aug 2026; Anthropic Project Vend;
Claude Code daily maintenance report (388 PRs, 46% merged); Sakana AI Scientist post-mortem (42%
experiments failed); Devin public task scoping.

Academic: TheAgentCompany https://arxiv.org/abs/2412.14161 · ITBench https://arxiv.org/abs/2502.05352
· tau2-bench https://arxiv.org/abs/2506.07982 · SWE-ABS https://arxiv.org/pdf/2603.00520 · Progent
https://arxiv.org/abs/2504.11703 · AgentSpec https://arxiv.org/abs/2503.18666 · ShieldAgent
https://arxiv.org/abs/2503.22738 · Verifiably Safe Tool Use https://arxiv.org/abs/2601.08012 · CaMeL
https://arxiv.org/abs/2503.18813 · IsolateGPT comparison https://arxiv.org/pdf/2607.05120 ·
Spotlighting https://arxiv.org/abs/2403.14720 · The Attacker Moves Second https://arxiv.org/abs/2510.09023
· AgentDojo https://arxiv.org/abs/2406.13352 · Cloud-OpsBench https://arxiv.org/html/2603.00468v1 ·
AIOpsLab https://arxiv.org/abs/2501.06706 · RCAEval https://arxiv.org/abs/2412.17015 · Adversarial
Network Imagination https://arxiv.org/html/2602.13203 · MAST https://arxiv.org/abs/2503.13657 ·
ChatDev https://arxiv.org/abs/2307.07924 · MetaGPT https://arxiv.org/abs/2308.00352 · AI Scientist
https://arxiv.org/abs/2408.06292 · Agent Laboratory https://arxiv.org/abs/2501.04227

## Done, in commands

```
grep -c "Build now" docs/specs/2026-09-09-autonomous-company-grounded-research.md   # 5 rows
bin/idp-ci                                                                          # spec lands green
# empirical, phase 2: one constrained tool call quoted from the LiteLLM log with response_format
# honoured, and one refused call quoted from the same log
```
