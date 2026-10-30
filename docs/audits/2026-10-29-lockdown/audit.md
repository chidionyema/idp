# Estate lockdown: memory and instruction continuity audit

Claim: chidionyema/idp#7480 | Agent: codex-lockdown-audit | Observed 2026-10-30 UTC.

**Operational certification is BLOCKED. No estate-wide CI lockdown has been activated by this audit.**
The real shared-memory endpoint refused a brief and the publication of the founder's actual instructions.
The instructions are preserved in `requests.json`, with verbatim transcript locators. A local register
does not satisfy cross-session delivery. This folder is an audit artifact, not another memory service.

## Authority and baselines

The founder's current instruction is to audit memory first, apply the same standard estate-wide,
stop easy shipping, enforce service levels mechanically, research widely, track every request,
and stop depending on the founder being at the laptop. Historical transcripts are context, not new
authorization. In particular, quoted agent claims inside a user message are not operational evidence.

The measured shared checkout HEAD was `3679304df11527ee6f447f11930dd6dcccacbcc5`.
Its `origin/main` was `714c300f635cda68e6f7006f2e3dced11307eaee`, dated 2026-10-29T23:52:47Z.
The checkout contains other agents' staged, unstaged and untracked work. This audit did not reset,
switch, commit or overwrite that work. Conclusions below distinguish current-main code, historical
specifications, unmerged governance code and live observations.

The bounded transcript pass parsed 120 JSONL files, 3,711 non-bootstrap user messages, and found
41 topic-matching messages. This is the available Codex/Pi corpus, not proof that all historical
Claude Desktop transcripts have been recovered. `~/.claude/projects` was absent. The current-main
documentation search exported 32 textual candidates. `corpus.json` contains 158 current-checkout
source candidates; inclusion means discovered, not individually certified as reviewed or operational.

## Measured blockers and failures

| Finding | Evidence | Consequence / acceptance needed |
|---|---|---|
| Shared memory cannot serve this caller | `estate-execute --from /private/tmp/lockdown-audit lockdown-audit action=memory-live`, exit 1, `URLError: <urlopen error EOF occurred in violation of protocol (_ssl.c:1129)>`, ticket `INTENT-20261030-001107-56e18970` | No claim that this agent has read a fresh shared brief. Restore the existing authenticated door and prove real reads. |
| The founder's actual instruction could not be published | Same intent, `action=publish-requests`, exit 1, same EOF; prompt `prompt-20261030T001108Z-95ae76`, ticket `INTENT-20261030-001107-b8407c8c` | A local intake record exists, but cross-session propagation is unproven. Retry the same durable instruction idempotently after recovery, then observe its use by another session. |
| Completion certifies a file instead of behavior | Unmerged `platform/estate/governance/specs.yaml:51-62`; `registry.evaluate_specs(repo_root)` reports `SPEC-prompt-intake=done` and proof `founder_intake.py exists`, while the live publish fails | File checks may certify inventory only. Every operational criterion needs a proposition-bound behavioral verifier. |
| Lockdown/supervision proofs are insufficient | Unmerged `specs.yaml:25-49`: `grep_present` for lockdown, `file_exists` for supervisor | Test refusal on every real write/execution/push seam, and demonstrate the deployed supervisor consuming real violations. |
| The spec-status CLI resolves the wrong root | `bin/estate-spec-status:39` walks above the repo; `action=spec-status`, exit 1 reports existing files missing, whereas explicit-root evaluation finds them | Fix the existing tool in its owner's claim. Do not substitute the explicit-root experiment for proof that the CLI operates correctly. |
| Codex missing from memory runtime contract | Current-main `platform/estate/memory/runtimes.json:26-58` lists Claude Code, Cursor, Gemini, OpenCode and Pi; no Codex entry. No estate-memory MCP tool was exposed in this session | Codex and each actual deployed harness must be covered by an installation-and-real-use matrix. Router coverage alone cannot prove direct-provider sessions are covered. |
| Memory use is bypassable at the router | Current-main `platform/llm/active_memory.py`: caller opt-out and a caller-supplied `<estate-memory` marker skip injection; failures return the request without memory | Mandatory founder-policy enforcement must sit at the existing action boundary, with authenticated exemptions. Retrieval text remains data. |
| The router does not persist every turn | Current-main `active_memory.py:533-534` returns without turn recording in MCP door mode; `ephemeral_turn` is not a durable founder directive | Capture founder directives at authenticated intake; verify capture across transports and restarts. Do not promote arbitrary model output to founder authority. |
| Focus refresh has a self-imposed deadline mismatch | Current-main `active_memory.py:288-293` caps the focus reader to the interactive budget; #7397 describes the independent fallback/refresh repair, still open | Prove a background refresh can complete, and recompute heartbeat expiry before using cached claims. |
| Operational proof is not in the CI success chain | Current-main `.github/workflows/ci.yml:623` has no live-memory or operational-certification job. `bin/idp-ci:438` suppresses the BDD proof gate with `|| true`; its comment admits it grades the wrong PR | Fix subject binding before making it required. All required candidate jobs must enter `ci-success`; missing/unknown proof cannot become a successful skip. |
| Existing memory gate overstates what it proves | Current-main `bin/memory-gate` has config/rung checks and in-pod write/recall probes; line 268 calls that operating. It does not demonstrate ten independent sessions applying a founder instruction | Preserve diagnostic probes; reserve operational certification for real caller consumption, application and enforcement with provenance. |
| Memory documents contradict themselves | `2026-10-02-memory-plane-cortex-adoption.md:54-58` keeps the existing store; lines 125-143 call Cortex/redb the record, and lines 241-242 request a redb PVC. ADR 0036 and #6164 preserve Postgres | Reconcile the existing spec against the accepted decision. Never build a second authoritative store from stale diagram text. |
| Research provenance is overstated | The 2026-10-19 comparison presents specific four-signal and focus formulas from mixed sources. Meta's primary Muse Wonder article defines the behaviors, not those formulas | Mark implementation formulas as third-party choices unless primary implementation evidence is verified. Evaluate estate behavior rather than claiming parity from matching terms. |

