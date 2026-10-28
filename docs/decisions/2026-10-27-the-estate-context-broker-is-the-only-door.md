# The estate's context broker is the only door, and gortex is the only engine

**Date:** 2026-10-27
**Status:** accepted (founder, 2026-10-27 — *"we don't need to land a lane in order to gather context for a question to be answered; common sense is lacking."*)
**Claim:** [idp#7262](https://github.com/chidionyema/idp/issues/7262) (lane `lane/estate-context-engine`)
**Spec:** [`docs/specs/2026-10-26-context-compiler-and-execution-gateway.md`](../specs/2026-10-26-context-compiler-and-execution-gateway.md)
**Evidence:** `bin/estate-context-gate` · `tests/test_estate_context_gate.py` · `.github/workflows/context-index.yml` · `platform/mcp/estate-context-broker.yaml`
**Completes:** [`2026-10-26-one-context-compiler-and-one-execution-gateway.md`](2026-10-26-one-context-compiler-and-one-execution-gateway.md) — points 1, 2 and 4, which were decisions without a door.

## Context

The 2026-10-26 record decided that the estate would have one context compiler and one
intelligence broker, and that the estate's existing layers would be reused rather than
rebuilt. What it did not have was a door, and the gap was measurable from the estate's own
ledger (`bin/capability-index decisions`, 2026-10-26): **1,927 MCP door calls across 122
sessions, of which 484 (25.1%) were `estate_show`** — a quarter of everything the estate's
agents did at its door was the agent asking the door how to use the door.

Meanwhile the compiler, as first written, was a **second retrieval system**: a hand-written
`rg` + TF-IDF ranker inside `bin/estate-context-compile`, ranking the tree in the repository
while the estate's context engine (gortex v0.64.11, Apache-2.0) was doing exactly that job
one layer down, better, with symbol resolution and impact analysis attached. AGENTS.md §6
calls a second copy of a layer a stitch, and a stitch is deleted in the same change.

Measured about the engine, on the laptop, 2026-10-27 (the numbers this record rests on):

| Fact | Measurement |
|---|---|
| `gortex call smart_context --json` answers | ~2.4 s, with `working_set` (ranked files), `relevant_symbols`, `files_to_edit`, `blast_radius`, `related_test_files`, `retrieval_note`, `etag` |
| `gortex repos --json` | per repo: `head_commit`, `indexed_commit`, `stale`, `freshness_scope` — the engine's OWN freshness line |
| `gortex tools list --format json` | classifies every tool `mutating: true/false` — the engine's own read/write boundary |
| `gortex tools describe smart_context` | **does not know it** — the tool list and the describe surface disagree, so the list is the authority |
| Indexing this repository | minutes of CPU; the node's whole request budget is 1.8 CPU (decision 0034) |
| Engine paths | prefixed with the checkout's directory name, so they must be normalised to repo-relative before they mean anything |

The founder's ruling of 2026-10-27 cut the ceremony in the right place: **gathering context
is not the thing that needs a claim; landing code is.** The lane exists for the door, the
policy, the CI and the cluster work — not for the act of asking a question.

## Decision

**The estate has one context engine, one compiler that is a client of it, and one door that
is the broker. The engine is private. The index is built in CI. The rule is checkable.**

1. **One engine: gortex v0.64.11.** It is the estate's only retrieval, ranking,
   symbol-resolution and impact engine. It is pinned by the SHA-256 of the release tarball
   (`gortex-engine.Dockerfile`), not by a tag: a tag can be moved, a digest cannot.

2. **The compiler is a client, never a ranker.** `bin/estate-context-compile` asks the engine
   and translates the answer; it does not score anything. The hand-written TF-IDF ranker was
   **deleted, not debugged**. What the compiler owns is the *budget and the order*: it keeps
   the engine's order (reordering it would be a second ranker wearing a plan's clothes),
   filters to the measured token budget (tiktoken `cl100k_base`), **names what it dropped**,
   lists the impact nodes it did not cover, and hashes the ordered items into `plan_hash` so
   two builds of the same tree are byte-identical.

3. **One door: the broker.** `platform/estate/context/broker.py` is the only public way to
   ask the estate's context anything. The engine is a **private sidecar in the broker's pod,
   bound to `127.0.0.1`, with no Service, no Ingress and no route of any kind** — a separate
   Deployment would need a Service to be called, and a Service is a route. The isolation is
   the network namespace, not a policy that can be misconfigured.

4. **The read-only surface is the engine's, and it is checked against the engine's own
   catalogue.** The broker allows 18 read-only tools and refuses 18 mutating ones, and the
   two lists are disjoint by construction. The mutating list is **measured**, not asserted:
   `gortex tools list --format json` classifies every tool, and the estate's list is aligned
   with that classification. On 2026-10-27 the alignment check found a real falsehood —
   `batch_symbols` was in the estate's mutating list and the engine classifies it read-only —
   and the list was corrected. A refusal that misdescribes a tool is worse than a short
   refusal, because a client acts on the reason.

   The catalogue is **not** the whole truth, and the estate does not pretend it is: it is
   preset-filtered (on the laptop daemon `gortex tools list` publishes 47 of the ~193 tools
   the engine can serve), so a name's absence from it proves nothing. The engine is the
   authority, and the estate asks it. On 2026-10-27 that found a second falsehood:
   `affected` was on the read-only allowlist, and `gortex call affected` answered
   *'unknown tool "affected"'* — a name the estate had invented, promising clients a tool
   the engine does not have. It was removed, and the gate now asks the engine about every
   name on the allowlist (check 6 below), so an invented name cannot come back unnoticed.

