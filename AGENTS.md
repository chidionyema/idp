# AGENTS.md — estate-wide. Every agent on this machine, and every product.

What the estate is and where things live. Enforcement is not in this file; it is in the executor,
the gates and the hooks, which refuse.

---

## 1. The graph

```bash
growmos --root ~/Documents/code/estate-graph context --brief   # cross-repo
growmos context                                               # inside a repo
growmos --root ~/Documents/code/estate-graph remember "<Name>" --type SYSTEM --desc "<fact>"
growmos --root ~/Documents/code/estate-graph link "<A>" "<predicate>" "<B>"
growmos --root ~/Documents/code/estate-graph journal "<what changed and why>"
```

Record durable facts as you learn them. The graph is shared memory; a context window is not.

---

## 2. Never hand-apply. Merge, and let Flux converge.

`kubectl apply` by hand is forbidden. PR merges to `main` → `build-multiarch.yml` builds amd64 +
arm64, Trivy, cosign → tag `ghcr.io/chidionyema/<name>:main-<run>-<sha>` → Flux image-reflector
polls → `image-automation` writes `flux/image-updates` → `deploy-when-green` merges on green.
`bin/build-image` enforces R24. Do not bypass it.

**An agent never hand-walks the commit → push → PR → re-run-CI loop.** That whole path is the
Greenlane's job (`merge-when-green`, `deploy-when-green`, Flux image automation), and it converges
on its own. Open the PR, then STOP. CI runs, `merge-when-green` lands it, Flux deploys it — a real
production log line is the only "done." If the local `gh` CLI (HTTPS) stalls or the pre-push gate
hangs, that is a flaky network path to report and a missing door to add — not a reason to drag the
founder through manual re-runs. `git` over SSH and `curl` to the GitHub API keep working; use those,
or add a governed capability, but never convert a pipeline the estate already runs into a
founder-manned procedure.

---

## 3. Proof, not assertion

Never declare something WORKING from a synthetic probe, a green CI gate, or an HTTP 200. Prove it
with a real production log line. **"Built" and "operating" are different facts** — say which one
you mean. A gate that cannot fail is not a gate; a test that executes nothing is not a test.

This is two rules kept as one because they are one: **narrating instead of proving** and **asserting
instead of proving** are the same defect, an agent producing words where a measurement belongs.

**Operational** means *used*: the thing is doing its job in production, for its real caller, and
the founder can watch it doing that job live on /fleet (the primary work surface; a new page when it
needs one). A safeguard is operational only when /fleet shows it deciding (pass / refuse) on real
agent actions as they happen. A router lane is operational when /fleet shows real calls through it.

**Done = operational.** Merged, deployed, green CI, a healthy pod, an HTTP 200, a passing test: none
of these is done. Each is a step on the way, never the finish.

**Report only two things: done, or seriously blocked.** A merged PR, an opened PR, a pushed commit,
a green check is not news; do not announce it. A claim of "blocked" carries its evidence: the intent
that was run (`estate-execute <intent>` or `estate_invoke`), its exit status, and the line it
printed. A blocker without an intent run behind it is a guess, and is not reported.

---

## 4. Secrets — by name only, from the vault

Keys arrive through `estate-secrets` (SOPS + age) or the Bitwarden human-vault bridge:

```bash
gh workflow run vault-seed.yml -f entry=laptop
git -C ~/Documents/code/estate-secrets pull
source ~/Documents/code/estate-secrets/scripts/secret-load
```

Never paste a key into a file, an env var in code, a commit, a message, a journal entry, or a graph
node. Reference it by env var name. Never print a secret value. Never ask the founder to carry one
between surfaces.

---

## 5. Coordination

**Docker runs on Rancher Desktop (moby, x86_64) — `docker` lives at `~/.rd/bin`, the engine socket is `~/.rd/docker.sock` via the `rancher-desktop` context; there is no Docker Desktop and no colima (the `colima` context is stale and must not be used).**