The last two rows are specification defects, not fresh measurements of a running server.
Historical descriptions of zero embeddings, Hindsight idleness or ghost claims are not reused as
current incident counts. Current-main source already contains embedding, ranking, consolidation
and harness code; their effective production state cannot be certified through the failed door.

## Feature acceptance inventory

No row below is operationally certified by this audit. `contracts.json` holds exact acceptance
criteria and proposed SLIs; a green static test does not change this inventory to operational.

| Feature | Existing home / relevant source | Current conclusion |
|---|---|---|
| One durable memory record | ADR 0036, unified-memory-server/Postgres | Accepted architecture; current live door broken |
| Founder instruction capture and reuse | founder_intake, memory door, master epic R-54 / EPIC-067 | Publish failed; downstream application unproven |
| Session wake briefing and every-harness coverage | runtimes.json, estate-memory-install, #6156 | Runtime contract misses Codex; all-harness use unproven |
| Running-session refresh / broadcast | master epic R-56/R-57, JetStream | Delivery, replay and acknowledgment unproven |
| Semantic recall and embedding backfill | server main.py, embed lane, prior diagnoses | Built in source; current quality and embedding coverage unknown |
| Hybrid Cortex retrieval and computed trust | ADR 0036, #6159, server harness | Existing architecture; live engine participation unproven |
| Temporal validity and supersession | schema/harness, master epic T-2 | Live as-of results and supersession behavior unproven |
| Namespace/tenant/access isolation | server security guards and RLS | Must test real positive and negative caller identities |
| Evidence-bearing memory writes | 2026-10-26 memory-rung ADR, claim checker | Source exists; a successful unrelated command cannot certify a proposition |
| Budgeted retrieval and calibrated quality | ranking.py, active_memory.py | Weights/limits in source; estate gold-set effectiveness unproven |
| Working memory/checkpoint persistence | harness scratchpad/idempotency/approval tables | Restart, duplicate-call and atomic-consumption proofs required |
| Preference consolidation / episodic distillation | consolidation.py, harness, Muse comparison | Distillation explicitly documented as missing in the comparison |
| Active Focus liveness / closed-claim retirement | focus.py, GitHub claims | Must prove live, closed, lapsed and unknown cases through each reader |
| Overlap refusal | claim-gate and runtime enforcement hooks | Ownership gate is not an operational-truth gate; runtime-wide coverage unproven |
| Stuck detection / bounded adaptation | focus register, active-runtime focus controller | Claim age is not goal progress; deployed in-run adaptation unproven |
| Agent identity / DNA | master epic R-12, claims, eval history | Persistent identity requirement recovered; exact agent-DNA source still unresolved |
| Graph and event ingest | growmos, graph capture/drain, NATS | Separate source adapters; freshness, replay and deduplication unproven |
| Backup and recovery | #7397 memory-second-home, #7391 database recovery | Open recovery work; restore into an isolated target must be proved |
| Duplicate-store retirement | #6162, ADR 0036 | Import completeness and deletion safety must precede retirement |
| Fleet visibility and voice reachability | #6164, master epic / Fleet contract | No fresh evidence of end-to-end founder use collected |
| Operational evidence / required CI | Aevum, memory-gate, idp-ci, ci-success | Existing layers to extend; current proof chain insufficient |
| Institutional learning | founder Loop Engineering doctrine, #7452 | A fixed instance must produce a reusable enforcement rule and measured recurrence outcome |

