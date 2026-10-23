# The harnesses the estate has, and how one gets swapped

Founder, this answers three questions in the order they matter: which coding agents this estate
actually has on it, what Fleet really does today when you hand it work, and the smallest change
that would let you point any harness at any piece of work on either the cloud or this laptop.

Everything below was measured on this machine on 2026-10-23. Where I could not measure something,
the gap is written out as a gap instead of being filled from what I already believed. Nothing was
edited to produce this document; it is read-only, and every claim names the command or the file
that shows it.

## 1. What is on the machine

Counting only things proven to exist, the estate has **four harnesses with their own home on this
laptop, of which two have actually done work**.

**Claude Code** lives in `~/.estate/harness/cc` — that is its home directory, not a copy of it. It
holds `settings.json`, its transcript folder, project state and shell snapshots. It starts by
typing `claude`, and it has run: the session store carries **423 sessions** whose provider is
`claude-code` (measured by reading `catalog/estate.db`, section 2). That file is machine-local — it
is gitignored (`.gitignore:12`) — so those are this laptop's sessions, not the repository's.

**pi** lives in `~/.pi/agent` and has settings, npm packages and a `sessions/` folder. It also has
run, **122 sessions**, and it is the harness this audit is being written in.

**Gemini CLI** is *configured but not installed*: `~/.gemini` and `~/.config/gemini-cli` exist, and
`command -v gemini` returns nothing. The estate's memory manifest nevertheless asserts it as a
runtime and `bin/estate-memory-install --check` prints `ok gemini`. That is a claim the machine
does not support, and it is listed as a defect in section 6.

**opencode** is installed (`command -v opencode` resolves, `~/.config/opencode` exists) and was not
running when I looked. **kimi** (the Moonshot CLI) is on `PATH` with no home directory of its own —
installed, never used. **codex** has a `~/.codex` home but appears in none of the estate's lists, so
it is "installed and not admitted".

Three more planes exist that carry agent work without being an interactive harness:

- **The studio** (`~/.estate/studio/studio.db`, started as `studio --serve-only`) is a resident
  supervisor daemon.
- **The agent-job workflow** (`.github/workflows/agent-job.yml`) runs a harness inside a GitHub
  runner, which is the only place any harness runs "in the cloud" today.
- **The Temporal session plane** (`estate_session_start`, `sovereign/engine/`) runs a *runner*, a
  different and much smaller notion than a harness — see section 4.

Declared but absent: **cyrus** (`AGENT_READ_DIRS` in `fleetview-backend/main.py` reads
`~/.cyrus/runs`, which does not exist), **dagster** (offered as an option in
`research-engine-dispatch.yml`), and **github-actions** (a value in `schema/session.json` with no
reader and no row). These are vocabulary, not harnesses.

On the cluster, three workloads that are supposed to be agents are not running: the `agent-workforce`
CronJob sits **Pending for 28 minutes**, `resident-brain` has **0 replicas**, and three of the
five Deployments in the default namespace have **no endpoints**. "Deployed" there does not mean
"operating", and this document does not count them.

## 2. What Fleet does today when you hand it an agent a job

There are two surfaces and they are not the same thing.

**On Fleet** there is a panel (`backstage/packages/app/src/modules/room/ui/AgentJobs.tsx`, mounted
in `FleetReactorApp.tsx`) where you type a task and pick a harness from a two-item list. That list is
a constant in the TypeScript:

    const HARNESSES = ['pi', 'claude-code'];

with a comment saying it mirrors `agent_jobs.HARNESSES` in the backend. The backend
(`backstage/plugins/fleetview-backend/src/fleetview_backend/agent_jobs.py`) has the same two names
again, and the dispatch workflow (`.github/workflows/agent-job.yml`) has them a third time as a
`choice` input whose `options:` array names the same two. So choosing a harness is choosing one of
two names that are written down in three languages and checked by nothing.

The path a job takes is: the panel posts to `/agent-jobs`, the backend dispatches
`agent-job.yml`, a GitHub runner installs that harness, runs it against the task, and the rows are
read back and drawn on the board. **The harness always runs in GitHub's cloud.** There is no
argument anywhere on this path that means "run it here, on the laptop".

**On Face** you can only watch. `FacePage.tsx` renders `FaceAgentJobs`, which prints up to three
jobs as `● task — stage`. There is no way to start one and no way to choose a harness. You can see
work; you cannot hand out work.

**By voice**, you cannot do either. The voice door (`voice_intents.py`) lists every `*.yaml` in
`~/.estate/intents/` — 333 files — and `load_catalog` simply globs that directory, so any intent
file becomes speakable with no code change. None of those 333 is about harnesses or agent jobs:
searching the intent names for `harness`, `runtime` or `agent-job` returns nothing.

## 3. Five words for one thing

