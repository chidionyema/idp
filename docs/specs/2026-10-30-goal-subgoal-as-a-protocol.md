# Goal and subgoal as a general protocol

Status: proposal. Date: 2026-10-30. Authors: pi lane (meridian-design).
Sources: `protocolkit.tar.gz` (the founder's toolkit), `idp-agent-protocols.patch` (the
founder's patch), `COMMERCIAL-READINESS.md` (the founder's diligence note).

## 0. The problem, measured

The founder's words: *"i dont see any goal and subgoal decialre, raiose a bug, no agent sould be
working with otu goals and subgoans and no agent shoud dbe aboe to break this"*.

Measured on this machine, `idp` at `origin/main` (`aacd1e919`), falsifier
`/tmp/plan_falsifier.py` (output `/tmp/plan_falsifier.out`):

| # | measurement | result |
|---|---|---|
| F1 | the estate's **one door**, `mcp/plugins/estate_executor.py::execute_command`, with no plan declared | `{"accepted": true, "job_id": "exec-1793332780-421"}` -- **accepted** |
| F2 | the Claude Code plan hook, `bin/estate-memory-enforce plan`, no plan declared | `permissionDecision: deny` -- the gate that *does* exist |
| F3 | the same hook with `ESTATE_PLAN_LOCK=off` | no output: the gate said nothing and the call passed |
| F4 | `bin/estate-memory-install --check` | exit **1**, `UNLOCKED gemini  /Users/roseonyema/.local/bin/gemini is installed and nothing holds it to a plan (#6675)`; `cursor` and `gemini` have `plan_lock: null`; **`codex` is not in `platform/estate/memory/runtimes.json` at all** and `/Users/roseonyema/.nvmpin/bin/codex` is on PATH |

The estate therefore does **not** enforce "no work without goals and subgoals". It enforces it in
three runtimes by three transcript-shaped adapters (pi extension, Claude Code hook, opencode
plugin), and it enforces it nowhere else:

- the door itself (F1) does not know what a plan is -- `rg 'plan_state|plan_gate|declared_plan|has_plan|require_plan|plan_lock' origin/main -- mcp/plugins/estate_executor.py platform/executor/daemon.py` returns nothing;
- the gate can be switched off by an environment variable (F3);
- the gate fails **open** whenever the transcript is unreadable -- `bin/estate-memory-enforce`: "Both fail OPEN on anything that is not a clear violation: no transcript, no gh, a slow ledger or an unreadable claim lets the call through";
- two installed runtimes are unlocked (F4) and one is not even registered;
- the plan is process-local and therefore **invisible**: `extensions/pi-plan-lock/index.ts` keeps it in `let plan: Plan | undefined` and resets it at `session_start`. The founder cannot see a declaration because there is nothing durable to see. (`idp#7443` already names this: "Plan state is process-local by explicit design ... so it is neither durable nor visible to the founder".)

The patch's `plan_declared` gate is in the same state: the patch's own text ties the gate to
`bin/idp-trajectory` and reports *"Status: BUILT, not operating"*. `TrajectoryLock.authorize()` has
no production caller.

## 1. What the founder supplied, and what each part contributes

**`protocolkit.tar.gz`** (`/tmp/protocolkit`) is the reference runtime model, and this spec adopts
its shape rather than inventing one:

- a protocol is a **closed, ordered list of typed stages** (`protocolkit/model.py`: `Protocol`,
  `Stage`, `ProtocolId`);
- every founder prompt binds to **exactly one** protocol (`registry.py`), and a prompt that binds to
  none is refused (`genesis.compile_system_prompt()` raises `GenesisError`);
- stages exchange **typed artifacts**, not prose (`Invocation`, `Instruction`, `Evidence`,
  `Discovery`, `Claim`, `Proof`, `ClaimProofSet`, `Assessment`, ...);
- **egress happens only after every stage passes** (`Run.egress()`, gated by `gates.py`);
- a `Run` keeps a **hash-chained audit trail** and aborts after repeated stage violations.

**`idp-agent-protocols.patch`** supplies the estate's own three protocols and their bindings:

