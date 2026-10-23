# What a harness is here, and every one the estate has

Founder, my last version of this was wrong in a way worth naming first: I counted the interactive
coding CLIs — `claude`, `pi`, `opencode`, `codex`, `gemini` — and called that "the harnesses". You
asked about firecracker, zeredge and agent-workforce, and those are not more of the same thing. They
are the substrate the work runs on, the gateway it is billed through, and the crew that runs it. So
this version starts with the definition, then walks every layer. Every line is measured, and where a
line comes from the estate's own inventory of 2026-09-23 (`docs/synthesis/factory-inventory.md`)
rather than from today, it says so.

## 1. The word means three different layers, and the estate uses it for all three

**The substrate — where the work is isolated while it runs.** `platform/executor/sandbox.py` is the
dispatcher, and its own docstring names the ladder: `firecracker -> gvisor -> docker -> temp_tree`.
It reports what it actually picked, as `ISOLATION_KIND`, rather than a baked-in string. Beside it:
`factory/sandbox.py` has a `SANDBOX_RINGS` table naming `subprocess`, `kronos.ring0` (whose command
is the literal placeholder `firecracker-run`), `kronos.ring1` and `docker`; and `kronos` (in
`~/Documents/code/kronos`, which the estate's inventory counts as Rust, 23 source files and 5
crates-of-rings — "a multi-ring isolation kernel for running untrusted AI agents in production") is the spec: ring0 KVM/firecracker-like, ring1
Wasmtime+WASI, ring2 eBPF, ring3 vsock egress with Vault, ring4 an append-only ledger.

**The runtime — what executes the agent's turns.** The CLIs are one family of these. The others are
not CLIs at all: `agent-workforce` is a crewAI crew that runs as a CronJob every 15 minutes against
the `ghcr.io/chidionyema/agent-workforce:main` image; `agent-foundry` is "a factory and its runtime
that lets someone order an army of specialised micro-agents"; `hermes-agent-gateway`,
`otto-gateway`, `otto-golden` and `mcp/agentgateway` are the long-running agent processes; `studio`
(`~/.estate/studio/studio.db`, `--serve-only`) is a resident supervisor.

**The door — how work is handed in.** Fleet's panel with its two-item constant; the
`agent-sandbox` workflow, which is the most complete door in the estate and the only one that names
its harnesses with the credentials each needs (`options: [claude-code, pi]`, plus
`CLAUDE_CODE_OAUTH_TOKEN` for one and `SEED_MINIMAX_API_KEY` for the other); the executor intent
door; the Temporal session plane; and the voice catalogue, which speaks any file in
`~/.estate/intents/`.

A change that swaps "the harness" can mean any of the three, and they are not interchangeable. That
is why the earlier version read as if it had missed the point.

## 2. Measured now: the substrate that is actually being used is the one with no isolation

On this laptop, `detect_backend()` from `platform/executor/sandbox.py` returns **`temp_tree`** — the
module's own words for it are "always available, never the spec, never silently chosen". The ladder
has no rung above it here, and this is what each rung measured today:

- `firecracker`: `/dev/kvm` absent and no `firecracker` binary. On macOS this rung is unreachable by
  construction, so the spec path has never executed anything on this machine.
- `gvisor`: no `runsc` binary locally.
- `docker`: `docker` resolves to `~/.rd/bin/docker`, and `docker ps` fails with "failed to connect to
  the docker API at unix:///Users/roseonyema/.rd/docker.sock … no such file or directory". The
  Rancher Desktop engine is **not running**, so the probe's `docker info` exits non-zero and the
  dispatcher moves on.
- `temp_tree`: chosen.

Which means every job the executor ran today — including every command behind this document — ran
with no isolation boundary at all, and nothing announced it. On the cluster it is the mirror image:
RuntimeClass `gvisor` is registered (45 days old) and **0 pods carry a `runtimeClassName`**. The one
substrate the estate has actually hardened is the one nothing uses.

`kronos` is not deployed anywhere: searching the idp tree for it finds the dispatcher, the factory
rings table, an intent wrapper for its `harv` crate (`platform/estate/intents/harv.yaml`, which runs
fetched parts in wasm deny-mode and shelves them with signed evidence in ring4), and synthesis docs.
No workload, no pod, no image in the cluster.

## 3. What is running on the cluster right now

- `agent-workforce` CronJob, `*/15 * * * *`: the current job is `Running 0/1` after 21 minutes and
  the previous one is `Failed`. A crew that never starts is not a harness that works.
