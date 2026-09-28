# Spec: the circuit breaker — three identical findings lock the primitive

Founder, 2026-09-12: *"write the interceptor to hash the outputs and throw the 423 Locked
exception at N=3."*

## What it does

An agent is free to diagnose. It may query, read or act on individual targets as much as the
work needs. When three targets return the **same finding**, the diagnosis is proved: there is one
cause, and the next linear action is waste. The breaker then:

1. **Locks the primitive** for that finding's target set. The next attempt is `HTTP 423 Locked`.
2. **Names the lever.** The only thing accepted afterwards is the fleet-level action.

The agent is not asked to be clever. It is refused the linear path once the pattern is proved.

## Two rules that keep it from being an outage (R38)

**A fingerprint, not a raw hash.** The same cause prints different bytes on different targets.
Measured today: six pull requests failed with identical `perl-base` CVEs at different log
positions and different stacks. Hashing the raw output would never have matched. The fingerprint
is the **stable identity of the finding** — for the measured case, the sorted set of CVE ids:

    CVE-2026-13221 CVE-2026-42496 CVE-2026-8376     -> one fingerprint, six targets

**Scoped to the targets that showed it.** The lock binds the fingerprint to the set of targets
that produced it, not to a tool. A seventh target with a *different* fingerprint is a new thing
and stays fully open. That is what keeps nine PRs with nine different failures fully workable.

## Interface

    breaker.observe(fingerprint, target)   -> record a finding against a target
    breaker.check(fingerprint, target)     -> allow | LOCKED

    check returns:
      {"locked": False}                                     the action may proceed
      {"locked": True, "status": 423,
       "message": "423 Locked: proven pattern (N=3) ...",
       "lever": "<the fleet action>"}                       the primitive is dead

## The lever

The breaker must name what to do instead, or it is a wall with no door. For the measured class
(a finding on many pull requests) the lever is the estate's own mechanism:
`gh workflow run merge-when-green.yml`, which refreshes every branch at once.

## Tests (failing until built)

1. `test_one_finding_is_not_locked` — flow is preserved for a single target.
2. `test_two_findings_are_not_locked` — N=3 means three.
3. `test_three_identical_findings_lock_the_primitive` — 423, and the status is on the result.
4. `test_the_lock_message_names_the_lever` — a wall with no door is an outage.
5. `test_nine_different_findings_never_lock` — the R38 case: nine PRs, nine causes, all workable.
6. `test_a_new_target_with_a_new_finding_is_not_locked` — the lock is scoped by fingerprint.
7. `test_a_different_fingerprint_on_a_locked_target_is_allowed` — the lock is not on the tool.
8. `test_the_fingerprint_is_order_independent` — the same CVE set in a different order is one finding.
9. `test_the_fingerprint_ignores_log_noise` — line numbers and stacks differ; the cause does not.
10. `test_it_is_not_decorative` — after the lock, `check` refuses the fourth target.

## Acceptance

    python3 -m pytest tests/test_circuit_breaker.py   all pass
    python3 -m ruff check bin/idp-circuit-breaker     clean
    python3 bin/law32-gate                            ok
