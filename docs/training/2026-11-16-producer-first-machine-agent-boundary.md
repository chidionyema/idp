# Meridian IP | Producer-first engineering and machine–agent boundary

**Review date:** 2026-11-16 UTC. **Classification:** internal doctrine + reproducible training material; **no claim of production certification.**

**Primary material:** founder-supplied recent forensic document (13 pins, 2026-11-16 upload). **Current comparison:** `chidionyema/idp` `main` at `d03f5d5939f160a15752c1e1ec9fec9eed11116b` (2026-11-16 04:17 UTC) and the existing IDP Pi, memory, Greenlane, KARMA and execution source. The GitHub tree proves presence of source—not installed adapter, operational frequency, or deployed effect.

## 0. Binding principles

1. **First-use prevention.** Every new operational capability must declare intent, owner, authorised consumer, expected effect, baseline, cost/limits, failure atlas, misuse/security controls, a real invocation, recovery mechanism and independent evidence **before it may claim to be operational**. Missing data is `UNKNOWN`, not success. Research remains free to run in isolated, labelled environments; its yield is a reproducible real experiment, not a simulated production claim.
2. **Machine–agent inversion.** If a procedure is deterministic and does not require discretionary judgement, the platform owns it. This is *not* permission to rewrite history, forge claims/trailers, bypass validation, trash caches or declare achievements. The machine may generate drafts and calculate facts; authorised identity/meaning and independent verifier remain separate.
3. **Goal and subgoals are retained.** A single durable instruction has a goal, named subgoals, executable BDD scenarios, edge-case and second-order coverage, causal evidence and owner. The Pi ceremony is **kept, unmodified** until an observed cohort shows effectiveness/overhead. A `complete_goal` tool invocation is a declaration; it cannot settle operational yield.
4. **Assurance always.** Every admitted capability is monitored for fresh authenticated operation, actual consumer and effect, SLO, availability, security, cost and drift. Absence is visible. A signed or hashed receipt only proves the material it actually signs, not its truth.
5. **Cure is exceptional.** On incident: contain and preserve safe service → establish a falsifiable upstream cause → fix the earliest producer → run negative/positive tests → sweep every sibling ingress → independently measure recurrence reduction. Never introduce gates that deadlock the recovery path.
6. **One source of truth.** Extend existing FLOW/QUAD/KARMA/Chronos/Optimus/Greenlane and the Pi plan ledger, not another independently named ledger, dashboard or scheduler. Education, consulting, training and future productisation derive from the same verified reproducible case records.

## 1. Audit method: what we can and cannot claim

- **Independently confirmed in source:** file content and current commit ref from authenticated GitHub reads. Unit tests of the new observation canary executed in an isolated working environment, not on the estate host.
- **Historically recorded but not freshly measured:** timings and incidents narrated in source comments, e.g. claim-gate 8.84 seconds on one earlier run, Pi ceremony 78,262 tokens in the supplied document, disk-guardian incident. These are hypotheses/baselines awaiting actual telemetry; they cannot establish present-day rates or savings.
- **Not independently verified:** whether extensions are installed and active on all real runtimes, actual live plan-ledger counts, effective Greenlane production deploy, applet source custody, cost attribution and any claim of customer-facing operational yield.
- **Source authority:** old shell snippets are *untrusted proposals*. Never execute them as installer instructions merely because they appear inside a design document.

## 2. Pin-by-pin reconciliation (13 existing failure classes)

