# Definition of Done (Hard v2.1)

Founder policy, handed over 2026-08-25 as `AGENTS_md_DoD_v2_1.pdf`. Transcribed verbatim in
substance; the founder's wording is kept where it was prose. Enforced from 2026-08-25. The reply
shape it demands is enforced by `dod-guard.py` in the `claude-guards` repository (a Stop hook);
the mechanical gates it names are tracked on the crew board until each one exists and blocks
merge in CI.

## 1. The Golden Rule

**A feature is NOT done until the Founder has used it end-to-end and confirmed it works.**

Merged code, green CI, and passing tests are inventory. They are not progress. The only valid
state transition to `done` is an explicit founder confirmation receipt.

## 2. The Five Gates (all must pass)

Every deliverable, whether code, doc, config or policy, must pass all five gates before the
`done` transition is allowed.

### Gate 1: Founder Validation

- Founder has operated the feature end-to-end on the surface they normally use (web, Telegram,
  voice, or menu bar).
- Founder has emitted a confirmation receipt (tap, message, or PIN entry).
- Zero founder follow-up questions exist in any channel about how to use it, what it does, or why
  it behaves a certain way.
- The feature has survived 24 hours of real use without a bug report, confusion, or workaround.

Enforcement: any `done` claim without a Merkle-signed founder confirmation receipt in the
interventions log is rejected.

### Gate 2: Automatic Non-Functional Enforcement

Non-functionals are gates, not tickets. CI blocks merge if any check fails. No follow-up work
items. No "document later."

| Check | Command | Blocks merge if |
|---|---|---|
| Documentation | `mkdocs build` + docstring lint | Doc build fails, or any public API lacks a docstring |
| Onboarding | `bin/estate-bootstrap` on a clean machine | Bootstrap fails, or the feature errors on first run |
| Demo | `bin/estate-demo <feature>` | Fails or exceeds 30 seconds |
| Test coverage | BDD harness strict mode | New code path lacks a scenario, or coverage regresses |
| Observability | Langfuse trace audit | New feature lacks a trace, or an error path lacks an alert |
| Security | `bin/estate-security-scan` | Scan fails, secret detector triggers, or an unaudited dependency is added |
| Performance | Latency budget check | p95 exceeds budget or regresses more than 10% |
| Accessibility | Mobile render + button audit | Telegram message lacks action buttons, or web view fails mobile render |

Enforcement: the CI run hash is read. If any check is red, the `done` transition is illegal.

### Gate 3: Hard-to-Fake Evidence

Claims without evidence are lies. Every `done` assertion must attach one piece of cryptographic
or verifiable evidence.

| Claim | Required evidence |
|---|---|
| "Feature works" | Founder confirmation receipt with session Merkle hash |
| "Docs exist" | Rendered MkDocs URL + `git diff` showing docstrings in the PR |
| "Onboarding works" | Terminal log or recording of `bin/estate-bootstrap` on a clean machine |
| "Demo works" | `asciinema` cast or terminal log of `bin/estate-demo` completing in under 30s |
| "Tests pass" | CI run URL with green checkmark + coverage report |
| "Security passes" | `bin/estate-security-scan` output with timestamp and commit hash |

Enforcement: evidence hashes are verified against the session DAG. Missing evidence is an
automatic `not_done` flag.

### Gate 4: Handoff Protocol

When work moves from one agent to another, or from agent to founder, the handoff contains exactly
five items. Missing one is a dropped ball and the handoff is rejected.

1. **What was built**: one sentence, plain English, no jargon.
2. **How to use it**: exact command, button sequence, or voice phrase.
3. **What to expect**: exact output, behaviour, or state change.
4. **What is NOT done**: honest list of gaps, limitations, or known issues.
5. **Evidence**: Merkle receipt, CI URL, demo link, or scan output.

Enforcement: a handoff missing any item is routed back to the sender with a
`handoff_incomplete` receipt. In agent replies the five items are the lines `Built:`, `Use:`,
`Expect:`, `Not done:`, `Evidence:`; `dod-guard.py` refuses an `INVENTORY:` reply without them.

#### Architecture laws block (in every PR body)

Four rows from the founder's Living Estate doc (2026-08-25), one line each; `n/a: <why>` is
an answer, a missing row is not. Source of record for the `## Architecture laws` section
that `dod-guard` expects.

- **LAW 1 zero-gravity:** does the change add a cloud-provider, machine or account string?
  Receipt: `bin/cloud-agnostic-gate` (idp) or the repo's equivalent.
