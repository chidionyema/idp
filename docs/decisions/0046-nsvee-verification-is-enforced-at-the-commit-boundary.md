# 0046 — NSVEE verification is enforced at the commit boundary

- **Date:** 2026-10-28 (decision taken 2026-10-27; landed 2026-10-28)
- **Claim:** idp#7298 · agent `estate-agent`
- **Gate:** `tests/test_nsvee_estate_enforcement.py` and `tests/test_nsvee_verify_door.py` -- this
  ADR's contract is executable, and the tests fail when the code and this document drift apart
- **Checker:** `python3 platform/estate/nsvee_enforcement.py --check` — exits 1 today and names
  the surfaces that do not enforce the receipt yet
- **Tickets:** idp#7263 (open — NSVEE productization), idp#7265 (merged — the productized
  engine), idp#6989 (claim rungs)
- **Founder's ruling (2026-10-27):** NSVEE is integrated estate-wide and mandatory. JEV is
  explicitly **not** a requirement for it, and stays out of the enforcement path.
- **Status (2026-10-30):** Phase 1 landed. Phase 2's API gap (D5) and the shared door (D8) are
  delivered: `nsvee.verify(artifact, tests) -> VerificationReport` exists, and the intent
  `nsvee.verify` makes it reachable by every estate runtime. The three enforcement surfaces
  below -- pre-commit, CI verification, merge gate -- are still unwired, so the estate does not
  yet *require* a receipt; it can now *produce* one on demand. The remaining gap is named by
  the checker, not by prose.

## Context

The founder's expectation is simple: an artifact that changes behaviour is verified by NSVEE
before it lands, everywhere, for every agent. What exists is narrower, and the difference is
worth stating exactly rather than rounding up.

### What NSVEE is today (measured, `nsvee/engine.py` at `205c3f196`)

This section is a measurement, pinned to a commit. The API gap it describes was closed on
2026-10-30 (D5, D8); the sections below say so where they are no longer true.

Sources are named by **symbol, not by line number**: a line number rots the next time the file is
edited, and a rotted citation is a false one. `tests/test_nsvee_estate_enforcement.py` reads every
symbol named here out of `nsvee/engine.py` and fails if one is gone, so this table cannot rot
silently.

| tier | what it does | where |
|---|---|---|
| 1 | `formalize(prompt)` turns a prompt into a `FormalSpec` with machine-checkable invariants and named ambiguities. An ambiguity ends the run as `HUMAN_INPUT_REQUIRED` — no code is emitted | `NSVEE.formalize`, `FormalSpec` |
| 2 | constrained JSON generation of `VerifiedTaskOutput{plan_steps, code_implementation, unit_tests, dependencies}` through a model-agnostic `Router` (`LiteLLMRouter`, `FakeRouter`) | `VerifiedTaskOutput`, `Router`, `LiteLLMRouter`, `FakeRouter` |
| 3 | `_verify(out, timeout_s)` runs the generated code **and** its tests in a sandbox — `DockerRunner` (no network, read-only filesystem) with `RlimitsRunner` as the fallback — and returns verdicts `PASS`, `FAIL`, `TIMEOUT`, `OOM`, `SANDBOX_ERROR`. One `PASS` is not a verdict: the run is repeated (`budgets.confirmation_runs = 1`) to defeat flakes | `NSVEE._verify`, `Verdict`, `DockerRunner`, `RlimitsRunner` |
| 4 | orchestration and feedback: `budgets.max_retries = 4`, `max_wall_clock_s = 600`, feedback capped at `max_feedback_chars = 4000` with the last `max_feedback_history = 3` failure reports | `Budgets`, `NSVEE.run` |

The terminal statuses a `PipelineReport` can carry are exactly: `VERIFIED`,
`HUMAN_INPUT_REQUIRED`, `EXHAUSTED`, `SANDBOX_DEGRADED`, `FORMALIZATION_ERROR`
(`PipelineReport.status`).

`post_verify(out)` is the seam for an independent oracle — "check the artifact against something
the model did not author". The base implementation returns `None`: it is a hook, not an
implementation (`NSVEE.post_verify`).

### The gap that decides this ADR

