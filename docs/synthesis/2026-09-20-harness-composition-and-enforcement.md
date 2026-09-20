# How agents work on this estate — full synthesis

**Written 2026-09-20 for an external consultant.** Everything below was measured on disk on this
date. Where a component is built but not running, that is stated, because "built" and "operating" are
different facts and this estate has repeatedly confused them.

---

## Part 0 — The shape of the problem

Over roughly three months this estate built a very large amount of agent machinery across at least
eight repositories: execution boundaries, sandboxes, hypervisor rings, evaluators, judges,
red-teamers, verifiers, gates, roles, lanes, evidence ledgers, and observability. Individually most
of it is well-designed and tested.

The composition problem is four questions:

1. **Can all of this run at once?** — Part 5
2. **Can we switch seamlessly between different harness compositions?** — Part 6
3. **What should the default composition be?** — Part 7
4. **How does any of it surface in FleetView/Backstage?** — Part 8

And one architectural question underneath all four:

5. **Where does enforcement live so that no model and no harness can bypass it?** — Part 4

---

## Part 1 — The agent-working surface: what exists

### 1.1 Guard rails (pre-execution policy)

| Layer | Implementation | Where |
|---|---|---|
| Harness hooks | **31 wired hook entries** across 5 events (SessionStart 4, UserPromptSubmit 2, PreToolUse 12, PostToolUse 2, Stop 11), drawn from **77 non-test guard tools** in `claude-guards/` | `claude-guards/`, wired in `~/.claude/settings.json` |
| Policy-as-code | `opa-hook.py` → OPA decisions | `claude-guards/opa-hook.py`, `platform/kyverno/` |
| Lane behaviour | `lanes.json` read fresh per hook call | `~/.claude/lanes.json`, enforced by `close-guard.py`, `tool-drip-guard.py`, `rule-guard.py` |
| Tool-call loop | `tool_guardrails.py` | `hermes-agent/agent/` |
| Narrative/claim guards | `dod-guard.py`, `sdod-live-claim-gate`, `test-prose-gate` | `claude-guards/`, `idp/bin/` |

The Claude Code hook tree (`idp/docs/reference/laws-and-guards.md`, generated):

- **SessionStart** — 4 guards: `sync-guard.py`, `laws-link-guard.py`, `peer-loop-fence.py`, `canonical-root-guard.py`
- **UserPromptSubmit** — 2: `directive-capture.py`, `founder-doc-capture.py`
- **PreToolUse** — 12: `scope-guard.py`, `config-syntax-guard.py`, `dupe-work-fence.py`, `pr-cap-guard.py`, `rule-guard.py`, `ticket-gate.py` (×2), `credential-guard.py`, `merge-divergence-hook.py`, `read-shunt.py` (×2), `opa-hook.py`
- **PostToolUse** — 2: `research-capture.py`, `slow_commands.py`
- **Stop** — 11: `opa-hook.py`, `secret-scrub.py`, `laws-link-guard.py`, `dod-guard.py`, `prompt-ledger.py`, …

### 1.2 Lanes — behaviour profiles, already dynamic

`~/.claude/lanes.json` is a **per-session behaviour profile**, read fresh by guards on every hook
call, so an edit changes live sessions with no restart. A session selects one with
`CLAUDE_LANE=<name>`; unset means `default`.

**Five lanes exist:**

| Lane | goal_required | readonly_run_limit | proactive | close_condition | gate |
|---|---|---|---|---|---|
| `default` | yes | 16 | no | off | report |
| `build` | yes | 12 | no | on | — |
| `research` | yes | 20 | no | on | — |
| `incident` | yes | 18 | no | on | — |
| `platform` | yes | 16 | **yes** | on | — |

Each lane carries **6 "best practices" lines** — deliberately no inheritance, and each line must
name a repeated failure *on this estate with its evidence*, never general advice
("general advice is what an agent learns to skip").

The threshold provenance is measured, not guessed, and is worth quoting because it shows the
estate's own instrument disagreement:

> `readonly_run_limit` was 25, a guess. Measured 2026-08-21 against 79 transcripts >50KB and 8,588
> read-only runs: p50=2 p90=6 p95=9 p99=16 max=43. **Two instruments disagreed by 24× and that
> disagreement is the main finding** — `session_noise.py` reported a worst run of 1017; this
> reports a corpus max of 43. Neither was broken: `session_noise` counted calls since the last
> Edit/Write *tool*, and **58.4% of this estate's state changes happen through a Bash command
> instead**.
> … The old 25 fired 8 times in 79 sessions — 0.10, **INERT**. It was not too aggressive, it was
> not there at all.

**This is the closest thing to the composition-profile selector already built.**

### 1.3 Roles

`claude-estate/agents/roles/` — 10 roles, each a "person per hat" with defined autonomous decision
authority: `ceo`, `engineering`, `finance`, `information-architect`, `inventor`, `legal`,
`marketing`, `operations`, `sales`, `ux`. Plus three functional agents: `pm-agent.md`,
`qa-agent.md`, `receipt-auditor.md`.

Roles live in `~/.claude/agents/roles/*.md`, graded by `role-guard.py` (15 selftest checks). The
design is evidence-based: *"A persona label buys no accuracy"* (EMNLP 2024, 4 model families, 2,410
factual questions).

### 1.4 Execution boundary

**Design** — `idp/mcp/plugins/estate_executor.py`, `idp/platform/executor/daemon.py`:

> The agent does not spawn a shell from its own process tree; it posts a JSON payload to the
> executor, which runs the command under the ceiling and returns the output. The ceiling is applied
> by the executor, not by the caller, so a caller that forgets it — or rewrites itself — does not
> remove it.

- `CEILING_SEC = 60`; a payload carrying its own higher ceiling is **refused, not trimmed**
- Transport: **UNIX domain socket** (`~/.estate/executor.sock`). *"A port would be a network surface
  on a laptop (LAW 21); a socket is a file, and its permissions are the access control."*
- `_runner_argv` wraps in `timeout --signal=TERM <ceiling>s bash -lc <cmd>` — **the kernel enforces
  the bound, not a loop watching a clock** (LAW 43)
- Also owns the **mutation ledger** (`~/.estate/runs/ledgers`), with `propose_mutation`,
  `admit_mutation`, `seal_mutation`, `verify_mutation`, `verify_inverse`

**Measured state** (`bin/idp-executor-status`, run today):

```
daemon:    MEASURED_FAIL   no socket at /Users/roseonyema/.estate/executor.sock
boundary:  UNKNOWN         the agent's own uid can still rewrite:
             platform/executor/daemon.py   owner=501 mode=0644
             bin/exec-daemon               owner=501 mode=0755
executions: none yet (/Users/roseonyema/.estate/runs is empty)
```

Corroborated: `~/.estate/runs` empty, no executor in `/Library/LaunchDaemons`, `_idp_executor` uid
absent.

**Measured consequence:** on this date an agent ran `brew install ffmpeg` as a foreground call for
**1,622 seconds** with no ceiling and no interrupt but killing the session. A 70-second call was then
run deliberately to confirm no harness timeout fires.

**The estate's own diagnosis:**

> The agent runs as `chidionyema`. So does `pi-governance/index.ts` … That is why the 60-second cap
> failed six times while being "fixed": **a control that shares an identity with what it controls
> cannot deny it.**

### 1.5 Sandboxing and execution arenas

| Layer | Implementation |
|---|---|
| 12 pluggable arenas | `hermes-agent/tools/environments/`: `base`, `local`, `docker`, `modal`, `managed_modal`, `daytona`, `vercel_sandbox`, `singularity`, `ssh`, `file_sync` |
| Devcontainer | `agent-guard/sandbox/devcontainer.json` — cgroup limits, cap-drop, read-only |
| systemd scope | `agent-guard/sandbox/systemd-run.sh` |
| vCluster | `idp/platform/sandbox/vcluster/` — OSS 0.36.1, 15m CPU, no persistence, 10m reconcile |
| Shadow/live runners | `idp/platform/sandbox/launch/`: `shadow-runner.yaml`, `live.yaml`, `arm-voice-bench.yaml` |
| k3d | `idp/platform/k3d/` |
| Chaos drills | `idp/platform/chaos/` (pod-kill, mesh), `idp/platform/drills/` |

### 1.6 The AgentOS kernel — `kronos`

Five rings, Rust, one crate each:

| Ring | Crate | Files | Technology |
|---|---|---|---|
| 0 | `ring0-hypervisor` | `vm.rs`, `cow.rs`, `snapshot.rs` | Firecracker/KVM |
| 1 | `ring1-wasm` | `sandbox.rs`, `fuel.rs` | Wasmtime + WASI, fuel-metered |
| 2 | `ring2-ebpf` | `tetragon.rs`, `ast_gate.rs` | eBPF/Tetragon syscall + AST gating |
| 3 | `ring3-egress` | `proxy.rs`, `capability.rs` | vsock proxy + Vault |
| 4 | `ring4-ledger` | `ledger.rs`, `amnesty.rs`, `workflow.rs` | SQLite + SHA-2 append-only |

`VmConfig` already carries `enable_vsock` / `vsock_cid`. Requires Linux 5.15+, eBPF BTF, K8s 1.28+.

### 1.7 Verification and assurance

- **BDD**: **407 scenarios** across 15 feature dirs in `idp/features/` — `sovereign-bus` 45,
  `gates` 24, `battalion` 10, `cognitive-stack` 8, `portal-product` 8, `fleetview` 7, `drills` 4,
  `self-aware-platform` 3, `assurance` 2, and `twin`/`chaos`/`cloud-agnostic`/`estate-rebuild`/`identity` 1 each
- **42 gates** in `idp/bin/` — `idp-evidence-gate`, `idp-reversibility-gate`, `idp-simulate-gate`,
  `idp-mechanism-gate`, `main-verdict-gate`, `dod-live-claim-gate`, `test-prose-gate`,
  `test-executes-gate`, `vendor-agnostic-gate`, `multiarch-gate`, `security-policy-gate`, …
