# The estate agent surface, measured

**Date:** 2026-10-26
**Kind:** reference — the stored output of a measurement, not a hand-written description
**Measured by:** `bin/estate-surface-map` (re-runnable: `bin/estate-surface-map`, `--json`,
`--check`)
**Spec this map feeds:** [`docs/specs/2026-10-26-context-compiler-and-execution-gateway.md`](../specs/2026-10-26-context-compiler-and-execution-gateway.md)
**Decision:** [`docs/decisions/2026-10-26-one-context-compiler-and-one-execution-gateway.md`](../decisions/2026-10-26-one-context-compiler-and-one-execution-gateway.md)

## Why this exists

The founder's question, 2026-10-26: *does the estate already have a central execution gateway
through which Pi, Claude Code and other coding agents operate, or can they independently access
filesystem, shell, Git and model providers?* And, for a consultant about to design against the
estate: *map the surface, so the design is built on what exists rather than on what is assumed.*

A written answer goes stale the moment a hook changes. This is therefore a **script that
measures** and a document that **stores what the script said on a named day**. Re-run it and the
map moves; the gaps are named so each can be closed and then re-measured as closed.

**No secret values appear here.** Where a configuration holds a credential, the map names the
header and says a value is present.

## How to re-measure

```bash
bin/estate-surface-map           # the map below, live
bin/estate-surface-map --json    # the same facts, for a diff or a CI assertion
bin/estate-surface-map --check   # exit 1 while a named gap is open
```

The timestamp is the only non-deterministic field. Everything else is read from a file on the
machine, and a file that is not there is reported `MISSING` rather than assumed present.

## The map, as measured on 2026-10-26