`~/Documents/code/crew` is shared coordination; `crew/STATE.md` is the live estate map. Never
restart another agent's process. Never touch the Telegram token's polling.

---

## 6. One of each layer. A second copy is stitching and gets deleted.

The platform is `idp`. Products run on it. Exactly one of each: routing, traces, identity, secrets,
scheduling, catalog, execution boundary, evidence, verification, memory. A product is never deleted
for living outside `idp`; a duplicate layer always is.

**Before building anything, prove it does not already exist** — `growmos query "<what you want to
build>"`, then read the candidate. The estate has built the same capability five to ten times. Do
not make it eleven.

---

## 7. Execution — intents only

Every action the agent performs goes through an **intent YAML** in `~/.estate/intents/`.

```
~/.estate/              # NOT a git repo — lives outside version control
  bin/estate-execute    # executor binary
  intents/*.yaml        # 24 intents: shell.parse, git.branch, ci.run, etc.
  libexec/*.sh, *.py    # helpers: shell-suggest.py, shell-verify.py, etc.

~/Documents/code/idp/mcp/plugins/estate_mcp.py   # MCP plugin (3 tools only)
  estate_list   — list all available intents
  estate_show   — show args for one intent
  estate_invoke — run an intent
```

**Rule: if an action is not a YAML intent, the agent cannot perform it.**

`estate_executor.py` (13 raw tools) is deleted. `estate_simulate.py` is deleted.
Only `estate_mcp.py` remains — it wraps the intent executor.

To add a new capability: write `~/.estate/intents/<name>.yaml`, commit to idp.
To invoke: `estate_invoke { intent: <name> }` via MCP, or `estate-execute <name>` directly.

Design spec: `docs/specs/2026-09-24-estate-agent-enforcement-platform.md`

## 8. Placement — the free tier decides, not the cluster

Nothing goes on the cluster by default. Place every workload by the ladder in
`docs/decisions/0034-workloads-are-placed-by-the-free-tier-not-by-the-cluster.md`, first rung
that fits: delete → GitHub Actions schedule → Grafana Cloud free → Cloudflare Workers free →
laptop just in time → KEDA scale-to-zero on the node → always-on on the node. Only free tiers that
need no card or are hard-limited qualify. A PR that adds to the node states its CPU/memory
requests; the node's requests stay under 1.8 CPU. Before any node reboot, resize or drain,
calico-node must be Ready on every node.

## 9. Voice first and realtime

The platform is moving to voice first and realtime (founder, 2026-09-26). The founder speaks to the
estate and hears it back, and watches what it does as it happens. The work surface is the Fleet
page: a capability the founder cannot reach by voice or see live there is not finished. State is
streamed as it changes over the estate's JetStream bus, not written up afterwards in a report.
Voice design: `docs/specs/2026-09-22-voice-intent-plane-architecture.md`.

The bar is 2100, not 2026: every surface the founder touches is futuristic, spoken to first and
watched live, never a form, a table dump or a report to read later.

**Drive to completion.** Agents here work as senior engineers: take the work to operational (§3)
without being chased, find the next blocker yourself and clear it, and do not stop to admire a
merge. A session that needs the founder to repeat an instruction, re-point it at existing work, or
check its claims has failed at the job, whatever it shipped.

## 10. Working style

- Only make the change that was asked for. No unsolicited refactoring.
- Do not guess. Search.
- Do not report a number you did not measure this turn.
- Do not grade a proxy — grade the thing itself.
- **Never use `grep -r`. Use `rg -l "pattern" path`** — `rg -l` finishes in <1s where
  `grep -r` times out at the 60s ceiling. A broad `grep -r` that hits the ceiling is a defect
  in the search, not evidence the thing is absent.

## 11. Living policy (crew#219 R38): the block below is code, not prose