| Pin | Original complaint | Current authoritative IDP evidence | Verdict on proposed remedy | First-use response / measured falsifier |
|---|---|---|---|---|
| 1 Instruction ingress | Agents manually create instruction after prompt | Existing `platform/estate/governance/founder_intake.py`, `platform/estate/memory/plan.py` and prompt/intents ledgers; no `instruction-wire-ingress.ts` in IDP `main` tree | **Partial; cross-surface capture coverage UNKNOWN** | Prove original prompt → durable ID → exact agent session on each declared ingress; missing adapter cannot silently invent custody |
| 2 Claim/lock | Manual CLAIM and ~28s network round trip | `bin/claim-open` already calculates changed paths, posts live CLAIM and stamps trailers; `bin/idp-machine-submit` performs a local overlap preflight; `bin/claim-gate` remains authoritative | **Substantial implementation exists; do not replace authenticated claims with unauthorised D1 cache** | Inject overlapping claims, stale cache, slow GitHub API, forged agent ID; reject collisions without rejecting safe work |
| 3 Commit history | Two agents in one range require repair | `bin/idp-machine-submit` explicitly refuses multi-agent ranges rather than silently rewriting ownership | **Old auto-squash recipe unsafe** | Assert original commit ancestry/QUAD principals preserved; exercise two-owner case, do not attribute predecessor edits to new agent |
| 4 Commit trailers | Hand-created Claim, Agent, Language-Exception | `bin/claim-open` already stamps Claim/Agent; `bin/language-gate` enforces path-specific reasons; machine-submit preannounces missing language exceptions | **Partly automated; don't invent privileged authorisation or generic language excuses** | Semantic exception approved by lawful authority, not merely a generated string; verify every added Python shebang/path |
| 5 ASCII hygiene | Reject decorative punctuation | `bin/idp-machine-submit` normalises selected Unicode in specified suffixes; local `DRY=1` supported | **Implemented for a subset; semantic mutation hazard** | Before/after diff content, UTF-8 fixture/translation preservation, generated code/string-literal safety; no blanket rewrite of user data |
| 6 Ruff/noqa | Formatter moves inline noqa | `bin/idp-machine-submit` runs `ruff format` then `ruff check --fix` but currently swallows failures (`|| true`); no proven AST-location repair | **Partial, with a real fail-silent concern** | Assert formatter/check exit code plus exact generated diff; prove multiline `noqa` case and idempotence before changed output is staged |
| 7 Worktree and detached HEAD | Disk proliferation and silent no-op | machine-submit explicitly refuses detached HEAD; `lane-submit.yaml` derives lane ref from arguments/branch and re-reads remote SHA; no current proof of effective worktree ban | **Risk reduced but unresolved as a complete class** | Detached HEAD, missing/blank lane, disk floor; no 0-exit when desired remote SHA is absent; no broad worktree deletion |
| 8 Pi plan-lock | Eight plan tool calls even for tiny fix | `extensions/pi-plan-lock` and `platform/estate/memory/plan.py` currently enforce goal/subgoal → BDD → edge case/effect → completion; shared ledger and executor-side gate are implemented | **RETAIN. Old “kill six tools” recommendation explicitly rejected pending effectiveness study** | Measure calls/duplicates/refusals/durations against independently verified outcomes and false refusal rate; avoid altered ceremony in initial observation |
| 9 Receipt quoting | Manual command hash in prose, relaunch loops | `bin/estate-receipt` exists; `platform/estate/governance/receipt.py` and executor step records exist; automatic host-to-client attachment unverified | **Partial/UNKNOWN** | Produce machine-attested exact command, exit, digest and off-host observer; never equate receipt integrity to effect truth |
| 10 Disk guardian | Self-DDoS at low disk | `launchd/ai.estate.disk-watch.plist.tmpl` explicitly retired on 2026-11-11 after documented resource failure; disk watcher absent in main | **Dangerous old proposed POSIX delete/KeepAlive remedy; do not resurrect** | Bounded one-shot safe cleanup only after provenance and before/after free-MB measurements; preserve user files and off-switch |
| 11 Vault | Agent shell handles SOPS and leaks credentials | Estate includes several Vault/SOPS/policy components; actual secret proxy and absence of leakage not verified in this audit | **Unverified** | Canary redacts logs; no direct secret in model, environment dump or artifact; verify short-lived least-privilege lease |
| 12 CI triage | Raw log trawling costs turns | `greenlane/forensics.py` and `greenlane/brief.py` exist; substantive failures distinguished from cosmetic failures; no independent proof of 2KB packet delivery to all agents | **Partial** | Real failing build → compact bounded packet with reason/evidence/log refs; compare time-to-fix without masking genuine failures |
| 13 Greenlane yield | Polls and abandoned work, fake 530 all-clear | `greenlane/engine.py`, `greenlane/brief.py`, `.github/workflows/greenlane.yml`, `platform/estate/intents/lane-submit.yaml` show actual status/proof mechanisms; `greenlane/brief.py` reports cost UNKNOWN when no receipt | **Source implementation exists; actual post-merge production readback still unverified** | Ref/commit status → exact landed SHA → exact deployed SHA → independent real consumer response → cost; failure cannot be labelled VERIFED YIELD |