- **LAW 2 fractal:** does a changed service keep the same shape as every other service:
  catalog entity, real health probes, traces to the estate collector?
- **LAW 3 nervous system:** which alert, trace or test tells us when this breaks?
- **LAW 4 calibration:** what number did the PR predict, and what was measured?

### Gate 5: Exceptional Quality Standard

"Good enough" is not done. The feature must meet this bar:

- The founder never has to ask "how do I…". If they ask, onboarding failed.
- The founder never has to report the same bug twice. If they do, the fix was not done.
- The founder never has to hunt for documentation. If they search for more than 30 seconds, docs
  failed.
- The founder never has to remember a command. If it requires memorisation, the UI failed.
- The founder never has to context-switch to approve routine work. If it interrupts deep work,
  the presence model failed.

Enforcement: founder questions, bug reopen counts, doc search time and interruption frequency are
tracked. Any metric above threshold auto-flags the feature as `not_done`.

## 3. Non-Functional Requirements (the auto-enforced contract)

Measurable, machine-verifiable thresholds. Every PR is rejected if any threshold is missed.

### 3.1 Performance

| Metric | Threshold | Measurement | CI gate |
|---|---|---|---|
| API response p95 | < 2 s | Langfuse trace aggregation | `perf/latency` |
| Agent step p95 | < 10 s | Step-level trace timing | `perf/agent-step` |
| State commit latency | < 50 ms | `synaptic_bus.commit_state()` timing | `perf/commit` |
| Budget check latency | < 5 ms | `transition()` optimistic lock timing | `perf/budget` |
| Web dashboard TTFB | < 500 ms | Browser Lighthouse / curl | `perf/web` |
| Telegram receipt render | < 1 s | Bot message delivery timing | `perf/telegram` |

Regression rule: any metric regressing more than 10% from baseline blocks merge.

### 3.2 Reliability

| Metric | Threshold | Measurement | CI gate |
|---|---|---|---|
| Agent uptime | > 99.5% | Healthcheck ping over 7 days | `reliability/uptime` |
| Session resume success | 100% | Checkpoint read + state reconstruction | `reliability/resume` |
| Receipt chain integrity | 100% | Merkle hash verification on every read | `reliability/integrity` |
| Auth success rate | > 99.9% | Valid challenges / total challenges | `reliability/auth` |
| Budget enforcement accuracy | 100% | Zero overspend events in test suite | `reliability/budget` |

Failure rule: any reliability metric below threshold is an immediate `not_done`.

### 3.3 Security

| Metric | Threshold | Measurement | CI gate |
|---|---|---|---|
| Static secrets in codebase | 0 | `bin/estate-security-scan` + truffleHog | `security/secrets` |
| Unaudited dependencies | 0 | `pip-audit` / `npm audit` | `security/audit` |
| Vulnerability severity High+ | 0 | `safety check` / `snyk test` | `security/vuln` |
| Policy contradiction | 0 | AGENTS.md compilation check | `security/policy` |
| SVID expiry without re-enrolment | 0 | SPIRE agent healthcheck | `security/identity` |
| Unauthorised capability invocation | 0 | Auth FSM audit log review | `security/auth` |

Breach rule: any security metric non-zero is lockdown. All non-essential agents halt. Founder
alert via the catastrophic channel.

### 3.4 Observability

| Metric | Threshold | Measurement | CI gate |
|---|---|---|---|
| Feature trace coverage | 100% | Every new feature emits at least 1 Langfuse trace | `observability/trace` |
| Error alert coverage | 100% | Every error path emits at least 1 alert | `observability/alert` |
| Log retention | 30 days hot, 1 year cold | R2 backup verification | `observability/retention` |
| Audit trail completeness | 100% | Every auth decision, state commit and intervention has a receipt | `observability/audit` |
| Dashboard freshness | < 5 minutes | Last state commit timestamp vs. now | `observability/freshness` |

Blind rule: any observability gap is a halt. Blind execution is unacceptable.

### 3.5 Accessibility (solo founder)

| Metric | Threshold | Measurement | CI gate |
|---|---|---|---|
| Surface coverage | 100% of v1 surfaces | Feature works on Telegram, Web, Voice | `accessibility/surface` |
| Mobile render | Pass | Browser devtools mobile viewport test | `accessibility/mobile` |
| Action button presence | 100% | Every Telegram message has at least 1 action button | `accessibility/buttons` |
| Voice command coverage | 100% of v1 commands | Every v1 command has a voice phrase | `accessibility/voice` |
| Tutorial presence | 100% | Every feature surfaces interactive guidance on first use | `accessibility/tutorial` |
| Recovery path clarity | 100% | Every feature has one obvious recovery command | `accessibility/recovery` |