<!-- Restored 2026-09-26: ca326fdb (#3959) removed this block, and sovereign/policy.py (every
     [budget], [routing], [merge] and [jev] key) has raised PolicyError since. -->


`sovereign/policy.py` parses the one ```toml block in this file, and `sovereign/config.py`
builds its `budget.usd_per_day.*`, `cost.*`, `routing.*` and `merge.*` keys from it. The
numbers config.py declares on its own are repeated under `[invariants]`, and
`sovereign/tests/bdd/test_policy.py` fails when the two disagree. Change a value here and the
code follows; change it in config.py alone and the suite goes red. Every key still takes the
usual env override (`sb config --lint` lists them).

- **Capabilities** (spec 4.4): what each agent class may do unattended. `destructive` ops need
  quorum and a hardware signature on top of budget; `nondestructive` need budget only.
- **FSM rules** (spec 4.3): `init -> planning -> tool_use -> synthesis -> terminal`; the
  cycle path repeated `max_cycles` times pauses the session before the next one.
- **Budget defaults** (spec 8, R40): USD per day per spender. The sum over `days_per_month`
  must sit inside the `[cost]` contract, $0 to $150 a month; the test proves it.
- **Model routing**: LiteLLM aliases from `llm/config.yaml`. `cheap` is the last entry of every
  fallback chain there, and the only one with zero marginal cost.
- **Merge criteria** (R41): `dev` is permissive, `main` is strict. A PR targeting a strict
  branch fails when any feature is still `pending`, or when a pending mark has no owner or
  says `unclaimed`. `.github/workflows/ci.yml` sets `SB_BDD_STRICT` from the PR's base branch,
  and `sovereign/tests/bdd/conftest.py` enforces it.

```toml
[capabilities]
nondestructive = ["fs_commit", "fs_read", "git_status", "tool_result", "doc_commit", "budget_refill"]
destructive = ["fs_delete", "git_push_force", "db_drop", "service_destroy", "rewind", "provision_paid_compute"]
engine = ["fs_read", "fs_commit", "git_status", "tool_result", "doc_commit"]
intake = ["fs_commit", "doc_commit"]
shadow = ["fs_read"]

[fsm]
initial_state = "init"
terminal_state = "terminal"
cycle_path = ["planning", "tool_use", "synthesis"]
max_cycles = 5

[budget.usd_per_day]
litellm = 3.0      # frontier calls through the proxy; llm/config.yaml max_budget is the hard ceiling
consensus = 1.0    # the three-model vote on destructive ops
vision = 0.5       # photo intake (spec 2.3)
ollama = 0.0       # local, no marginal cost
langfuse = 0.0     # self-hosted

[cost]
contract_min_usd_month = 0
contract_max_usd_month = 150
days_per_month = 31   # the longest month, so a sum under the cap holds in every month

[routing]
# default=minimax (floor, never a routing choice); cheap=groq (free, request-metered, since
# SEED_GROQ_API_KEY landed 2026-09-10 -- deepseek was the prior cheap lane, dead since 2026-09-04,
# history in ~/AGENTS-FULL.md). deepseek stays a consensus voter only (rejoins default/cheap the
# moment its key returns, no PR needed).
default = "minimax"
vision = "vision"
cheap = "groq"
consensus = ["deepseek", "minimax", "gemini"]

[merge]
strict_branches = ["main"]
require_bdd_green = true
pending_owner_required_on = ["main"]

[invariants]
"consensus.quorum" = "2/3"
"consensus.timeout_s" = 30
"branch.count" = 3
"branch.budget_pct" = 10
"approval.timeout_min" = 15
"blind.halt_after_min" = 5
"alerts.digest_over_per_hour" = 50
"spiffe.max_missed_heartbeats" = 3

[jev]
default_confidence_floor = 0.7
timeout_ms = 2000
escalate_on_timeout = true
model = "jev-1.13.0"
force_on_decisions = true   # when true, the Stop-hook blocks turns that skip Jev for bounded decisions
```
