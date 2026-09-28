# The full capability map — everything we have, categorised by how it is actually used

**Written 2026-09-20.** Nothing omitted. This is the picture to decide consolidation from, not a
summary of it.

Every entry is a thing that exists on disk and was read. Where something is built but not operating,
that is stated in the **State** column, because this estate has repeatedly confused the two.

State vocabulary, used strictly:

| State | Means |
|---|---|
| **live** | running, wired, and observed |
| **wired** | connected to something that runs; will fire |
| **built** | exists, tested, not connected to anything that runs |
| **dormant** | was running, is not now |
| **orphaned** | exists on a branch or in a repo nothing references |

---

## Layer 0 — How the founder works today

This is the axis everything else has to be judged against.

| Door | What reaches the founder | State |
|---|---|---|
| **Voice** | `sovereign/voice/` (`server.py` on :8899, `client.html`), `idp/platform/voice-gate/`, `mums-concierge` (sherpa-onnx + edge-tts) | voice-gate built; sovereign/voice **live** on :8899; concierge **not deployed** |
| **Telegram** | `otto-gateway`, `platform/otto-golden`, `jit-broker` (approve from phone), `hermes-operator` | gateway built; jit broker built; operator shell built |
| **Board** | `board_serve.py`, `founder_board.py`, `ESTATE_BOARD.jsonl`, crew board | **live/wired** |
| **Portal** | Backstage + FleetView (22 backend modules, 7 BDD files) | Backstage **live** on :3100 (dev mode) |
| **Claude Code** | harness on this laptop, 31 wired hook entries | **live** |
| **pi** | harness on this laptop, 2 extensions, no blocking hook | **live but ungoverned** |

---

## Layer 1 — The harnesses themselves

Things an agent session runs *inside*.

| Harness | What it is | Where | State |
|---|---|---|---|
| **Claude Code** | the main working harness; 31 wired hook entries, 77 guard tools, 43 incident tests | `~/.claude`, `claude-guards` | **live** |
| **pi** | second harness; `fleetview-directives.ts`, `read-shunt.ts`; no `tool_call` hook, no permission model | `~/.pi/agent` | **live, ungoverned** |
| **pi-governance** | 4-pillar DNA extension (epistemic humility, semantic tools, P-P-E, closed-loop self-healing) | `prospector/pi-governance/` | **built — not installed** |
| **hermes-agent** | the largest agent runtime (6,251 source files); 12 execution arenas, 3 eval harnesses, verify subsystem, guardrails | `hermes-agent/` | built |
| **hermes-v2 ("The Architect")** | watches production, opens PRs you approve from a phone | `hermes-v2/` | built |
| **hermes-operator** | Telegram-driven ops shell: launchctl, prospector control, remote coding | `hermes-operator/` | built |
| **hermes-config** | skills, memories, prompts, simulators | `hermes-config/` | built |
| **agent-workforce** | crewAI 1.9.3 crew, one board item in | `agent-workforce/` | built |
| **agent-foundry** | factory + runtime that "orders an army of specialised agents" | `agent-foundry/` | built |
| **agent-guard** | containment for agent subprocesses (reap, launchd-lint, load-probe) | `agent-guard/` | wired (launchd lint every 6h) |
| **podd** | POPDD agent | `prospector/popdd_agent.py` | retired (ADR 0028) |

---

## Layer 2 — Where agents run (isolation and arenas)

| Capability | What it is | Where | State |
|---|---|---|---|
| **12 execution arenas** | `local`, `docker`, `modal`, `managed_modal`, `daytona`, `vercel_sandbox`, `singularity`, `ssh`, `base`, `file_sync`, `modal_utils` | `hermes-agent/tools/environments/` | built |
| **kronos ring0** | Firecracker/KVM VM boundary (`vm.rs`, `cow.rs`, `snapshot.rs`) | `kronos/crates/ring0-hypervisor` | built (Linux/K8s only) |
| **kronos ring1** | Wasmtime+WASI, fuel-metered (`sandbox.rs`, `fuel.rs`) | `kronos/crates/ring1-wasm` | built |
| **kronos ring2** | eBPF/Tetragon syscall + AST gating | `kronos/crates/ring2-ebpf` | built |
| **kronos ring3** | vsock proxy + Vault egress (`proxy.rs`, `capability.rs`) | `kronos/crates/ring3-egress` | built |
| **kronos ring4** | SQLite+SHA-2 append-only ledger | `kronos/crates/ring4-ledger` | built |
| **kronos kernel** | orchestrator, supervisor, budget | `kronos/crates/kernel` | built |
| **devcontainer sandbox** | cgroup limits, cap-drop, read-only | `agent-guard/sandbox/devcontainer.json` | built |
| **systemd scope** | `systemd-run` sandboxing | `agent-guard/sandbox/systemd-run.sh` | built |
| **vCluster** | OSS 0.36.1 `demo-sandbox`, 15m CPU, no persistence | `idp/platform/sandbox/vcluster/` | built |
| **k3d** | local cluster | `idp/platform/k3d/` | built |
| **staging canary** | canary namespace | `idp/platform/staging/` | built |
| **colima** | container VM, 4 CPU / 8 GiB pinned | `agent-guard/sandbox/colima.md` | **live** |
| **gVisor** | gVisor runtime + cell namespaces | `idp/platform/gvisor-runtime/`, `bin/gvisor-cell-gate` | built |