This is the reason "swap the harness" is not a one-line change. The estate calls the same object a
**harness** (Fleet's panel), a **runtime** (the memory manifest `platform/estate/memory/runtimes.json`),
a **provider** (the session store column), a **runner** (the Temporal session plane) and a
**harness.invocation** (the event envelope in `schema/session.json`). Because the words differ, the
lists differ, and because nothing compares the lists, they have already drifted apart in ways that
are measurable today:

- `bin/estate-memory-install --check` exits **1** and prints thirteen `MISSING` lines — pipelines,
  tools, workloads, cluster, runtime, mcp, sentinel, router, heartbeat, pager, graph, channels —
  plus nine `ok`, including `ok gemini` for a binary that is not installed. This is the only check
  in the estate that refuses when two lists disagree, which is why section 5 builds on it.
- `sovereign/engine/runners.py` registers exactly `['ask', 'burn', 'echo', 'llm', 'sleep']`
  (measured by importing it). `claude` is not among them, yet the capability description of
  `estate_session_start` offers `claude`. Calling it with `claude` would reach a registry that does
  not know the name — the session plane cannot start a real harness at all.
- The live board reports **545 sessions in two runtimes** — `claude-code` 423 and `pi` 122 — and
  says `unreachable: []`. Counting the names the estate itself admits, that is **two of seven**, and
  the board is not saying so: a runtime with no rows and a runtime that does not exist look
  identical.

## 4. The thing that is already the right shape

One store is already harness-agnostic, and it is the one the founder already looks at. The session
table in `catalog/estate.db` (machine-local and gitignored, but the exact table the deployed backend
reads through `_estate_db_path`) is:

    id, provider, model, created_at, metadata_json

with **no CHECK constraint on `provider`** (measured from the DDL). It holds 423 rows from one
harness and 122 from another, under the same schema, with no column added for either. This is the
seam: a new harness becomes visible by writing rows whose `provider` is its name, not by changing a
schema, a migration, or an enum.

The other three planes each give one piece for free:

- The **voice door** speaks anything that is a file in `~/.estate/intents/`.
- The **memory manifest's `--check`** is the only thing in the estate that fails loudly when a
  written-down list does not match the machine.
- **`bin/estate-runtime-sync`** already converges a runtime tree from `main` and has a
  `--from-checkout` mode that runs `estate-memory-install` against another tree — the mechanism for
  "the same content, deployed differently" that the router fix used.

What does *not* exist is any one of these being the authority for "what a harness is".

## 5. The smallest change that makes any harness assignable, anywhere

Five edits, in this order, each one failing loudly if the next is skipped.

**One registry.** Add a `harnesses:` block to `platform/estate/memory/runtimes.json` — the file that
already holds one entry per thing the estate runs — with, per harness: the name, how to install it,
how to start it, which environment it needs (the router URL and its `x-litellm-api-key` header are
the same for all of them), and `where: cloud | laptop | both`. This becomes the only place a
harness is *described*.

**One check that refuses.** Extend `bin/estate-memory-install --check` to compare that block against
the three lists that exist today — the TypeScript constant, `agent_jobs.HARNESSES`, and the
workflow's `options:` — and exit non-zero naming the list that disagrees, exactly as it already does
for the thirteen missing entries. A test in `tests/` then fails when the two agree only by accident.
The point is not tidiness: it is that a harness offered by the picker and not installed by the
workflow is a button that breaks a run.

**`where` becomes real.** Today the workflow is the only executor. Give the job path a target:
`cloud` keeps the existing `agent-job.yml`; `laptop` writes the same job row and hands it to the
executor door on this machine, where the harness environment already exists (all of them point at
`http://127.0.0.1:4000`). The two stores stay separate — a GitHub job and a laptop session never
need to talk to each other — and the board keeps one projection over both, which it already does.

**One intent for the voice.** `agent.dispatch` with `harness`, `task`, `where` and cost as
arguments. It refuses a harness that is not in the registry, and because the catalogue globs the
intent directory it is speakable the moment the file lands — no code change on the voice side. That
is the whole "swap from Face" story: *"pi, take this on the laptop"* becomes a sentence against one
file.

**Proof, not a green gate.** The change is operational when `/fleet` shows one row per harness with
the environment it would run in, and a real job on a **third** harness — opencode, which is
installed and doing nothing — runs end to end on the laptop and appears live on the board. Until
that row exists, this is a design, not a capability.

What it deliberately does not do: no live handoff of a session from one harness to another (a
session is a process; the unit of assignment is the next piece of work, not the current one), and no
new agent — the estate already has eight names and needs one list.

## 6. Defects found while measuring, each with its evidence

1. **The board under-reports and says it is healthy.** `/sessions` returns two runtimes and
   `unreachable: []` while five admitted names have no rows. Evidence: the API response and the
   distinct `provider` values in `catalog/estate.db`.
2. **The session plane cannot run a harness.** `runners.REGISTRY` = `ask, burn, echo, llm, sleep`;
   the capability advertises `claude`. Evidence: the import above.
3. **`estate_capabilities` describes tools that no longer exist.** It lists thirteen raw tools
   including `estate_executor`, which `AGENTS.md` §7 says is deleted. Documentation that describes a
   deleted boundary is worse than no documentation.
4. **The `no-harness-folders` guard cannot see the tree it most needs to.** `find` inside
   `~/Documents/code` returns "Operation not permitted" — a macOS TCC grant the guard does not have,
   so `.claude` folders exist in that tree. Evidence: the guard's own stderr.
5. **Gemini is asserted and not installed** (section 1), and `--check` calls it `ok`.
6. **Three copies of the harness list, compared by nothing** (section 2).
7. **Cluster agents that are not running** — `agent-workforce` Pending 28m, `resident-brain` 0
   replicas, three Deployments with no endpoints.

## 7. What this document does not answer

It does not measure what each harness costs per task, because the router bills most of them at zero
and the real cost is wall-clock on this machine. It has not run a third harness end to end, so
"opencode works" is an inference from it being installed, not a measurement. And it changes nothing:
no file outside this document was written, so the estate behaves exactly as it did before you read
it.
