# INS-00011 — Legion Workforce and Genesis Founder Surface: Fleet Decision Record

**Recorded:** 2026-11-11  
**Authority:** Founder direction and INS-00011 handover; architecture decisions captured here, not proof of deployment  
**Scope:** IDP, Argon Genesis, Crew, Greenlane, estate-wide agents, and all founder interaction surfaces  
**State:** DECIDED ARCHITECTURE / IMPLEMENTATION AND OPERATIONAL PROOF OUTSTANDING  
**Programme:** docs/epics/2026-10-25-estate-master-epic.md  
**Existing operational contract:** AGENTS.md; docs/runbooks/greenlane.md; .github/workflows/agent-sandbox.yml  
**Related:** Genesis founder visibility, One Eye / All-Seeing Eye, FLOW instruction-to-yield, Zero-Laptop order, Chesed/Geburah, IDP #7775 and #7777.

## Executive decision

Legion is the estate's **model-agnostic, cloud-resident workforce execution capability**. A founder instruction or an authorized agent can delegate bounded work to Legion; Legion selects a formation, leases verified workers, carries out real work, independently evaluates outcomes, submits through the existing Greenlane, and returns authenticated operational evidence. Legion is not a chatbot, a list of model names, a standalone second orchestrator, or a database of pretend worker activity.

**Estate owns missions. Agents execute. Models supply capabilities. Surfaces provide access.** A session is replaceable; its mission, custody, state, proof, and recovery path are not.

**Founder Surface is the mission control plane, not the execution engine.** It presents the whole estate and each agent's current view, offers authenticated voice-first and visual control, and shows handoffs, active work, CI, release, runtime, failures, cost, and independently verified outcomes without losing existing capabilities.

**Priority is operational yield, not scaffolding or narration.** Internal R&D follows Chesed (build, run, expand) then Geburah (measure, falsify, refine). Research is not blocked by premature commercial release ceremony. Protected side effects still use the existing authorization and security boundaries.

## Decisions

### D1. Reuse canonical infrastructure; do not create a rival estate

- Existing remote execution: founder-authorized [LEGION] issue path via .github/workflows/agent-sandbox.yml; ephemeral GitHub runner, model harness, encrypted transcript, independent epistemic firewall, claim gate, governed Greenlane. Extend and compose these paths.
- Existing delivery: lane/<mission> branches, exact-SHA CI, Greenlane as the only protected main promoter. No agent raises its own pull request or pushes protected main.
- Existing primitives: estate instruction ledger, estate-execute, identity and claims, capability inventory, capacity router, telemetry/event ring, memory/Active Focus, evaluation and incident mechanisms. Integrate instead of duplicating.
- MacBook is a thin client, **not** a production service, fleet host, mandatory executor, or CI worker. All critical missions and resumptions must function with the founder's laptop offline.
- A future bin/legion CLI, Telegram command, mobile session, and Genesis Surface command must call the **same durable dispatch contract**. Interfaces cannot create their own parallel lifecycle.

### D2. Eight Legion formations — selectable execution policies, not eight systems

| Formation | Use when | Runtime contract | Independent proof |
| --- | --- | --- | --- |
| **Sniper** | One bounded file/defect, clear falsifier | One worker, isolated path claim, deadline, up to two same-hypothesis retries | Repro test red before fix, green after; exact diff and receipt |
| **Phalanx** | Many independent files or endpoints | Disjoint sharded ownership, N bounded remote workers, reducer validates tree and conflicts | Per-shard evidence and integration checks on combined SHA |
| **Pipeline** | Spec → implementation → testing → release | Durable stage handoff; each stage consumes structured prior artifact, cannot bypass dependency | End-to-end output and independent live acceptance |
| **Swarm** | Backlog of independent issues or audits | Atomic queue claims, TTL, heartbeats, work-steal, duplicate suppression, bounded capacity | Per-work-item output, no unowned/orphaned tasks |
| **Supervisor / Centurion** | Multi-repo dependencies and a DAG | Supervisor plans dependency graph; workers can only start ready leaves; bounded replan on failure | Integrated dependency and outcome proof |
| **Adversarial** | Auth, crypto, trust, concurrency, irreversible operations | Blue builds; Red independently attacks; successful exploits become permanent tests | Break case demonstrated and rerun after patch |
| **Tournament** | Hard bug or optimization with several viable solutions | Heterogeneous independent candidates race in isolated sandboxes, common falsifier; cancel losers after **verified** winner | Best measured passing candidate; no winner on trivial command |
| **Sieve** | Critical test adequacy or risky changed lines | Mutation testing in sandbox with surviving mutants reported; additional targeted tests | Mutants killed by real assertions; changed-code acceptance |