- **External verifier**: `claude-estate/scripts/consultd.py` — *"a second mind on tap, over HTTP,
  for every agent on this machine."* Backend cascade: `kimi-bridge` → `deepseek` → `ollama` →
  `none` (always 503, so the caller's fallback stays honest). Plus `consult-verify.sh` →
  `hermes-v2/bin/verify-consult`.
- **Verifier suites**: `hermes-v2/otto/verify/` (13 modules incl. `verifier.py`, `reply_judge.py`,
  `eval_hook.py`, `credentials.py`, `identity.py`); `hermes-agent/agent/verify/`
  (`environment.py`, `recipes.py`, `runner.py`); `hermes-config/scripts/post-claim-verifier.py`;
  `idp/platform/verification/`; `crew/scripts/verify.d/` (20 steps)
- **Judge-drift detection**: `idp/platform/eval/judge_drift.py` + `judge_drift_loop.py`

### 1.8 Evidence — Aevum (ADR 0028)

`idp/docs/decisions/0028-aevum-replaces-popdd-as-the-evidence-layer.md`. Founder, 2026-09-12:
*"we going forward with the decin for better silution"*.

Aevum (`pypi: aevum-core`) replaced POPDD. The reason is structural:

> POPDD is an HMAC-chained receipt library. Its weakness is structural, not a bug: HMAC is a
> **symmetric** key, so a receipt can be verified only by the party who holds the signing key. That
> is a record two parties share, not evidence a third party can check.

Aevum signs with **Ed25519 AND ML-DSA-65 (post-quantum)** — asymmetric, so any party verifies with a
public key. Each entry is a **COSE_Sign1** receipt with an **RFC 3161** trusted timestamp. It ships
`aevum-verify`, a standalone verifier sharing no code with the runtime. Measured: hash-chained
(`prior_hash`, `payload_hash`), tamper detected (`verify_sigchain()` → `False` after in-place
mutation), frozen dataclass (`FrozenInstanceError` on assignment).

Gate `aevum-evidence` (decision 0028) is fail-closed on an empty ledger:

> Aevum's default store is in-memory and `verify_sigchain()` answers **True about a chain with no
> events**, so a misconfigured deployment reports green while recording nothing.

Local instance exists: `idp/.aevum/local.jsonl`, `idp/platform/observability/aevum.yaml`,
`idp/platform/image-automation/aevum.yaml`.

### 1.9 MCP tooling — 11 doors

`idp/mcp/plugins/`, served by `idp/platform/mcp/estate-mcp.yaml` (2 replicas, topology-spread,
`runAsNonRoot` 10001, no SA token, seccomp `RuntimeDefault`) behind `agentgateway.yaml`:

| Plugin | Tools |
|---|---|
| `estate_executor` | `execute_command`, `simulate_command`, `propose_mutation`, `admit_mutation`, `seal_mutation`, `verify_mutation`, `verify_inverse`, `read_job`, `propose_patch`, `verify_patch`, `simulate_patch`, `admit_payload`, `seal_payload` |
| `estate_simulate` | `simulate_change`, `execute_change` |
| `estate_memory` | `remember`, `recall` |
| `estate_sessions` | `list_sessions`, `get_session` |
| `estate_holmes` | `ask_holmes` (investigator) |
| `estate_guards` | `get_estate_guards` |
| `estate_inventory` | `get_estate_inventory` |
| `estate_state` | `get_estate_state` |
| `estate_twin` | estate-twin state |
| `workload_logs` | `get_workload_logs` |
| `workload_state` | `get_workload_state` |

### 1.10 Control plane and steering

- **`idp/bin/idp-directive-consume`** — reads pending directives written by FleetView's
  `signals.py`, marks consumed in place, appends an ack row. Runs at a Claude Code
  `SessionStart`/`PostCompact` hook, **or a pi turn boundary**.
- `idp/bin/idp-dispatch-install`, `idp/bin/idp-linear-dispatch`
- `idp/platform/orchestrator.py`, `platform/temporal/`, `platform/queue/` (NATS JetStream),
  `platform/router-events/`
- `platform/llm/efficiency_gateway.py`, `platform/efficiency/token_killer.py`, `gisting.py`
- `hermes-agent`, `agent-workforce`, `agent-foundry`, `otto-gateway`, `maestro`, `crew`

### 1.11 Observability

`platform/observability/`, `platform/observability-collector/`, `platform/monitoring/`,
`platform/dagster/`, Langfuse (+ `claude-observability-plugin`), `platform/estate-db/`,
`idp/bin/idp-clickhouse-twin-ttl`.

### 1.12 Twin estate

`idp/bin/estate-twin-runtime`, `mcp/plugins/estate_twin.py`, `idp/features/twin/estate-twin.feature`.
Purpose — grade **ACTUAL vs DECLARED**:

> The estate has three inventories and every one reports DECLARED state as if it were ACTUAL.
> Measured 2026-09-12: **1,523 unmerged branches, 178 worktrees, 722 files on branches that exist on
> no commit of main, 11 deployments scaled to zero, and three agents deployed and dead** (research
> 0/1, hindsight 0/1, otto-gateway 2/13). No inventory could name a single one of those.

---

## Part 2 — What runs on this machine, measured

**Two harnesses installed:** `pi` (`/usr/local/bin/pi`), `claude` (`/usr/local/bin/claude`).

- Pi extensions: `fleetview-directives.ts`, `read-shunt.ts`. **No `tool_call` handler in either.**
  `~/.pi/agent/settings.json` has **no permission model**. Pi documents no bash-timeout env var.
- `claude-guards` searched for `\.pi/`, `pi-coding-agent`, `PI_SESSION`, `PI_CODING_AGENT` →
  **zero hits.** The guard estate covers Claude Code only.
- `slow_commands.py`'s timing corpus is built from Claude Code transcripts, so tool calls from any
  other harness are invisible to it.
- `~/.pi/agent/bin/run` — cited by `estate_executor.py` as the detached runner — **does not exist**
  (`daemon.py:125` records that as a hardcoded path later fixed by deriving from `__file__`).
- `prospector/pi-governance/src/index.ts` — the four-pillar DNA extension (`EPISTEMIC HUMILITY`,
  `SEMANTIC TOOL PRIORITIZATION`, `PERCEPTION-PLANNING-EXECUTION`, `CLOSED-LOOP SELF-HEALING`) —
  **exists, but is not installed** into `~/.pi/agent/extensions/`.
- `bin/idp-laws-guards-report` — the generator of the estate's own law index — currently emits
  `## The 0 laws` with an empty table and exits 0. Its source (`~/AGENTS-FULL.md`) is not found.

---

## Part 3 — The four enforcement attempts, and why each is incomplete

| Attempt | Layer | Why it is not sufficient alone |
|---|---|---|
| Claude Code hooks (31 wired entries from 77 guard tools, plus 43 incident tests) | the harness | Binds **one harness**. Nothing for pi, CrewAI, Rust, or a shell script. |
| `lanes.json` | the harness | Behavioural, not an execution bound. Read by Claude-side guards. |
| `agent-guard` | OS/resources | Built against a **load-227 incident**; contains CPU/launchd abuse. Not an execution ceiling, not a sandbox for agent sessions. |
| `estate_executor` | OS/process | **Correct layer.** Built, tested, never started; daemon still agent-owned. |

**Conclusion:** only the *last* is in the right place. The first three are useful, and none of them
can be the boundary.

---

## Part 4 — Where enforcement must live (the architectural answer)

**Enforcement cannot live in the model, the harness, or the framework.** Patch pi's tool registry and
you must patch the next harness. Patch a LangChain callback and you must patch the next framework.
Each is a new hole, and the whole point of model- and harness-agnosticism is that you don't patch
per-agent.

**It must sit below all of them — at the OS/process/container boundary.** That is what `kronos`'s
rings are, and why `estate_executor` is a *socket* rather than a library: **a socket is reachable by
anything; a library only by Python.**

```
    ┌──────────────── sandbox (ring0/ring1 · agent-guard · vcluster) ─────────────────┐
    │                                                                                 │
    │    pi        claude       crewai      rust-harness     intern's shell script    │
    │     │           │            │              │                  │               │
    │     └───────────┴────────────┴──────────────┴──────────────────┘               │
    │              no shell · no direct network · no host mounts                      │
    │                              │                                                  │
    │                    the ONE mounted channel:                                     │
    │                       executor socket                                           │
    └──────────────────────────────┼──────────────────────────────────────────────────┘
                                   │
                          ── boundary ──
                                   │
                  ┌────────────────▼─────────────────┐
                  │  executor daemon                  │
                  │  separate uid (_idp_executor)     │
                  │  outside the sandbox              │
                  │  ceiling applied HERE, not by     │
                  │  the caller                       │
                  │  decides: what · as whom · where  │
                  └────────────────┬─────────────────┘
                                   │
                        ring4 / Aevum ledger (append-only)
```

**If that is the environment, the agent's identity is irrelevant.** Claude, GPT, a local model,
CrewAI, a Rust harness, or a script an intern left running — none can reach raw execution, because
there is no raw execution to reach. **The environment has one door.**

Three properties make it hold, each already designed in the codebase:

1. **The ceiling is applied by the executor, not the caller** — and a payload claiming a higher
   ceiling is refused, not trimmed.
2. **The executor runs outside the sandbox as a uid the agent does not hold** —
   `bin/idp-executor-install`.
3. **The socket is the only channel** — *"a socket is a file, and its permissions are the access
   control."*

---

## Part 5 — Can all of this be used at once?

**No — not as it stands. The reason is compositional, not a shortage of components.**

The estate has **N parallel implementations of the same concepts**:

| Concept | Implementations found |
|---|---|
| Guard / policy | Claude hooks (31) · `hermes-agent/agent/tool_guardrails.py` · `agent-guard/bin/*` · OPA · Kyverno · `post-claim-verifier.py` |
| Ledger / evidence | `kronos/ring4` · executor mutation ledger · Aevum (`.aevum/local.jsonl`) · `crew` board · `prompt-ledger.py` · Langfuse |
| Eval / judging | `idp/platform/eval/` (17) · `hermes-agent/evals/` (×3) · `hermes-v2/otto/verify/` (13) · `prospector` golden sets · `bin/prm_grader.py` |
| Sandbox / arena | `hermes-agent/tools/environments/` (12) · `kronos` rings 0–1 · `platform/sandbox/{vcluster,launch}` · `agent-guard/sandbox` · k3d · staging canary |
| Session steering | `idp-directive-consume` · FleetView `signals.py` · `agent-workforce` |
| Verification | `crew/scripts/verify.d/` (23) · `hermes-config/scripts/verify_*.py` · `platform/verification/` |

A guard binds **only the harness it is installed into**. Twelve Claude PreToolUse guards do nothing
for a pi session, a CrewAI crew, a Rust binary, or a shell script. Three ledgers mean three answers to
"what happened". Five judging planes mean five notions of "verified". **This is the actual blocker.**

**What is genuinely composable today:**

- **`estate-mcp`** (11 tools, 25+ tool functions) — HTTP/MCP, so anything speaking MCP can call it.
  FleetView's `executor_link.py` already does.
- **`platform/queue` (NATS JetStream)**, `platform/temporal/`, `platform/orchestrator.py` — transport-level, agent-agnostic
- **`estate_memory`** (`remember`/`recall`), **`estate_sessions`** — shared state any harness can use
- **`kronos`** — agnostic by construction; its rings do not know what an agent is
- **`agent-guard/sandbox`** — agnostic at the OS layer
- **`lanes.json`** — already a live, per-session, dynamically-read behaviour profile

So an agnostic layer **exists**. What does not exist is **a rule that everything must enter through it.**

---

## Part 6 — Can we switch seamlessly between compositions?

**Yes — and more of the mechanism exists than is commonly realised.** Three pieces are already in
place:

1. **`lanes.json` is read fresh on every hook call**, so changing a lane changes a live session
   **with no restart**. The estate already solved dynamic re-composition.
2. **`idp-directive-consume`** already delivers steering to **both** Claude and pi, at a pause
   point. It is a working operator→session channel.
3. **FleetView `executor_link.py`** already long-polls from the cluster to the laptop daemon over the
   tailnet, with `tag:founder-mac` as the only permitted source.

**What is missing is the join:** lanes are Claude-side only, and they govern *behaviour*
(`goal_required`, `readonly_run_limit`, `proactive`, `close_condition`), not *containment* (sandbox
ring, ceiling, egress, ledger). There is no single declared "profile" that a session runs under, and
no way for an operator to switch it.

### 6.1 Proposed composition profiles

| Profile | Sandbox | Ceiling | Egress | Ledger | Use |
|---|---|---|---|---|---|
| `explore` | ring1-wasm or devcontainer | 60s | deny-all + allowlist | ring4 | read-only reconnaissance |
| `build` | devcontainer | 300s | package registries only | ring4 | normal implementation |
| `operate` | devcontainer + vault sidecar | 60s | estate endpoints | ring4 + mutation ledger | anything touching production |
| `evaluate` | ring0-vm | per-task | replay fixtures only | ring4 | evals and red-team |
| `unleashed` | none | none | unrestricted | ring4 | **founder-only, named, time-boxed, logged** |

**The profile is chosen by the operator or the scheduler, never by the agent.** The agent cannot
request a different profile; it can only be placed in one. That is what makes switching seamless
without making it bypassable.

The join to build: extend `lanes.json` from behaviour-only to behaviour + containment, and let
FleetView set it through the directive channel that already works.

---

## Part 7 — What should the default composition be?

Three classes, one entry requirement:

1. **Default for all agent work: sandboxed, no exceptions.** An agent session runs inside a sandbox
   with no shell, no direct network, no host mounts, and one mounted channel — the executor socket.
   (`agent-guard/sandbox` shape + `estate_executor` socket; `kronos` rings 0/1 where the platform
   supports it.)
2. **Default harness = whichever the operator prefers, because the harness stops mattering.** Pi,
   Claude, CrewAI, Rust — equivalent, because none can reach raw execution. **This is the payoff of
   Part 4.**
3. **Default judging = the estate's own, not the harness's.** `idp/platform/eval/` and
   `hermes-agent/evals/` run against *artifacts*, not sessions. A harness's internal notion of "done"
   is not evidence — `dod-guard.py` exists to refuse exactly that claim.

---

## Part 8 — FleetView / Backstage integration

### 8.1 What exists

`idp/backstage/plugins/fleetview-backend/src/` — **22 modules**: `sessions.py`, `signals.py`,
`mutations.py`, `evals.py`, `trace.py`, `spend.py`, `graph.py`, `blast.py`, `ledger_tail.py`,
`executor_link.py`, `nats_adapter.py`, `claude_code_adapter.py`, `voice.py`, `handoff.py`,
`notes.py`, `history.py`, `redact.py`, `device_access.py`, `config_guard.py`, `serve.py`,
`routes.py`, `__init__.py`.

**7 BDD feature files**: `cp1_contract`, `cp2_board`, `cp3_signals`, `cp4_every_runtime`,
`cp5_offering`, `cp6_adapters`, `cp8_steering`.

And critically — **`executor_link.py` already connects FleetView to the executor daemon**, reading
and acting on the *one* mutation ledger and speaking its AF_UNIX protocol. Its own header explains
why the ledger is never duplicated:

> `daemon.py`'s `live_worktree()` derives the working tree from the daemon's own file location, so the
> daemon can only ever mean the founder's real, current, possibly-uncommitted checkout … the ledger
> and the daemon stay laptop-side, unmoved, and this module is the wire between an in-cluster HTTP
> call and that unmoved laptop process — **never a second store, never a second gauntlet (LAW 43)**.

Trust is the tailnet: `platform/tailscale/policy.hujson` names `tag:founder-mac` as the only source
permitted to reach `tag:estate-fleetview-executor`.

**So the integration surface already exists. It is not a new build.**

### 8.2 A new page: "Harness & Enforcement"

The missing operator view of Part 4. Proposed panels, each backed by data that already exists:

| Panel | Source | Answers |
|---|---|---|
| **Boundary status** | `bin/idp-executor-status` (already reports `MEASURED_OK`/`UNKNOWN`) | Is the executor running? Does the agent's uid still own the daemon? |
| **Sessions × harness** | `sessions.py` + `claude_code_adapter.py` | Which sessions run, under which harness, in which ring |
| **Composition profile per session** | new (Part 6) | Is this `build` or `unleashed`, and who chose it |
| **Ceiling violations** | `~/.estate/runs/` + ring4 | Every command that hit or approached the ceiling |
| **Command timings** | `slow_commands.py`'s `command-timings.jsonl` | What is slow here; was it backgrounded |
| **Guard firing per harness** | `hook-outcomes.jsonl` + OPA | Which guards fired, on which harness, and which are blind |
| **Eval / judge results** | `evals.py`, `platform/eval/` | Last eval per artifact; judge-drift status |
| **Evidence chain** | Aevum `.aevum/*.jsonl` + `idp-evidence-gate` | Does the chain verify? Is the ledger empty (fail-closed)? |
| **Ledger tail** | `ledger_tail.py`, ring4 | The append-only record, live |
| **Mutation queue** | `mutations.py` | Pending approve/reject, as today |
| **Twin: ACTUAL vs DECLARED** | `estate_twin` MCP tool | Where the estate's own reports disagree with reality |
| **Lanes** | `lanes.json` + `guards.json` | Which lane each session is in, and what it binds |

The **Boundary status** panel is the one that closes the loop: today, whether an agent is contained
is **asserted**; this makes it **measured**, per session, continuously.

### 8.3 The three integration seams

1. **`executor_link.py`** — already wired. Extend it to carry the executor's *status envelope*
   (ceiling, uid, socket ownership) alongside the mutation ledger, so boundary health is a panel
   rather than a script someone remembers to run.
2. **`signals.py` / `idp-directive-consume`** — steering already reaches Claude **and** pi. The same
   channel is the natural carrier for **profile selection**: an operator sets a session's profile in
   FleetView; the session's next turn boundary applies it. **This is how "switch seamlessly"
   becomes an operator action rather than a re-launch.**
3. **The MCP `estate_*` doors** — `estate_sessions`, `estate_state`, `estate_twin`, `estate_guards`,
   `estate_evidence` already expose the data. A Backstage page should read the **MCP server**, not
   open a new path to the filesystem, so the portal sees exactly what an agent sees.

### 8.4 Why FleetView specifically

FleetView is already the live control surface for agent sessions (`cp2_board`, `cp4_every_runtime`,
`cp8_steering`). Enforcement status is the same class of fact as "is this session thinking or stuck"
— and it is currently **the only major session fact with no panel.** Adding it there means an
operator sees containment and session state in one view, which is the precondition for trusting the
composition at all.

---

## Part 9 — What is actually missing

1. **`sudo bin/idp-executor-install` has not been run.** Creates `_idp_executor` + root LaunchDaemon.
   It deliberately refuses agent invocation (*"it refuses to proceed on anything that looks like an
   agent-invoked shell"*) — correct, and why it is a founder step (LAW 54).
2. **The agent's bash has not been removed or routed.** The instruction was *"find where we have done
   this, operationalise it, make sure every agent session is aware, and **remove bash access
   afterward**."* The last clause is undone.
3. **No sandbox is used for agent sessions on this machine.** Pi and Claude run on the host as the
   founder's uid.
4. **`pi-governance` exists in `prospector`, not installed into `~/.pi/agent/extensions/`.**
5. **No composition-profile selector.** Part 6's profiles are a proposal; nothing chooses them.
6. **`bin/idp-laws-guards-report` emits "0 laws"** — the estate's own law index is empty.
7. **Five ledgers, five judging planes, five verification suites** — no projection reconciles them.

---

## Part 10 — Open questions for the consultant

1. **Where should the default composition be enforced** — harness launcher, sandbox image, or the
   scheduler? (The estate has no single launcher today.)
2. **Is `kronos` the target runtime, or is `agent-guard` + `estate_executor` the pragmatic macOS
   path?** `kronos` needs Linux 5.15+/eBPF/K8s; this machine is macOS. Both are built and do not
   currently interoperate.
3. **How should N parallel ledgers be reconciled** — adopt one, or build a projection?
4. **What is the minimum bypass-proof version on macOS**, given no firecracker and no eBPF?
5. **Should the composition profile be a session, task, or environment property?** This determines
   whether switching is cheap or expensive.
6. **Should lanes (behaviour) and profiles (containment) merge into one concept**, or stay separate?

---

## Appendix A — Every guard tool, one line each


`claude-guards/` — 125 files: **77 non-test guard tools** (below), **43 incident tests** (§A.2), and 5 other tests. Which tools are *wired* to which hook event is `idp/docs/reference/laws-and-guards.md`; a tool existing here does not mean it runs.


| Tool | What it does |
|---|---|
| `action_items` | Every action item in every programme doc, extracted and tracked without anyone asking. |
| `blocker-guard` | Stop hook (LAW 47 / R30). A reply that says FOUNDER ACTION: or STAGED: must have reached the |
| `board-deliver` | Hand a running session the board messages it has not seen yet. |
| `board_serve` | Serve the founder's board on a fixed local URL, so reading it needs no agent session. |
| `canonical-root-guard` | Tell a session, at its start, when it is working outside the canonical root. |
| `close-guard` | Refuse a reply that does not close, and a DONE: that carries no receipt. |
| `config-syntax-guard` | PreToolUse guard: refuse a write that would leave a config file unparseable. |
| `config-syntax-sweep` | Count every config file on this estate its own consumer cannot parse. |
| `config_syntax` | Parse a config file the way the service that reads it parses it. |
| `consultd` | A second mind on tap, over HTTP, for every agent on this machine. |
| `credential-guard` | Refuse a credential value in a reply or in a GitHub comment body (crew#407, LAW 21). |
| `decision-log` | The estate's research trail and decision log, shared by every session and agent. |
| `deepseek_bridge_backend` | consultd.py backend for the DeepSeek browser bridge. |
| `direct_api_backends` | Consult backends that are one HTTPS call to a key, with no browser in them. |
| `directive-capture` | Capture every founder message to a durable, queryable log, in every project, forever. |
| `directives` | Read back everything the founder has ever said, in one command. |
| `dod-guard` | Refuse a reply that claims done without the Definition of Done evidence. |
| `dupe-work-fence` | Refuse a pull request that duplicates another session's claim. |
| `estate-broadcast` | Estate Broadcast System — Safe, concurrent, validated JSON append. |
| `estate-selftest` | One command that runs every guard's own selftest and says PASS or FAIL out loud. |
| `estate-state-relay` | estate-state-relay.py -- crew#648 CP4: every session starts with the whole estate, structured. |
| `estate_board` | The board, as code. crew#306 (founder, 2026-08-26): "You never say 'keep moving' again. |
| `estate_broadcast` | Estate Broadcast System — Safe, concurrent, validated JSON append. |
| `feed-guard` | feed-guard: every session writes a six-line handoff to ~/.estate/feed.md every 15 minutes. |
| `feed_meter` | feed_meter: the measured token bill, one line for every handoff (crew#26 CP-D). |
| `feed_publish` | feed_publish: render, redact and publish the estate feed to the IDP state branch. |
| `founder-blocker` | The one command for a founder blocker (LAW 47 / R30). Founder, 2026-08-25, after missing the |
| `founder-deliver` | Nothing for the founder goes into the void: a DONE: reply that links a deliverable is sent to |
| `founder-doc-capture` | A founder-pasted document becomes a file in git the moment it arrives. No session searches for it. |
| `founder_actions` | Every thing only the founder can authorise, in one place, closing itself when it is done. |
| `founder_board` | The founder's board: what is done, what is broken, what is waiting on him. |
| `friction-relay` | Carry the founder's complaints to every session, not just the one that heard them. |
| `goal_graph` | The goal net: objectives as a graph, a walk back to core, and a return path after a switch. |
| `guard_report` | The one place a guard says "I broke" out loud. |
| `hc-wrap` | hc-wrap.sh <slug> <command...> — run a scheduled job under Healthchecks dead-man monitoring. |
| `hook-run` | hook-run.py <hook.py> [args...] -- run one Claude Code hook and record its outcome. |
| `issue_dod` | The body and lane every automatically opened issue carries. |
| `kimi_bridge` | Kimi browser bridge. Drives a signed-in www.kimi.com session over Playwright. |
| `kimi_bridge_backend` | consultd.py backend that talks to the Kimi browser bridge over loopback. |
| `law-writer` | Write the dynamic laws from what actually keeps going wrong, and find contradictions. |
| `laws-link-guard` | Keep every provider's rules file pointing at ~/AGENTS.md. |
| `memory-loop` | memory-loop.py — automatic "checkpoint to permanent memory, survive the reset" loop. |
| `merge-divergence-hook` | PreToolUse(Bash) hook: refuse a `git merge <target>` when the target has |
| `merge-target-divergence-guard` | Refuse a `git merge <target>` call if the target has diverged wildly from |
| `no-local-vm-guard` | R26-no-local-vm-on-laptop (founder 2026-08-25): no VM boots on the Mac; compute is Oracle. |
| `opa-hook` | Ask OPA about a hook payload. Decides nothing itself. |
| `peer-loop-fence` | Refuse a peer message that re-raises something already on the estate board. |
| `pr-cap-guard` | PreToolUse adapter for policy/pr_cap.rego (crew#504 CP5, crew#66): `gh pr create` is refused |
| `pr-evidence` | — |
| `pr-green-guard` | Refuse a reply that names a pull request whose checks are not green (R61). |
| `pr-why` | Print WHY each open pull request is red, not that it is red. |
| `prompt-ledger` | Every founder prompt, captured once and closed with proof. |
| `read-shunt` | read-shunt.py — Claude Code PreToolUse shim over the read-shunt core. |
| `reflect` | Mine the transcripts for the moments the founder stopped an agent, and rank what caused them. |
| `repo_secrets` | Refuse to let a credential reach a git remote, and find the ones already there. |
| `research-capture` | PostToolUse hook: capture a research pass without being asked (crew#72). |
| `rotate-key` | Replace one API key everywhere it is stored, without it ever touching a log. |
| `rule-guard` | PreToolUse guard: turn written rules into refusals. |
| `scope-guard` | PreToolUse guard: keep the global rules file free of project-specific content. |
| `secret-scrub` | Keep live credentials out of the files agents and shells write. |
| `session-recorder` | Write a recovery file after every turn, so a dead session loses nothing. |
| `session-timeout` | crew#306 CP3. Every 5 minutes: a session holding a goal that has produced no transcript |
| `session_emit` | Emit one OTLP log record per turn, so an agent session is a workload the estate can see. |
| `session_live` | What every agent session is doing right now, computed at read time from the hook ledger. |
| `silent_side_effect` | Find the guards that cannot tell you they are broken. |
| `single-session-guard` | single-session-guard.py -- enforce the 2026-09-08 standing rule: only one interactive |
| `slow_commands` | Tell a session when it is about to block on a command that has always been slow. |
| `state_vocabulary` | crew#656 CP0: the state vocabulary, and the banned-token check that enforces it. |
| `statusline-context` | statusline-context.py — Claude Code status line that surfaces the ONE number |
| `stuck_detector` | stuck_detector.py — notice when an autonomous agent session has stopped making progress. |
| `stuck_detector_tick` | One tick of stuck_detector.py, with a heartbeat. |
| `sync-guard` | The Mac runs main. At every SessionStart the live guards checkout fast-forwards to origin/main, |
| `ticket-gate` | Every session carries a GitHub issue, or it does not get to change anything. |
| `token-audit` | Token-spend probe for Claude Code sessions.  READ-ONLY. |
| `tool-drip-guard` | tool-drip-guard.py — PreToolUse enforcement for the batching / delegation rules. |
| `tracked` | LAW 24: if it is load-bearing, it is in git. |
| `vendor-lock-guard` | vendor-lock-guard: no plan step, checkpoint or instruction may require a vendor-only channel. |

*77 non-test guard tools.*


### Appendix A.2 — Incident tests (the rung-4 record)


Each is a real incident frozen as an executable test.


| Test | The incident it encodes |
|---|---|
| `test_incident_20260907_ops_is_computed_not_produced` | The /ops page is computed on the request, so it cannot freeze again. |
| `test_incident_blocked_escape_inside_backticks` | Incident 2026-08-28 (session f3f21d6e, crew#593): a validated BLOCKED: reply was refused by |
| `test_incident_crew13_live_copy_behind_main_is_reinstalled_not_pushed` | claude-guards aae334c, 2026-08-27 04:42Z: tracked.py --sync read ~/.claude/settings.json and |
| `test_incident_crew13_no_job_names_hermes_home` | Incident crew#13 (2026-08-26): ~/.hermes was retired on 2026-08-22, but eight loaded launchd |
| `test_incident_crew13_tracked_never_mirrors_a_generated_entry` | Incident crew#13 (2026-08-26): claude-guards#80 moved eight committed plists off |
| `test_incident_crew153_body_file_named_through_a_variable_is_read` | Incident crew#153 (2026-08-27): `gh pr create --body-file "$SP/body.md"` was refused by |
| `test_incident_crew280_pause_guard` | crew#280 / LAW 48: session 8f034e1e found the KINI worker down and wrote "I stop here since |
| `test_incident_crew284_founder_asked_to_resend` | Incident 2026-08-27 (crew#284): three FOUNDER ACTION lines asked the founder to resend /sb-list |
| `test_incident_crew306_hard_execution_chain` | Rung 4 (incident test): crew#306. Founder, 2026-08-26: agents ended turns goalless, claimed |
| `test_incident_crew306_launchd_gh_path` | Incident crew#306: launchd ran auto-objective --scan with PATH=/usr/bin:/bin and printed |
| `test_incident_crew312_render_selftest_is_check` | crew#312: jobs.json drifted from 23 live plists and nothing said so, because render.py --check |
| `test_incident_crew323_ticket_gate_skips_compaction_summary` | Incident test (rung 4), named for crew#323: the auto-ticket hook took a compaction |
| `test_incident_crew326_audit_check_registered_after_main` | crew#326: c_hook_router was appended to CHECKS after `raise SystemExit(main())`, so the |
| `test_incident_crew488_auto_merge_outruns_the_guard` | crew#488 (2026-08-29): idp#675 was queued with |
| `test_incident_crew490_no_checks_names_the_conflict` | crew#490 (2026-08-27): a pull request that conflicted with main had zero check runs for 40 |
| `test_incident_crew526_a_box_only_the_founder_can_tick` | Founder, 2026-08-28: "should be waiting on [me] unless its physical action [machines] cannot do". |
| `test_incident_crew526_board_closes_what_is_finished` | crew#526 CP2 (founder 2026-08-27: "158 unclaimed open how come this never goes down"): guards filed |
| `test_incident_crew527_board_ranks_finish_first` | crew#527 CP2 (founder 2026-08-27: "we have many features half done ... prioritisation"): the |
| `test_incident_crew527_new_issues_carry_a_lane_and_three_boxes` | crew#527 CP4 (founder 2026-08-27: "we have many features half done"): 123 of 187 open crew issues |
| `test_incident_crew52_an_empty_session_is_idle_not_waiting` | crew#52: on 2026-08-23 aiden raised 9 alerts and 7 were WAITING lines from ONE empty |
| `test_incident_crew656_cp0_state_vocabulary` | crew#656 CP0. The two failures of 2026-08-29 in test form, plus the false-refusal |
| `test_incident_crew69_backup_copy_committed_into_scripts` | crew#69: a backup copy of a script was committed into ~/.claude/scripts (context-guard-hook.py.bak-20260806). |
| `test_incident_crew69_every_script_is_wired` | crew#69: 31 of 59 scripts were reachable by nothing and read as live machinery. |
| `test_incident_crew73_every_producer_row_carries_its_time` | Incident crew#73: 902 close-guard observations and 1,526 stuck_detector session rows had no |
| `test_incident_crew81_ingit_findings_are_not_a_dead_man_failure` | crew#81 (rung 4): com.founder.ingit exits 1 whenever the estate has a hole, which is most of the |
| `test_incident_founder_action_without_steps` | Founder, 2026-09-09: "every founder action should come with clear instructions, else needs back and forth". |
| `test_incident_founder_asked_to_click_a_console` | Incident 2026-08-26 (crew#269 -> crew#281): a session sent the founder a FOUNDER ACTION to create a |
| `test_incident_founder_blocker_claimed_a_self_serve_credential` | Incident 2026-08-26 (crew#325, crew#267, crew#284): four sessions sent FOUNDER ACTION: "tap Create on |
| `test_incident_founder_blocker_pushed_a_password` | Incident 2026-08-26 (crew#269): founder-blocker.py sent the catalogue password over Telegram. |
| `test_incident_founder_blocker_sent_a_flag` | Incident 2026-08-26: `founder-blocker.py --help` reached Telegram as "STAGED: --help is ready" |
| `test_incident_rule_guard_bare_kubectl` | Incident test. 2026-08-28, session a0d64ea4, crew#66: a bare `kubectl get ds -n observability-agent` |
| `test_incident_rule_guard_graded_the_wrong_repo` | rule-guard refused a 1-file crew PR as "65 files" by grading the session's repo. |
| `test_incident_rule_guard_merge_by_variable_fails_open` | rule-guard let `gh pr merge "$PR"` through while the PR's qa check was still running. |
| `test_incident_rule_guard_prose_flags` | Rung 4 (incident test). 2026-08-26, session 78caaa17: rule-guard refused |
| `test_incident_rule_guard_quiet_push` | Rung 4 (incident test). 2026-08-26, session 78caaa17: `git push -q ... | tail -1` |
| `test_incident_rule_guard_repo_flag_from_another_gh_call` | rule-guard applied a -R from a later `gh issue comment` to the merge's check query. |
| `test_incident_rule_guard_repo_flag_graded_the_wrong_repo` | rule-guard refused `gh pr merge 2 --repo chidionyema/claude-estate` with another repo's checks. |
| `test_incident_rule_guard_second_telegram_poller` | Incident test. 2026-08-27 23:30 -> 2026-08-28 08:15, crew#516: The Architect went silent on |
| `test_incident_rule_guard_tilde_cd_graded_the_wrong_repo` | rule-guard refused `cd ~/dev/code/idp && gh pr merge 6` by reading another repo's PR #6. |
| `test_incident_secret_scrub_orphan_pileup` | 2026-08-31: 38 orphaned secret-scrub.py processes (ppid 1, hours old) took the founder's |
| `test_incident_staged_sentence_doubled` | Incident 2026-08-26 (idp#160, Telegram msg 14076): a session passed the whole STAGED |
| `test_incident_state_mirror_push_goes_no_verify` | The state-mirror push in feed_publish.py goes --no-verify (claude-guards#239). |
| `test_incident_tracked_committed_into_a_checkout_it_does_not_own` | tracked.py --sync mirrored load-bearing files into ~/.claude/scripts itself. |

*43 incident tests.*


---

## Appendix B — Every gate, one line each


`idp/bin/*-gate` — 42 gates. Each is a refusal, not a report.


| Gate | What it refuses |
|---|---|
| `ai-act-gate` | ai-act-gate [ROOT]: every registered AI system has an Annex IV technical file |
| `cloud-agnostic-gate` | Count provider-specific references in the platform outside the compute provisioner. |
| `dod-live-claim-gate` | dod-live-claim-gate [FILES...]: a doc that claims a capability is built AND live must show |
| `estate-zone-gate` | The estate's DNS zone is written once, in clusters/<cluster>/estate-config.yaml (ESTATE_ZONE). |
| `gvisor-cell-fence-gate` | Refuse a gVisor-cell namespace whose fence allows internet egress (crew#892 CP4, ZT step 6). |
| `gvisor-cell-gate` | Grade one YAML file or directory for a gVisor cell namespace violation (crew#892 CP4). |
| `idp-api-version-gate` | idp-api-version-gate — an apiVersion the cluster does not serve is a row that never reconciles. |
| `idp-availability-gate` | Every founder-facing surface survives losing one node (crew#539). |
| `idp-bdd-proof-gate` | No pull request without BDD proof, across all agent sessions. |
| `idp-catalog-links-gate` | Refuse a catalog entity whose metadata.links[].url is not an absolute https/http URI. |
| `idp-catalog-spec-type-gate` | Refuse a catalog entity whose spec.type is not in the estate ontology. |
| `idp-envsubst-gate` | Flux post-build substitution, run before the PR merges, with the tool Flux runs (crew#483). |
| `idp-evidence-gate` | idp-evidence-gate — a receipt that does not verify is not evidence. |
| `idp-flux-subst-gate` | Refuse a shell parameter expansion Flux will rewrite before the pod runs it. |
| `idp-grader-exit-gate` | Refuse a grading step whose verdict cannot fail the run (LAW 28). |
| `idp-local-evidence-gate` | Validate .aevum/local.jsonl: non-empty, hash chain intact. |
| `idp-main-green-gate` | idp-main-green-gate -- refuse a new branch when main's last CI run is red. |
| `idp-max-open-prs-gate` | idp-max-open-prs-gate — refuses a push when the REPO already has > MAX open non-bot PRs. |
| `idp-mcp-first-gate` | idp-mcp-first-gate — a state question answered by shell recon instead of the platform. |
| `idp-mechanism-gate` | A mechanism this repository depends on may not be switched off, deleted or unproduced. |
| `idp-reversibility-gate` | idp-reversibility-gate — a mutation with no inverse is a mutation nobody can take back. |
| `idp-router-egress-gate` | Guard against a second, undeclared LiteLLM router config landing outside the reviewed set |
| `idp-session-gate` | The session-plane caller for the gates that grade a TURN, not a pull request. |
| `idp-simulate-gate` | bin/idp-simulate-gate — no state-changing estate MCP tool without a simulate twin (MUM-288). |
| `idp-wip-gate` | idp-wip-gate -- refuse a new PR when 3 or more PRs are already failing CI. |
| `law32-gate` | LAW 32 at the pull request: a feature ships with a demo and an onboarding. |
| `main-verdict-gate` | main-verdict-gate: a workflow that grades main never cancels main's own run. |
| `matrix-gate` | The reference decision matrix, enforced (ADR 0009, crew#562). |
| `migration-gate` | migration-gate <script>: R22 mechanism 1 (crew#186 CP1). Three phases on a |
| `multiarch-gate` | multiarch-gate: every image build that can reach a registry names both |
| `nodesoftware-operator-gate` | bin/nodesoftware-operator-gate |
| `ns-fence-gate` | Refuse a namespace that is born without its fences. |
| `owner-account-gate` | owner-account-gate [FILE]: how many external providers the estate depends on have a single |
| `plist-gate` | Every launchd/*.plist.tmpl must render to a plist that parses. |
| `port-gate` | port-gate: a port is bound only if catalog/ports.yaml says so. |
| `security-policy-gate` | security-policy-gate [PAGE]: every control row on the security policy page |
| `spec-gate` | spec-gate [BASE_REF]: a change to code must come with a change to the |
| `static-secret-gate` | Count every static credential the estate still holds, on this host and in the vault. |
| `test-executes-gate` | A test that executes nothing is not a test. |
| `test-prose-gate` | R76 (founder 2026-09-03): a test grades behavior or parsed structure, never prose. |
| `vendor-agnostic-gate` | Refuse a hardcoded vendor name in the engine's product code, outside its one registry. |
| `vendor-name-collision-gate` | A deck that replaces a vendor operator may not reuse the operator's cluster-scoped names. |

*42 gates.*


---

## Appendix C — Execution arenas, one line each


`hermes-agent/tools/environments/` — every backend an agent can be placed in.


| Arena | Backend |
|---|---|
| `base` | Base class for all Hermes execution environment backends. |
| `daytona` | Daytona cloud execution environment. |
| `docker` | Docker execution environment for sandboxed command execution. |
| `file_sync` | Shared file sync manager for remote execution backends. |
| `local` | Local execution environment — spawn-per-call with session snapshot.""" |
| `managed_modal` | Managed Modal environment backed by tool-gateway.""" |
| `modal` | Modal cloud execution environment using the native Modal SDK directly. |
| `modal_utils` | Shared Hermes-side execution flow for Modal transports. |
| `singularity` | Singularity/Apptainer persistent container environment. |
| `ssh` | SSH remote execution environment with ControlMaster connection persistence.""" |
| `vercel_sandbox` | Vercel Sandbox execution environment. |

### C.2 — Agent-side guards and the verification subsystem


| Module | What it does |
|---|---|
| `tool_guardrails` | Pure tool-call loop guardrail primitives. |
| `tool_executor` | Tool-call execution — sequential and concurrent dispatch. |
| `__init__` | Project verification subsystem. |
| `environment` | Environment manifest for project verification. |
| `recipes` | Static run-recipe detection for project verification. |
| `runner` | Verification runner: execute a Recipe's phases and smoke-test the app. |
| `empty_response_guard` | Deterministic-empty detection and cost-aware retry budgets (NS-503). |
| `nous_rate_guard` | Cross-session rate limit guard for Nous Portal. |
| `repetition_guard` | Cheap content-sanity checks for the truncated-response continuation path. |
| `ssl_guard` | Preventive SSL CA certificate checks for Hermes Agent. |
| `tool_guardrails` | Pure tool-call loop guardrail primitives. |
| `outbound_webhooks` | Outbound webhook notifications. |
| `plugin_stream_hooks` | Asynchronous per-consumer plugin observers for streaming LLM output.""" |
| `shell_hooks` | Shell-script hooks bridge. |
| `verify_hooks` | Verification-loop helpers for the ``pre_verify`` round-end gate. |
| `plugin_stream_hooks` | Asynchronous per-consumer plugin observers for streaming LLM output.""" |

---

## Appendix D — Evaluation and judging planes


`idp/platform/eval/` — the estate's control loops.


| Module | What it does |
|---|---|
| `comparison_policy` | ComparisonPolicy: configuration for partial evaluation decisions. |
| `hook_wrapper` | Hook wrapper: failure isolation for all control-loop hooks. |
| `judge_drift` | Judge drift detection and calibration control loop. |
| `judge_drift_loop` | JudgeDrift control loop: continuous calibration monitoring. |
| `judge_worker` | Judge worker: transcript evaluation and kappa calibration. |
| `loops_bootstrap` | Bootstrap: register all control loops with the registry. |
| `pareval_layer` | PartialEvalDecisionLayer: sequential comparison with bootstrap CI. |
| `pareval_loop` | ParEval control loop: smart halt gate. |
| `pareval_policy` | ParEvalLayer comparison policy selection and defaults for coding tasks. |
| `payload_validator` | Payload validation: format, semantic, and category validation. |
| `protocol` | ControlLoop protocol: enterprise standard for eval loop integration.""" |
| `red_team_loop` | RedTeam control loop: payload generation and injection. |
| `red_team_payloads` | Red team payload pipeline: generation, curation, mutation, and lifecycle. |
| `span_retention` | Span storage retention manager: four-tier architecture. |
| `span_retention_loop` | SpanRetention control loop: four-tier storage lifecycle. |
| `test_control_loops` | Automated verification gates for control-loop wiring spec (W-01 through W-07). |

### D.2 — `hermes-agent/evals/` — three independent eval harnesses


| Harness | Files |
|---|---|
| `evals/browser_use/` | `orchestrate`, `orchestrate_cloud`, `report`, `single_run` |
| `evals/compaction/` | `build_html_report`, `codex_arm`, `fixtures`, `policies`, `reconstruct_lineage`, `replay_lineage`, `report`, `runner`, `test_region_scoping` |
| `evals/readtool/` | `fixtures`, `report`, `runner`, `tasks` |

### D.3 — `hermes-v2/otto/verify/` — the verifier suite


| Module | What it does |
|---|---|
| `bus` | Verdict bus: the one thing the prover and the orchestrator share. |
| `credentials` | Prover credentials: read-only by construction, per system. |
| `errors` | Exceptions for the Verification Plane. |
| `eval_hook` | False-success eval hook: known-bad work must never earn a PASS. |
| `identity` | Verifier identity: the only holder of verdict-signing key material. |
| `ledger` | Task ledger and completion gate: the only path to ``completed``. |
| `model` | Data model: claims, claim envelopes, and Ed25519-signed verdicts. |
| `reply_judge` | A verdict for a chat reply, from the verify lane, before it is rendered. |
| `store` | Verdict store: durable record of every verdict, fail closed when down. |
| `verifier` | Verifier core: checks a claimed-work envelope, signs a verdict. |

---

## Appendix E — MCP doors, one line each


`idp/mcp/plugins/` — datasette plugins, each registering one MCP tool surface.


| Plugin | Registered tools |
|---|---|
| `estate_executor` | `admit`, `admit_mutation`, `execute_command`, `propose_mutation`, `propose_patch`, `read_job`, `seal`, `seal_mutation`, `simulate_command`, `simulate_patch`, `verify`, `verify_inverse`, `verify_mutation` |
| `estate_guards` | `get_estate_guards` |
| `estate_holmes` | — |
| `estate_inventory` | — |
| `estate_memory` | — |
| `estate_sessions` | — |
| `estate_simulate` | `execute_change`, `simulate_change` |
| `estate_state` | — |
| `estate_twin` | — |
| `workload_logs` | — |
| `workload_state` | — |

---

## Appendix F — Lanes, in full


### `default`


`goal_required=True` · `readonly_run_limit=16` · `proactive=False` · `close_condition=False` · `gate=report`


What the lane tells the agent not to do (each line names a failure on this estate):

- Do not trust prose in a doc or a memory over a command. The CLAUDE.md you were served may be an orphaned worktree copy, 361 lines adrift from main.
- Do not write a guard, test or script before one command looks for its owner: git log --all -1 -- <path>; git show origin/main:<f>; rg -l '<symbol>'.
- Do not report a number you did not measure this turn. A tilde is where a command should have run: I said ~25 minutes, measured it was 5.7.
- Do not grade a proxy. Four guards in one day graded comments, English words, a line prefix and a file extension instead of the thing itself.
- Do not `git add -A` in this estate. store/ and storage/ are TRACKED runtime state that pytest writes to.
- Do not leave an allow-list with a silent miss case. A bare `return` on the unknown branch dropped 10 criticals in 18 hours and no test failed.


### `build`


`goal_required=True` · `readonly_run_limit=12` · `proactive=False` · `close_condition=True` · `gate=—`


What the lane tells the agent not to do (each line names a failure on this estate):

- Do not commit from a tree whose .git is dead: `git ls-files` prints nothing AND exits 0, so every guard grades an empty repo and blames anything but git.
- Do not edit a failing test green until you have read its docstring. 2026-08-21: two of four pinned the correct behaviour and my change was the wrong one.
- Do not push before `git fetch origin main && git merge origin/main --no-edit`. A stale branch fails as somebody else's bug: 4 of 5 red lines were not mine.
- Do not read an exit status through a pipe. `cmd | tail` reports TAIL's status, so a failed build reads as exit 0. Capture the real one first.
- Do not make a worktree with `git worktree add` alone. Run scripts/setup_worktree.sh -- .venv, agent.pem and node_modules each fail by accusing something else.
- Do not say done from prose. Run the project's state probe and quote its green line: a roadmap read 'live' while the process ran 32-hour-old code.


### `research`


`goal_required=True` · `readonly_run_limit=20` · `proactive=False` · `close_condition=True` · `gate=—`


What the lane tells the agent not to do (each line names a failure on this estate):

- Do not call one measurement proof. Two angles that can fail differently, or write 'single angle' and name the second one you would run.
- Do not calibrate with an instrument that censors its own counterfactual. A guard blocking at 3 can never log a run of 4, so its log 'proves' 4 is inert.
- Do not calibrate on a percentile. The unit is firing rate per session against the bands: >=3 is noise, 0.6-3 usable, <0.15 inert.
- Do not report a capped list without saying how many it dropped. Silent truncation reads as completeness.
- Do not grind for a number this box cannot give. At load average 282 every wall-clock reading is fiction; say unobtainable, with the reason.
- Do not import your own copy of a classifier when calibrating a guard. Import the guard's, or the calibration drifts from the thing it calibrates.


### `incident`


`goal_required=True` · `readonly_run_limit=18` · `proactive=False` · `close_condition=True` · `gate=—`


What the lane tells the agent not to do (each line names a failure on this estate):

- Do not write a test, a guard or a memory while the objective's number has not moved. That is LAW 6 work and it fires after the fire is out.
- Do not read a status letter as a cause. F is FAILED, not QUEUED. Open the failing job log before you touch a single machine.
- Do not fill a wait with prevention. Say what you are waiting on and when you will look again, then stop. The CI run does not finish sooner.
- Do not report what was BUILT. Report what was RESTORED, with the number, on line 1 of the reply.
- Do not disguise a refused command to get it past the filter. A denial you have to dress up is a denial to respect and say out loud.
- Do not trust prose over a command: re-measure any claim in a doc that decides what you do next, including this one.


### `platform`


`goal_required=True` · `readonly_run_limit=16` · `proactive=True` · `close_condition=True` · `gate=—`


What the lane tells the agent not to do (each line names a failure on this estate):

- Do not go deep without the platform number first. Depth feels like rigour: 19.6 hours moat-blind while I measured signing keys perfectly.
- Do not leave a discovery as information. A trap you found and described is a trap every peer still walks into; fix it at the SOURCE.
- Do not send a peer a subject already on the board. `tail -20 ~/.claude/ESTATE_BOARD.jsonl` first -- the fence refuses the repeat, not the first raise.
- Do not add a recurring cost without saying one-off or operational and pricing it IN WRITING before the run. Destroy what you rented the hour it stops earning.
- Do not decide alone what you cannot undo alone. Broadcast the plan, the blast radius, and the one thing that would make you stop.
- Do not trust prose over a command. The CLAUDE.md you were served may be an orphaned copy 361 lines adrift from main.


---

## Appendix G — Roles


`claude-estate/agents/roles/` — one person per hat, with autonomous decision authority.


| Role | Tools granted |
|---|---|
| `pm-agent` | Read, Write, Edit, Grep, Glob, Bash |
| `qa-agent` | Read, Grep, Glob, Bash |
| `receipt-auditor` | Read, Grep, Glob, Bash |
| `ceo` | Read, Grep, Glob, Bash, WebSearch, WebFetch |
| `engineering` | Read, Edit, Write, Grep, Glob, Bash, WebSearch, WebFetch |
| `finance` | Read, Edit, Write, Grep, Glob, Bash, WebSearch, WebFetch |
| `information-architect` | Read, Edit, Write, Grep, Glob, Bash |
| `inventor` | Read, Grep, Glob, Bash, WebSearch, WebFetch |
| `legal` | Read, Edit, Write, Grep, Glob, Bash, WebSearch, WebFetch |
| `marketing` | Read, Edit, Write, Grep, Glob, Bash, WebSearch, WebFetch |
| `operations` | Read, Edit, Write, Grep, Glob, Bash, WebSearch, WebFetch |
| `sales` | Read, Edit, Write, Grep, Glob, Bash, WebSearch, WebFetch |
| `ux` | Read, Edit, Write, Grep, Glob, Bash, WebSearch, WebFetch |

---

## Appendix H — FleetView backend modules


`idp/backstage/plugins/fleetview-backend/src/` — the portal's agent surface.


| Module | What it does |
|---|---|
| `blast` | FleetView item #7: blast radius, on the board instead of a terminal. |
| `claude_code_adapter` | FleetView CP6: Claude Code ledger tail — bridges the prompt-ledger to the NATS event bus. |
| `config_guard` | Fail fast: refuse to start half-configured, and say what is missing in one sentence. |
| `device_access` | Device access state: what THIS device's read-only cluster identity is, if anything. |
| `evals` | FleetView item #9: a receipt check over production traces -- repeatable, not a model judging |
| `executor_link` | The in-cluster half of the mutations relay: one laptop, long-polling, over the tailnet. |
| `graph` | FleetView estate graph snapshot: every node and edge in `catalog/estate.db`, for a spatial |
| `handoff` | The portal must never receive or emit a secret. This module is where that is enforced. |
| `history` | History and query: the fleet over time, and a way to ask about it. |
| `ledger_tail` | FleetView CP7: last N rows of a session's prompt-ledger, for the log pane. |
| `mutations` | FleetView door onto the typed multi-domain mutation ledger (docs/tickets/2026-09-15-typed- |
| `nats_adapter` | FleetView CP6: NATS adapter — publish agent events and subscribe to the live stream. |
| `notes` | FleetView notes: leave a note for a session, any runtime, read later. |
| `redact` | Redact likely secrets from free text before it reaches the board. |
| `routes` | FleetView backend plugin: the two routes CP1's done-command names. |
| `serve` | FleetView launcher. |
| `sessions` | FleetView CP1: the session contract, served. |
| `signals` | FleetView item #6: nudge a stale session. |
| `spend` | FleetView spend reader (item #4): per-session $ spend for sovereign sessions. |
| `trace` | FleetView CP7: fetch a session's Langfuse trace spans as React Flow nodes + edges. |
| `voice` | Voice: ask the fleet, in words, and get an answer worth speaking. |

---

## Appendix I — The external verifier and the evidence layer


### I.1 `consultd` — a second mind, on tap, for every agent


`claude-estate/scripts/consultd.py` + `consult-verify.sh` (which execs `hermes-v2/bin/verify-consult`).


| Backend | Address | Notes |
|---|---|---|
| `kimi-bridge` | 127.0.0.1:8766 | browser bridge to the kimi.ai web app |
| `deepseek` | 127.0.0.1:8767 | browser bridge to chat.deepseek.com |
| `ollama` | 127.0.0.1:11434 | local, offline, weakest, always there |
| `none` | — | always ready, always 503, so the caller's fallback stays honest |

Cascade order is tried in sequence; the first ready backend answers, and the reply names which one did.

- `consult-verify.sh` — One command, from anywhere, for the consult service.
- `consultd.py` — A second mind on tap, over HTTP, for every agent on this machine.
- `deepseek_bridge_backend.py` — consultd.py backend for the DeepSeek browser bridge.
- `kimi_bridge.py` — Kimi browser bridge. Drives a signed-in www.kimi.com session over Playwright.
- `kimi_bridge_backend.py` — consultd.py backend that talks to the Kimi browser bridge over loopback.
- `setup-kimi-bridge.sh` — Kimi browser bridge, one command.
- `test_bridge_edges.py` — Exhaustive edge case harness for the bridge HTTP surface and job queue.
- `test_bridge_live.py` — Live edge cases: the real browsers, the real consult cascade, real money.
- `test_kimi_bridge_boot.py` — Incident test: a failed boot must not kill the bridge's worker thread.
- `test_kimi_bridge_reap.py` — Incident test: `launchctl kickstart -k` SIGKILLs the daemon, the playwright

### I.2 Aevum — the evidence layer (ADR 0028)


Replaced POPDD. POPDD signed with HMAC (symmetric): a record two parties share, not evidence a third party can check. Aevum signs with **Ed25519 AND ML-DSA-65 (post-quantum)**, wraps entries in **COSE_Sign1** with an **RFC 3161** trusted timestamp, and ships `aevum-verify` sharing no code with the runtime.


| Artifact | Path |
|---|---|
| `platform/observability/aevum.yaml` | present |
| `platform/observability/aevum.Dockerfile` | present |
| `platform/image-automation/aevum.yaml` | present |
| `docs/gates/aevum-evidence.md` | present |
| `docs/decisions/0028-aevum-replaces-popdd-as-the-evidence-layer.md` | present |
| `bin/idp-evidence-gate` | present |
| `bin/idp-local-evidence-gate` | present |
| `tests/fixtures/aevum-evidence/bad/chain.json` | present |
| `tests/fixtures/aevum-evidence/good/chain.json` | present |

Measured properties: hash-chained (`prior_hash`, `payload_hash`); tamper detected (`verify_sigchain()` returned `False` after in-place mutation); frozen dataclass (`FrozenInstanceError` on assignment); gap reporting (`record_capture_gap`); replay (`replay(audit_id=...)`).


**Fail-closed:** Aevum's default store is in-memory and `verify_sigchain()` answers **True about a chain with no events**, so `idp-evidence-gate` treats an empty ledger as FAIL, not a clean bill.


---

## Appendix J — The remaining harnesses


### J.1 `hermes-v2` — The Architect (Otto)


| Module | What it does |
|---|---|
| `otto/verify/bus.py` | Verdict bus: the one thing the prover and the orchestrator share. |
| `otto/verify/credentials.py` | Prover credentials: read-only by construction, per system. |
| `otto/verify/errors.py` | Exceptions for the Verification Plane. |
| `otto/verify/eval_hook.py` | False-success eval hook: known-bad work must never earn a PASS. |
| `otto/verify/identity.py` | Verifier identity: the only holder of verdict-signing key material. |
| `otto/verify/ledger.py` | Task ledger and completion gate: the only path to ``completed``. |
| `otto/verify/model.py` | Data model: claims, claim envelopes, and Ed25519-signed verdicts. |
| `otto/verify/reply_judge.py` | A verdict for a chat reply, from the verify lane, before it is rendered. |
| `otto/verify/store.py` | Verdict store: durable record of every verdict, fail closed when down. |
| `otto/verify/verifier.py` | Verifier core: checks a claimed-work envelope, signs a verdict. |
| `otto/spine/bus.py` | The JetStream bus (spec §4, P4 of the constitution). Thin wrapper over |
| `otto/spine/cli.py` | `otto` CLI — the two commands spec §17 Phase 0 asks for: `otto replay |
| `otto/spine/envelope.py` | The task envelope (spec §3) and the two structural invariants that ride |
| `otto/spine/eval_runner.py` | `otto eval run --suite core` (spec §11, §17 Phase 0: "eval corpus v1 + |
| `otto/spine/inventory.py` | The signed capability inventory (spec §15, §17 Phase 0: "capability |
| `otto/spine/lifecycle.py` | Task-lifecycle publish helpers: the surface a later orchestrator |
| `otto/spine/outbox.py` | The transactional outbox, Python translation of decision D3 of ADR-0012 |
| `otto/spine/replay.py` | `otto replay <task_id>` (spec §4: "Replay is a feature ... this is the |
| `otto/spine/subjects.py` | Subject taxonomy, spec §4. Every subject this build ever publishes on |

### J.2 `hermes-config` — configuration, simulators, verification


| Script | What it does |
|---|---|
| `agent_simulator.py` | agent_simulator.py — Simulated agent traffic (Round H2). |
| `alarm_gate.py` | alarm_gate — decide whether an alarm state is worth telling the founder AGAIN. |
| `alert-resolver.py` | Alert Resolution System — PROBE-VERIFIED resolution (Fire 4-LF fix). |
| `alert_router.py` | alert_router.py — Multi-channel alert routing. Telegram, email, Slack, webhook, PagerDuty.""" |
| `api_server.py` | FastAPI production server — replaces ThreadingHTTPServer with JWT-secured API. |
| `append-regression-trend.py` | append-regression-trend.py — Appends coverage % + timestamp to regression-trend.jsonl. |
| `audit-trail.py` | Audit Trail Recorder. |
| `auto_close_identity.py` | Tier 6-7: Auto-close low-risk gaps + Agent identity & versioning. |
| `auto_fixer.py` | auto_fixer.py — Autonomous fix engine with verification and learning. |
| `bayesian_ab.py` | Bayesian A/B testing engine — replaces Welch's t-test for policy attribution. |
| `build_rsi_evalset.py` | Build the RSI evalset from RECORDED task outcomes instead of authored taste. |
| `capability_audit.py` | Capability audit — does the estate actually PRODUCE anything? |
| `ceo_mode.py` | ceo_mode — phone defaults to cards for ops; free chat still reaches the agent. |
| `check-daemon-staleness.py` | Is each long-lived daemon running the code that is on disk? |
| `check_fly_apps.py` | Grade the estate's Fly apps against ~/.hermes/config/fly_apps_expected.tsv. |
| `ci-watchdog.py` | CI watchdog — what is actually blocking the estate's pull requests. |
| `ci_watchdog_core.py` | The CI watchdog's logic, separated from its I/O so it can be tested. |
| `circuit_breaker.py` | Circuit breaker for self-healing operations. Stops infinite retry loops. |
| `claude_handback_gate.py` | claude_handback_gate — stop Otto from self-fixing an issue Claude already owns. |
| `claude_usage_limit.py` | A shared, cross-process record of when the Claude subscription's usage wall lifts. |
| `complaint_ledger.py` | Persist the founder-complaint scan so it stops evaporating between sessions. |
| `conflict-resolver.py` | F3 — Conflict Resolution Engine for Otto. |
| `constitutional_validator.py` | Constitutional invariants for Hermes/Otto self-improvement. |
| `coordinator.py` | coordinator.py — the persistent autonomous-estate coordinator (Phases 2-5). |
| `corpus_hygiene.py` | corpus_hygiene.py — collapse health-bridge spam into unique failure classes. |
| `cost_policy_mgmt.py` | Cost attribution + Policy compression for Hermes self-improvement. |
| `cron-job-health-probe.py` | cron-job-health-probe — read-only probe for CRON_SILENT / CRON_ERROR classes. |
| `cross-project-bridge.py` | Cross-Project Pattern Bridge. |
| `cross_project.py` | cross_project.py — Estate-wide health, correlation, and dependency map. Rounds K1-K3.""" |
| `daily-digest.py` | daily-digest.py — 9am morning briefing. |
| `daily_reflection.py` | Otto Daily Self-Reflection. Runs at 6pm daily via cron. |
| `db_health.py` | db_health.py — Database vacuum, TTL cleanup, backup, integrity check.""" |
| `delivery.py` | Production delivery system — replaces fire-and-forget with guaranteed delivery. |
| `delivery_canary.py` | delivery_canary — proves that an estate alert actually REACHES the founder. |
| `diagnostics.py` | diagnostics.py — Active diagnosis engine (Round E1-E4). |
| `dispatch-guard.py` | dispatch-guard.py — Pre-dispatch enforcement for delegate_task. |
| `dispatch_gate.py` | Dispatch gate — structural guard against asking when I should be doing. |
| `dropped-ball-tracker.py` | dropped-ball-tracker — telemetry probe for Otto's own failures (Ball 19 addendum). |
| `estate-audit.py` | estate-audit.py — the FULL estate audit, reproducible on command (Telegram: "Otto audit"). |
| `estate-auto-remediation.py` | Estate Auto-Remediation — takes the optimization report and actually |
| `estate-diff.py` | Estate diff — show ONLY what changed since last check. |
| `estate-drift-detector.py` | Estate Drift Detector — compares today's inventory to last snapshot. |
| `estate-inventory.py` | Estate Inventory — complete map of every component. |
| `estate-optimization-scanner.py` | Estate Optimization Scanner — reads all analysis outputs from the |
| `estate_alert.py` | estate_alert — gateway-INDEPENDENT operator alerting. |
| `estate_config.py` | estate_config.py — Universal estate model loader. |
| `estate_migrator.py` | estate_migrator.py — Migrate hardcoded projects to estate.yaml.""" |
| `estate_watchdog.py` | estate_watchdog.py — independent supervisor so Telegram is never silently down. |
| `eval-confidence.py` | F2 — Eval confidence scoring + divergence detection for Otto. |
| `evidence_verify.py` | import os |
| `feature_registry.py` | feature_registry.py — Feature registry (Round G1-G4). |
| `flight.py` | flight.py — the MISSION ENGINE (autopilot) for the autonomous estate. |
| `gap-finding.py` | Gap-Finding Engine (#3 of the Continuous Learning Build). |
| `gateway_crashloop_watch.py` | gateway_crashloop_watch — detect a crash-looping gateway and alert the operator. |
| `gateway_preflight.py` | gateway_preflight — validate edit-prone gateway modules BEFORE going live. |
| `health_endpoint.py` | health_endpoint.py — Lightweight HTTP health check for uptime monitoring. |
| `health_monitor.py` | Health monitor — runs every 5 minutes via cron. |
| `hermes_claims.py` | Dropped-ball watchdog — catches self-certification at the substrate level. |
| `hermes_domains.py` | One capability vocabulary, shared by the half that finds gaps and the half that records outcomes. |
| `hermes_fingerprint.py` | Canonical alert/event fingerprinting — single source of truth. |
| `hermes_gateway.py` | hermes_gateway.gateway_liveness — load-immune gateway liveness. |
| `hermes_lease.py` | One Hermes leader, decided by a lease both machines can see. |
| `hermes_queue.py` | Hermes relay queue — Otto-side ingestion of cron/probe/watchdog events. |
| `hermes_selfcheck.py` | One command that answers "is Hermes actually healthy", by invariant rather than by liveness. |
| `hermes_subprocess.py` | hermes_subprocess.run_bounded — the ONE safe way to run a child with a deadline. |
| `holdout_eval.py` | Holdout evaluation + causal attribution for Hermes self-improvement policies. |
| `idle-consolidation.py` | Idle Consolidation Engine (#1 of the Continuous Learning Build). |
| `idle-curiosity.py` | Idle Curiosity Pass — runs every 2h during idle time, does genuine learning work. |
| `idle_engine.py` | idle_engine.py — Continuous background learning for Otto. |
| `improver-switcher.py` | improver-switcher.py — Improver versioning and swap tracking. |
| `incident_manager.py` | incident_manager.py — Full incident lifecycle: detect → diagnose → fix → verify → resolve → postmortem."" |
| `integration.py` | integration.py — Wires all Tier 0-7 modules into the operational system. |
| `known_classes.py` | known_classes — the proactive dispatcher's decision table. |
| `latch_expiry.py` | Latch expiry — no automatic trip may require manual recovery forever. |
| `launchd_receipt.py` | launchd_receipt.py — sign a capability receipt around any launchd job. |
| `launchd_selfheal.py` | Re-load estate launchd agents that fell out of launchd. READ-ONLY without --apply. |
| `learning_switch.py` | learning_switch — ONE honest kill switch for all self-improvement loops. |
| `memory-hygiene.py` | memory-hygiene — enforce a last_verified stamp on every memory entry. Item 6. |
| `memory_retrieval.py` | Memory retrieval — Phase 3: embedding-based retrieval layer. |
| `mentor-reflect.py` | mentor-reflect — Claude is Otto's permanent mentor (continuous, not session-bound). |
| `meta-improver.py` | meta-improver.py — Core meta-improvement loop for Otto. |
| `mini_app_server.py` | mini_app_server.py — Telegram Mini App backend + WebSocket real-time engine. |
| `morning_brief.py` | morning_brief.py — deterministic CEO brief (no LLM). |
| `near-miss-analyzer.py` | Near-Miss Analyzer: finds patterns that almost triggered but didn't. |
| `ops-monitor.py` | ops-monitor.py — Operational health monitor (Phase 2/3 recursive self-improvement). |
| `otto-correction-gate.py` | otto-correction-gate.py — structural enforcement for the most common dropped balls. |
| `otto-correction-scan.py` | Continuous-audit trigger — operationalizes the user's rule: |
| `otto-dispatch.py` | otto-dispatch — the proactive relay step (Ball 17 + proactive-substrate). |
| `otto-introspect.py` | otto-introspect.py — Introspection surface for Otto's operational state. |
| `otto-learn.py` | otto-learn — Policy management CLI for Otto's correction-learning loop. |
| `otto-why.py` | otto-why.py — Rationale reconstruction for Otto decisions. |
| `outbox.py` | Transactional outbox for coordinator escalations (spec §7 Phase 2, integrated |
| `outcome-accelerator.py` | Outcome Accelerator: logs every completed task as a mini-outcome record. |
| `outcome-evaluator.py` | outcome-evaluator.py — F2-aware outcome evaluator. |
| `outcome_tracker.py` | SQLite-backed OutcomeTracker — ACID-compliant replacement for JSONL appends. |
| `platform_bridge.py` | platform_bridge.py — Future-proofing layer: LLM abstraction + multi-estate + performance. |
| `policy-composer.py` | policy-composer.py — Slope maximisation via policy co-firing analysis. |
| `policy-enforcer.py` | policy-enforcer.py — Runtime pre-action gate. |
| `policy_enforcer.py` | — |
| `policy_firing_guard.py` | Regression guard for the policy enforcer wiring (F-NEW-INV-1). |
| `policy_firing_notifier.py` | Send policy firing events to Telegram — proves the loop is closed. |
| `post-claim-verifier.py` | Post-claim verifier — runs automatically after every significant claim. |
| `predictor.py` | predictor.py — Predictive intelligence (Round D1-D4). |
| `preflight.py` | Pre-flight check — run before EVERY gateway restart. |
| `progress.py` | progress.py — make self-improvement OBSERVABLE. |
| `proof-probe.py` | import sys |
| `prove_learning.py` | prove_learning.py — falsifiable proof of the operational-learning loop. |
| `prove_rsi.py` | prove_rsi.py — falsifiable, hermetic proof of the RSI improvement-gate. |
| `provider_chain_check.py` | Refuse a provider chain whose members cannot authenticate here. |
| `proving-ground-probe.py` | proving-ground-probe — READ-ONLY verdict for the proving-ground failure class. |
| `proving-ground.py` | proving-ground.py — self-integrity auditor (existence-aware: MISSING != PASS). |
| `quality_defense.py` | Tier 4-5: Distributional quality monitoring + Prompt injection defense. |
| `receipt_rotate.py` | Bound the growth of state/capability_receipts.jsonl without breaking its semantics. |
| `reflect-on-correction.py` | Post-correction reflection runner. |
| `reflection_digest.py` | Mid-day digest — runs at 1pm and 8:50am. |
| `reflection_pulse.py` | Lightweight reflection pulse — runs every 30 minutes. |
| `reliability_report.py` | reliability_report — the estate's single "is anything actually broken?" alarm. |
| `repo-health-check.py` | Multi-repo health check — PARALLEL, budgeted (Ball: 5c). |
| `repo-health-probe.py` | repo-health-probe — READ-ONLY verifier for the repo-health failure class. |
| `report_generator.py` | report_generator.py — Weekly/monthly reports and ROI dashboards.""" |
| `requeue_failed.py` | Recover the stranded `failed` tasks — bounded, deduped, dry-run by default. |
| `resilience.py` | resilience.py — Operational resilience (Round F1-F4). |
| `return-summary.py` | return-summary.py — "What happened while I was away?" probe. |
| `route.py` | route(role, prompt) — per-role provider rotation for the autonomous estate. |
| `rsi-orchestrator.py` | rsi-orchestrator.py — Recursive Self-Improvement (RSI) loop for the Hermes/Otto agent. |
| `rsi_loop_guard.py` | Refuse to let the self-improvement loop run in silence again. |
| `rsi_outcome_ledger.py` | Outcome attribution for the self-improvement loop — which lever can move the metric? |
| `sandbox.py` | Disposable git-worktree sandboxes + strike matrix (spec §7 Phase 3 primitives). |
| `score_driver.py` | score_driver.py — Score-driven improvement (Round H1, H3, H4). |
| `secrets_manager.py` | secrets_manager.py — Encrypted secrets store using age encryption. |
| `self-audit.py` | self-audit.py — Weekly self-audit: "What could I have prevented?" |
| `self-detect.py` | self-detect.py — Self-detected failure handler (B). |
| `self-healer.py` | Self-Healer: reads watchdog alerts and auto-fixes what it CAN — honestly. |
| `self-regression.py` | Self-Regression Engine (#2 of the Continuous Learning Build). |
| `self_improve_runner.py` | Self-improvement loop closer — in-process, no subprocess shelling. |
| `set-cockpit-menu.py` | set-cockpit-menu.py — install the operator menu, chat-scoped so it wins. |
| `setup-embedding-model.py` | Download the ONNX embedding model for the F1 retrieval layer.""" |
| `skill-hygiene.py` | skill-hygiene — flag orphan skills (created, never wired). Item 6. |
| `status_engine.py` | Status engine — background cache for all project status data. |
| `telegram_ledger.py` | telegram_ledger — a record of what this estate actually sent to the operator. |
| `telegram_noise.py` | telegram_noise — what actually reached the operator's channel, and from where. |
| `telegram_ux_probe.py` | Daily Telegram UX probe — replace the goal-ping cron with a real watchdog. |
| `test_async_executor.py` | Proof for Phase C: executors run OFF the tick thread (non-blocking) and concurrency |
| `test_claude_usage_limit.py` | Proofs for the shared usage-wall marker. No network, no CLI, no wall clock. |
| `test_coordinator.py` | Proof for coordinator.py — Phases 2-5 of the heavenly-estate design. |
| `test_cost.py` | Hermetic proof of the cost + seamlessness controls in coordinator.py: |
| `test_cutover.py` | Phase 3 CUTOVER proof: worktree isolation + merge-back wired into agentic_execute. |
| `test_delivery_canary.py` | Tests for the delivery canary. |
| `test_escalation_outbox.py` | Integration test: the LIVE coordinator.escalate() writes the transactional outbox and |
| `test_flight.py` | Hermetic proof of the Mission Engine (flight.py): a mission is plotted, flown |
| `test_mentor_reflect.py` | Acceptance probe for the mentor-reflect CRON_ERROR fix. |
| `test_outbox.py` | §7 Phase 2 sabotage test for outbox.py, run against a tasks-table schema that |
| `test_progress_stream.py` | Proof for Phase A1: progress_notify streams as ONE editing Telegram message. |
| `test_reaper.py` | §7 Phase 1 sabotage test for coordinator.run_bounded(). Run: python3 test_reaper.py |
| `test_reliability_alarm.py` | Tests for the reliability alarm: alarm_gate, missed-run intake, WARMING. |
| `test_resolution_disease.py` | Deterministic proof for the resolution-disease fix (war-room root cause). |
| `test_retry_storm_livelock.py` | Proofs for the retry-storm livelock of 2026-08-08. |
| `test_route.py` | Proof for route.py — Phase 1 of the heavenly-estate design. |
| `test_rsi_authority_window.py` | Proofs for the RSI authority recency window. |
| `test_rsi_evidence_ruler.py` | Proofs for attempt-level attribution and the outcome-grounded ruler. |
| `test_rsi_outcome_ledger.py` | Proofs for rsi_outcome_ledger — the gate that stops RSI tuning a lever it cannot move. |
| `test_rsi_prompt_tuning.py` | Proof that the RSI prompt tuner's retry attempts carry their own task, and that it |
| `test_sandbox.py` | §7 Phase 3 sabotage test for sandbox.py, against a real throwaway git repo. |
| `test_watchdog_liveness.py` | Proof that the watchdog can tell a BUSY coordinator from a DEAD one. |
| `test_watchdog_suspend_clamp.py` | Acceptance test — CRON_SILENT_STRETCH must not fire on host-suspend time. |
| `test_watchdog_wake_grace.py` | Regression proof for the 2026-08-11→13 false CRON_SILENT_STRETCH page. |
| `trend-analyzer.py` | Cross-session Trend Analyzer. |
| `verify_pipeline.py` | End-to-end verification of the complete self-improvement pipeline. |
| `verify_system.py` | System Verification Suite — zero human intervention required. |
| `warroom.py` | warroom.py — convene an Execution-Grounded Multi-Agent War Room. |
| `warroom_eval.py` | warroom_eval.py — Execution-Grounded War Room CI Duel Harness (NET-SAFE). |
| `watchdog-cron.py` | watchdog-cron.py — cron-boundary wrapper for watchdog.py (exit-contract fix). |
| `watchdog-state-probe.py` | watchdog-state-probe — read-only health verdict from the watchdog's OWN recorded state. |
| `watchdog.py` | Continuous Health Watchdog — GRADED on invariants (exit-code honest). |
| `weekly-progress-digest.py` | weekly-progress-digest — the visible-evidence dashboard the user asked for. |
| `alert-resolver-probe.sh` | alert-resolver-probe — receipt for the Fire 4-LF false-clear fix. |
| `auto-guard.sh` | auto-guard.sh — File watcher that auto-runs preflight + safe restart on code changes. |
| `auto-push.sh` | no-agent config auto-push — hourly sync of the hermes config repo to its private remote. |
| `brain-liveness.sh` | Ask every configured model provider for a real token, hourly, and tell the founder DIRECTLY |
| `check_single_environment.sh` | Hermes runs in ONE place. This check fails when it is running in two. |
| `ci-watchdog.sh` | set -u |
| `closed-loop-proof.sh` | closed-loop-proof — Item 9. Proves the WHOLE relay loop end-to-end in one isolated |
| `cockpit-daemon.sh` | Cockpit daemon — kept alive by launchd (ai.hermes.cockpit) |
| `coordinator-daemon.sh` | Launchd wrapper for the autonomous coordinator. launchd gives a bare environment: |
| `daemon-stability-probe.sh` | daemon-stability-probe — fires when signal_engine.daemon restarts 2+ times in 1h. |
| `dashboard-up.sh` | Bring the Hermes web dashboard up and make it reachable from the phone. |
| `dropped-ball-probe.sh` | dropped-ball-probe — receipt for the dropped-ball watchdog (hermes_claims.py). |
| `estate-full-run.sh` | Estate Full Report — runs the entire estate pipeline: |
| `git-pre-commit-hook.sh` | pre-commit guard for the Hermes estate. Two jobs: |
| `goal-of-the-moment.sh` | goal-of-the-moment.sh |
| `handoff-gate.sh` | handoff-gate.sh — Claude's pre-handoff integrity gate. |
| `hourly_pulse.sh` | Otto Hourly Improvement Pulse |
| `idle-learning-probe.sh` | idle-learning-probe — fires (exit 2) when idle-continuous-learning has exited |
| `idle-learning-run.sh` | # Idle-Time Self-Improvement Pipeline (resilient). |
| `improvement-probe.sh` | Self-improvement probe: finds common gaps and files structured failure entries |
| `install_keepawake.sh` | install_keepawake.sh — durable Mac-local always-on assertion for the estate host. |
| `launch-report.sh` | Launch status report — aggregated view for all projects. |
| `launch_dashboard.sh` | launch_dashboard.sh — Otto Dashboard with Cloudflare tunnel |
| `lease-guard.sh` | The laptop side of the leader lease, run on a timer by ai.hermes.lease-guard. |
| `memory-capacity-probe.sh` | memory-capacity-probe — substrate prevention for the "memory tool fails to add" wall. |
| `methodology-probe.sh` | methodology-probe.sh — Watches for POPDD/PDD compliance drift. |
| `ngrok-daemon.sh` | ngrok daemon — kept alive by launchd (ai.hermes.ngrok) |
| `open-loop-aging-probe.sh` | open-loop-aging-probe — follow-through for the mentor lesson of 2026-08-18 |
| `otto-correction-scan-probe.sh` | otto-correction-scan-probe — receipt for the continuous-audit trigger. |
| `otto-daemon.sh` | Otto daemon — kept alive by launchd (ai.hermes.otto-server) |
| `otto-daily-digest.sh` | 9am briefing: yesterday's prospector stats, cron health, engine status, top |
| `otto-db-cleanup.sh` | Daily DB TTL cleanup (30-day-old sessions) + gzip backup of state.db and |
| `otto-dispatch-probe.sh` | otto-dispatch-probe — receipt for the PROACTIVE dispatcher (registry + auto-claim + dedup). |
| `otto-dispatch.sh` | otto-dispatch.sh — cron wrapper for the Otto relay step (Ball 17). |
| `popdd-init.sh` | popdd-init.sh — Initialize/append a POPDD session receipt to today's chain. |
| `post-task-hook.sh` | post-task-hook.sh — Called after every Hermes task completes. |
| `progress-snapshot.sh` | progress-snapshot.sh — decoupled autonomy-trend snapshot (cron-driven). |
| `prospector-run.sh` | prospector-run.sh — hourly guard/liveness probe for prospector generation (Ball: 5b). |
| `proving-ground-probe.sh` | proving-ground-probe — receipt for the existence-aware audit (Ball 19). |
| `publish-lux-stack.sh` | publish-lux-stack.sh — Automated publish of LUX/POPDD packages |
| `pytest-orphan-cleanup.sh` | pytest-orphan-cleanup.sh — kills pytest processes whose PPID is 1 |
| `queue-curate.sh` | queue-curate — Otto's curation pass over the relay queue (FIRE 0 consumer). |
| `queue-probe.sh` | queue-probe — FIRE 0 receipt. |
| `reliability-watchdog.sh` | Reliability watchdog — the job that turns silence into a failure. |
| `rsi-autorun.sh` | rsi-autorun.sh — fenced, autonomous RSI self-improvement tick (cron-driven). |
| `runaway-reaper.sh` | # runaway-reaper.sh — reap long-lived CPU hogs that starve the host. |
| `safe-restart.sh` | safe-restart.sh — Pre-flight check → restart → post-flight verify |
| `self-improve-hourly.sh` | Hourly self-improvement cycle: gap-finding → auto-close, self-regression, |
| `sign-interpreters.sh` | sign-interpreters.sh — ad-hoc codesign the Python interpreters the estate runs, so macOS stops |
| `signal-engine-daemon-watchdog.sh` | signal-engine-daemon-watchdog — a PROBE, not a launcher. Silent when healthy. |
| `signal-engine-watchdog-probe.sh` | signal-engine-watchdog-probe — FIRE 1 loop-closer. |
| `strategist-audit-wrapper.sh` | strategist-audit-wrapper.sh — daily strategist audit wrapper |
| `telegram-ux-probe.sh` | telegram-ux-probe.sh — shell wrapper around telegram_ux_probe.py. |
| `test_auto_push_net_transient.sh` | End-to-end proof for the transient-network classification added to auto-push.sh |
| `test_auto_push_secret_guard.sh` | Regression test for auto-push.sh's credential backstop. |
| `test_auto_push_status_timeout.sh` | Regression test for the `git status` timeout path in auto-push.sh. |
| `test_auto_push_tmp_race.sh` | Repro + regression test for the 2026-08-14 21:01 auto-push failure: |
| `test_signal_engine_watchdog.sh` | test_signal_engine_watchdog.sh — executable proof for signal-engine-daemon-watchdog.sh |
| `test_verify_estate_alerts.sh` | Tests the ALERTS section of verify_estate.sh — the pull-side proof that escalation |
| `test_verify_estate_installed.sh` | Tests the INSTALLED section of verify_estate.sh. |
| `test_verify_estate_launchd.sh` | Tests the LAUNCHD section of verify_estate.sh. |
| `test_verify_estate_single_environment.sh` | Proves check_single_environment.sh can actually fail. A guard nobody has seen fail is a |
| `uncommitted-watch.sh` | uncommitted-watch.sh — silent watchdog for uncommitted work. |
| `verify_estate.sh` | verify_estate.sh — THE single executable source of truth for estate operational state. |
| `watchdog-probe.sh` | watchdog-probe — receipt for exit-code grading (hidden-restart-loop fix). |
| `weekly-lux-verify.sh` | weekly-lux-verify.sh — Weekly `lux verify` across all projects with specs. |

### J.3 `prospector` — the parallel estate and its 76 operational scripts


| Script | What it does |
|---|---|
| `agent_estate_sync.py` | Mirror the agent estate -- ~/.claude -- into this repo, and fail when the two drift. |
| `backfill_ladder_prices.py` | C1 — move the live catalogue off the flat £49 onto the L1 segment ladder. |
| `backfill_price_anchors.py` | Backfill cited price anchors onto PASS dossiers generated before the check existed. |
| `backfill_tiers.py` | Fill `ambition_tier` on legacy dossiers, so the L1 ladder can price them at all. |
| `backup_agent_estate.py` | Pack the agent estate — ~/.claude — into one archive, without shipping credentials with it. |
| `backup_store.py` | Back up the two irreplaceable things in store/ to R2, and prove the copy is readable. |
| `blocker_probe.py` | What is actually blocking each open programme item — as a measurement, not prose. |
| `branch_backlog.py` | Which branches carry work that has not landed, and which are safe to delete? Read-only. |
| `build_docs_bundle.py` | Build ONE self-contained HTML file containing every document in docs/. |
| `checkout_currency.py` | Keep the shared developer checkout on origin/main, so no session is briefed from stale rules. |
| `ci_capacity.py` | Check that CI's declared capacity contract still matches the workflows and the runners. |
| `ci_fleet_keeper.py` | Start stopped CI runner machines back up, with no agent involved. |
| `ci_fleet_probe.py` | Can CI actually run? Grade every self-hosted runner fleet against its repository. |
| `ci_local.py` | Run a CI job's shell steps locally, in order, with the same environment. |
| `ci_runner_tools.py` | The self-hosted runner image carries the tools our workflows actually run. |
| `claudeignore_sync.py` | Compile .claudeignore into the Read() deny rules Claude Code actually enforces. |
| `deploy_status.py` | When did each deployable last ship, and is anything stuck on the way out? |
| `dns_zone.py` | DNS is the one thing with no substitute. This keeps a committed copy of it and diffs it daily. |
| `doc_lint.py` | Fail a doc that points at something which is not there any more. |
| `dual_write_parity.py` | Prove the Postgres shadow holds exactly what SQLite holds. |
| `engine_failover.py` | Where is the engine, is it alive, and how do we move it - one command for all three. |
| `estate_census.py` | What is in this repo, what refers to what, and what nothing refers to at all. |
| `estate_inventory.py` | One inventory of every resource this business depends on. |
| `estate_map.py` | Print the estate as it is right now: every part, where it runs, and whether it answered. |
| `founder_tasks.py` | The founder's task list, so it survives a session ending. |
| `gen_budget_guard.py` | Commit gate: projected GENERATION time must fit its share of the tick deadline. |
| `graphify_query_hook.py` | UserPromptSubmit hook — inject graph EVIDENCE, not instructions (spec R6, G-USE/S2). |
| `graphify_session_hook.py` | SessionStart hook — the "never stale" trigger (spec R5, R10). |
| `graphify_sweep.py` | Graphify estate scoreboard and refresher. |
| `green_guard_cause.py` | Was this commit the cause of the red main, or did it inherit one? |
| `guard_dead_branch_push.py` | Refuse a push that RECREATES a branch whose pull request is already finished. |
| `guard_main_push.py` | Refuse a push that lands directly on main. |
| `guard_protected_deletions.py` | Guard against SILENT deletion of protected files. |
| `handoff.py` | Write a session handoff that another session cannot overwrite. |
| `incident.py` | The incident loop: record, sweep, guard, grade. The process is docs/INCIDENT_PROCESS.md. |
| `launchd_plists.py` | launchd_plists.py — track the estate's launchd job definitions, and detect drift. |
| `live_checkout.py` | Report and update the checkout the production daemons actually run from. |
| `load_gate.py` | Decide whether this machine is currently capable of producing a trustworthy test result. |
| `main_red.py` | Is main red, what exactly is it red ON, and does this PR fix that and only that? |
| `model_pin_probe.py` | Print the model every part of the engine will actually run on. |
| `ops_state.py` | ops_state.py — print the live value of every fact §6 of LAUNCH_OPS_PROGRAM.md asserts. |
| `ops_status.py` | Derive the launch-ops programme's status from the repo, not from prose. |
| `pack_banner_probe.py` | Probe every live pack for the retired PASS banner — the claim the renderer stopped making. |
| `popdd_verify.py` | Prospector POPDD proof runner — lane-aware. |
| `pr_triage.py` | Why is every pull request red? Separate a broken TEST from a broken MACHINE. |
| `process_audit.py` | Inventory every automated process in this estate and grade it. |
| `prove_test_fails.py` | Prove a test can fail, and refuse to report a mutation check that never mutated anything. |
| `prune_branches.py` | Retire branches whose content is already in main, and worktrees that are gone. |
| `reconcile_orphan_index.py` | Reconcile index rows whose dossier JSON is not where the index says it is. |
| `restore_drill.py` | R4 — the restore drill. A backup nobody has ever restored is not a backup. |
| `retrieval_parity.py` | Grade the Rust retrieval port against the Python it replaces, on live pages. |
| `rework_metrics.py` | Measure rework, so the efficiency scoreboard cannot be gamed by cutting corners. |
| `service_health.py` | Ask every deployed service whether it is still serving, and alert when one stops. |
| `session_check.py` | Did this session leave anything behind? Read only, run it before you stop. |
| `site_spec_probe.py` | Probe the live state of the mumchimp.com site spec. |
| `store_audit.py` | Audit the operator's real store/ — the checks that are about DATA, not about code. |
| `store_migrate.py` | Move the engine's store between hosts, and prove it arrived. |
| `test_impacted.py` | Run only the tests that can see your change. |
| `unit_economics.py` | What does it cost to produce one sellable pack, and what is the margin? |
| `vendor_ratchet.py` | Count a vendor's call-sites and refuse to let the number grow. |
| `watch_engine.py` | Live view of what the engine is doing right now. |
| `workflow_health.py` | Report GitHub Actions workflows that are DEAD — failing without ever producing a job. |
| `worktree_census.py` | Every worktree on this machine, and whether the work in it exists anywhere else. |
| `worktree_gc.py` | Which worktrees are safe to delete, and which have drifted from main? Report by default. |
| `worktree_snapshot.py` | Copy every dirty worktree's uncommitted state onto a remote branch, touching no working tree. |
| `backfill_packs_parallel.sh` | Backfill the P5 pack artefacts (Complete_Pack.pdf, First_Fortnight.html, |
| `ci-gate.sh` | ───────────────────────────────────────────────────────────────────────────── |
| `copy_audit.sh` | Copy audit across BOTH lanes. Read-only: reports, changes nothing. |
| `install_control_center_agent.sh` | (Re)install the Control Center launchd agent, bound to the CURRENT tailnet address (R24). |
| `install_push_shim.sh` | Install the pre-push shim into this repo's hooks directory. |
| `run_ops_console.sh` | Launch the Ops Console (Next.js) — the replacement for the Streamlit control centre. |
| `seed_action_cache.sh` | Seed the self-hosted runners' action archive cache. |
| `setup_worktree.sh` | Make a fresh `git worktree` actually usable in this repo. |
| `verify_engine_change.sh` | THE ENGINE IS THE CROWN JEWEL. This is the proof that a change to it is safe to commit. |
| `warm_ci_uv_cache.sh` | Build every wheel CI needs, once, into the shared uv cache the runners read. |

### J.4 `crew` — the board and its verification steps


| Step | What it verifies |
|---|---|
| `10-laws.sh` | LAW 22 has a section in the laws file, not just a passing mention. |
| `12-mature-platform.sh` | A new script on this branch must name the mature platform it rejected. |
| `15-code-standard.sh` | Every language this repo writes has a checker in front of it, and it runs on the diff. |
| `20-pr-evidence-tool.sh` | The camera resolves, runs, and passes its own controls. |
| `25-source-registry.sh` | The warehouse's source registry, tested in BOTH directions. |
| `26-datamap-register.sh` | LAW 50: every producer of data carries a verdict, every gap a ticket. The full gate runs |
| `27-showcase-check.sh` | crew#403 CP-A: every science capability on the showcase can describe and demo itself. A mo |
| `30-evidence-on-pr.sh` | The pull request carries a screenshot. Read only. |
| `35-evidence-gate-refuses.sh` | A negative control: strip the evidence off the pull request, prove the gate |
| `40-tests.sh` | This repo's own suite is green, run through the interpreter the README names. |
| `50-cli.sh` | The tool a person actually types resolves and answers. |
| `60-issue.sh` | The tracked issue's boxes, and who is allowed to have ticked them. |
| `70-triage.sh` | The founder's shape: an issue that shows its work, and templates that say the |
| `80-research-ledger.sh` | LAW 35: the estate researches the world, records where it looked, and closes |
| `85-risk-register.sh` | LAW 41: a buyer arrives tomorrow and reads the risks before the features. |
| `86-risk-policy.sh` | The same register, judged by Open Policy Agent instead of by our own Python. |
| `87-hazard-page.sh` | crew#495 CP2: the hazard page is generated from the register. Report mode: prints the |
| `88-incident-page.sh` | crew#668 CP1: the incident page is generated from the ledger, and a row that teaches |
| `90-data-contracts.sh` | crew#84: the data function's day-0 standard, as a gate. Every collected source has a |
| `95-docs.sh` | The documentation standard, enforced. Founder, 2026-08-24: "we need better dos |

*20 numbered verification steps.*


### J.5 `kronos` — the AgentOS kernel, ring by ring


| Ring | Source files |
|---|---|
| `ring0-hypervisor` | `cow.rs`, `lib.rs`, `snapshot.rs`, `vm.rs` |
| `ring1-wasm` | `fuel.rs`, `lib.rs`, `sandbox.rs` |
| `ring2-ebpf` | `ast_gate.rs`, `lib.rs`, `tetragon.rs` |
| `ring3-egress` | `capability.rs`, `lib.rs`, `main.rs`, `proxy.rs` |
| `ring4-ledger` | `amnesty.rs`, `ledger.rs`, `lib.rs`, `workflow.rs` |
| `kernel` | `budget.rs`, `lib.rs`, `main.rs`, `orchestrator.rs`, `supervisor.rs` |

Also: `crates/kernel/`, `k8s/`, `tetragon/`, `wit/` (component-model interfaces), `rust-toolchain.toml`. Requires Linux 5.15+ (eBPF BTF), Kubernetes 1.28+, Temporal.

---

## Appendix K — measured, one-line facts

Every number below was produced by a command on this machine on 2026-09-20, not carried forward.

- Harnesses installed: `pi` (`/usr/local/bin/pi`), `claude` (`/usr/local/bin/claude`). Pi has
  **no blocking `tool_call` hook** and **no permission model**.
- `claude-guards`: **zero** references to pi or to `PI_*`. The guard estate covers one harness.
- `~/.pi/agent/bin/run` — cited by `estate_executor.py` as the detached runner — **does not exist**.
- `prospector/pi-governance/src/index.ts` — exists; **not installed** into `~/.pi/agent/extensions/`.
- `~/.estate/executor.sock` **absent** · `~/.estate/runs` **empty** · no executor LaunchDaemon ·
  `_idp_executor` uid **absent**.
- `bin/idp-executor-status` → `daemon: MEASURED_FAIL`, `boundary: UNKNOWN`.
- Unbounded foreground call measured on this date: **1,622 seconds**.
- `bin/idp-laws-guards-report` → writes 1,337 bytes, emits `## The 0 laws` with an **empty table**.
- `claude-guards/` = 125 files: **77 non-test guard tools**, **43 incident tests**, 5 other tests.
- Wired hook entries: **31** across 5 events (SessionStart 4, UserPromptSubmit 2, PreToolUse 12,
  PostToolUse 2, Stop 11).
- Lanes: **5** (`default`, `build`, `research`, `incident`, `platform`), each with 6 best-practice lines.
- Roles: **10** (`ceo`, `engineering`, `finance`, `information-architect`, `inventor`, `legal`,
  `marketing`, `operations`, `sales`, `ux`) + 3 functional agents.
- Gates: **42** in `idp/bin/*-gate`.
- BDD: **407** scenarios across 15 feature directories.
- MCP: **11** plugins in `idp/mcp/plugins/`.
- Execution arenas: **12** in `hermes-agent/tools/environments/`.
- Verifier modules: **13** in `hermes-v2/otto/verify/`.
- FleetView backend: **22** modules, **7** BDD feature files.
- `crew/scripts/verify.d/`: measured count above.
- `prospector/scripts/`: **76** operational tools.
- `kronos`: **6** crates (5 rings + kernel).
- Aevum: Ed25519 + ML-DSA-65, COSE_Sign1, RFC 3161, hash-chained, tamper-detected (ADR 0028).
- `consultd` cascade: `kimi-bridge` → `deepseek` → `ollama` → `none` (always 503).
- Live outage at time of writing (`prospector/scripts/estate_map.py`):
  `api.mumchimp.com/catalog` → **HTTP 503** (wanted 200),
  `api.mumchimp.com/healthz/money-rail` → **503**,
  `prospector-engine.fly.dev` → **404**,
  `mumchimp.com/` → **200**.