**There is no verify-only entry point.** The public surface of `NSVEE` is `NSVEE.formalize`,
`NSVEE.post_verify` and `NSVEE.run`. `NSVEE._verify` is private and takes a `VerifiedTaskOutput`
— the object the generation pipeline itself produced. `NSVEE.run()` always starts from a prompt
and generates.

So NSVEE can verify an artifact it generated. It cannot, today, verify an artifact that arrived
from anywhere else: an agent's edit, a human's commit, a dependency bump.

That single fact decides the shape of the enforcement, and it also kills one tempting design: a
commit boundary cannot ask "NSVEE, verify this diff", because no such call exists. Regenerating
a *different* artifact from a prompt at commit time and calling that a verification of the
committed tree would be theatre — it would prove that the model can write a passing test, not
that the committed code passes. The estate does not grade a proxy (`AGENTS.md` §10).

**Closed 2026-10-30 (D5, D8).** `nsvee.verify(artifact, tests) -> VerificationReport` now
exists as a public, model-free entry point, and the intent `nsvee.verify` puts it behind the
one door every estate runtime already uses. The commit boundary can therefore ask the right
question now; what it does not yet do is ask it on every commit.

### Expectation against reality

| the founder expects | what the tree measures |
|---|---|
| NSVEE verifies every agent artifact, estate-wide | no estate surface references NSVEE at all: `git grep -l -i nsvee origin/main` outside `nsvee/`, `docs/` and `tests/` returns nothing. pi *development* sessions have exercised the engine directly (`import nsvee`, `python3 -m nsvee` appear in 8 session transcripts under `~/.pi/agent/sessions/`), but no runtime surface -- intent, MCP tool, CI job -- calls it. An agent today reaches it only by hand-writing Python against the library (until 2026-10-30: the `nsvee.verify` intent, D8) |
| the verification is automatic | nothing invokes it. There is no receipt, no gate, no verdict bound to a change |
| an agent cannot ship unverified code | the commit path runs ruff format, ruff check, tsc, shellcheck and yamllint (`.githooks/pre-commit`) and CI runs the fast gate. None of those verify semantics |
| there is a verdict per change | there is a `PipelineReport` per *run*, unbound to any commit, tree, or artifact digest |

## Decisions

**D1. Two tiers, both mandatory, at two different doors.**

- **Tier A — generation.** An artifact produced by an estate generation surface (an intent or an
  MCP generation tool) comes out of NSVEE's pipeline. Only a `VERIFIED` result may be handed to
  a caller. A non-`VERIFIED` result is returned *as* a non-`VERIFIED` result — `HUMAN_INPUT_REQUIRED`,
  `EXHAUSTED`, `SANDBOX_DEGRADED`, `FORMALIZATION_ERROR` — never dressed up as a finished artifact.
- **Tier B — binding.** Every commit that changes behaviour carries a **receipt**: a small
  record binding the verified artifact to the exact commit. A commit is verified when the
  receipt's commit and artifact digest match the tree being committed.

**D2. The chokepoint is the commit boundary — the pre-commit gate and the CI receipt — not the
harness, and not the model router.**

The reasoning is universality. A commit can be made by an agent, by the founder, by a bot, or by
a tool that never touches the pi extension, the Claude Code harness, or any harness at all. Only
the commit/merge path is universal, so only it can make the class impossible rather than
merely unlikely.

- The **pre-commit hook** is the early, cheap refusal: it catches the unverifiable change
  before it becomes a commit. It is a guard, and a guard that can be skipped (`--no-verify`) is
  a guard, not a boundary.
- The **CI receipt** is the mandatory one: CI verifies the tree, publishes a receipt bound to
  that commit, and the merge gate refuses a commit without one. This is where the class becomes
  impossible.

What is explicitly *not* an enforcement point, and why:

- **The model router** (`https://llm.${ESTATE_ZONE}`, the laptop route as fallback) routes model
  calls. It does not see files, trees, or commits. Routing a decision is not enforcing a verdict.
- **The executor intent library** gates the actions an agent takes *through intents*. `git
  commit` reaches the tree by many paths, and the executor is not on all of them.
