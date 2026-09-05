# Checkpoint

## RESUME HERE — the agent workforce (crew#850)

The founder asked for three things in a row on 2026-09-05: take CrewAI to its full advanced
surface, rename it to something general rather than "infra", and get it right because "we
[are] setting up a company and [a] proper crew". The design, the research and the checkpoints
are all on https://github.com/chidionyema/crew/issues/850.

**Where the work is.** `~/dev/code/infra-crew`, branch `crew850-agent-workforce`. The pass in
flight renames the package `infra_crew` to `agent_workforce`, the environment prefix
`INFRA_CREW_*` to `AGENT_WORKFORCE_*`, and the queue from the single label `lane:infra` to the
general lane set already on the board. After that comes the feature adoption: a Flow with
structured state and `@persist`, `CheckpointConfig` so a killed pod resumes, `MCPServerAdapter`
against the estate MCP server, a `PRE_TOOL_CALL` hook that raises `HookAborted` on merge,
deploy, dispatch and cluster verbs, the unified `Memory` class, native `planning`, and the
version move from 1.9.3 to 1.15.20.

**Two measured facts that shape it.** The `lane:infra` label never existed on the board, so the
CronJob has matched nothing on every run since it was deployed — that is why "we have it set up"
produced nothing. And the estate MCP server offers nine tools including `remember`, `recall` and
`get_workload_logs`, which replaces our own `tools/estate.py`, while the github route offers only
six read tools, so the write path still needs the official GitHub MCP server (CP7).

**Cannot be verified on this Mac.** It is an Intel machine, and `crewai==1.15.20` depends on
lancedb, which publishes no macOS x86_64 wheel. Verification is the repository's own CI on
ubuntu, not a local run.

**Other lanes.** idp#1656 (the one-shot cleanup) is open with auto-merge on and deletes the two
crew539 incident tests that are the last red on idp#1521 (Cyrus). idp#1521 also carries the
CA-bundle fix, commit 92196da5. The founder still owes two calls on crew#850: CrewAI AMP against
self-hosting, and whether the customer-facing agent surface is CrewAI's frontend protocol or
Backstage. BuilderPack, which he sent as an input, is recorded on crew#846.
