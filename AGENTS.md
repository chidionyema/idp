# AGENTS.md — the rules of this repository, and the gate that reads them

This file is the version-controlled boundary for agent work in `idp` (crew #180, CP6).
The estate's laws live in `~/AGENTS.md`; this file holds only what is specific to this
repo. Each row names the gate that enforces it and the two fixtures that document what the
gate calls bad and good.

The rung that re-ran every gate against those two fixtures on every single run was deleted on
2026-09-04 (founder: "run each of the nine gates in the AGENTS.md table against its two
fixtures ... this is stupid"). It graded this file's own fixtures, so no defect in the estate
could ever fail it and no change to the estate could ever pass it differently. The gates
themselves still run, against the repository, where a real defect can trip them.

Row format, one rule per row. `gate` is a shell function or command defined in `bin/idp-ci`;
`must-fail` and `must-pass` are paths relative to this file.

| rule | gate | must-fail | must-pass |
|---|---|---|---|
| No file names where the checkout, home directory or machine lives (LAW 46) | hardcode_scan | tests/fixtures/hardcoded-path.bad.sh | tests/fixtures/hardcoded-path.good.sh |
| No dependency whose licence blocks a sale; a scan with no licences is not clean (LAW 40) | policy_gate | policy/fixtures/sell-blocking.json | policy/fixtures/clean.json |
| No scheduled job on this laptop that runs in the sleep window or is never pinged (LAW 28) | policy_gate | policy/fixtures/placement-misplaced.json | policy/fixtures/placement-ok.json |
| Paid capacity is auto-defaulted up to estate-defaults.yaml node_pool.budget_monthly_usd and refused above it (crew#289, R14) | policy_gate | policy/fixtures/capacity-over-cap.json | policy/fixtures/capacity-under-cap.json |
| Only the gateway binds a non-loopback address; everything else is 127.0.0.1 or nothing (R20) | bind_audit | tests/fixtures/listeners.bad.txt | tests/fixtures/listeners.good.txt |
| No namespace without a both-ways default-deny NetworkPolicy, a ResourceQuota, a LimitRange and a DNS exception (crew#191) | ns_fence_gate | tests/fixtures/ns-fence/bad.yaml | tests/fixtures/ns-fence/good.yaml |
| Every scheduled job reaches the Dagster UI with a description of what it does (LAW 28) | job_described | tests/fixtures/schedule-undescribed.yml | tests/fixtures/schedule-described.yml |
| A code location loads the way workspace.yaml loads it: by file path, not as a package (LAW 45) | defs_validate | tests/fixtures/definitions/relative-import.py | tests/fixtures/definitions/loads-by-path.py |
| A workflow that grades main never cancels main's own run; stale pull-request runs still are (crew#865) | main_verdict_gate | tests/fixtures/main-verdict/bad.yml | tests/fixtures/main-verdict/good.yml |
| A test grades behavior or parsed structure, never prose: no test function may only assert sentences or string membership in file text (R76, founder 2026-09-03) | prose_pin_scan | tests/fixtures/prose-pin/bad.py | tests/fixtures/prose-pin/good.py |
| One credential is one tenant's; the operator's road never widens the customer's (decision 0021) | tenant_split_gate | tests/fixtures/tenant-split/bad.yaml | tests/fixtures/tenant-split/good.yaml |

Rules that are already types or tools, and so need no row: compose files must parse
(`docker compose config`), the gateway config must match its release schema
(`check-jsonschema`), every catalog entity must match the Backstage schema, and every
script must pass `shellcheck`, every generator must be idempotent (two runs over one
inventory, byte-identical), the generated catalogue must carry a relationship graph, and
every entity reference in it must resolve to an entity something defines
(`bin/catalog-refcheck`, proved both ways in the same run). Those run unconditionally in
`bin/idp-ci`.

Adding a rule: add a row, add both fixtures, run `bin/idp-ci`.

## Platform queries go through the estate MCP server (ADR 0006)

Founder, 2026-08-25: the platform is self-aware; one interface answers questions about it. So: a
question about estate state is one `mcp__estate__*` tool call, not a shell recon. A new query tool
summarises by default and drills only on request, under a byte ceiling. Any tool that changes state
is two calls, propose then execute, and execute refuses when the state hash in the proposal no longer
matches. Events reach agents debounced through the Sovereign Bus, never raw. Extend `mcp/`; never add
a second server. Full text: `docs/decisions/0006-the-platform-answers-for-itself-over-one-mcp.md`.

## Living policy (crew#219 R38): the block below is code, not prose

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
destructive = ["fs_delete", "git_push_force", "db_drop", "service_destroy", "rewind"]
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
default = "deepseek"
vision = "vision"
cheap = "deepseek"
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
```


## THE EMPIRICAL PROOF RULE (founder 2026-09-05, verbatim; record: `~/.claude/docs/founder/2026-09-05T1415Z-he-generalized-rule-empirical-proof-over-synthetic-probes-a79801e5.md`)

NEVER declare a system "WORKING" or "MEASURED_OK" based solely on synthetic probes, CI gates, or HTTP 200 health checks. Synthetic checks lie.

Before claiming a fix is successful, you MUST prove it empirically:
1. **Read live traffic:** Fetch the actual pod logs (`kubectl logs --tail=100`) and quote a real, end-to-end user transaction completing successfully.
2. **Check for silent failures:** Look at the most recent cluster events (`kubectl get events`) to ensure the pod isn't crashing or OOMing immediately after answering a probe.
3. **Verify the critical path:** If it's a bot, verify the upstream webhook and LLM generation path. If it's a database, verify a real row was written.

If you cannot quote a successful production log line, the system is NOT working.