- **Harness-specific hooks** (the pi extension, the Claude Code harness) are advisory. They
  reduce the number of bad commits; they cannot make the class impossible, because they are not
  present when the founder edits a file.

The consultant's dual placement is adopted for exactly this reason: generation is where
correctness can be *produced*, the commit boundary is where it can be *required*.

**D3. The receipt is the binding artifact, and it does not live inside the commit.**

A receipt names the commit it describes. A file inside that commit changes the tree, which
changes the sha, which invalidates the receipt. So the receipt travels with the CI run for that
commit, and the merge gate reads it from the run. The contract is in
`platform/estate/nsvee_enforcement.py`:

```json
{
  "schema": "estate.nsvee.receipt/1",
  "commit": "<40 hex sha>",
  "artifact_digest": "<64 hex sha256 of the verified artifact>",
  "verifier": "nsvee",
  "status": "VERIFIED",
  "paths": ["path/to/artifact.py"],
  "report": {},
  "oracle": ""
}
```

`artifact_digest` is the sha256 over the changed paths (path, then the sha256 of its bytes) or
over the whole tree, depending on what was verified. It is what makes the receipt a binding
rather than a decoration: change a byte and the digest changes. `paths` names the scope the
digest covers -- `null` means the whole tree -- and the checker honours the scope the receipt
claims, never a wider one (D8).

**D4. Only `VERIFIED` is a pass. The gate fails closed.**

`HUMAN_INPUT_REQUIRED`, `EXHAUSTED`, `SANDBOX_DEGRADED` and `FORMALIZATION_ERROR` are the gate
*failing*, not passing softly. A missing receipt is a failure. An unavailable verifier is a
failure. There is no "skip" and no "assume verified".

**D5. NSVEE must gain a verify-only entry point before Tier B can judge arbitrary edits.**
(delivered 2026-10-30)

`nsvee.verify(artifact, tests) -> VerificationReport`: the Tier-3 machinery (`_verify` promoted
to public) plus the oracle seam (`post_verify`), so the commit boundary can verify code it did
not generate. Until that exists, Tier B can only bind the receipt of a *generation* run to the
commit that carries that generated artifact — which covers the Tier A path completely, and
leaves hand-edited code unbound. That is the honest limit of Phase 2, and the falsifier for it
is the API's existence plus a test that verifies an artifact NSVEE did not write.

**D6. JEV stays out of the enforcement path.**

JEV is the estate's one decision layer (ADR 0030) and it stays. It is not a requirement for
NSVEE enforcement, and it is not on the commit path, for three reasons:

1. A decision layer can *escalate*. `escalated=true` means "the layer was consulted and could not
   answer" (ADR 0030's escalation table). A gate that escalates is not a gate: it turns a
   missing verdict into a shrug.
2. JEV is a service call with a vendor dependency, reached through the estate router (LAW 34:
   the router holds vendor keys, the laptop holds none — `docs/tickets/2026-09-26-ruthless-gateway.md`).
   The commit path must not gain a network dependency with a vendor timeout.
3. The verdict that binds a commit must be deterministic: sandbox verdicts and digests. JEV may
   be consulted to *choose the tier* (is this diff big enough for the full suite?). It never
   decides whether a commit is verified.

**What this change does to `jev.decide` — and does not.** Keeping JEV out of the enforcement
path is a statement about NSVEE, not a demotion of JEV: JEV is already in estate use, and its
availability is not this ADR's business. What this change fixes is the *caller contract* of the
`jev.decide` intent, so that a future caller cannot read an escalation as a verdict:

- the context is a JSON-encoded **string** (the executor's argument schema requires string
  values), and the intent parses it and refuses anything that is not a JSON **object** before
  it is used;
- a malformed context is refused with a reason and a non-zero exit, never guessed at;
- `_fallback=jev_unavailable` with `escalated=true` is labelled as an escalation and is **not** a
  negative ruling;
- a typed answer carrying an inspectable decision identifier is a ruling; anything else is not.

The proof is `tests/test_jev_decide_context_contract.py`, including the case that proves the
repository's executor interpolation quotes the complete JSON context as **one** argument (six
array elements for three flag/value pairs, the context at `args[5]`) — so the trap is not
whitespace inside the JSON, and the contract says so instead of guessing.