## Lockdown contract and CI design

Use the existing memory door, context broker, action executor, claim ledger, Aevum evidence,
memory-gate and `ci-success`. This design creates no second truth oracle, memory store or ticket
ledger. New checks belong in those existing layers.

1. Bind each requirement to a service, invariant, real caller, SLI, threshold, window and
   verifier. Carry the founder's source, owner, candidate SHA, image digest/config revision,
   trace/log ids, observation time and freshness limit in evidence references.
2. On PR, queue and merge-group candidates, require behavioral conformance and falsifier tests.
   Run the correct candidate's tests. No empty suite, stale SHA, missing artifact, unknown
   result or `continue-on-error` may satisfy a required criterion.
3. Operational certification additionally requires real usage evidence collected by the
   existing trusted evidence layer. The change author cannot certify their own free-form JSON
   or print a success string to obtain it. Verify provenance and the exact asserted property.
4. Promotion must follow a controlled candidate rollout, observe the candidate, then verify.
   Do not demand future production evidence before any repair candidate can be exercised:
   that deadlocks an outage. Read-only diagnosis and explicitly scoped recovery work remain
   available under the existing execution policy; no unrestricted agent-controlled bypass.
5. An outage or exhausted agreed error budget blocks ordinary feature promotion. A governed
   reliability repair can be tested; it cannot claim the failed service operational. After
   rollout, continuous checks expire/revoke certification when evidence becomes stale or red.
6. The gate reports `CONFORMANT` separately from `OPERATIONAL`. Only fresh applicable evidence
   for every mandatory criterion permits the latter. Fleet streams both the refusal and the
   recovery. A healthy pod, successful HTTP status, file, test count or merge is insufficient.
7. Critical founder directives are authenticated, versioned policy inputs. Semantic memory
   remains untrusted context. A remembered sentence cannot become execution authority merely
   because retrieval ranked it highly. Supersession/revocation must reach existing sessions.

**Trade-off:** this reduces feature throughput while evidence is absent. It also introduces
availability dependence on the evidence verifier. Bound that dependence with trusted cached
policy/focus, explicit expiry, and the constrained repair route; never silently treat unknown
ownership or stale authority as permission. Candidate-bound evidence costs collection time and
storage but prevents unrelated green runs and outdated deployments certifying current behavior.

## Ownership and next proof

#7474 owns the current unmerged governance/CI files. A coordination comment at
https://github.com/chidionyema/idp/issues/7474#issuecomment-6511582836 records the weak-proof finding.
This audit did not edit that claim's files. #7443 already specifies the deterministic completion
verifier; it explicitly does not prove a reference's subject is meaningful. Extend that work rather
than duplicate it. #6164 is the existing whole-memory operational gate work; #6156 is the all-runtime
integration; #7397 is memory resilience. Open issues are not evidence those features work.

Next: restore the shared memory caller path, republish the recorded directive idempotently, have
distinct fresh and already-running sessions retrieve its version and apply it, deliberately attempt
a violating action, observe refusal on Fleet, restart those sessions, and repeat without asking the
founder to restate it. Keep all failing/unknown criteria open until that chain is evidenced.

The previous `work-audit days=2` and `continuity-rescue` invocations exited 124 at the executor's
100-second ceiling. No conclusion that work is lost, absent or fully rescued follows from them.
`work-inflight` did return a ledger; its LANDED state is code location, not operational acceptance.

## Research

See `research.md`. Broad external benchmarks inform the test dimensions; they do not replace
estate-specific gold sets, real caller evidence or founder service-level obligations.


