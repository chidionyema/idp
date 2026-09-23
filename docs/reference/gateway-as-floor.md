# Gateway-as-floor: agents emit events, the gateway writes

Moved out of `AGENTS.md` on 2026-09-19, verbatim, to hold that file under its 300-line gate
(`agents-md-gate.yml`). Nothing here changed: the rule, its reasoning and its break-glass
protocol are as the founder stated them on 2026-09-17. `AGENTS.md` now carries the rule in
one line and points here.


**The gateway is the only writer. Agents have no write capability — not gated, not audited, not wrapped. Removed.**

The harness (judge, PRM, Aevum, dod-guard, pareval, shadow-verify) existed before this rule but was bypassed at session start: every terminal, every Claude Code session, every CI runner was a direct writer with git credentials and a repo mount. Building N enforcement layers around N entry points is lossy — every new entry point is a new hole. This rule inverts the topology.

**What agents may do:** emit an event to the gateway. That is the complete capability set.

**What the gateway does:** on event receipt, materialize a fenced worktree (isolated per-event, no shared state), execute the plan, collect the diff, pass through the full judge/PRM/Aevum/dod-guard chain. Only after DoD v3 signs does anything touch a real branch.

**What every UI becomes:** a gateway client. Terminal, Telegram, Backstage, phone, cron, CI — all emit events. None write. None self-verify. There is no "interactive writer."

**Why this changes agent behavior structurally:** an agent with no git binary, no credentials, no repo mount cannot run tests and call it done, because it cannot run tests. It cannot push, because it cannot push. It can only propose. The gateway decides. The agent's self-model shifts from "worker with tools" to "planner that proposes work" — not as a policy, but because the substrate does not support the old model.

**The migration:** replace every write capability (Claude Code hooks, CI runners, local shells, orchestration jobs) with a gateway client that calls `emit(event)`. The gateway, orchestrator, judge, Aevum, and dod-guard already exist — they were sitting behind a door everyone walked around. This removes the door.

**The one implementation invariant:** worktrees are isolated per-event. Two concurrent proposals must never share a worktree — that would re-introduce the same race condition being eliminated from the agent side.

### Enforcement: how write capability is physically removed

Policy is bypassable. Physical removal is not. The enforcement path:

1. **Agent sandbox:** agent processes run in a container (OrbStack/OCI) with no git binary, no credentials mounted, no repo volume. The only outbound socket is the gateway client endpoint. This is not a firewall rule — the binary does not exist in the image.
2. **Gateway client only:** `bin/idp-gateway-emit <event-json>` is the one tool the sandbox exposes. It validates the event schema and posts to NATS. No other write path exists.
3. **CI runners:** GitHub Actions runners for agent jobs use the same restricted image. Human-triggered jobs (deploys, rollbacks) use a separate runner class with explicit credential injection, audit-logged per run.

### Enablement: what agents gain, not lose

The gateway client is not a narrowing — it is a richer interface than raw git. Agents can:
- Propose multi-step plans with dependencies, not just single diffs
- Request shadow-verify runs against a fenced worktree before committing to a proposal
- Subscribe to gateway events (watch a build, receive judge feedback, retry a step)
- Query the estate twin for live cluster state without needing kubeconfig

The constraint is on *writing verified work to a real branch*. Everything else — read, propose, observe, query — remains available and is expanded by the gateway's event model.

### Break-glass: when the cluster is down (black plan)

If the cluster is unavailable and the gateway itself cannot be reached, the estate needs a recovery path. That path must be **narrower, not wider**, than normal operation.

**Break-glass protocol:**

```bash
# Step 1: mint a time-limited break-glass token (founder hardware key required)
bin/idp-break-glass mint --reason "<one line>" --ttl 30m --scope recovery
# Writes a signed token to ~/.local/state/idp/break-glass-token (expires in TTL)
# Appends a gate.run receipt to .aevum/local.jsonl immediately

# Step 2: agent recovery session starts in restricted mode
IDP_BREAK_GLASS_TOKEN=$(cat ~/.local/state/idp/break-glass-token) claude
# The session hook reads the token, enables write capability ONLY to recovery/ branch prefix
# Every tool call is written to .aevum/local.jsonl before execution

# Step 3: after recovery, post-mortem is mandatory
# The break-glass token expiry automatically opens a post-mortem PR with the Aevum log
```

**What break-glass allows:**
- Write to `recovery/*` branches only — no direct main, no feature branches
- Run pre-approved recovery scripts: `bin/idp-workstation-bootstrap`, `bin/idp-oci-bootstrap`, `bin/idp-flux-reconcile-force`
- Read cluster state via `bin/idp-kube` (read-only, same as normal agent access)
- Emit events to NATS if the gateway is partially up

**What break-glass never allows:**
- `git push --force` to any branch
- Direct `kubectl apply` (cluster writes still go through Flux)
- Skipping the Aevum receipt for any action taken
- Extending its own TTL

**The post-mortem requirement:** every break-glass session automatically generates a PR titled `recovery/<date>-<reason>` containing the full Aevum log of every action taken. That PR must be reviewed and merged before another break-glass token can be minted. This is the accountability loop.

### Agent-assisted cluster revival — Claude Code unrestricted

When the cluster is down, the gateway is unreachable, and the estate needs to be revived, **Claude Code on the founder's machine is the recovery tool**. In this scenario the gateway-as-floor rule is explicitly suspended for the duration of the recovery session. This is not a loophole — it is the designed exception.

**What triggers this:** the cluster is confirmed down (`bin/idp-kube` returns no nodes), the gateway pod is not running, and Flux cannot reconcile anything. Normal operation is impossible by definition.

**How to start a recovery session:**

```bash
# Confirm the cluster is actually down (not just a probe failure)
bin/idp-kube get nodes 2>&1
bin/idp-kube get pods -n flux-system 2>&1

# Start Claude Code in recovery mode — full write capability, Aevum-logged
IDP_RECOVERY_MODE=1 claude
# The session hook records a gate.run receipt at start: {gate_id: "break-glass", result: "open", plane: "recovery"}
# Every subsequent tool call appends to .aevum/local.jsonl before execution
```

**What Claude Code can do in recovery mode:**
- Full shell access, git, kubectl — everything needed to diagnose and fix
- Push to `recovery/*` branches directly (Flux can reconcile from these)
- Run `kubectl apply` for emergency patches if Flux itself is down
- Restart pods, rotate secrets, re-seed vault, re-bootstrap OCI credentials

**The one hard constraint:** every action taken must be committed to `.aevum/local.jsonl` before it executes. The session hook enforces this — if the receipt write fails, the tool call is blocked (LAW 38 exception: if the Aevum path itself is corrupted, the founder types `IDP_AEVUM_SKIP=1` explicitly at the terminal — never scripted).

**After recovery:** a post-mortem PR is required within 24 hours. Title: `recovery/<date>-<reason>`. Must include the full `.aevum/local.jsonl` diff from the session. No new break-glass session opens until this PR is merged.