**D7. The contract is executable, and the gap is named by the checker.**

`platform/estate/nsvee_enforcement.py` holds the receipt schema, the validation, and the list of
surfaces that must enforce it. `tests/test_nsvee_estate_enforcement.py` proves the contract, and
keeps this document honest: it fails if the engine's public surface, its terminal statuses, or
the surface list drift away from what is written here.

The surfaces this ADR requires — the same list the checker enforces, in a machine-readable form:

```json
[
  {"id": "pre-commit", "path": ".githooks/pre-commit", "markers": ["nsvee_enforcement"]},
  {"id": "ci-verification", "path": ".github/workflows/verifier.yml", "markers": ["nsvee_enforcement", "receipt"]},
  {"id": "merge-gate", "path": ".github/workflows/ci.yml", "markers": ["nsvee_enforcement", "receipt"]}
]
```

And the engine surface this ADR cites, in the same machine-readable form, so the citation is
checkable rather than decorative:

```json
{
  "engine": "nsvee/engine.py",
  "symbols": [
    "NSVEE.formalize", "FormalSpec", "VerifiedTaskOutput", "Router", "LiteLLMRouter",
    "FakeRouter", "NSVEE._verify", "Verdict", "DockerRunner", "RlimitsRunner",
    "Budgets.max_retries", "Budgets.max_wall_clock_s", "Budgets.max_feedback_chars",
    "Budgets.max_feedback_history", "Budgets.confirmation_runs", "PipelineReport.status",
    "NSVEE.post_verify", "NSVEE.run"
  ]
}
```

The markers are deliberately distinctive. The word "receipt" on its own was already in
`ci.yml` for unrelated reasons, and a marker a file satisfies by accident reports a surface as
enforced that enforces nothing — worse than reporting nothing.

**D8. The door is an intent, so every runtime reaches it the same way.**

D2 puts the *enforcement* at the commit boundary, because only that path is universal. But
universal enforcement and universal *reachability* are two different properties, and the second
one is what was still missing: every estate runtime -- pi, otto, the fleet page, claude, gemini,
cursor -- already has exactly one governed way to act, an intent in `~/.estate/intents` run by
the executor. A Python library call that each runtime has to wire up for itself is N
integrations, and the one nobody wires up is the one that matters.

So the door is:

| | |
|---|---|
| name | `nsvee.verify` |
| intent | `platform/estate/intents/nsvee.verify.yaml` |
| script | `platform/estate/libexec/nsvee-verify.py` |
| engine entry point | `nsvee.verify(artifact, tests) -> VerificationReport` |
| receipt | `estate.nsvee.receipt/1` -- the contract in `platform/estate/nsvee_enforcement.py` |
| exit | 0 only when the verdict is `VERIFIED`; 1 when the artifact is not verified; 2 when the door could not run |

Five properties make it a door and not a helper:

1. **Model-free.** The verdict comes from executing the artifact in the sandbox, not from
   asking anything. It costs no tokens, depends on no router, and cannot be flattered by a
   model that wants to agree. This is what makes it usable as a gate rather than an opinion,
   and it is why it does not need JEV (D6).
2. **Same engine, same verdicts.** The door calls the Tier-3 machinery the pipeline uses, with
   the same confirmation runs (a `PASS` is re-run, so a flake is not mistaken for a proof), and
   it reports the receipt's own statuses. One engine, two entry points -- not a second verifier.
3. **Fail-closed.** A failing artifact, a broken sandbox and a receipt that cannot be written
   are all failures. There is no "skip" and no "assume verified" (D4).
4. **The receipt binds, and it says what it binds.** The door writes the digest of what it
   verified, so a tampered artifact no longer matches the receipt
   (`check_receipt_against_tree`). The receipt is written *outside* the tree it describes -- a
   receipt inside the commit it names would change the tree it binds to -- and a request to do
   so is refused rather than answered with a receipt that is false the moment it is written.
   The binding is **scoped**: the receipt carries the `paths` it covers (the artifact and its
   tests), because a whole-tree digest of the estate's own checkout costs ~60 s -- measured,
   6,425 files, 288 MB, ~7 ms a file of open overhead -- which is more than the executor's
   entire budget. `--whole-tree` buys the stronger binding for a caller that has the time,
   which is what the CI surfaces will use; the receipt says which of the two it is, and the
   checker never widens a receipt's scope on its behalf.
