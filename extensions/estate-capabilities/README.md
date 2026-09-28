# estate-capabilities — named capabilities, never a shell

An agent on this estate has **no raw `bash`**. It has a closed set of named capabilities, and each
invokes something the estate already owns. The list is deliberate; a capability is added as a row,
never acquired by reaching for a shell.

## The capabilities

| name | invokes | kind of work |
|---|---|---|
| `estate_executor_status` | the daemon's `health` verb | liveness, before any work |
| `estate_run_gate` | `bin/idp-ci` / `bin/verify` | the estate's own verification gate |
| `estate_run_tests` | `pytest` | one test target, no shell metacharacters |
| `estate_git_state` | `git status` / `git log` | read-only checkout state |
| `estate_execute` | the executor daemon | any command through the one door |
| `estate_graph_sync` | `bin/sync-all` / `bin/graph-health` / `bin/sync-repos` | the knowledge graph |
| `estate_session_start` | `sb start` → Temporal SessionWorkflow | fleet-scale agent sessions |
| `estate_capabilities` | (lists itself) | the refusal that names a missing capability |

## The one door

Every command these rows build goes through `runThroughDoor` → the executor daemon's UNIX socket
(`~/.estate/executor.sock`). Nothing in this file spawns a process directly. See
`extensions/executor-door/` for the daemon that owns the ceiling and the ledger.

## Injection is closed, and proven

The daemon runs every command via `bash -lc` (`platform/executor/daemon.py`), so any free-form value
interpolated into a command string is single-quoted by `quoteSh` before it meets the shell. Rows
that take a free-form `task`/`repo`/`runner` (only `estate_session_start`) route them through it;
rows that don't need it only ever interpolate validated tokens (test ids pass a regex, script names
are literals). Proven by running a hostile `task` (`...; rm -rf ~; $(touch /tmp/x); 'quote'`)
through the real `bash -lc` path: nothing executed.

## Placement, for whoever installs this

```
idp/extensions/estate-capabilities/index.ts        # authoritative (this repo)
~/.pi/agent/extensions/estate-capabilities/index.ts # installed
```

The repo copy is authoritative; `~/.pi/agent/extensions/` is the installed one. An extension
directory with an `index.ts` is auto-discovered by pi and hot-reloadable with `/reload` — no restart
needed. A broken extension in that directory stops every session from starting, so check before it
lands in both copies.
