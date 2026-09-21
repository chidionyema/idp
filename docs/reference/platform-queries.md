# Platform queries: the tools, and how to call them when the door is shut

Companion to **ADR 0006** (`docs/decisions/0006-the-platform-answers-for-itself-over-one-mcp.md`)
and to the one-line rule in `AGENTS.md`: *a question about estate state is one `mcp__estate__*`
call, never a shell recon.*

This file exists because that rule, on its own, is a prohibition with no command attached. An
agent who cannot name the call falls back to the shell recon the rule forbids.

---

## Why this is written down (the incident, 2026-09-19)

One session, one question — *is component X live?* — and it was answered wrong **twice**. The
agent:

1. read `docs/reports/flux-state.md` (a scheduled artifact, written every 15 minutes) and
   reported a row dated the previous day as the current state of the cluster;
2. quoted an `oke-check` job log the same way, as if a log were a live read;
3. searched `~/.claude/projects/*.jsonl` — **other sessions' private transcripts** — to infer
   what a peer could do, and built a confident, unfalsifiable answer from it;
4. reported the wrong CNI for the cluster by quoting a commit message from weeks earlier.

At no point did it call the tool that answers the question directly. Every one of those was
shell recon standing in for a query the platform already serves. Twice it was wrong in a way
that would have caused real damage if acted on.

---

## The tools

`mcp/plugins/` registers these (name — what it answers):

| Tool | Answers |
|---|---|
| `get_estate_state` | What the estate actually IS, not what it declares: overview (freeze, rulings, sessions, board), delivery (open P0s, failed runs), runtime (clusters, Flux rows, surfaces), docs/apis, security |
| `get_estate_inventory` | Every Backstage entity (kind, name, owner, repo) + the `STATE.md` timestamp it was read from |
| `get_workload_state(app)` | **"Why is X down"** — catalog entry, desired vs actual, summarized metrics |
| `get_workload_logs(app, tail)` | Last N log lines, bounded by `ESTATE_LOGS_MAX_TAIL` |
| `get_catalog_drift(rule)` | Where the catalog's *declared* pick disagrees with the graph's *measured* state |
| `ask_holmes(question)` | HolmesGPT on what is happening in the cluster and why |
| `list_sessions` / `get_session(name)` | What the founder has been running |
| `remember` / `recall` | The estate's permanent memory |
| `get_estate_guards` | Which guards exist, and whether they *fired* (never conflates `idle` with `working`) |

State-changing pairs — **two calls, joined by a state hash** (`propose` records the hash it was
computed on; `execute` refuses when the live hash differs):

`simulate_change`/`execute_change` · `simulate_command`/`execute_command`/`read_job` ·
`propose_patch`/`simulate_patch`/`verify` ·
`propose_mutation`/`verify_mutation`/`seal_mutation`/`admit_mutation`

---

## When the gateway does not answer

`bin/idp-mcp-door --route estate` BLINDs on an unset `MCP_GATEWAY_KEY` (vault entry
`mcp-gateway`, needs an OCI session). The plugin **functions are pure Python** and run against
the local store. This is the sanctioned fallback, and it is still **one query, not a recon
sweep**:

```bash
# The store the tools read, when their /data default paths are absent
ESTATE_DB_PATH="$PWD/catalog/estate.db" \
ESTATE_CATALOG_PATH="$PWD/catalog/catalog-info.yaml" \
python3 -c '
import sys, json; sys.path.insert(0, ".")
from mcp.plugins.workload_state import build_workload_state
print(json.dumps(build_workload_state("<app>"), indent=2))'
```

---

## The rule this incident paid for

**When a peer's state is unknown, ask the peer.** The crew board
(`~/.claude/ESTATE_BOARD.jsonl`, fleetview `/channels`) exists for exactly this.

Do **not** read another session's transcript, `~/.claude/projects/*.jsonl`, or a process's
environment to infer what that session can do. Those files are not a state source; they are
private working memory. They record what a session *believed*, including beliefs it later
corrected — so quoting one produces a confident answer that cannot be checked and is often
wrong. Sessions have been graded on this.

---

## `UNKNOWN` is a real answer

If the MCP answer is `found: false` or `available: false`, **that is the answer**: the platform
does not hold the fact. Say so, and name what would. Do not reach for a file that happens to
mention it.

`UNKNOWN` and `stale: true` are truthful results, not failures to route around. Measured
2026-09-19: `get_estate_state` returned `available: false` — *"the producer (crew#648 CP2) has
not written one"* — while `get_workload_state` returned `found: false` with
`state_error: no k8s nodes for workload`. Both were correct. The estate DB genuinely held no
cluster rows, because its collector had not run.

A fence that refuses the read and offers nothing in its place is **LAW 38**: a fence a correct
machine cannot satisfy is an outage. That is why the guards in `claude-guards/policy/command.rego`
(`direct_cluster_read`, `stale_report_as_truth`, `peer_transcript_recon`, `estate_store_bypass`)
each carry a typed escape marker rather than being absolute.

---

## Related

- `docs/decisions/0006-the-platform-answers-for-itself-over-one-mcp.md` — the decision
- `AGENTS.md` — the one-line rule
- `docs/reference/agent-identity.md` — how a device gets read-only cluster access (WJ.1)
- `bin/estate-twin-runtime` — the graph the read tools are built on