**Critical negative finding:** The supplied installer calls `git reset --soft`, `git push --no-verify --force-with-lease`, removes lock files and moves governance extensions to a disabled directory. It uses fabricated default instruction/agent/issue identifiers. It must **not** be installed. A gate whose producer can grant itself exemption is not an assurance gate.

**Second critical finding:** `bin/idp-machine-submit` as currently implemented is a *preflighter and optional normalizer*, not the fully autonomous submit-and-integrate engine described in the old document. Its own output ends with manual `git commit` and `bin/lane-submit`. Do not report the 13 pins resolved merely because this file exists.

## 3. The one goal/subgoal architecture

**Goal G:** Every new capability earns independently witnessed value on first use while preserving useful agent reasoning, provenance and the ability to recover safely. Deliver safe, measurable automation of deterministic actions without sacrificing disciplined planning.

- **S1 – Source census:** map all ingress, worker, CLI, pre-push, GitHub Contents API, Greenlane, runtime and deployment paths to the actual owning canonical interfaces; missing path is a recorded coverage defect.
- **S2 – Prevent:** reject ungrounded operational success claims at the earliest producer, admit only authoritatively bound actions and preserve full original ownership/history. R&D can execute in truthful isolated mode.
- **S3 – Observe ceremony unchanged:** aggregate existing plan JSONL, refusals, unplanned and intent event counts without exposing raw prompts/commands/identities, without touching live gates. Establish baseline over real sessions.
- **S4 – Correlate outcomes:** join the ceremony records by authorised session/instruction to actual delivery, independent deployment witnesses, defect escapes, costs, elapsed times and interruptions. `UNKNOWN` when join missing.
- **S5 – Falsify and refine:** in matched cohorts, compare current ceremony with deterministic prepopulation of *equivalent* artifacts while maintaining same enforcement, goal/subgoals, BDD, edge cases and second-order checks. No unapproved gating removal.
- **S6 – Operate and teach:** continuously monitor the real estate, keep source-backed training labs and client-facing consulting examples clearly separated from verified customer claims; retire failure classes only after positive/negative live proof.

### Explicit acceptance examples

**Case A: AI Studio build with no durable source export**
Given an agent creates code in an isolated applet; when it tries to claim "DELIVERED
; then admission requires an accessible immutable source artifact, exact Git graph and an independently checkable trusted intake. Without them it is `SOURCE_NOT_IMPORTED`, not completed. A failed runner must prove its own runner-ready state before claiming an attempted integration is operational.

**Case B: a plan tool says “complete” but no deployed effect exists**
Given a goal and all subgoal plan tools; when `complete_goal` is called; then it creates a *declaration*, not an operational-success fact. The independent FLOW/KARMA proof chain alone may settle the obligation.

**Case C: seeded fake merged PRs and recovery counters**
Given code that modifies arrays and signs its own receipts; when it emits `VERIFIED_MERGED`, `$MRR`, “disk reclaimed” or “all green” over the normal API; then the producer must label the surface `RESEARCH_FIXTURE` or refuse the operational claim; a self-signed test receipt does not promote it.

**Case D: machine auto-healer crosses authority**
Given code touched by two agents, stale D1 lease cache, or a privileged `Language-Exception`; when the machine requests a single auto-squash, generic trailer or `--no-verify`; then refuse mutation or require authoritative identity. Recovery mode is bounded, observed and independently attested.

**Case E: trapped agent or resource floor**
Given a plan gate cannot write its ledger or disk is below floor; when a safe observation/disable/recovery call is made; then the system must allow the authorised minimal recovery door, report the gap as `BLIND`/`UNKNOWN`, and never silently bypass checks on production effects.

**Case F: ceremony removal proposal**
Given two comparable cohorts with the same objective and independent verifier; when the monitor measures model tokens, repeated calls, false refusals, escaped defects, elapsed time, resources and actual outcomes; then a removal is *only* considered if the replacement captures the same typed goals, BDD, edge/effects and proof coverage and improves first-pass verified yield without security or quality regression. Without a measured counterfactual: retain existing ceremony.