---

## Layer 3 — How agents are driven (control plane)

| Capability | What it is | Where | State |
|---|---|---|---|
| **Directive consume** | reads pending steering, marks consumed, appends ack; Claude `SessionStart`/`PostCompact` **or pi turn boundary** | `idp/bin/idp-directive-consume` | **wired** |
| **Signals** | writes steer/stop directives | `idp/backstage/plugins/fleetview-backend/src/signals.py` | **wired** |
| **Mutation ledger door** | propose/admit/seal/verify typed mutations | `idp/bin/exec-daemon`, `platform/executor/daemon.py` | built |
| **FleetView executor link** | cluster↔laptop relay over tailnet, `tag:founder-mac` ACL | `fleetview-backend/src/executor_link.py` | **wired** |
| **JIT broker** | one named write at a time, founder approves by Telegram tap | `idp/platform/jit/` | built |
| **Temporal** | durable workflow orchestration | `idp/platform/temporal/` | built |
| **NATS JetStream** | the one event bus | `idp/platform/queue/`, `event-bus/` | built |
| **Orchestrator** | estate orchestration | `idp/platform/orchestrator.py`, `orchestration/` | built |
| **dispatch install / linear dispatch** | work dispatch | `idp/bin/idp-dispatch-install`, `idp-linear-dispatch` | built |
| **Scheduler** | periodic estate jobs | `idp/platform/scheduling/`, `bin/scheduler-migrate` | built |
| **KEDA** | event-driven autoscaling | `idp/platform/keda/` | built |

---

## Layer 4 — What agents are allowed to do (governance)