A mission may combine formations (e.g. Supervisor with Phalanx leaves followed by Adversarial and Sieve). This is a composition of policies over one execution engine, not an invitation to duplicate controllers. Choose formation by dependency graph, blast radius, expected parallel speedup, worker availability, budget, and evidence; tournament is **not** the universal default.

### D3. Mandatory durable instruction and work-item contract

Before any privileged tool call, capture the founder's **verbatim** request and produce a durable, immutable instruction ID, parent ID if applicable, actor identity, provenance, chronological sequence, authorization scope, acceptance criteria, and idempotency key. Decomposition produces child tasks that preserve the parent relationship. Record each state transition with monotonic ordering and evidence.

Every Legion work item must contain:
- mission_id, ins_id, parent_task_id, scope/allowed paths, forbidden effects, target repository and **exact base SHA**;
- goal, expected externally observable outcome, falsifier/test command, expected negative control, source-of-truth evidence and acceptance threshold;
- formation, candidate model(s), actual model/harness used, budget and expiry, resource/lease/fencing token, dependency list, attempt count and retry class;
- runner execution ID, output artifact/diff digest, **Git commit SHA separately from log digest**, CI/check runs, Greenlane disposition, runtime verification receipt, rollback/compensation and owner;
- UTC event timestamps, trace/span correlation, causal ordering, meaningful-progress checkpoint and recovery/alternate executor.

**Required lifecycle:** RECEIVED → AUTHORIZED → PLANNED → DISPATCHED → LEASED → EXECUTING → CANDIDATE → FALSIFIED → SUBMITTED → INTEGRATED → OPERATIONALLY_VERIFIED. FAILED_FENCED, BLOCKED_WITH_EVIDENCE and CANCELLED are explicit outcomes; a retry is a new attempt on the same durable mission. The canonical estate FLOW lifecycle is authoritative if state labels differ; this list illustrates the information that must be captured, not a competing state machine.

A claimed worker, queued workflow, passing local unit test, green CI, merged SHA, and verified operational effect are **different states**. Only independent outcome verification may close operational yield. Research experiments can yield measured learning, including a proved negative result, without pretending to be commercial production.

### D4. Delegation, isolation, retries, and recovery

- Dispatch must actually launch remote workers with bounded leases; store provider job IDs and verify a worker started and produced output. Never equate a row INSERT with a worker.
- Claims are atomic and fencing-aware; workers with stale leases cannot publish winning results or protected effects. Do not assume disjoint globs prove disjoint changes; validate actual write sets and Git trees before reduction.
- Checkpoints are durable; when a provider, host or session dies, another eligible worker resumes without the founder repeating instructions.
- Detect **600 seconds without evidenced meaningful progress**; classify the cause and re-route. At most two identical retries before changing the hypothesis or worker; renewals must be based on useful output, not mere heartbeats.
- Authorization is effect-based and checked at executor/GitHub/deployment boundaries. Untrusted prompts, worker output and memory must never self-grant privileges. Test code and candidate scripts run sandboxed without production credentials.
- On winner selection in Tournament, promote only an independently verified candidate against the same exact baseline, with cost/quality regression guardrails. Cancel competitors after a real winner exists.
- Preserve existing live services while trialling. Operational repair paths must be authorized, bounded and independently checked; failures produce remediation intelligence rather than repeated blind execution.

### D5. Founder Surface — actual job-to-yield experience

The Founder Surface must support this single testable journey:

1. Founder speaks or types an instruction from Genesis or Telegram; it is durably recorded immediately with its verbatim wording and INS ID.
2. Genesis shows current estate state, capabilities, candidates, costs, dependencies and scope; recommends a formation but allows an authorized override.
3. The founder can inspect or issue the mission. The UI shows mission owner, formation, real workers/actual models, leases, stages, progress, blockers, cost, and ETA **only if measured**.
4. The system shows source SHA, actual runner, test and adversarial results, Greenlane status, deploy/release progression, independently observed live effect, and actionable recovery.
5. Founder sees both **One Eye** (coherent estate-wide reality) and **All-Seeing Eye** (what each worker sees, what it does not see, and stale/divergent context). Missing coverage or unavailable data is visible, not painted green.
6. The same mission and voice context continue across phone, web, CLI and fleet sessions without a laptop session being the custodian.