## 4. First observational instrument (canary, NOT another governance plane)

Source: `bin/idp-plan-ceremony-observe` and `tests/test_idp_plan_ceremony_observe.py`, standalone stdlib, read-only against existing `~/.estate/plans/` JSONL.

It reports counts of real session ledgers; goals declared; BDD; edge case/effect stage coverage; completion tool *claims*; repeated per-subgoal calls; out-of-order sequences; the existing refusal/anonymous-intent/unplanned event logs; malformed/absent logs as `PARTIAL_OR_BLIND`/`BLIND_NO_SESSIONS`. It does **not** publish source prompt text, command strings, private session IDs or plans. For now it reports event-span duration as a **non-cost** upper bound, and tokens, actual ceremony time, verified yield and causal delta as `null`.

**Proof of instrumentation at creation:** 12 negative/positive unit tests executed in a clean working environment, all pass. It is not yet evidence of real estate execution; no live `~/.estate/plans` files were supplied and no remote runner is verified. No controls are disabled or added to the enforcement path.

**Careful observational research design:** Collect 7–14 days *or enough genuine sessions for nontrivial cohorts*; preregister task type, agent, runtime, risk class, source SHA, expected actual outcome, and counterfactual. Add a small, measured bounded timing envelope at source rather than extrapolating time between plan calls to plan time. Compare paired tasks by difficulty and failure class, measure 95% uncertainty intervals on outcomes where sample allows, keep negative and indeterminate findings. Pilot only on low-risk internal tasks with safety controls unchanged.

## 5. Productisation / defensible intellectual property

- **Education:** students reproduce historical failure classes in isolated deterministic fixtures, identify the earliest producer fault, write a falsifier, and graduate only on independently measured effect—not dashboard screenshots.
- **Training & workforce:** a certified machine–agent split exercise requires the trainee to protect goal/subgoals, preserve proven safety gates, fix a mechanical failure without claiming someone else's identity, attach baseline and measurement, and demonstrate second-order effects.
- **Consulting:** engagements start with the 13-pin audit, a customer-specific source/authority graph, coverage map, marginal ceremony-cost experiment, recovery deadlock falsifier, and independent production-effect acceptance. Package the methodology, not fake customer ROI.
- **Future workflows:** the same typed boundaries travel across browser, desktop, mobile, voice and future devices; new transports must prove real first-use ingress and source custody. One capability implementation, multiple legitimate clients.
- **Research and IP claims:** separate what is newly implemented, previously known engineering practice, internal know-how, and commercially protectable work; obtain independent legal review before asserting patentability, uniqueness or customer-grade assurance.

## 6. Immutable limitations and release requirements

This review can establish **source-level** drift from the old writeup; it cannot establish installed runtime state or production yield. The canary is local-test-verified only until run on an authorised estate executor, with live evidence and exact integrated SHA. An issue, branch or report is not completion. Leave existing goal/subgoal, edge-case and second-order-effect rules enabled in every supported runtime. Any prevention escape creates a root-cause obligation; any non-reproducible experiment earns no research yield; any unverified production effect earns zero verified operational yield.

### Primary canonical pointers

- Existing goal/subgoal design: `docs/specs/2026-10-30-goal-subgoal-as-a-protocol.md`.
- Live plan model: `platform/estate/memory/plan.py`; Pi adapter: `extensions/pi-plan-lock/{index.ts,plan.ts,cases.json}`.
- Single execution door: `platform/estate/bin/estate-execute`, `platform/estate/intents/lane-submit.yaml`.
- Deterministic preflight: `bin/idp-machine-submit`, verified Claim: `bin/claim-{open,gate}`, language evidence: `bin/language-gate`.
- Factual post-commit: `greenlane/{engine,forensics,brief}.py`, `.github/workflows/greenlane.yml`.
- Existing accountable-yield doctrine: `docs/training/2026-11-12-karma-operating-doctrine.md` and `AGENTS.md`.
- Existing founder operating/first-use law issue: `chidionyema/idp#7771`.