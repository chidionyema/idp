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

Every rule lives in `rules.yaml`, one row each: the statement, the law it serves, the argv that
grades it, the fixture pair that proves it both ways, and the planes it is enforced on (the
repository's CI, a session hook, the cluster's admission controller). `bin/idp-rules` is the only
thing that reads it -- `run` grades the repository, `cluster` checks the admission policy a row
names is on disk, `session` grades the files a hook hands it, and `render-agents-md` writes the
table below. The table is generated: edit `rules.yaml`, not these lines. `bin/idp-ci` runs
`bin/idp-rules render-agents-md --check`, so a row and its rule cannot drift apart.

Before 2026-09-07 each rule was a bash rung in `bin/idp-ci`, a hand-written row here and, for
several, a third copy inside `bin/policy-test` -- so a rule could be worded one way, graded
another, and listed a third. Fifteen fixtures under `policy/fixtures` were named by no runner at
all. Founder, the Unification Move: "Ruthless Deletion ... Do not leave them as dead code. Do not
deprecate them. Eradicate them."

The full generated rule table (85 rows) lives in `docs/policy/rules-table.md`, not here --
it is re-graded by CI every run but no longer re-injected into agent context every turn
(founder, 2026-09-14: it was ~32KB of the ~37KB in this file, loaded on every single turn
for no reason). Open it when you need to look up a specific gate.

Rules that are already types or tools, and so need no row: compose files must parse
(`docker compose config`), the gateway config must match its release schema
(`check-jsonschema`), every catalog entity must match the Backstage schema, and every
script must pass `shellcheck`, every generator must be idempotent (two runs over one
inventory, byte-identical), the generated catalogue must carry a relationship graph, and
every entity reference in it must resolve to an entity something defines
(`bin/catalog-refcheck`, proved both ways in the same run). Those run unconditionally in
`bin/idp-ci`.

Adding a rule: add a row to `rules.yaml`, add both fixtures, run `bin/idp-rules render-agents-md`
and `bin/idp-ci`. No new rung, no new gate script.

## Hooks first: bin/idp-install-hooks on every clone (2026-09-16)

**Mandate: On any fresh checkout, run `bin/idp-install-hooks` before your first commit.**

The estate's `.githooks/pre-push` is the hook the founder shipped (crew#584 CP2) to refuse a
push whose session-plane rules would fail in CI seven minutes later. It only fires when
`core.hooksPath` names `.githooks`, which a fresh clone does not do. On 2026-09-16 that gap cost
three CI cycles on idp#3627 to catch two static defects (portal-buttons drift, LAW 46 hardcode)
that this hook would have refused in seconds. Running `bin/idp-install-hooks` is idempotent and
takes under a second; `bin/idp-ci` prints a WARN banner at the tail of every run on a clone that
has not wired it, so the missing setup is impossible to miss.

## Token Efficiency: idp-exec wrapper (2026-09-15)

**Mandate: You are forbidden from running raw shell commands. You must prefix every command with `bin/idp-exec` to preserve token efficiency.**

Why: Raw command output can exceed 50 lines and bloat the context window. `bin/idp-exec` automatically:
- Clamps output to first 25 + last 25 lines if it exceeds 50 lines
- Saves full output to `~/.pi/agent/state/last_exec.log` for later inspection
- Returns the exact exit code of the underlying command

Usage: `bin/idp-exec cat large_file.log` instead of `cat large_file.log`

## Workstation bootstrap: bin/idp-workstation-bootstrap on any fresh machine (2026-09-17)

**Mandate: On any fresh workstation (Mac, Linux, CI runner, dev container), run `bin/idp-workstation-bootstrap` once to reach dev-ready. It is idempotent; re-runs keep whatever already works.**