```
ESTATE AGENT SURFACE MAP
measured_at: 2026-10-26T21:02:49+00:00
==============================================================================

1. RUNTIMES AND WHAT EACH MAY TOUCH
  [pi]
     entry    pi extension (tools + session_start)  <- platform/estate/pi/estate-commands.ts
     entry    pi MCP server over stdio  <- ~/.pi/mcp.json
     entry    estate capabilities extension  <- extensions/estate-capabilities/index.ts
     entry    pi plan extension (in-process plan lock)  <- extensions/pi-plan-lock
     shell    removed from the model's tool set at session_start (bash, shell)
              <- platform/estate/pi/estate-commands.ts:205
     door     estate_execute accepts a free-form command string and runs it through the executor daemon (ceiling 100s). The door is bounded and recorded; it is NOT intents-only.
     tools    estate_capabilities, estate_execute, estate_executor_status, estate_git_state, estate_graph_sync, estate_run_gate, estate_run_tests, estate_session_start
     mcp      estate
     read     read-shunt: a read of a file over the threshold is replaced by a digest from a free worker model. Fail-open by construction -- a missing core, a timeout or an error passes the original content through unchanged. Compression, not authorization.
     model    pi defaultProvider=estate defaultModel=minimax_m27
     drift    the INSTALLED extension runs growmos context at session_start; the repository copy does not -- the live surface and the tree disagree
  [claude-code]
     entry    Claude Code CLI  <- /Users/roseonyema/.estate/harness/cc/settings.json
     entry    MCP: estate-memory (global)  <- /Users/roseonyema/.estate/harness/cc/.claude.json
     entry    MCP: project servers from .mcp.json  <- .mcp.json
     mcp      global=estate-memory  project=growmos
     hooks    read=1 write=1 bash-specific=0 catch-all PreToolUse=1
              catch-all: python3 /Users/roseonyema/.estate/memory/bin/estate-memory-enforce plan
     deny     (EMPTY)
     autoMode 10 allow entries
     model    http://127.0.0.1:4000  (opus)
     creds    header names only: x-litellm-api-key -- values not printed

2. THE DOOR
     executor daemon   present
     ceiling           100s
     intents           346
     audit log         present
     law               AGENTS.md section 7: 'if an action is not a YAML intent, the agent cannot perform it'. The Pi capability surface also exposes a free-form command door (estate_execute), and the Claude Code surface reaches the shell through the tool, not through an intent. The law and the machine differ.

3. CONTEXT PLANE (what decides what the model sees)
     read_shunt                   present
                                  <- /Users/roseonyema/.estate/hooks/idp-read-shunt
     read_shunt_threshold_lines   350
                                  <- /Users/roseonyema/.estate/hooks/idp-read-shunt
     per_request_token_ceiling    200000
                                  <- platform/llm/request_ceiling.py
     efficiency_gateway           present -- per-call pre-steps m1..m10 and an outcome row per call
                                  <- platform/llm/efficiency_gateway.py
     efficiency_ledger            present
                                  <- ~/.estate/efficiency-ledger.jsonl
     deterministic_code_graph     catalog-projection: one Component per .py, one edge per import, SHA256(output) is a pure function of SHA256(input)
                                  <- bin/catalog-projection
     impact_selection             idp-affected-graph: three-layer impact map (AST + import edges, prompt/schema, graph topology), decided by Jev, fails OPEN toward running
                                  <- bin/idp-affected-graph
     tree_sitter_code_graph       ZeroEdge (router-attached optimizer) and its TTCS code graph -- the Bloop analogue already exists in the estate
                                  <- platform/llm/zeroedge_gateway.py

4. STATE AND PROMOTION
     authoritative_state          git commits + ~/.estate evidence + cortex memory + the .growmos graph; the claim comment on the issue is the durable task state
                                  <- AGENTS.md
     required_checks_on_main      ['bdd', 'ci-success', 'executes-gate', 'fast-gate / fast-gate', 'feature-request-plan', 'greenlane', 'guarded-paths', 'portal-app', 'test']
     ruleset_source               platform/github/ruleset.idp.required-checks.json
                                  <- platform/github/ruleset.idp.required-checks.json
     promotion                    main is protected by a required-checks ruleset; a lane raises the PR and fast-forwards main only on green -- no agent self-promotes
                                  <- .github/rulesets (applied by bin/repo-rulesets)

5. NAMED GAPS (each is a fact about this machine)
     G1  No single execution gateway: each runtime has its own door
         what:  Pi reaches the executor through an MCP server whose tools are intents-only, AND through estate_execute, which takes a free-form command string. Claude Code reaches the shell through its own Bash tool; the estate's plan hook sees that call but the command itself never becomes an intent. There is no component all agents go through.
         so:    A context compiler or a policy inserted at 'the gateway' has nowhere universal to sit. Enforcement is per-surface and therefore uneven.
         proof: extensions/estate-capabilities/index.ts; ~/.estate/harness/cc/settings.json (PreToolUse catch-all)
     G2  The Claude Code shell is gated by session discipline, not by policy
         what:  The catch-all PreToolUse hook runs estate-memory-enforce's plan gate: it refuses a shell call when the session has no declared plan or no BDD scenario for the active sub-goal. That is a discipline gate. Nothing inspects WHICH command runs, and permissions.deny is empty while autoMode.allow carries 10 broad grants (read any file, run python3, git, gh, merge).
         so:    The estate's central law (intents only) does not hold on this runtime. Any invariant enforced only at a door is unenforced here.
         proof: ~/.estate/harness/cc/settings.json (permissions, autoMode); platform/estate/memory/plan.py:271
     G3  The Pi door has a free-form command entrance
         what:  estate_execute takes a command STRING. It is bounded (100s ceiling) and recorded in ~/.estate/logs/mcp.jsonl, but it is not intents-only, so the door and AGENTS.md section 7 disagree.
         so:    A policy boundary inserted at the door is only as strong as the widest entrance to that door.
         proof: extensions/estate-capabilities/index.ts
     G4  Claude Code is routed at the laptop router, not the cloud router
         what:  ANTHROPIC_BASE_URL points at 127.0.0.1:4000 (the fallback). The estate law is cloud-first: llm.<zone> is the default route and the laptop is the fallback. Pi, by contrast, is on the estate provider.
         so:    Cloud-only state (virtual keys, max_budget, the shared Redis answer cache) is not on this surface, so cost and cache policy cannot be enforced where this runtime spends.
         proof: ~/.estate/harness/cc/settings.json (env.ANTHROPIC_BASE_URL)
     G5  A model credential sits in a plaintext config value
         what:  settings.json carries a credential in x-litellm-api-key. The value is not printed by this map. It is a key in a file on disk, outside the vault path (SOPS + age) the estate law names for secrets.
         so:    A credential that lives in a config file is rotated by hand, is not revocable in one place, and leaks into any transcript that prints settings.
         proof: ~/.estate/harness/cc/settings.json (env.ANTHROPIC_CUSTOM_HEADERS)
     G6  No context compiler: nothing decides WHAT an agent may read
         what:  The read path is unmediated except by the read-shunt, which shrinks a big file to a digest AFTER the model asked for it, fail-open. Nothing resolves a task to a bounded, ranked, provenance-carrying source set with a token budget. The request ceiling stops an oversized call; it does not put the right source in it.
         so:    Context spend and context QUALITY are both uncontrolled on every surface, and the read-shunt's digest is a lossy stand-in for a real selection.
         proof: platform/llm/request_ceiling.py; ~/.estate/hooks/idp-read-shunt
     G7  The live Pi extension and the repository's copy have drifted
         what:  The installed extension at ~/.pi/agent/extensions/estate-commands.ts runs growmos context at session_start; the repository copy does not. What agents actually run is not what the tree says.
         so:    Every claim about 'what Pi does' sourced from the tree is a claim about a different program than the one running.
         proof: ~/.pi/agent/extensions/estate-commands.ts vs platform/estate/pi/estate-commands.ts
```

