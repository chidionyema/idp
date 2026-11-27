<!-- estate:routed-from AGENTS.md -- current law, not history. It is loaded on demand through the AGENTS.md route table instead of at Turn 1 (idp#8636). Moved verbatim. -->

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