- `hermes-agent-gateway` 1/1, `mcp/agentgateway` 2/2, `otto-gateway` 2/2, `otto-golden` 2/2 — these
  are up, and they are the estate's live agent processes.

So of the runtimes, four are running and one (the crew) has been stuck for weeks' worth of
15-minute slots.

## 4. The rest of the zoo, one line each, and what it is not

- **zeroedge** (`~/Documents/code/zeroedge-repo`, 27 Python files by the inventory's count): "a provider-agnostic, drop-in
  LLM cost-optimization gateway" — canonicalise, compress, cache, budget, route. It is classified
  `incubating` in `docs/synthesis/factory-inventory.md` and "off unless `ZEROEDGE_URL` is set". It is
  **not** a harness; it is a second cost/routing layer next to the platform's own router, which is
  the "one of each layer" question in `AGENTS.md` §6, and I am not resolving it here.
- **agent-workspaces** (`~/Documents/code/agent-workspaces/task-*`): per-task worktrees, each with
  its own `AGENTS.md` and `sovereign/verifier.py` — the disposable copy of production an agent works
  in. That is a substrate too, at the git layer rather than the kernel layer.
- **vcluster shadow environments** (79 files mention vcluster; `platform/sandbox/vcluster/`,
  `.github/workflows/demo-sandbox.yml`, `bin/idp-sandbox-sweep`): virtual clusters as the isolation
  boundary for cluster-side work.
- **gVisor sandbox namespace** (`platform/edge/otto-gvisor-sandbox-namespace.yaml`, 91 files mention
  gVisor): declared, and per section 2, used by nothing.
- **factory gates** (`factory/sandbox.py`): the ring table that decides which isolation a *gate*
  runs under, with `UNKNOWN_SANDBOX_<name>` as a refusal rather than a default.

## 5. The corrected swap: assignment must name the substrate, not only the agent

The earlier design (one registry, one check that refuses, `where: cloud | laptop`, one voice intent)
was right about the module that assigns work and wrong about what gets assigned. The registry entry
now needs three fields, because a harness on its own does not say where or how it runs:

    name: pi
    where: laptop | cloud | both
    isolation: temp_tree | docker | gvisor | firecracker

`isolation` is read from the substrate that will actually run it, so a job that asks for
`firecracker` on this laptop is refused with the reason (`/dev/kvm absent`) instead of quietly
running in `temp_tree`. The check that refuses compares four lists now, not three: Fleet's
TypeScript constant, `agent_jobs.HARNESSES`, `agent-sandbox.yml`'s `options:`, and the registry —
plus the substrate ladder, so a harness offered without a reachable isolation is a refusal at the
door rather than a silent fallback.

Nothing about this is operational. It is a design with the two facts that make it necessary now on
the record: the laptop has no isolation rung, and the cluster's hardened rung has no users.

## 6. Defects, each with the evidence that found it

1. **Every laptop job runs unisolated, silently.** `detect_backend()` returns `temp_tree`; `/dev/kvm`,
   `firecracker`, `runsc` all absent; `docker ps` → socket missing. No warning, no log line.
2. **The hardened substrate has no users.** RuntimeClass `gvisor` exists, 0 pods request it.
3. **The spec path has never run.** Firecracker is named as the architecture in
   `platform/executor/sandbox.py` and as `kronos.ring0` in `factory/sandbox.py`, whose command is a
   placeholder string `firecracker-run`.
4. **The work crew does not start.** `agent-workforce` current job `Running 0/1` 21m, previous
   `Failed`.
5. **Four copies of "which harnesses exist", compared by nothing**: the Fleet constant,
   `agent_jobs.HARNESSES`, `agent-sandbox.yml` `options:`, and the registry that does not exist yet.
6. **A second routing/cost layer sits beside the platform's** (`zeroedge`), classified incubating and
   switched off, and nothing decides whether it or the platform router is the one.
7. **This document's predecessor was wrong** and is replaced by it: it measured the CLIs and called
   them the harnesses.

## 7. What I did not measure

I have not run a single job on firecracker or gVisor, here or on the cluster, so I cannot tell you
what they cost or whether they work — only that nothing currently uses them. I did not bring the
Docker engine up to test the `docker` rung, because starting a container runtime is a decision about
this machine, not a measurement. And I have not audited `kronos`' rings beyond reading their
documentation and their call sites, so its state is "incubating, never deployed", not "works".