## Closure update - 2026-10-30T01:28Z

The prior observations above remain timestamped findings, not an assertion that other agents'
later deployments did not change them. Origin/main advanced to a8743fc3e9568f4dfdb70da20f0843a950c1a506.
Governance #7474 and durable Fleet inbox code have landed since the first baseline.

The founder directive relay was actually stored on ESTATE_FLEET sequence 2 and received through
the existing durable inbox. Its instruction id is `fleet:ESTATE_FLEET:2`; SHA-256 of the received
message is `dbc2a44e917f351616459f2c4739e3f632c403996470a9fd2e246151a1a4d635`.
This proves this session received it. It does not prove ten other sessions applied it.
It is explicitly an agent relay of founder authority, not a hardware-signed founder command.

The existing executor now has a candidate admission/receipt extension, with 20 passing focused
tests and a real shared-focus claim verification. It refuses missing/stale instruction context,
wrong or stale claims, altered receipts and policy deletion after activation. It retains command
stdout and records actual exit/output evidence in the executor's existing SQLite ledger.
An execution receipt always says `operational: false`; it cannot certify a service's behavior.
This closes a proposed command-evidence link, not the whole estate's response/completion standard.

Emergency stage `INTENT-20261030-012414-de1f0e8a` exited 1 with
`managed-release symlink: use the release mechanism`. No runtime patch was made. Inspection found
the executor symlink points into the converged runtime tree and that runtime-sync resets hand edits.
The activation path therefore changes policy state only after exact executor/module convergence;
it never replaces the managed runtime. No active estate-wide guard is claimed.

The real memory brief was retried outside the network sandbox via `lockdown-audit action=memory-live`,
ticket `INTENT-20261030-012830-594db1be`, exit 1:
`FAIL memory real caller path: URLError: <urlopen error EOF occurred in violation of protocol (_ssl.c:1129)>`.
The caller failure persists; it is not inferred from a static configuration check.

Remaining closure obligations: converge and activate the guard; show real refusal/acceptance on
Fleet; receive application acknowledgments from actual independent sessions; connect existing
governance completion verification to issued evidence instead of keyword matching; cover native
action paths outside estate-execute; restore the shared memory caller; enforce candidate-bound
behavioral and operational criteria in the existing CI chain under #7474. No item is closed by
publication, a test count, a merge, or this document.

## Candidate verification - 2026-10-30T01:44Z

52 passed, 1 skipped in 28.39s. See `verification.json` for exact command, log digest and limitations.
The one skipped legacy FastMCP test does not prove the live MCP transport.
Policy file loss/corruption now restores the last digest-checked policy recorded in the existing
executor ledger, then still requires valid instruction context and a live claim.
Pass/refuse admission decisions use the existing Fleet outbox with runtime `estate-execute`;
the existing Fleet UI renders gate events without filtering this runtime. Live display remains unproven.
Two old intent-engine test defects were reproduced against the untouched baseline, then repaired
with disposable worktrees/homes and real exit/output assertions. No live intent files are edited.


## Recovery update - 2026-10-30T10:40Z

The isolated candidate commit `611eadbe3ccf7e92210b04e94ae8ac78ef0b6351` survived
while its temporary worktree was removed during session loss. It remains unlanded. The latest
normal lane push was refused because sparse checkout omitted the schema gate's own proof file
`tests/test_schema_conformance.py`; the ratchet itself reported zero new violations. This is a
delivery problem, not evidence of runtime operation.

The previous executor claim lapsed during the interruption. At 10:35 UTC the live claim register
reported an overlap with `idp#7518` (`pi-meridian`) on `platform/estate/bin/estate-execute`.
This audit will not edit or submit that file under the overlapping claim. The owner was given the
existing commit and integration context at
https://github.com/chidionyema/idp/issues/7518#issuecomment-6520655605.
A docs-only claim on `idp#7480` was renewed at 10:36:51 UTC.

The real memory caller was retried: `estate-execute --from /private/tmp/lockdown-audit
lockdown-audit action=memory-live`, ticket `INTENT-20261030-103716-0670acd9`, exit 1,
`FAIL memory real caller path: URLError: <urlopen error EOF occurred in violation of protocol
(_ssl.c:1129)>`. Thus memory retrieval and founder-instruction application remain unproven.
The audit contract remains a draft, and no estate-wide active guard is certified.
