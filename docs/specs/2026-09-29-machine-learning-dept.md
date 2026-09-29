# Machine Learning dept — the environment becomes intelligent, the agents get better
**Status: PLAN — 2026-09-29.** Founder: "need a plan of how estate becomes intelligent and agents get better."

This is the founding charter of the estate's ML department. It is written against what was
measured this day, not against the vendor-shaped blueprint the founder pasted (decision trees,
DBSCAN, PPO, isolation forest, Redis, six free-tier SaaS databases). Where the blueprint names a
capability the estate already has, the plan uses ours. Where it names one we lack, the plan
says which rung of the placement ladder (ADR 0034) it lands on. Where it is wrong for us, it
says why in one line.

---

## 1. What was measured on 2026-09-29 (the baseline the dept is graded against)

Every number below has the command behind it in the session that wrote this file.

| Signal | Measured | Source |
|---|---|---|
| PRs opened / merged / closed-unmerged, 14d | 1505 / 1361 (90.4%) / **134 (8.9%)** | `gh api search/issues` |
| Median time-to-merge (merged PRs) | 1.5 min | `gh pr list --limit 300` |
| Commits per PR | mean 3.5, median 4, max 8 | 30 most recent PRs |
| `build-multiarch` failure rate (28-min window) | 6 / 6 | `gh run list --limit 300` |
| `ci` / `shadow-verify` / `factory-ci` failure rate | 29% / 33% / 21% | same |
| `merge-when-green` + `deploy-when-green` cancelled | 40 / 61 (66%) | same |
| Intent tickets, 7d: ok / halted / broken | 1402 / 186 / 159 (**20% not ok**) | `~/.estate/estate.db intent_tickets` |
| Step timeouts (exit 124), 7d | 41 steps, **59 min wall-clock** | `step_runs` |
| Router `/v1/chat/completions` errors, last 2000 log lines | 20 / 29 (402 deepseek, 429, 401) | `~/Library/Logs/litellm-local.log` |
| Efficiency ledger rows | 33,761; arms control 1014 / treat 1931 in last 5000 | `~/.estate/efficiency-ledger.jsonl` |
| `fix` commits, 14d | 139 / 1584; ~22% are CI/gate plumbing | `git log --since=14.days` |
| Unified memory server | deployed 44h, **0/0 replicas, no caller anywhere** | `kubectl get scaledobject -n unified-memory` |
| Local memory MCP (`estate-core/memory/mcp_server.py`) | crashes: `No module named graphiti_core` | this session's MCP connect |
| Forge CI-flake model | 97.8% agreement, +9.0 pts over majority class, **never exported** | `forge/experiments/20260911T1657Z-ci-flake-triage.md` |
| Voice → intent catalogue | 73 committed intents; 2 lifetime voice-intent audit rows | `platform/estate/intents`, `~/.estate/voice-intents.jsonl` |
| Node CPU requests | 3115m + 2330m (over the 1.8-CPU-per-node law) | `kubectl describe nodes` |

The shape of the waste: **not** GitHub rate limits (5000/5000 remaining), **not** a boss-agent
bottleneck. It is (a) actions the environment lets through that it could have refused or
answered in-process — red PRs that die, halted intents, timeouts; (b) agents with no memory of
what the last agent learned; (c) decisions made by a frontier model that a 1-ms model could make.

---

## 2. What already exists (one of each layer — nothing below gets built twice)