No capability disappears from the complete Genesis capability inventory. Otto is a capability within Genesis, not its replacement. The surface needs elite accessible visual craft, mobile/voice-first command, real-time event projection, and a regression test across the whole capability inventory. An attractive mock with simulated numbers fails the founder acceptance test.

### D6. Unified memory and Active Focus are shared capabilities

The INS-00011 proposal to add Active Focus, operational memory, bi-temporal fact history, negative/failure memory and executable fact probes is **an architectural research direction**. Map it against existing estate-memory, context compiler, event ring, graph and execution receipts before implementation. Extend the canonical stores, not a second uncontrolled ~/.estate/estate.db truth system.

Memory facts need valid time **and** recorded/transaction time, source receipts and trust ranking; historical facts remain inspectable. Supersession must handle late/out-of-order events and conflicting evidence, not automatically treat the latest INSERT or prompt as truth. Context rendering selects relevant, fresh, trusted facts with a measured token budget and evidence of what was omitted. Failure memory includes expiration, context, alternate remediation and a path to re-test a previously failed hypothesis after circumstances change. Executable probes must be approved, typed and sandboxed; no arbitrary shell commands from mutable memory rows.

Do not seed runtime facts such as infrastructure retirement or target architecture as present-tense operational truth without authoritative, fresh verification.

### D7. Language tooling and safety are effect-sensitive, evidence-based

Adopt the intent of fast compiler/AST checks, explicit deadlines, typed IDs, finite numerical telemetry, structured model outputs, shell hygiene, and mutation falsification. Reuse existing repo toolchains and measure incremental latency before switching linters. The INS-00011 suggestions (ast-grep, Oxlint, Biome, cargo-nextest/mutants, Kani, mutmut) are **candidates**, not already installed or demonstrated fleet-wide.

Prefer prevention of silent exception swallowing, unchecked side effects and false-green tests. Do **not** blindly impose impossible universal rules: some Rust code legitimately needs controlled unsafe, shell portability differs from Bash, and SQLite reversibility cannot be guaranteed by generic inverse-SQL triggers for all operations. Introduce narrow exceptions with tests and evidence; do not cause a permanent gate that blocks authorized emergency recovery or internal experiments.

### D8. Capacity, routing and competitive model evaluation

Route by measured correctness, time-to-evidence, context fit, tool support, remaining quota and full cost. Cheap workers handle bounded repetitive work; expensive reasoning models are invoked only where marginal improvement warrants the spend. Heterogeneous entrants (including **Carbon when admitted**) are evaluated through the **same** Legion missions, falsifiers, traces and independent results. No provider receives authority by brand, marketing or model-supplied claims.

Model prices, available versions, rate limits and cohort composition are configuration backed by live telemetry, not hard-coded claims. The handover's illustrative probabilities (e.g. three independent 65% successes ⇒ 95.7% combined success) assume independence; correlated model errors invalidate that performance claim. No 3x speed / 10x cost / sub-millisecond assertions become fleet facts without recorded benchmarks.

Primary metrics: percentage of dispatched missions with **real worker execution**, verified outcomes per pound, cycle time founder-instruction-to-live-yield (p50/p95), time to first useful experiment, recovery time, stale-lease incidence, rework/repeated-error rate, test mutation score, protected-effect incidents, hidden visibility gaps, and founder interventions per mission.

## Critical distinction: what INS-00011's proposed installer actually does

**Do not run or promote the pasted installer unchanged as a production deployment.** The supplied bin/legion code plans SQLite subtask rows then runs a single local falsifier. It contains no model invocation, remote runner launch, true worker leases, Git-tree reducer, CI/Greenlane integration, winner comparison, cancellation, or cloud resumability. It marks all pseudo-workers PASSED_CIF and the mission VERIFIED_YIELD when the command passes, even if no worker executed. Its default falsifier is the always-successful shell command true. The supposed receipt_sha is actually a hash of console output, not a commit or verified receipt. These are correctness failures, not a mere TODO list.

