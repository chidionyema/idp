# Onboarding: the executor daemon — how an agent runs a command with no shell

**What it is for.** It removes `bash` from the agent and gives it a road that cannot hold a turn
open. The agent submits a command, gets a job id back in milliseconds, and reads the result later.
Because the command never runs inside the agent's own process tree, **the 60-second ceiling is
unexpressible rather than merely caught** — no spelling of a longer wait gets past it. That is the
whole point, and it is what six previous attempts failed to achieve by putting the ceiling inside
the process it was supposed to control.

**What it costs.** One launchd job (`ai.estate.executor`) holding a UNIX socket, idle at rest. No
network listener: the socket is `srw-------` under the owner's home, never a TCP port (LAW 21). No
new database. Job output is one small `.log` / `.exit` / `.pid` triple per run.

**Where it lives.**

| path | what it is |
|---|---|
| `platform/executor/daemon.py` | the daemon: owns the ceiling, the socket, the job records |
| `platform/executor/run.py` | the runner: starts the command detached, records its real exit code |
| `bin/exec-daemon` | the entry point launchd execs — resolves the interpreter, because launchd does not search PATH |
| `launchd/ai.estate.executor.plist.tmpl` | the job template; rendered by `bin/idp-install-launchd` |
| `extensions/executor-door/index.ts` | the door into the daemon from an agent session |
| `bin/idp-exec` | the same daemon from a terminal |
| `bin/idp-executor-status` | what state the daemon and the boundary are in |

**How an agent works under it.** Two tools, and no third option: `execute_command` submits,
`read_job` reads. From a terminal it is `bin/idp-exec <command...>` and `bin/idp-exec --read <id>`.
`--simulate` answers what would happen, running nothing.

**How to turn it on, and off.**

```
bin/idp-install-launchd --check          # what would be installed
bin/idp-install-launchd                  # render and load
bin/idp-executor-status                  # daemon state, ceiling, boundary
launchctl bootout gui/$(id -u)/ai.estate.executor   # to stop it
```

To load the door into a session that is already open, `/reload` re-reads auto-discovered
extensions — no restart needed. `bash` leaves the tool set at `session_start`, and the door also
refuses a severed tool at `tool_call`, which is the channel that reaches live sessions.

**Honest gap — and it is named loud.** `bin/idp-executor-status` reports **`boundary: UNKNOWN`**.
The daemon applies the ceiling, but the agent's own uid can still rewrite `daemon.py`, `bin/exec-daemon`
and the plist. A control that shares an identity with what it controls cannot deny it. Closing this
needs the daemon under a separate uid — `bin/idp-executor-install`, a LaunchDaemon step that requires
the founder (LAW 54). Until then this is a **move** of the execution plane, not a lock on it, and the
status tool says exactly that rather than reporting a green it cannot support.

**What is refused, in both paths.** A ceiling above 60 in every spelling (`61`, `2m`, `150s`, `1h`,
`gtimeout -k 5 150`, `--kill-after=10 300`), and any command that waits on something outside its own
process (`sleep`, `watch`, `gh run watch`). A detached run of a waiting command is still a job nobody
is waiting for.

**Why the door is an extension and not an MCP server.** pi has no MCP support — its README, line 495:
*"No MCP. Build CLI tools with READMEs, or build an extension that adds MCP support."* The daemon half
is exactly as the founder specified; the door into it, on this harness, is the one mechanism the
harness has. An MCP server pi cannot load would be a file, not a tool.

**The order, and its sequencing.** Founder, 2026-09-13: *"get something working, then take away bash
access."* The road first, the fence second — in that order. Full text and the verbatim spec:
`extensions/executor-door/README.md` and `AGENTS.md` § "How an agent runs a command".