5. **The index is built in CI and shipped as an artifact.** `.github/workflows/context-index.yml`
   builds the index for the commit that landed, **proves the engine's own freshness line says
   `indexed_commit == GITHUB_SHA` and `stale == false`**, proves the engine answers a real
   question from the index it just built, writes the manifest the broker reads as its ground
   truth, checks the artifact fits the 2 GiB volume the pod mounts, publishes it to
   `oci://ghcr.io/chidionyema/idp/context-index` under its commit and as `:latest`, and signs
   it with cosign. The pod pulls the artifact and **opens** the index; it does not build one.
   An index that cannot prove its commit is not published, because the broker's `STALE_REJECT`
   must never be guarding a fiction.

6. **The rule is checkable, and the check can fail.** `bin/estate-context-gate` admits the
   context plane only if: there is one ranker; the read-only surface agrees with the engine's
   catalogue; the engine is private (loopback, no published port, no route anywhere under
   `platform/`); the policy still refuses a stale index, an unproven index, a path outside
   the claim, a mutating tool and an over-budget answer; the plan keeps the engine's
   order, fits its budget and is deterministic; and **every tool the broker allowlists is a
   tool the engine actually has**. `--self-test` runs every check against a
   deliberately broken input and **requires it to fail** — a gate that cannot fail is not a
   gate (AGENTS.md §3). The gate is a rung of `bin/idp-ci`, so CI grades the plane.

7. **The laptop daemon is the fallback door; the cluster broker is the normal one.** The
   broker in the pod is the only holder of the engine's token, so a client that bypasses its
   own harness still meets the policy. The laptop daemon exists so a cluster outage does not
   disable every agent, and it is not where new capability is built.

## Alternatives rejected

| Alternative | Why not |
|---|---|
| **Keep the compiler's own ranker and add the engine beside it** | Two rankers answer the same question differently, and which one a client got is a coin flip. AGENTS.md §6: a second copy of a layer is deleted in the same change. |
| **Debug the TF-IDF ranker** | It was a second retrieval system, not a bug. The engine already does the job with symbol resolution and impact analysis attached. |
| **The engine as its own Deployment with a Service** | A Service is a route. Anything in the cluster that can reach the address can reach the engine, and the "private" engine is private only by convention. |
| **Expose the engine through the gateway directly** | Then the policy is a client-side convention, and the client is the thing the estate does not control. The door must be the broker. |
| **Index inside the pod** | Minutes of CPU per restart against a node budget of 1.8 CPU (decision 0034). The index is a build artifact; the pod serves it. |
| **Let the broker trust the estate's own hand-written tool lists** | The engine classifies its own tools. A hand-written list drifts, and when it drifts the refusal lies. The alignment is measured against the live catalogue. |
| **A gate with no broken fixtures** | A gate nobody has seen fail is a gate nobody can trust. The self-test and the pytest fixtures are the proof. |

## Consequences

**Positive.**

- The estate has one context layer, and it is checkable rather than stated.
- The compiler's cost is bounded and its order is the engine's, so two agents asking the same
  question get the same source set.
- A client that bypasses its harness still meets the policy: the engine is unroutable.
- The index carries its own proof — the engine's freshness line, a signed artifact, and a
  manifest the broker reads as ground truth.

**Negative, and accepted.**

- The engine's catalogue is a **live dependency of the policy**. When the daemon is not
  reachable, the alignment check degrades to a **warning that names the reason**; it never
  passes silently as "aligned". The estate's CI cannot run the engine's daemon, so the live
  check is a laptop-and-cluster duty, and the gate says so in its own output.
- The same is true of the existence check (check 6): asking the engine about every
  allowlisted name costs **eighteen engine calls, about twenty seconds** on the laptop and
  nothing at all where there is no engine. It is a warning when the engine is not there, and
  a failure when the engine says the name is unknown.
- `plan_hash` makes the plan reproducible but also makes a changed engine answer a changed
  plan. That is the point: a plan that is not reproducible cannot be compared.
- The broker is a **single point of failure** for context. It must fail **closed for
  authorization** (`UNPROVEN_INDEX`, `STALE_REJECT`, `ENGINE_UNREACHABLE`) and **open for
  observation** (the refusal names the door that would work).

**Risks to watch.**

- The engine is a third-party binary the estate did not write. The pin is by digest, the
  image is built and scanned by the estate's own pipeline, and the broker never trusts the
  engine for anything but content — the policy is the estate's own code.
- The read-only allowlist and the engine's catalogue must move together. The gate catches the
  disagreement on a machine with the daemon; a **change to the engine's version without a
  change to the allowlist** is the case that only the live check sees.
- The allowlist is the estate's promise to its clients, and a promise the engine does not
  keep is a broken door. The existence check (check 6) is what keeps that promise honest,
  and it is the check that has already caught one: the estate had promised a tool called
  `affected` that the engine does not have. Anything added to the allowlist must be a name
  the engine answers to.

## Links

- Spec: `docs/specs/2026-10-26-context-compiler-and-execution-gateway.md`
- Prior decision: `docs/decisions/2026-10-26-one-context-compiler-and-one-execution-gateway.md`
- The door: `platform/estate/context/broker.py`, `platform/estate/context/server.py`
- The pod: `platform/mcp/estate-context-broker.yaml` (broker + private engine, one pod)
- The engine: `gortex-engine.Dockerfile` (gortex v0.64.11, pinned by SHA-256)
- The compiler: `bin/estate-context-compile`
- The index: `.github/workflows/context-index.yml`
- The gate: `bin/estate-context-gate`, `tests/test_estate_context_gate.py`
- The engine: <https://github.com/zzet/gortex> (Apache-2.0)