| Capability | What it is | Where | State |
|---|---|---|---|
| **31 wired hook entries** | SessionStart 4 · UserPromptSubmit 2 · PreToolUse 12 · PostToolUse 2 · Stop 11 | `~/.claude/settings.json` → `claude-guards` | **live** |
| **77 guard tools** | see Appendix A of the synthesis doc for all 77, one line each | `claude-guards/` | **live** |
| **43 incident tests** | 2,657 lines; each encodes a real incident | `claude-guards/test_incident_*.py` | **live** |
| **rules.yaml** | 101 rules, each with planes, run argv, fixtures, cases | `idp/rules.yaml` | **live** (via `bin/idp-rules`) |
| **42 gates** | see Appendix B, one line each | `idp/bin/*-gate` | 35 declared in rules.yaml |
| **OPA** | policy decisions | `claude-guards/opa-hook.py`, `idp/policy/` | wired |
| **Kyverno** | in-cluster admission policy | `idp/platform/kyverno/` | built |
| **5 lanes** | behaviour profiles: default, build, research, incident, platform; each with 6 best-practice lines | `~/.claude/lanes.json` | **live** (read per hook call) |
| **10 roles** | ceo, engineering, finance, information-architect, inventor, legal, marketing, operations, sales, ux | `claude-estate/agents/roles/` | built |
| **3 functional agents** | pm-agent, qa-agent, receipt-auditor | `claude-estate/agents/` | built |
| **agent-reader SA** | read-only cluster identity for agents | `idp/platform/rbac/agent-reader.yaml` | built |
| **bin/idp-kube** | the one way a laptop speaks to the cluster; mints short-lived `agent-reader` token; `--break-glass` for founder | `idp/bin/idp-kube` | **live** |
| **rule-guard / bare_kubectl** | refuses bare `kubectl`, names `bin/idp-kube` | `claude-guards/rule-guard.py`, `policy/command.rego` | **live** |
| **guard rail: tool drip** | batching/delegation enforcement | `claude-guards/tool-drip-guard.py` | **live** |
| **estate_executor ceiling** | `CEILING_SEC = 60`, applied by the executor | `idp/mcp/plugins/estate_executor.py` | **built — daemon never started** |
| **idp-executor-install** | creates `_idp_executor` uid + root LaunchDaemon | `idp/bin/idp-executor-install` | **built — needs sudo, refuses agent** |
| **idp-execution-boundary** | adjudicates the boundary | `idp/bin/idp-execution-boundary` | **wired** |
| **idp-executor-status** | reports `MEASURED_OK` / `UNKNOWN` | `idp/bin/idp-executor-status` | **live — reports FAIL** |
| **session-timeout** | kills idle sessions (crew#306 CP3) | `claude-guards/session-timeout.py` | wired (launchd) |
| **slow_commands** | warns on historically slow commands | `claude-guards/slow_commands.py` | **live** |
| **stuck_detector** | notices sessions not progressing | `claude-guards/stuck_detector.py` | wired |
| **single-session-guard** | one interactive session per machine | `claude-guards/single-session-guard.py` | wired |
| **tool_guardrails** | tool-call loop primitives | `hermes-agent/agent/tool_guardrails.py` | built |
| **7 hermes guards** | empty-response, nous-rate, repetition, ssl, outbound webhooks, shell hooks, verify hooks | `hermes-agent/agent/` | built |
| **conscience** | OPA tenets | `idp/conscience/` | built |

---

## Layer 5 — Verification and evidence

| Capability | What it is | Where | State |
|---|---|---|---|
| **Aevum** | Ed25519 + ML-DSA-65, COSE_Sign1, RFC 3161, hash-chained, tamper-detected | `idp/platform/observability/aevum.yaml`, `.aevum/local.jsonl` | **built — ledger empty** |
| **idp-evidence-gate** | fail-closed on an empty ledger | `idp/bin/idp-evidence-gate` | **live** |
| **idp-local-evidence-gate** | validates `.aevum/local.jsonl` | `idp/bin/idp-local-evidence-gate` | **live** |
| **POPDD** | the retired HMAC receipt layer | `prospector/popdd_agent.py` | **retired** (ADR 0028) |
| **5 judge/eval planes** | idp (48 files), hermes-agent (26), hermes-v2 (13), hermes-config (13), prospector (7) | see Appendix D | built |
| **judge-drift** | detects the judge itself drifting | `idp/platform/eval/judge_drift.py` | built |
| **pareval** | pairwise eval with bootstrap CI | `idp/platform/eval/pareval_*.py` | built |
| **red-team loop** | adversarial payload generation + promotion | `idp/platform/eval/red_team_*.py` | **live** (rule `redteam-payload-promotion`) |
| **span-retention** | 4-tier trace retention | `idp/platform/eval/span_retention*.py` | built |
| **hermes evals** | browser_use, compaction, readtool | `hermes-agent/evals/` | built |
| **otto verify** | 13 verifier modules incl. `reply_judge`, `eval_hook`, `credentials`, `identity` | `hermes-v2/otto/verify/` | built |
| **external verifier `consultd`** | a second mind; cascade kimi-bridge → deepseek → ollama → none | `claude-estate/scripts/consultd.py` | **live** |
| **consult-verify** | estate-wide handle onto `hermes-v2/bin/verify-consult` | `claude-estate/scripts/consult-verify.sh` | wired |
| **407 BDD scenarios** | 15 feature dirs | `idp/features/` | **live** |
| **crew verify.d** | 20 numbered verification steps | `crew/scripts/verify.d/` | **live** |
| **hermes-config verifiers** | verify_estate, verify_pipeline, verify_system, evidence_verify, post-claim-verifier | `hermes-config/scripts/` | built |
| **deterministic verifier** | rule `deterministic-verifier` | `idp/bin/` | **live** |
| **prm_grader** | process reward model grader | `idp/bin/prm_grader.py` | built |
| **`--selftest`** | every tool proves itself | everywhere | **live** |
| **estate-selftest** | one command runs every guard's selftest | `claude-guards/estate-selftest.py` | **live** |

---

## Layer 6 — State, memory, and the record

| Capability | What it is | Where | State |
|---|---|---|---|
| **estate-twin** | grades ACTUAL vs DECLARED state | `idp/bin/estate-twin-runtime`, `mcp/plugins/estate_twin.py`, `features/twin/` | built |
| **estate.db** | the estate's asset database / graph of record | `idp/catalog/estate.db`, `platform/estate-db/` | **live** |
| **estate-state relay** | every session starts with the whole estate, structured | `claude-guards/estate-state-relay.py` | wired |
| **10 ledger implementations** | kronos ring4, executor mutation ledger, Aevum, crew board, prompt-ledger, crew science ledger, hermes skill ledger, prospector listing ledger, hermes-config complaint/rsi ledgers, estate-broadcast | spread across 10 repos | mixed |
| **estate-graph** | growmos knowledge graph, cross-repo memory | `estate-graph/` | **live** |
| **per-repo growmos graphs** | each repo's own `.growmos/` | everywhere | **live** |
| **estate_memory MCP** | `remember` / `recall`, one memory for every agent | `idp/mcp/plugins/estate_memory.py` | built |
| **hermes memory** | 98 memory-related files | `hermes-agent/` | built |
| **decision log** | research trail shared by every session | `crew/`, `claude-guards/decision-log.py` | **live** |
| **session recorder** | recovery file after every turn | `claude-guards/session-recorder.py` | wired |
| **prompt ledger** | every founder prompt captured once and closed with proof | `claude-guards/prompt-ledger.py` | **live** |
| **Langfuse** | tracing for sessions | `idp/platform/`, `claude-observability-plugin` | built |
| **ClickHouse** | twin TTL, analytics | `idp/bin/idp-clickhouse-twin-ttl` | built |
| **dagster** | data orchestration | `idp/platform/dagster/` | built |

---

## Layer 7 — The doors (MCP and APIs)

| Door | Tools exposed | Where | State |
|---|---|---|---|
| **estate_executor** | `execute_command`, `simulate_command`, `read_job`, `propose_patch`, `simulate_patch`, `verify`, `seal`, `admit`, `propose_mutation`, `verify_mutation`, `seal_mutation`, `admit_mutation`, `verify_inverse` | `idp/mcp/plugins/` | built |
| **estate_simulate** | `simulate_change`, `execute_change` | same | built |
| **estate_guards** | `get_estate_guards` | same | built |
| **estate_memory** | `remember`, `recall` | same | built |
| **estate_sessions** | `list_sessions`, `get_session` | same | built |
| **estate_holmes** | `ask_holmes` (investigator) | same | built |
| **estate_inventory** | `get_estate_inventory` | same | built |
| **estate_state** | `get_estate_state` | same | built |
| **estate_twin** | twin state | same | built |
| **workload_logs** | `get_workload_logs` | same | built |
| **workload_state** | `get_workload_state` | same | built |
| **estate-mcp server** | serves all of the above, 2 replicas, non-root, no SA token | `idp/platform/mcp/estate-mcp.yaml` | built |
| **agentgateway** | the MCP gateway | `idp/platform/mcp/agentgateway.yaml` | built |
| **github-mcp** | GitHub over MCP | `idp/platform/mcp/github-mcp.yaml` | built |
| **FleetView API** | 22 backend modules | `idp/backstage/plugins/fleetview-backend/` | **live** |
| **LiteLLM router** | one router key per identity (LAW 34); the estate's model door | `idp/platform/llm/` | **live** |
| **efficiency gateway / token killer / gisting** | token-cost control | `idp/platform/llm/`, `platform/efficiency/` | built |
| **Backstage** | the portal | `idp/backstage/` | **live** (:3100) |

---

## Layer 8 — Secrets and identity

| Capability | What it is | Where | State |
|---|---|---|---|
| **SOPS + age vault** | `estate-secrets` | `estate-secrets/` | **live** |
| **Bitwarden human-vault bridge** | ExternalSecret/PushSecret pairs | `idp/platform/human-vault-bridge/` | **live** |
| **vault-seed workflow** | mints keys onto a laptop | `idp/.github/workflows/vault-seed.yml` | **live** |
| **LAW 34 — one router key per identity** | nothing calls a vendor directly | estate-wide | **live** |
| **SPIRE** | workload identity | `idp/platform/spire/` | built |
| **jit-broker** | just-in-time cluster write grants | `idp/platform/jit/` | built |
| **rotate-key** | replaces one key everywhere without logging it | `claude-guards/rotate-key.py` | **live** |
| **secret-scrub** | keeps credentials out of files agents write | `claude-guards/secret-scrub.py` | **live** |
| **credential-guard** | refuses a credential in a reply or comment | `claude-guards/credential-guard.py` | **live** |
| **repo_secrets** | refuses a credential reaching a remote | `claude-guards/repo_secrets.py` | **live** |
| **static-secret-gate** | counts static credentials | `idp/bin/static-secret-gate` | **live** |
| **owner-account-gate** | single-provider dependency | `idp/bin/owner-account-gate` | **live** |
| **root-trust register** | who owns each credential | `idp/docs/reference/policy/root-trust.md` | **live** |

---

## Layer 9 — Delivery (how anything reaches production)

| Capability | What it is | Where | State |
|---|---|---|---|
| **Flux GitOps** | the reconciler; hand-apply is forbidden | `idp/clusters/`, `platform/weave-gitops/` | **live** |
| **image-automation** | watches GHCR, writes `flux/image-updates`, merges when green | `idp/platform/image-automation/` | **live** |
| **build-multiarch** | amd64+arm64, Trivy, cosign | `idp/.github/workflows/build-multiarch.yml` | **live** |
| **deploy-when-green** | merges when CI passes | `idp/.github/workflows/deploy-when-green.yml` | **live** |
| **pre-push hook** | the local refusal chain | `idp/.githooks/pre-push` | **live** |
| **ci.yml** | runs `bin/idp-ci` (all rungs) + `bin/idp-rules` | `idp/.github/workflows/ci.yml` | **live** |
| **61 workflows** | the CI surface | `idp/.github/workflows/` | **live** |
| **concierge-deploy** | Modal deploy for the per-order runtime | `idp/.github/workflows/concierge-deploy.yml` | built — `agent.py` only |
| **ironcage** | provable research engine (MCTS + formal) | `ironcage/` | built |
| **lifeboat / survival-stack** | disaster recovery | `idp/platform/lifeboat/`, `survival-stack/` | built |
| **cross-node-drill / drills / chaos** | failure drills | `idp/platform/{cross-node-drill,drills,chaos}/` | built |
| **healing** | automated heal | `idp/platform/healing/` | built |
| **via-negativa** | negative constraints | `idp/platform/via-negativa/` | built |

---

## Layer 10 — The products

| Product | What it is | Where | State |
|---|---|---|---|
| **prospector** | business-opportunity vetting engine selling research packs; 76 scripts, golden sets, 20 persona audits, its own `pi-governance` | `prospector/` | **live** — money rail **503** |
| **mums-concierge** | consent-gated personal agent for Nunn | `chidionyema/mums-concierge` | built, not deployed |
| **sovereign** | personal agent scaffold: concierge, sentinel, vision_brain, shadow | `sovereign/` | built |
| **verdict** | Next.js product (auth, payments, moderation, judges) | `verdict/` | built |
| **haworks-platform** | .NET 9 microservices | `haworks-platform/` | built |
| **mumchimp-medusa** | Medusa commerce | `mumchimp-medusa/` | built |
| **maestro** | requirements/board engine | `maestro/` | built |
| **sentinel-loop** | loop spec + cockpit | `sentinel-loop/` | built |
| **estate** | agents/roles/guards | `estate/` | built |
| **portfolio-site / precedent / tfp / crux / merkleroot / nethermind / ebookStore / ecommerce / nextjs-*** | other repos | various | built |

---

## The exposure — capability built, not used, rebuilt instead

| Capability | Implementations | Should be |
|---|---|---|
| **Ledger / evidence** | 10 | 1 (Aevum) |
| **Judge / eval** | 5 planes, 107 files | 1 |
| **Guard / policy** | 5 implementations | 1 |
| **Sandbox / arena** | 4 (12 backends + kronos + devcontainer + vcluster) | 1 entry rule |
| **Executor** | 3 | 1 (`estate_executor`) |
| **Memory** | 4 (estate_memory, hermes 98 files, growmos, hermes-v2) | 1 |
| **Session steering** | 2 (directive-consume, workforce) | 1 |
| **Twin** | 1 — built, and nothing else uses it | wire it |
| **Voice** | 3 (sovereign/voice, voice-gate, concierge) | 1 |
| **Incident tests against one guard** | 9 (`rule-guard`) | the guard's design is wrong, not under-tested |

---

## The founder's stated target, against measured reality

| Want | Built | Operating |
|---|---|---|
| Work locally **or** cloud | 12 arenas, `local.py` … `vercel_sandbox.py` | agent runs on bare Mac |
| Voice prompt | `sovereign/voice`, `voice-gate`, concierge | sovereign/voice on :8899 |
| Fully model agnostic | `estate-mcp` (11 doors), LiteLLM router, `platform/llm/` | pi ungoverned; router live |
| Fully safe and secure | `agent-reader` SA, JIT broker, kronos 5 rings, 12 arenas | executor **not started**; agent has `kubectl` |
| Fully trusted | Aevum (tamper-detected, PQ signatures), estate-twin | Aevum **ledger empty** |
| Zero chance of cluster down / corruption / breach | Flux reconcile, `bin/idp-kube` read-only, Kyverno, drills, lifeboat | partially |
| Founder snoozing nightly | `jit-broker` phone approvals, `otto-gateway`, board, alerts | built |
