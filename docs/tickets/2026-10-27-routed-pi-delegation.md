# Routed Pi delegation — the generic, harness-independent launch path

**2026-10-27 · issue #7310 · agent `pi-delegate-intent`**

The estate already had a delegation boundary: `platform/estate/libexec/delegate-build.py`
(`plan` → `dispatch` → `status`) with the `delegate-build` intent in front of it. That boundary
is Claude-specific — every model call it makes is a `claude -p` child, and the caller cannot
choose the harness. The founder asked for delegation that is model/harness independent and
prefers routed headless Pi, while keeping the existing caller model selection working.

This is the extension of that one boundary, not a second one.

## What was added

`delegate-build.py` gained two verbs and the machinery they need:

| Verb | What it does |
|---|---|
| `launch task=<task.json> slug=<name>` | Runs a caller-supplied task through a routed harness, with preflight, bounds, measured progress and persisted state |
| `cancel slug=<name>` | Stops **only** this launch's own child (proved by the run id in the child's argv) |

### The task packet

The caller supplies a JSON packet. Nothing in the common path names a vendor:

```json
{
  "task_id": "demo-1",
  "spec": "/path/to/spec.md",
  "worktree": "/path/to/worktree",
  "identity": "pi-delegate-intent",
  "claim_issue": 7310,
  "harness": "pi",
  "provider": "estate",
  "model": "minimax_m27",
  "done_check": "grep -q DELEGATED artifact.md",
  "milestones": [{"id": "artifact", "kind": "file", "path": "artifact.md"}],
  "budget": {"max_wall_s": 75, "max_attempts": 2, "max_steps": 32},
  "strategies": ["write it directly", "write it another way"]
}
```

**Harness and model are separate.** `harness` says *how* the work is run (`pi`, `claude`); `model`
says *which model* the harness asks for. `provider` and `model` are the caller's choice; the pi
adapter defaults to `provider=estate`, `model=minimax_m27`.

### Preflight — before the first model call

A refused preflight costs nothing, so everything that can be known is known first:

1. **Identity.** The launcher's identity (`ESTATE_AGENT`, else the name the intent call carried)
   must equal the task's `identity`. A mismatch is a refusal, not a preference. The child is
   launched with `ESTATE_AGENT` bound to that identity.
2. **Claim.** The identity must hold a live `CLAIM` on `claim_issue`, with a heartbeat no older
   than two hours. A stale or absent claim is a refusal.
3. **Worktree.** It must exist, be a directory and be a git root of its own (not a subdirectory
   of some other checkout).
4. **Route.** The pi catalogue (`~/.pi/agent/models.json`) must carry the provider, the provider
   must carry a `baseUrl` (a route) and must offer the model id. A model the provider does not
   carry is refused — the route is never swapped silently. No credential is ever read or printed.
5. **Output.** The state directory must be writable.

### The child

`PiHarness` runs headless Pi against the estate router:

```
pi --offline --provider <provider> --model <model> --mode json --print \
   --no-skills --no-prompt-templates --session-dir <dir> --session-id <run-id> @<prompt>
```

`ClaudeHarness` is the same contract with the `claude -p` child, so the existing path and the
new one share one contract rather than two.

The child is bounded three ways — wall clock (default 75 s, under the intent door's 100 s
ceiling), tokens and steps. It is started in its own session, so the only processes the launcher
can terminate are the ones it started. Unknown token usage stays unknown (`null`), never zero:
an unknown spend is not a free spend.

### Progress is measured, not narrated

The `done-check` is reality: the launch succeeds when the check exits 0, never when the worker
says it is done. The worker's own words are kept in the state as `said` and are never used as
evidence.

A **milestone** is a predicate the dispatcher runs against the actual deliverable (a file that
must exist, a command that must exit 0). `last_verified_milestone`,
`tokens_since_milestone` and `elapsed_since_milestone_s` are what progress means here. A
heartbeat, a tool call or a touched file is liveness, and liveness is not progress.

### Recovery is empirical, and a repeated failure is escalated

The second attempt is rebuilt from what reality said: the same `[EMPIRICAL_STATE]` block the
plan/dispatch path already used, carrying the raw check output and never the failed attempt's
words (`empirical_block()` in `delegate-build.py`).

* An **identical retry** (the same strategy twice) is refused before the child starts.
* A **repeated failure signature** (the same normalized check output twice) is escalated:
  `blocker` says `needs-supervisor` and `next_recovery` says `needs-supervisor`.
* A **terminal failure kind** (context overflow, permission, identity, schema) is never retried:
  the same input would fail the same way.
* The **budget carries** across attempts: the wall clock and the token bound are the run's, not
  the attempt's, so a second attempt only gets what is left.

### State Fleet can read

`~/.estate/delegate/<slug>/state.json` holds the run: state, route, identity, milestones, the
verified milestone, spend since it, failure signatures, blocker, next recovery, and the paths of
the raw event logs. `~/.estate/delegate/<slug>/results.json` keeps the existing shape the Fleet
reader already reads (`done`, `attempts`, `empirical`, `scratchpad`, `usage`).

The Fleet reader (`backstage/plugins/fleetview-backend/src/fleetview_backend/delivery.py`) was
extended minimally: when a `state.json` sits next to a `results.json`, its measured progress is
surfaced as `delegate[].progress`, and `/fleet` shows the state, the milestone and the blocker.

## Decisions

* **Extend, do not add a supervisor.** A new module would have been a rival delegation boundary
  carrying its own copy of the done-check and its own state. The estate has one of each layer
  (AGENTS.md §6), so the generic path lives in the same file.
* **The pi adapter is the default; Claude keeps working.** `harness=claude` is the same contract,
  so the old callers are untouched, and the old `plan`/`dispatch`/`status` verbs are unchanged.
* **The route is the caller's.** The launcher validates that the route exists and never silently
  substitutes a model.
* **Refuse early.** Preflight, the identical-retry check and the repeated-failure check all run
  before a child is started, because a refusal costs nothing and an exploration costs the run.

## What is proved, and how

* `tests/estate/test_delegate_launch.py` — eleven empirical tests: the done-check decides
  success, preflight refuses a foreign identity, a missing worktree, a model off the route, a
  missing claim and a stale claim *before any child starts*; the second attempt is built from
  the failed check and not from the failed attempt's words; an identical retry and a repeated
  failure signature are escalated; `cancel` refuses a pid it does not own.
* `backstage/plugins/fleetview-backend/tests/test_delivery.py` — the Fleet reader surfaces the
  measured progress, and a delegation without a state file simply has none.
* `tests/estate/test_delegate_build_reality.py` — the existing empirical recovery suite still
  passes unchanged.

The real routed demonstration is recorded in
[`2026-10-27-delegated-pi-demo.md`](2026-10-27-delegated-pi-demo.md).