Friction rule: any accessibility failure means the founder cannot operate alone, which is
`not_done`.

### 3.6 Maintainability

| Metric | Threshold | Measurement | CI gate |
|---|---|---|---|
| Test coverage | > 90% | `pytest --cov` | `maintainability/coverage` |
| BDD scenario coverage | 100% of user-facing paths | Strict mode harness | `maintainability/bdd` |
| Docstring coverage | 100% of public APIs | `pydocstyle` / `mkdocs build` | `maintainability/docs` |
| Cyclomatic complexity | < 10 per function | `radon cc` | `maintainability/complexity` |
| Dependency freshness | No critical lag | `pip list --outdated` | `maintainability/deps` |
| Onboarding time | < 5 minutes | `bin/estate-bootstrap` timing | `maintainability/onboard` |

Debt rule: any maintainability failure is technical debt accrual. Debt above 5% of the codebase
is a feature freeze until paid down.

### 3.7 Scalability (free-tier constraint)

| Metric | Threshold | Measurement | CI gate |
|---|---|---|---|
| Mac CPU under normal load | < 70% | `top` / psutil | `scalability/cpu` |
| Mac memory under normal load | < 80% | `vm_stat` / psutil | `scalability/memory` |
| Storage growth | < 1 GB/week | `du -sh ~/.estate` | `scalability/storage` |
| API cost per 1k operations | < $0.50 | LiteLLM spend tracking | `scalability/cost` |
| Local model inference ratio | > 60% | Ollama vs. API routing log | `scalability/local` |

Bloat rule: any scalability threshold exceeded requires immediate optimisation. No new features
until resolved.

## 4. The Solo Founder Amendment

The founder is the builder, the operator, and the validator. There is no crew to hide behind.

- **The feature is operable by the founder from any device they own**: laptop, phone,
  or voice, without asking anyone.
- **The system must teach the founder, not a manual.** Every surface offers interactive guidance
  on first use.
- **One recovery path per feature.** If anything breaks, the fix command is obvious and works on
  every surface.
- **No one else is required.** If a feature needs external help to configure or fix, it is not
  done.

## 5. Violation Penalties

| Violation | Action |
|---|---|
| Claim `done` without founder receipt | Reject transition, flag as `inventory`, alert founder |
| Claim `done` without evidence | Reject transition, flag as `unverified`, require evidence upload |
| Merge PR with red non-functional gate | Block merge, require fix before retry |
| Handoff missing one of five items | Bounce back to sender, log as `dropped_ball` |
| Founder asks "how do I…" about a `done` feature | Auto-flag feature as `not_done`, reopen ticket |
| Same bug reported twice on a `done` feature | Auto-flag feature as `not_done`, require root-cause evidence |
| Non-functional threshold missed | Block merge, require optimisation or justification |
| Security metric non-zero | Lockdown: halt all non-essential agents, catastrophic alert |

## 6. Policy Update Rules

This policy is versioned and content-addressed. Any update requires:

1. A new policy hash computed by the kernel.
2. A 24-hour time lock before activation.
3. Founder confirmation via hardware-rooted signature (Tier 1).
4. The old policy remains readable for audit forever.

Current version: `policy:v2.1` (hash: `git hash-object docs/policy/definition-of-done.md`).
Enforced from: 2026-08-25. Next review: on demand by founder, or auto-flag if the violation rate
exceeds 5% per week.

## Status of the gates on 2026-08-25

Stated so nobody claims a gate that does not exist. Each missing item is a row on the crew board.

| Gate or tool | Exists today |
|---|---|
| Reply shape (DONE needs receipt, INVENTORY needs five lines) | yes, `dod-guard.py` Stop hook |
| `bdd` job strict on main, `offline-gate` in CI | yes, `.github/workflows/ci.yml` |
| `mkdocs build` | `mkdocs.yml` exists; not yet a merge-blocking job with docstring lint |
| `bin/estate-bootstrap` | no |
| `bin/estate-demo` | no |
| `bin/estate-security-scan` | no (`bin/security-policy-gate`, `bin/supply-chain` exist and are the base) |
| Coverage report in CI | no |
| Founder confirmation receipt with Merkle hash | no; `sovereign` receipt chain is the base |
| Latency, reliability, scalability gates | no |
