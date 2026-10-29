# ESTATE — Adversarial Engineering Audit and CI/CD Acceleration

Date: 2026-10-27
Status: INITIAL SOURCE INSPECTION; NOT A LIVE PRODUCTION CERTIFICATION
Repository: `chidionyema/idp`

## Scope and evidence standard

Four product surfaces: Otto, Face, Fleet, voice engine. Cross-cutting: CI/CD throughput and verification. Findings are tagged VERIFIED-SOURCE (observed in fetched repository content), HISTORICAL-REPORTED (described by a repository specification but not reproduced), or UNVERIFIED (requires live evidence). No claim of live deployment health is made.

## F-001 — CI verifier exit-status inversion [P0, VERIFIED-SOURCE]

Source: `.github/workflows/verifier.yml`, `run verifier gauntlet` step. Existing code:

```sh
if ! echo "$diff_out" | python3 bin/idp-ci-verify; then
  rc=$?
  echo "verifier verdict: FAIL (exit $rc) — an unproven diff does not pass"
  exit "$rc"
fi
```

Shell `!` negates the pipeline status, so `$?` within the `then` branch is zero for a failing verifier. This can turn a verifier failure into a successful job. Independent reproduction is required with a deliberately failing fixture; do not claim the job is secure until the fixture is refused.

Candidate correction (subject to tested shell semantics):

```sh
if echo "$diff_out" | python3 bin/idp-ci-verify; then
  echo 'verifier verdict: PASS'
else
  rc=$?
  echo "verifier verdict: FAIL (exit $rc)"
  exit "$rc"
fi
```

Acceptance: known-good passes; known-bad and BLIND fail; required pre-merge context fails closed; no pipeline/pipefail regression. Preserve actual failure code.

## F-002 — Fast-gate exempts bot-authored changes [P1, VERIFIED-SOURCE]

Source: `.github/workflows/fast-gate.yml`. A `bot exemption` step marks `*[bot]` and `estate-agent*`; lint/dependency setup and strict checks run only when `bot != '1'`. A separate verifier explicitly has no bot exemption. Risk: autonomous authors bypass important fast-gate checks. Measure bot PR frequency, reasons for exemption, and whether equivalent checks execute elsewhere. Remove or replace exemptions only after validating GitHub identity/event semantics and runner economics.

Acceptance: same minimum structural/security/lint checks for human and agent code; targeted regression fixture for bot-authored PR; no increased false green.

## F-003 — Otto has documented historical real-path failure [P0, HISTORICAL-REPORTED]

Source: `docs/specs/2026-10-23-founder-agent-gate.md` (#6921). Documents HTTP 400 `No connected db` on two attempts, no model invocation, synthetic probes green; inventory 19/56 graded, 37 ungraded. These are historical, not verified as present today.

Adversarial tests: real Telegram/Face/Fleet/console path; identity and binding; router, budgets and actual provider call; dedup; exactly-once user-visible response; stop-on-budget; real browser, calendar, file and email tasks; provenance of tool actions; truthful refusal. Freeze the existing 30-task × three-run gate and independently verify receipts. No Otto 'ready' label until current production-path gate passes.

## F-004 — CI throughput and gate placement [P1, VERIFIED-SOURCE/HISTORICAL-REPORTED]

Source: `.github/workflows/ci.yml` and `.github/workflows/fast-gate.yml`. Comments record historical queue eviction on main, missing merge_group events, 451/586 seconds in per-file Kyverno invocations, and improvements through batching, diff scoping, SHA-specific concurrency, and fast-gate. These comments are evidence of design decisions, not live current timing.

Instrument: queue latency; runner allocation; checkout; dependency installation; cache hit rate; per-step wall time; CPU and memory saturation; tests selected and skipped; flaky retry count; PR-to-verified-merge time; production proof time; defect escape rate. Benchmark 30–100 recent runs by change class, actor, branch and job. Protect pre-merge admission; never shift required verification after merge solely to improve headline CI duration.

Potential controlled experiments: eliminate redundant checkout where safe; lockfile-keyed caches; prebuilt pinned runner images; sharding based on measured durations; test impact selection with full periodic sweeps; speculative parallel test legs after cheap gates; deduplicate equivalent candidate SHAs; immutable attested verification receipts; separate quick feedback from authoritative pre-merge and production gates. Each requires measured baseline, regression coverage and rollback.

## F-005 — Face [P1, UNVERIFIED]

Inspect frontend source, routes, design system, rendering path, deployed environment, telemetry and E2E suites. Hostile journeys: cold launch, auth expiry, offline/slow network, stale Oracle evidence, concurrent status updates, screen reader, reduced motion, mobile viewport, avatar/voice session transitions, API failure, visual regression, and latency under load. Require independently captured user-journey receipts and p50/p95 performance, accessibility and error budgets.

## F-006 — Fleet [P1, UNVERIFIED]

Inspect worker lifecycle, queue/claim implementation, lease expiry, concurrency budgets, dedup, task dependency DAG, retries, heartbeats and progress estimation. Hostile tests: duplicate claim, crashed worker, network partition, dead-letter replay, priority inversion, starvation, orphaned tasks, partial completion, conflicting write and falsely claimed success. Metrics: verified outcomes/hour, idle capacity, queue age, claimed-vs-completed, work-in-flight, cost per verified outcome, p95 completion and estimated-vs-actual duration.

## F-007 — Voice engine [P1, UNVERIFIED]

Split responsibility: Engineering owns streaming runtime; Media owns voice identity and performance; Face owns interaction; Science evaluates models; QA owns independent E2E gates. Inspect STT/TTS providers and routing, local model availability, consent/privacy, barge-in, endpointing, audio buffering, packet loss, silence detection, duplex behaviour, language coverage, session recovery and cost. Test p50/p95 time to first audio, interruption stop latency, recognition error rate, conversational success, cross-device and noisy-environment performance. Repository inventory reports TTS/STT providers IN THE IMAGE, which is not evidence that they work on the live ingress path.

## Programme reconciliation

Use existing #7256 transformation claim and master epic as programme of record. Read `docs/specs/2026-10-26-machine-first-agent-action.md`, `docs/specs/2026-10-26-context-compiler-and-execution-gateway.md`, `docs/specs/2026-10-26-efda-spine.md`, #6921 founder-agent gate, #7034 Face/Fleet, #7263 NSVEE, and existing policy/definition-of-done documents. Do not create duplicate bus, registry, scheduler or evaluator. Preserve NATS→Temporal→Aevum evidence spine and existing Greenlane admission; verify deployed reality before claiming completion.

## Audit closure contract

Each finding needs source permalink+SHA, reproduction steps, observed evidence, impact, priority, owner, remediation PR, independently failing regression fixture before fix, passing fixture after fix, current deployment receipt, cost/latency delta, and final status. `UNKNOWN` is a valid status; synthetic green is not a production receipt. No production change was made in this audit.