| Layer | Estate component | State |
|---|---|---|
| Execution boundary, every action typed | `~/.estate/bin/estate-execute` + 455 intent YAMLs (73 committed to `platform/estate/intents`) | operating |
| Action audit (the (s, a, r) log) | `~/.estate/estate.db` `intent_tickets`, `step_runs` (1753 tickets, exit codes, durations) | operating |
| Per-call LLM ledger with randomised control arm | `efficiency_gateway.py` `_arm()` hashes the conversation into `control`/`treat`; `efficiency-ledger.jsonl` | operating |
| Refusing router hook | `request_ceiling.py` — refuses over-sized calls at the router, not after | operating |
| Bus | NATS JetStream `event-bus/nats-0`, `ESTATE_AGENT` stream `estate.agent.>` | operating |
| Scale-to-zero substrate | KEDA + HTTPScaledObject (unified-memory proves the pattern) | operating |
| Confidence-and-decision service | JevLayer (ADR 0030): `mcp__jev__{choice,score,noul}`, `jev_decisions` table | built, use unproven |
| Bayesian hypothesis racing | `hypotheses.race` intent, `libexec/hypotheses-race.py` | operating (net-triage) |
| Offline training with pre-registered gates | `forge/` — Modal + Kaggle launchers, `experiment_record.py`, `cost_gate` | trained once, never exported |
| Memory (cluster) | `platform/unified-memory-server` (Postgres, MAPLE guard, curation worker) | deployed, asleep |
| Memory (laptop) | `estate-core/memory/mcp_server.py` (Graphiti) | broken import |
| Shared knowledge graph | growmos (`.growmos/`, 128 nodes, 577 sources pending) | operating, under-fed |
| Founder surface | Fleet page + `voice_intents.py` (token match → `estate-execute` → visual cue) | operating |

---

## 3. The design: three loops, one substrate

```
                 ┌────────────────────────────────────────────────┐
  agent action ──►  estate-execute (intent)  ── ticket/step rows  │  (s, a, r, s')
                 │        │                                        │
                 │   [A] GATE  ── policy.predict(intent, args, ctx) <2 ms, refuses/holds
                 │        │                                        │
                 └────────┼────────────────────────────────────────┘
                          ▼
                  NATS estate.agent.>  ──►  [C] fleet voice + visual (live)
                          │
                          ▼
               [B] LEARN: nightly Forge job ── label from outcomes ── new policy.onnx ── PR
```

**Loop A — the environment decides (inference, laptop + cluster, <2 ms).**
A single `estate-policy` model called from inside `estate-execute` before a step runs, and from
inside the router before a call is sent. Inputs are what the audit already records: intent
name, arg shape, caller session, recent exit codes for that intent, time since last identical
run, ledger arm, context size. Output: `allow` / `hold N s` / `refuse` with a confidence.
Below the confidence floor it defers to JevLayer, and below that to today's behaviour. The
model is a gradient-boosted tree exported to ONNX (scikit-learn → onnxruntime, ARM-native); no
GPU, no frontier call, no new datastore.

**Loop B — the environment learns (training, free GPU, off-cluster).**
The Forge already does this for one task. The dept makes it the *only* way a model enters the
estate: a task YAML with pre-registered gates, labels taken from recorded outcomes
(`step_runs.exit_code`, PR merged/closed, ledger `ok`), a record filed per run, and export only
when gates pass. Training runs on Kaggle (30 GPU-h/week, already wired) or Modal ($30/mo,
already wired); CPU-only trees train in GitHub Actions minutes. Weights land in the repo as an
artifact the policy loads — reviewable, revertible, one PR.

**Loop C — the founder watches and steers (voice, Fleet).**
Every policy decision is a NATS event; Fleet renders refusals/holds as they happen; "why did you
hold that" is a voice intent that speaks the top three features behind the decision. A model
whose decisions the founder cannot see on /fleet is not operational (§3 of AGENTS.md).

---

## 4. Workstreams, in order. Each ends operational, not merged.

### W0 — Wake the memory layer (prerequisite; 1 PR, no ML)
Agents cannot get better without remembering. Today both memory surfaces are dead.
- Fix the laptop MCP's import (`graphiti_core` in the estate venv) or delete it — one memory, not two. The cluster server is the one (memory: unified-memory-server-is-the-memory).
- Give `unified-memory-server` its first caller: `estate-execute` posts each ticket's outcome line to it; the Stop hook path reads back "what happened last time this intent failed".
- Done = KEDA scales it 0→1 on a real call, `memories` row count > 0, and Fleet shows the recall.

### W1 — The dataset exists by construction (1 PR)
- `bin/estate-policy-dataset`: joins `intent_tickets` × `step_runs` × ledger × PR outcome into one JSONL row per action: features + label (`ok` / `halted` / `broken` / `timeout`; for PRs: `merged` / `closed`).
- Runs as a scheduler job every hour; rolling 30-day window (self-bounding, memory: self-sustaining-not-capped).
- Done = row count on Fleet, matches ticket count.

