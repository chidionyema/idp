# executor-door — how an agent runs a command with no shell

An agent on this estate has **no `bash`**. It has two tools, and they are the only road to a shell.
There is no third option and no fallback.

```
execute_command({ command, cwd, ceiling_sec? })  ->  { ok, job_id }   in milliseconds
read_job({ job_id })                             ->  { state, exit_code, log }
```

Submit, then read. Not run, then wait.

## Why it is shaped this way

A command that never runs inside the agent's own process tree **cannot hold a turn open**, whatever
it was written to do. That is the difference between a ceiling that is caught and a ceiling that is
**unexpressible** — the founder's point when he said *"it should not even get bera teh"*, after six
failed attempts at a 60-second cap.

Each of those six attempts put the ceiling inside the guarded identity. **A control that shares an
identity with what it controls cannot deny it.** The fix was not a seventh policy in the same
process; it was to move the execution plane to the far side of a message.

## The pieces, and which one owns which fact

| piece | file | owns |
|---|---|---|
| the door | `extensions/executor-door/index.ts` | registers both tools, removes `bash`, refuses a direct call |
| the daemon | `platform/executor/daemon.py` | the 60-second ceiling, the socket, the job records |
| the runner | `platform/executor/run.py` | starts the command detached, records its real exit code |
| the status tool | `bin/idp-executor-status` | says `MEASURED_OK` or `UNKNOWN`, and which files are still rewritable |

**One ceiling owner.** The daemon holds the number. The door imports it and does **not** implement a
second timeout — a second copy of the number is a second answer and the two drift (LAW 44).

**Fail closed.** If the daemon is unreachable the door **REFUSES**. It never falls back to spawning a
shell locally. That fallback is the exact defect class this estate keeps catching.

## Two ways to run a command without a shell, both legitimate

From an agent session — the tools:

```
execute_command <command>          -> job id, immediately
read_job <job-id>                  -> state, exit code, output
```

From a terminal or a script — the same daemon, the same socket:

```
bin/idp-exec <command...>          -> job id, immediately
bin/idp-exec --read <job-id>       -> the result
bin/idp-exec --simulate <command>  -> what would happen, running nothing
bin/idp-executor-status            -> daemon state, ceiling, and what is still rewritable
```

## What is refused at the door, in both paths

- **A ceiling above 60, in every spelling** — `61`, `2m`, `150s`, `1h`, `gtimeout -k 5 150`,
  `--kill-after=10 300`. The daemon refuses them all; there is no spelling that gets past it.
- **Any command that waits on something outside its own process** — `sleep`, `watch`,
  `gh run watch`. A detached run of a waiting command is still a job nobody is waiting for.

## The severance, and how a running session gets it

`bash` leaves the active tool set at `session_start`. A session that began *before* the door loaded
gets no such event — so the door also refuses a severed tool at `tool_call`, which fires in every
live session. That is the channel that reaches sessions already running.

To load the door into a session that is already open, `/reload` re-reads auto-discovered extensions.
Extensions in `~/.pi/agent/extensions/` or `.pi/extensions/` are auto-discovered and can be
hot-reloaded this way — **no restart needed.** `pi -e ./path.ts` is for quick tests only and is not
hot-reloadable.

## Placement, for whoever installs this

An extension directory with an `index.ts` in it is the discovery pattern:

```
~/.pi/agent/extensions/executor-door/index.ts
```

A broken extension in that directory stops **every** session from starting, so a change here is
checked before it lands in both copies. The repo copy under `extensions/executor-door/` is
authoritative; `~/.pi/agent/extensions/executor-door/` is the installed one.

## A gate is not a wall, and this one says so

`bin/idp-executor-status` reports `boundary: UNKNOWN` while the agent's own uid can still rewrite the
daemon, the door and the plist. It prints that instead of a green it cannot support:

```
daemon:    MEASURED_OK   listening on <socket>, ceiling 60s
boundary:  UNKNOWN       the agent's own uid can still rewrite: ...
```

Closing it means the daemon running under a separate uid — `bin/idp-executor-install`, a LaunchDaemon
step that requires the founder's `sudo`. Until that lands, this is a **move** of the execution plane,
not a lock on it, and the status tool says so out loud rather than leaving a half-boundary to read as
a whole one.

## The order this came from

Founder, 2026-09-13, verbatim:

> Solution 2: Decoupled Execution Daemon (The True Enterprise Pattern). The agent shouldn't have raw,
> unrestricted bash spawned directly from its own process tree. It should request execution from an
> isolated daemon. We strip the native bash tool from pi entirely. We replace it with an MCP server
> called `idp-executor-mcp`. The Hard Boundary: this MCP server runs as a background macOS launchd
> service under a restricted configuration or a separate user profile. The Enforcement: the server
> accepts `execute_command` JSON payloads from the agent, wraps the command in the 60-second timeout,
> runs it, and returns the stdout/stderr. The Result: the agent can still run `git commit` or
> `pytest`, but it does so via the daemon. Because the agent cannot edit the daemon's binary or
> launchd plist, it cannot bypass the ceiling. The execution plane is completely severed from the
> agent's local write privileges.

**Why this is an extension and not an MCP server.** pi has no MCP support — its own README, line 495:
*"No MCP. Build CLI tools with READMEs, or build an extension that adds MCP support."* So the daemon
half is exactly as specified; the door into it, on this harness, is an extension. Registering an MCP
server pi cannot load would have been a file, not a tool — and a file no session loads is decoration.

**The sequencing rule, from the founder:** *get something working, then take away bash access.*
Building the fence before the road exists is the error this estate already made once.