## The answer to the founder's question

**No. The estate does not have a central execution gateway.**

- **Pi** has two doors: an intents-only MCP server (`estate_list`, `estate_show`,
  `estate_invoke`, approval-gated `estate_create`) and `estate_execute`, which takes a free-form
  command string.
- **Claude Code** has one door of its own — its Bash tool — where the estate's only gate is the
  plan gate (a session-discipline gate, not a policy gate).
- The two runtimes are on **different model routes**: the estate (cloud) provider for Pi, the
  laptop fallback router for Claude Code.
- **Filesystem, Git and model providers** are all reachable without an estate policy decision in
  the path, on at least one surface.

The estate does own every *part* of a gateway — executor daemon, 346-intent registry, MCP plugin,
plan gate, router, efficiency ledger, affected-graph — and none of the *whole*.

## What a consultant should build on (and not rebuild)

| Estate capability (measured) | Use it for | Do **not** build |
|---|---|---|
| `bin/catalog-projection` — deterministic, content-addressed component/edge graph | the substrate for impact-aware source ranking | a second AST/symbol index |
| `bin/idp-affected-graph` — three-layer impact map, Jev-decided, fails open toward running | the `impact_score` and its evidence | a second impact analyser |
| ZeroEdge + TTCS — the tree-sitter code graph | symbol/AST retrieval | a new tree-sitter service |
| `platform/llm/efficiency_gateway.py` + `~/.estate/efficiency-ledger.jsonl` | the measurement substrate for every per-call metric | a second ledger |
| `platform/llm/request_ceiling.py` — 200k | the hard ceiling a context budget sits under | a second ceiling |
| `~/.estate/hooks/idp-read-shunt` — 350-line threshold, fail-open digest | the **fallback** compressor under a real selector | a selection mechanism |
| `platform/executor/daemon.py` — 100s ceiling, recorded | the execution substrate of the gateway | a second executor |
| `~/.estate/intents/*.yaml` — 346 intents | the only vocabulary the gateway accepts | — |
| `platform/estate/memory/plan.py` — the plan gate | session discipline; it stays | a policy gate |
| `platform/github/ruleset.idp.required-checks.json` + the lane | promotion control: required checks, no self-promotion | agent-side promotion |

## Gap → what closes it → where it is specified

| Gap | Closes at | Spec section |
|---|---|---|
| G1 no single gateway | the gateway (existing executor, made mandatory) | §1.3, C3, m2 |
| G2 shell gated by discipline | the gateway + the broker's decision point | §1.2, §5 m3 |
| G3 free-form command entrance | the gateway's intent-only contract | C3, m2 |
| G4 laptop route on one surface | the broker on the cloud route | §5 m6, I6, I7 |
| G5 credential in a config file | the estate's vault path (SOPS + age) | §4 (secrets are by name only) |
| G6 no context compiler | the compiler | C1, I3, I4, m4 |
| G7 live/tree drift | the measured map in CI | I10, m5 |

## What this map does not claim

It measures the **laptop's** estate surfaces on the measured day. It does not measure the
cluster's, other agents' runtimes (Cursor, Gemini, opencode — reached through the same estate
memory bridge but with their own configurations), or anything about a runtime that is not
installed here. It is the honest starting position for this machine, re-measurable at will —
not a claim about every machine the estate owns.