### W2 — First policy: the refuse/hold gate (2 PRs)
- Task `forge/tasks/intent-outcome.yaml`: predict `not ok` before the step runs. Gate: ≥ 0.85 precision on `refuse` at ≥ 30% recall, held-out by week. Baseline (predict majority) is recorded and the model must beat it by a pre-registered margin, not "a lot".
- Export: ONNX, loaded by `estate-execute` behind `ESTATE_POLICY=shadow|enforce`. Shadow first: log what it *would* have refused; Fleet shows the counterfactual. Flip to enforce only when the shadow log shows a week of ≥ 0.85 precision on real actions.
- Target: the 20% not-ok tickets and 59 min/week of timeouts fall by half. Measured from the same tables.

### W3 — Ship the model that already exists (1 PR)
- Forge CI-flake triage: 97.8% agreement, refused only at export. Re-run with ≥ 300 labelled rows (799 exist), export, and wire it where a frontier call currently reads a red run (`ci-status` / `ci.errors` intents). Done = ledger shows frontier calls on red runs drop; `flake` vs `real` verdict spoken on Fleet.

### W4 — The router learns its lanes (1 PR)
- The ledger already runs a control arm. Add a contextual bandit (Thompson sampling over lanes, reward = `ok` ∧ latency ∧ cost) on top of `efficiency_gateway.py`, for the `cheap` and `consensus` chains only; `default` stays pinned (policy.py [routing]). Kill-switch: bandit off = today's static chain.
- Target: `/v1/chat/completions` error rate from 69% to < 5% by routing around a lane that is 402/429ing *before* the call, not after the retry storm.

### W5 — PR lane outcome model (1 PR)
- Label: merged vs closed-unmerged (134/1505). Features: files touched, guarded paths hit, commits, author class, checks at open. Used by `pr-ready` intent to say "this PR is 80% likely to die; here is why" before open — and by `merge-when-green` to order the queue. Target: closed-unmerged from 8.9% to < 3%.

### W6 — Anomaly containment (1 PR, after W2 has data)
- Isolation forest over per-session action rate, repeat-identical-intent rate, exit-code entropy. Output is a `hold` on that session's next step plus a Fleet alarm, never a kill. Target: a looping session is held within 3 repeats.

### W7 — Agents get better: the memory→prompt loop (ongoing)
- Every refusal, hold, and Forge record becomes a growmos node and a memory row. The SessionStart path reads the last 10 for the intents this session touches. Measured by W1's dataset: a session that read memory should have a lower not-ok rate than one that did not (control arm, same mechanism as the ledger).

---

## 5. What the pasted blueprint gets wrong for this estate (one line each)
- **Redis / Upstash / Turso / Neon / Qdrant** — six new state stores; we have Postgres (estate-db), NATS, sqlite. One of each layer (§6). Refused.
- **A local 3B LLM on 1.5 OCPU / 10 GB** — node requests are already 3.1 and 2.3 CPU; the free tier is cut to 2 OCPU/12 GB (memory: free-tier-hard-ceiling). Refused; semantic routing goes to Groq/Gemini free lanes the router already has.
- **GitHub secondary rate limits** — 5000/5000 remaining; not our failure class. Dropped.
- **Cloudflare webhook gateway in front of GitHub** — the executor is already the gateway for every agent action; a second gateway is a duplicate execution boundary. Refused.
- **PPO / DQN** — no dense reward, no simulator; trees + bandits first, RL only when W2 shows a policy that a tree cannot express.
- **DBSCAN swarm clustering** — no boss-agent problem exists; agents coordinate through JetStream and PRs. Deferred until a measured collision class appears.

## 6. Placement (ADR 0034)
Training: GitHub Actions (trees) / Kaggle (LoRA). Dataset job: scheduler on laptop. Inference:
in-process ONNX inside `estate-execute` (laptop) and the router; the cluster copy runs inside
`unified-memory-server`'s pod (already scale-to-zero) — no new always-on pod.

## 7. Done
The dept is operational when /fleet shows, live, a policy decision refusing or holding a real
agent action, the founder can ask by voice why, and the weekly W1 dataset shows not-ok tickets
and closed-unmerged PRs below the targets in §4. Merged PRs, green CI and passing gates are
not done.