Why (founder 2026-09-17): "our system must be able to bootstrap itself in any env". The prior bootstrap chain (`bin/idp-bootstrap-estate`) assumed the tool set was already installed and did not wire local `gh`/`kubectl` conveniences, so a fresh macbook on 2026-09-17 had age identity but no OCI config, no kubeconfig, and unauthed `gh` — which blocked Lane E (PR #3599) on a laptop-only credential gap. This script closes Level 0 (portable tool install per OS family) and Level 3 (local `gh auth` + `~/.kube/config`) around the existing Level 2 estate bootstrap.

The one hand a person still gives is the age identity restore (iCloud Keychain / paper / hardware key); this script refuses to proceed if `SOPS_AGE_KEY_FILE` is not readable. Vendor-neutral throughout: no local container runtime is installed by this script (see 2026-09-17 container-runtime mandate above).

## The estate twin: ask the graph, not the cluster (2026-09-12)

Ask before you touch the cluster: `bin/estate-twin-runtime --once --code|--dead|--state|--history <node>|--blast-radius <n>`.
Extends `catalog/estate.db` (no second store/bus/MCP server, per THE HEADLINE). `UNKNOWN` is
the default, not a failure; `stranded` is not serving. Full spec, rules and proof:
`docs/specs/2026-09-12-estate-twin-complete-spec.md`, `docs/evidence/estate-twin/PROOF-OF-WORK.md`.

## Platform queries go through the estate MCP server (ADR 0006)

A question about estate state is one `mcp__estate__*` call, never a shell recon. A state-changing
tool is two calls (propose, execute), execute refusing on a stale state hash. Extend `mcp/`; never
add a second server. Full text: `docs/decisions/0006-the-platform-answers-for-itself-over-one-mcp.md`.

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
```


THE EMPIRICAL PROOF RULE binds here too, verbatim, inherited from `~/AGENTS.md` — not repeated
below to avoid loading the same block twice in one context (measured duplicate, 2026-09-14).

<!-- growmos:start — managed by `growmos integrate`; edits inside this block will be overwritten -->
## growmos — living knowledge graph (shared memory for humans + agents)

This repository keeps a knowledge graph in `.growmos/` (entities, typed relations, provenance,
profiles, a journal). It is the shared world model that survives context windows. Treat it as
memory you read at the start of work and write to as you develop. Zero-config commands:

1. **Session start** — run `growmos context` (a compact brief: hubs, health, pending work, latest journal).
   If it lists pending work, run the `growmos next` → apply loop (step 4) right away, without being asked —
   it is quick, needs no permission, and is how the graph stays alive.
2. **Before cross-cutting questions** ("what depends on X?", "why was Y decided?") — run
   `growmos query "<question>"`; answer from the returned subgraph and cite edge ids.
3. **When you learn or decide something durable** (new component, architectural decision, ownership,
   dependency, gotcha) — write it back immediately:
   - `growmos remember "<Name>" --type <TYPE> --desc "<one grounded sentence>"`
   - `growmos link "<A>" "<predicate>" "<B>"`   (short verb phrase predicates: "depends on", "replaces")
   - `growmos journal "<what changed and why>"`
4. **Feed the organism** — run `growmos next`. It hands you a *task packet* (extraction / resolution /
   profile / gold set / review) with the exact prompt, the JSON shape, and the `growmos apply …` command.
   Do the judgment work yourself, write the JSON, apply it. Repeat until `growmos next` says the graph is
   up to date — that loop covers everything, including the evaluation gold set and the periodic node review.
   If it reports the daily extraction cap, run `growmos next --force` (the cap only guards unattended runs).
   Never invent facts not in the source; every relation must connect two extracted entities.
5. **Before claiming facts about the repo in a summary/report** — `growmos check "<claim text>"` grounds
   your claims against edges with provenance (evaluator–optimizer loop).
6. **Session end** — `growmos journal "<summary of the session>"` so the next session picks up here.

Store files are plain JSONL under `.growmos/` — commit them with your code. Do not hand-edit
`entities.jsonl`/`relations.jsonl` (use the CLI); prompts in `.growmos/prompts/` are yours to tune.
More: `growmos --help`, docs at https://github.com/codician-team/growmos.
<!-- growmos:end -->