- protocols `grounded_inquiry`, `deep_synthesis`, `execution`;
- fsm gates `plan_declared`, `proofset`, `contradictions_disposed`, `attested`, `epistemic`;
- bindings `shadow -> grounded_inquiry`, `engine -> execution`, `intake -> execution`;
- typed answer/proof entities with `check_proofset()` (source, quote and agent-authored-evidence checks).

**`COMMERCIAL-READINESS.md`** supplies the diligence questions that must themselves become
declarable goals, and two integrity defects that are written into the acceptance criteria below.

The two are complementary: the patch is *which* protocols the estate has and how they bind to
capability classes; the toolkit is *what a protocol is* -- stages, artifacts, gates, egress.

## 2. The model: goal and subgoal are a cross-cutting PLAN stage

**Decision: the goal/subgoal discipline is not a fourth protocol. It is a stage every protocol
carries, and it is the first one after the instruction.**

```
grounded_inquiry : invocation -> instruction -> PLAN -> discovery -> claimset:proofset -> response
execution        : invocation -> instruction -> PLAN -> state_assessment -> action_plan:dry_run
                                              -> commit -> response
deep_synthesis   : invocation -> instruction -> PLAN -> divergent_discovery -> contradiction_resolution
                                              -> unified_claimset:proofset -> response
```

Why a stage and not a hook:

- a stage is **closed** -- `Run` cannot enter the next stage until the PLAN artifact validates;
- a hook is **optional per runtime** -- and today two installed runtimes have none (F4);
- the founder's requirement is *"no agent should be able to break this"*: a rule that lives in a
  runtime adapter can be absent, misconfigured, or disabled by an env var (F3); a rule that lives in
  the stage machine of the one runtime cannot.

So: **PLAN is a stage in the model (protocolkit), and the plan state lives in the estate's one door
(the enforcement point).** The runtime adapters become thin clients of the same state.

### 2.1 Typed artifacts

Added to `protocolkit/model.py` in the style of the existing dataclasses, and mirrored by the
estate's plan ledger (`~/.estate/plans/`, append-only JSONL -- the ledger from `idp#7443`, so the
durable store and the typed model are the same thing seen from two sides):

| artifact | fields | produced by | consumed by |
|---|---|---|---|
| `Goal` | `statement`, `done_when: list[str]`, `scope` | `declare_plan` | PLAN stage gate, graders |
| `SubGoal` | `id`, `text`, `depends_on: list[str]`, `verifiable_by` | `declare_plan` | PLAN stage gate |
| `PlanDeclaration` | `goal`, `subgoals`, `protocol`, `declared_at`, `parent_plan?` | PLAN stage | every later stage, /fleet |
| `Scenario` | `goal_id`, `given`, `when`, `then` | `add_bdd` | per-subgoal gate, research-plan grader |
| `EdgeCaseRecord` | `goal_id`, `cases: list[(case, handling)]` | `address_edgecases` | completion gate |
| `SecondOrderEffect` | `goal_id`, `effects: list[(effect, mitigation)]` | `address_2nd_order_effects` | completion gate |
| `CompletionReceipt` | `goal_id`, `evidence: list[EvidenceRef]`, `proof`, `at` | `complete_goal` | proof gate, `idp#7443` |
| `ResearchPlanGrade` | `plan`, `scores: dict[str,float]`, `verdict` | plan grader | PLAN stage refusal |
| `CommercialReadinessGrade` | `milestones`, `evidence`, `gaps` | diligence grader | founder report |

### 2.2 The mapping onto the tools the estate already has

The pi/Claude tools are not the model; they are one adapter's spelling of the PLAN stage. The
mapping is one-to-one and total, so no runtime can be "missing" part of the discipline:

| tool | artifact | stage rule |
|---|---|---|
| `declare_plan` | `PlanDeclaration` | must validate: goal is a sentence, >=1 subgoal, unique ids |
| `revise_plan` | new `PlanDeclaration` | keeps recorded evidence for subgoals that keep their id |
| `add_bdd` | `Scenario` | required **before** work on that subgoal |
| `address_edgecases` | `EdgeCaseRecord` | required before completion; "none, because <reason>" counts, an empty list does not |
| `address_2nd_order_effects` | `SecondOrderEffect` | required before completion |
| `complete_goal` | `CompletionReceipt` | requires scenario + edges + effects + a **verifying** proof (`idp#7443`) |