The proposed memory engine likewise is not ready to serve as the canonical estate truth: MAX(sequence)+1 is not a safe distributed sequence allocator, its fact assertion is not a fully specified bitemporal conflict-resolution protocol, focus rendering does not enforce the stated token bound or scope filter, and arbitrary stored shell falsifiers cross a trust boundary. The sample Pi hook suppresses errors and has no demonstrated event-contract compatibility. Local bootstrap targets the founder's laptop, violating zero-laptop operational custody.

**Consequence:** treat INS-00011 as requirements and illustrative source, not deployment evidence. Do not erase its ideas; retain this falsification as the first negative-memory entry and run a real remote first trial through the existing substrate.

## Implementation sequence and acceptance (no substitute document work)

**P0 — Demonstrate one real cloud Legion Sniper from the existing agent-sandbox path.** With the laptop offline, capture a genuine instruction ID, dispatch a cloud agent, observe its real provider/runner ID, produce a restricted diff, show a red-then-green regression, submit via Greenlane, and independently verify the resulting effect. Emit an honest FAILED/BLOCKED receipt for missing model credentials or inability to start a worker.

**P1 — Establish durable common dispatch, leases and evidence.** Extend the existing instruction/event/claim substrate with exact-SHA tasks, fencing, recovery and candidate provenance; prove double-claim prevention and lost-runner recovery under concurrency. Make the CLI, Telegram and Genesis projections of this same contract.

**P2 — Exercise formations, not merely register names.** Prove Sniper; then Phalanx on disjoint changes; Pipeline checkpoint recovery; Swarm lease-steal; Supervisor dependency/failure replan; Red/Blue on a real testable boundary; heterogeneous Tournament on reproducible criteria; Sieve with a surviving mutant repaired by a test. Record what each formation costs and where it loses against simpler alternatives. Dynamic feature flags allow rapid internal trials.

**P3 — Founder Surface closed-loop acceptance.** From phone or browser, issue a spoken mission, observe real worker activity and per-agent context gaps, recover from one forced worker failure, see exact Greenlane and release receipts, verify actual deployment and historical memory, without local-laptop support. Preserve feature parity, readable typography and public release quality.

**P4 — Promote by measured evidence.** Compare variants against a measured baseline. Remove failed or duplicative mechanisms; promote only independently verified capabilities to protected/commercial lanes. Record successes, failed hypotheses, cost and lessons in the existing shared memory and evaluation plane.

### Non-negotiable tests

1. **False-green test:** a non-started worker plus a successful no-op falsifier MUST NOT become VERIFIED_YIELD.
2. **Failover test:** worker loses host/network; stale attempt cannot commit; another authorized worker resumes from durable checkpoint.
3. **Concurrency test:** at least two workers race same lease; one fenced winner; zero conflicting protected writes.
4. **Context test:** stale/superseded fact cannot silently override a newer verified observation; historical query can recover both.
5. **Regressions test:** founder surface retains every registered existing capability and visibly labels unknown data.
6. **Real-world test:** with the MacBook disconnected, founder-originated instruction completes to independently observed live service effect.
7. **Budget test:** actual model identity, tokens, cost, p50/p95, and quality outcome attributable to real runs; no hard-coded savings claims.
8. **Recovery test:** no meaningful progress for 600s triggers autonomous diagnosis and alternate bounded route, not an infinite heartbeat loop.

## Ownership and visibility

- **Founder:** prioritizes missions and product direction; intervenes on true authority/effect choices, not routine scheduling.
- **Genesis/IDP:** instruction custody, dispatch, identity, policy, scheduling, telemetry, recovery, and provenance.
- **Legion workers:** scoped execution and candidate artifacts; never self-attest production success.
- **Independent evaluator/Greenlane:** falsification, exact-SHA checks, merge qualification and release evidence.
- **Founder Surface / Otto / Telegram:** consistent, read-write authorized views into one estate, not separate brains.

**Evidence status at time of writing:** GitHub's default branch has the existing agent-sandbox cloud workflow and Greenlane runbook. The supplied INS-00011 installer and proposed multi-formation CLI are not proven deployed there. This decision record itself does not prove operational Legion, production deployment, CI success, or founder-surface integration. The next acceptable update is a cloud run plus verifiable effect receipt.

**Doctrine:** More capability first, then stronger falsification; every worker minute must buy execution, intelligence, or a measured improvement. More agents without real jobs, verifiers and evidence are just more noise.