5. **One integration, estate-wide.** `bin/estate-runtime-sync` stages
   `platform/estate/intents` and `platform/estate/libexec` from `origin/main` into `~/.estate`
   for every runtime, so one landed intent becomes live everywhere without a second wiring
   job per harness.
6. **One path rule.** Every path the door is given -- the tree, the artifact, the tests, the
   receipt -- is resolved the same way before it is compared with another. The tree is
   resolved, so an artifact that arrives through a symlink (macOS: `/tmp` is a symlink to
   `/private/tmp`) has to be resolved too, or the door refuses a verification it should have
   accepted. This is not a nicety: it was the door's first real refusal, measured below.

**What the door is not.** It is not a replacement for the pre-commit gate or the merge gate
(D2): it is the measurement those gates consume, and it is the one door an agent can call on
demand -- for the founder's own check, and for any runtime that wants to verify before it hands
work over. The three surfaces below still have to be wired for the receipt to be *required*
rather than *available*.

*Falsifier:* `tests/test_nsvee_verify_door.py` -- the door runs, writes a receipt the contract
accepts, refuses a failing artifact (exit 1) while still leaving the evidence, breaks its
binding when the tree is tampered with, refuses to write a receipt inside the tree, and the
intent that names it exists in the estate's catalogue.

## The gap, stated plainly

| | founder's expectation | today's reality | what closes it |
|---|---|---|---|
| enforcement point | the commit boundary, estate-wide | no surface calls NSVEE | D1/D2 + Phase 2 |
| verification of arbitrary edits | any change can be verified | NSVEE only verifies what it generated; `run()` always regenerates | D5 -- `nsvee.verify()` -- **closed 2026-10-30** |
| reachability | every runtime can verify | the only route was hand-written Python against the library | D8 -- the `nsvee.verify` intent -- **closed 2026-10-30** |
| proof per change | a verdict bound to the change | a `PipelineReport` per run, unbound to a commit | D3 -- the receipt -- the door writes one on demand; the surfaces do not yet require it |
| the gate's behaviour | refuses what is unverified | no gate exists | D4 + Phase 2 |
| generation path | generation surfaces produce verified artifacts | generation is not routed through NSVEE | D1 Tier A — Phase 3 |

## Phases, each with a falsifier

**Phase 1 — this change.** The contract, the checker, the executable proof, the ADR. No surface
is wired yet. *Falsifier:* `python3 platform/estate/nsvee_enforcement.py --check` exits 1 and
names `pre-commit`, `ci-verification`, `merge-gate`.