### 2.3 The enforcement point

**The one door.** `mcp/plugins/estate_executor.py::execute_command` is the estate's single
execution door: it is what the daemon calls, what the MCP surface calls, and what every runtime
reaches. The refusal is made on the far side of the message, by a process the caller's own tool
calls do not live inside -- the daemon's own words.

The door consults the **plan state** before accepting anything that mutates state, spends money or
runs code. Three cases:

- a plan exists for the presented session, and the active subgoal has a `Scenario` -> accept;
- no plan, or no scenario for the active subgoal -> **refuse** with `refused: true`,
  `fatal: true`, `reason: "plan_not_declared"` / `"subgoal_scenario_missing"`;
- read-only commands (reads, searches, `git status`) are allowed without a plan, because reading is
  how a plan is made -- the same carve-out the existing `NEVER_BLOCKED`/`MEMORY_READS` lists in
  `extensions/pi-plan-lock/plan.ts` already make.

**Session identity.** The door must know whose plan it is. The caller presents a session id
(`ESTATE_SESSION_ID` in the environment, or a `session_id` field on the tool call). No session id
presented, no plan found, mutation refused -- fail-closed by construction.

**Automation is not an agent.** CI, the fleet collector and the governed jobs are not agents and
cannot declare plans. They present a **service identity** (`ESTATE_CALLER=service:<name>`) from a
small, explicit allowlist, and every use of an exemption is written to the enforce ledger
(`~/.estate/memory/enforce-ledger.jsonl`), so "who was exempt, and when" is a question with an
answer.

**Runtime adapters stay, as defence in depth.** The pi extension, the Claude Code hook and the
opencode plugin keep refusing early (they refuse before the tool call, which is cheaper than the
door). They are re-pointed at the same durable plan state instead of keeping their own copy, and
they stop being the *only* enforcement. `codex` and `gemini` get adapters; until they do, they
stay listed `UNLOCKED` with an owner -- and, critically, the door refuses their mutations anyway.

## 3. The invariants, and the falsifier that proves each one

A gate that cannot fail is not a gate. Each invariant below ships with a red-before/green-after
falsifier in the same change.

| # | invariant | falsifier |
|---|---|---|
| I1 | no mutating action reaches the door without a plan for the calling session | call `execute_command` with no session and no plan -> expect `refused`, `accepted: false` |
| I2 | no work on a subgoal without its `Scenario` | declare a plan, then call the door -> expect refusal naming `add_bdd` |
| I3 | completion requires scenario + edge cases + second-order effects + a verifying proof | `complete_goal` with each missing -> expect refusal; with all present and a bad proof -> expect refusal |
| I4 | the gate cannot be switched off by an agent | `ESTATE_PLAN_LOCK=off` in the agent's environment -> the door still refuses a mutation (F3 today: it does not) |
| I5 | every runtime that can reach the door is adapted or explicitly UNLOCKED with an owner | `bin/estate-memory-install --check` lists `codex` and `gemini` as UNLOCKED with owners, and the door refuses their mutations meanwhile |

**R38 (a fence a correct machine cannot satisfy is an outage) is honoured by shipping in two
phases:** phase 0 makes the plan durable and visible (ledger + `bin/estate-plan-status` + /fleet)
with no refusal; phase 1 turns the door refusal on in **observe mode** (log the refusal, do not
block) for a measured week, with the false-refusal count published; phase 2 enforces. I4 is the one
invariant that does not wait for phase 2: an agent's own env var must never disable the gate.

## 4. The research plan is evaluable

A research plan is a `PlanDeclaration` plus, for every subgoal, a `Scenario`, an
`EdgeCaseRecord` and a `SecondOrderEffect`. That is enough to grade it mechanically, because each
piece has a defined shape:

| dimension | question | source |
|---|---|---|
| goal clarity | is "done" a condition that can be observed, or a wish? | `Goal.done_when` non-empty, each entry a checkable predicate |
| subgoal verifiability | does each subgoal's `then` name an observable? | `Scenario.then` must name a command, a file, or a receipt |
| coverage | does every subgoal carry scenario + edges + effects? | the four artifacts per subgoal |
| decomposition | do the subgoals partition the goal, with dependencies declared? | `SubGoal.depends_on` is acyclic and every subgoal is reachable |
| evidence linkage | does the plan say how each subgoal will be proved? | `SubGoal.verifiable_by` names a proof kind (`commit:`, `run:`, `log:` -- the kinds `idp#7443`'s verifier already knows) |
| protocol fit | does the plan's shape match the protocol it was declared under? | an `execution` plan requires a dry-run stage; a `grounded_inquiry` plan requires a proofset |

The grader is deterministic and lives beside the existing ones (`bin/prm_grader.py`,
`bin/budget_governor.py`): same inputs, same score, no model in the loop. Its verdict has three
outcomes -- `PASS`, `FAIL`, and `BLIND` (unknown, which is never a pass). The plan is graded **at
declaration**, not at the end: a plan that cannot be graded is refused then, while it is cheap to
fix.

The score is a number the founder can read; the reasons are a list of the exact missing fields. The
founder's "we also need the research plan evaluable" is answered by this table, not by a rubric
document.

## 5. Commercial readiness is the same protocol, not a separate process

`COMMERCIAL-READINESS.md` is a list of diligence questions. Under this model each question is a
`Goal`, each mitigation is a `SubGoal`, and each acceptance is a `CompletionReceipt` with proof.
The protocol binding is `commercial_readiness`, and the artifacts are the same ones: no second
framework, no second ledger.

The note's two integrity defects become **subgoals with falsifiers**, because a report that cannot
fail is the thing the founder is actually buying against:

1. **Legal guidance lives outside the repository.** The required legal basis is referenced through
   `~/AGENTS-FULL.md`, which is not versioned, not reviewable and not provable to a third party.
   *Subgoal:* the legal basis is in-repo, versioned, dated, with its source recorded.
   *Falsifier:* `rg -l 'AGENTS-FULL' --no-heading .` finds only the historical references, and the
   in-repo document resolves to the same text -- a diff, not a claim.
2. **The enforcement summary can report zero laws and still succeed.** A summary that enforces
   nothing and exits zero is a green light on an empty estate.
   *Subgoal:* the summary exits non-zero when it enforces nothing.
   *Falsifier:* run the summary against an empty policy set -> expect a non-zero exit and a line
   naming the count.

The rest of the note's strengths (rule-enforcement gates with fixtures, one-of-each capability
layer, evidence and audit trails, scoped agent identity, hash-chained receipts, Sigstore sealing,
break-glass controls, incident handling, licensing gates, honest limitations) are already
enforceable invariants of this estate; each becomes a subgoal whose receipt is a passing gate run.

**Honesty boundary:** this spec does not claim commercial readiness. It is a static design over
the repository; the live system was not run, and legal claims were not independently verified.
The commercial-readiness grade is a *plan* for the grade, and the grade itself is a receipt.

## 6. What lands, in what order

| phase | work | proof it landed |
|---|---|---|
| 0 | durable plan ledger + `bin/estate-plan-status` + /fleet view; PLAN stage and the typed artifacts in the model | a session's declarations visible without reading a transcript |
| 1 | door observe-mode: log a refusal for every mutating action with no plan | the observe log names the session and the command |
| 2 | door enforcement + the five falsifiers | red before, green after, in one change |
| 3 | `codex` and `gemini` adapters; the door already refuses them meanwhile | `bin/estate-memory-install --check` lists no UNLOCKED runtime |
| 4 | research-plan grader; commercial-readiness protocol binding | a plan that scores below threshold is refused at declaration |

Phases 0-2 are one issue (`idp#7443` for the ledger and the proof seam; this spec for the stage
and the door). Phase 3 is a second issue. Phase 4 is a third.

## 7. Non-claims

- This does not make the gate refuse a human-driven session by default; `ESTATE_PLAN_LOCK=off`
  stays for the founder's own sessions, and the ledger records every use (I4 applies to *agents*,
  not to the founder at the keyboard).
- This does not replace `idp#7443`'s proof seam or its durable ledger; it consumes both.
- This does not claim the live system was validated. It is a design and a set of falsifiers.
- This does not add a second plan store. The ledger is the store; the model is its schema.