**Phase 2 -- the binding.** `nsvee.verify()` (idp#7263) -- **delivered 2026-10-30**; the shared
door `nsvee.verify` (D8) -- **delivered 2026-10-30**; the pre-commit gate, the CI job in
`.github/workflows/verifier.yml` that verifies the tree and publishes the receipt, and the merge
gate in `.github/workflows/ci.yml` that refuses a commit without one. *Falsifier:* the checker
exits 0, and a CI run on a commit with no receipt is red -- proved by running it, not asserted.

**Phase 3 — Tier A.** The estate's generation surfaces return only `VERIFIED` artifacts, and a
non-`VERIFIED` result is visible as such on the surface that produced it. *Falsifier:* a
generation surface that hands back an `EXHAUSTED` artifact is a failing test.

## Rejected alternatives

- **Enforce in the harness** (pi extension, Claude Code hooks). Not universal; a commit made
  without the harness is unverified and unnoticed. Advisory only.
- **Enforce in the model router.** The router sees calls, not trees. It is where cost and
  identity are owned (ADR 0039), not where artifacts are judged.
- **Enforce in the executor door.** The door gates actions taken *through intents*. `git` is
  reached many ways; the door is not on all of them.
- **Let JEV arbitrate a commit.** Escalation is a legal outcome of a decision layer; a gate
  must fail closed (D6).
- **Regenerate at commit time and call it verification.** It verifies a different artifact than
  the committed one. Theatre (D5).
- **Treat a green CI gate as proof of verification.** A green gate that ran lint is not semantic
  verification (`AGENTS.md` §3: "built" and "operating" are different facts).
- **Commit the receipt.** A receipt naming its own commit cannot live in that commit (D3).

## How to check this ADR right now

```bash
python3 -m pytest tests/test_nsvee_estate_enforcement.py tests/test_nsvee_verify_door.py \
  tests/test_jev_decide_context_contract.py -q
python3 platform/estate/nsvee_enforcement.py --check    # exits 1 today: the named gaps
python3 platform/estate/nsvee_enforcement.py --verify-receipt receipt.json --tree .
#   exits 0 only if the receipt's artifact digest is the digest of this tree

# the shared door, through the executor, exactly as any runtime calls it:
~/.estate/bin/estate-execute nsvee.verify artifact=path/to/artifact.py tests=path/to/tests.py repo="$PWD"
#   exits 0 and prints status=VERIFIED with the receipt path; exits 1 on a failing artifact
```

## The door's first real invocation (measured 2026-10-30)

The door landed as `e27de193a` (#7517) and `bin/estate-runtime-sync` installed it estate-wide
(`~/.estate/intents/nsvee.verify.yaml` and `~/.estate/libexec/nsvee-verify.py`, byte-identical
to `origin/main`). The first call through the executor -- the one a runtime makes -- was
**refused**:

```
[estate] intent=nsvee.verify  ticket=INTENT-20261030-041659-47c8080d
[step 1 / verify] python3 ~/.estate/libexec/nsvee-verify.py --artifact /tmp/nsvee-door-proof/calc...
  exit 2  (15888ms)
  stderr: nsvee-verify: the artifact and its tests must live inside the tree the receipt binds
          to (/private/tmp/nsvee-door-proof)
```

Root cause: the tree was resolved and the artifact was not, so on macOS -- where `/tmp` is a
symlink to `/private/tmp` -- an artifact under `/tmp` never matched the tree it was in. The
same rule was missing on the receipt's own path, which meant a receipt written into the tree it
describes was possible through a symlink. Fixed in `lane/nsvee-verify-path-fix` (property 6
above), with two regression tests that fail against the pre-fix door.

The lesson is recorded here because it is the law this door lives by: **a gate is proved by the
call the estate actually makes, not by the call the author imagined.** The unit tests passed
before the door was ever called by a runtime; the first runtime call refused.

## References

- `nsvee/engine.py` — the engine this ADR binds to
- `nsvee/__init__.py` -- exports `verify` and `VerificationReport` as the package's public door
- `platform/estate/intents/nsvee.verify.yaml`, `platform/estate/libexec/nsvee-verify.py` -- the
  shared door (D8)
- `tests/test_nsvee_verify_door.py` -- the proof of that door
- `platform/estate/nsvee_enforcement.py` — the receipt schema, the validator, the checker
- `platform/estate/intents/jev.decide.yaml`, `platform/estate/libexec/jev-decide.py` — the
  hardened JEV caller contract (D6)
- `tests/test_jev_decide_context_contract.py` — the proof of that contract
- `.githooks/pre-commit`, `.github/workflows/verifier.yml`, `.github/workflows/ci.yml` — the
  surfaces that must enforce it
- `docs/decisions/0030-jevlayer-unified-confidence-and-decision-service.md` — the decision layer
  this ADR keeps out of the enforcement path
- `docs/decisions/0034-workloads-are-placed-by-the-free-tier-not-by-the-cluster.md` — where the
  verification job runs
- `docs/decisions/0043-the-bound-lives-at-the-door.md` — one budget, one door, one number
- `docs/decisions/0044-machine-first-agent-action.md` — the action boundary this receipt serves
- `docs/tickets/2026-09-26-ruthless-gateway.md` — LAW 34: the router holds vendor keys
- idp#7263 (open), idp#7265 (merged), idp#6989
