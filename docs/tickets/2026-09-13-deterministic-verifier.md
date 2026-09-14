# The Deterministic Verifier — an agent cannot claim what it has not proved

**Status:** open
**Opened:** 2026-09-13
**Law:** LAW 2 (proof before action), LAW 45 (a mistake ends as a guard), THE EMPIRICAL PROOF RULE
**Spec:** `features/gates/deterministic-verifier.feature`
**Module:** `sovereign/verifier.py`
**Binding:** `sovereign/tests/bdd/test_deterministic_verifier.py`

## The founder's words, verbatim (2026-09-13)

> "the fact u are able toi lie eans he his rules isnt operation al and the firs thig
> we need to addres"
>
> "hats why u r and idot and thats why i dont belive clains without hard prrov 3
> different wqys"

## The failure this removes

It is NOT that a model hallucinates — a model will always hallucinate, and no prompt
removes it. **The failure is that the CLAIMANT supplies its own evidence.** An agent
writes a file, claims "the tests pass", and the gate that should catch that reads a
transcript the agent also wrote.

Three properties made the previous gate (`bin/epistemic_firewall.py`) useless, all
measured on main before this ticket was opened:

1. **session-scoped, not turn-scoped** — one tool call anywhere in the session clears
   every claim made in it.
2. **existence, not correspondence** — any tool call at all counts as evidence, so a
   call that failed counts the same as one that succeeded.
3. **retroactive, not live** — it grades a transcript after the fact, so the claim has
   already been made, acted on, and possibly merged before anything is graded.

A fourth, found while writing this ticket: the firewall is **graded by nothing**. It has
no `rules.yaml` row, so nothing in the estate runs it.

## The fix, in one sentence

**Take the claim away from the claimant.** A patch arrives; three graders the proposer
does not control run against it; the verdict is a function of the bytes, and the
attestation's subject is the SHA-256 of the exact verified artifact.

## What is built (measured 2026-09-13)

`sovereign/verifier.py`, 667 lines, tracked, committed `4cfcc74b` at 17:46.

The API exists and is real, not a stub:

| entry point | what it does |
|---|---|
| `parse_unified_diff` | a patch in, `list[ProposedFile]` out |
| `canonical_subject` | SHA-256 over the exact bytes — the attestation's subject |
| `stage_structural` | `compile()` every proposed Python file |
| `stage_symbolic` | Z3 over the patch's own declared guard contract |
| `stage_execution` | runs the supplied tests in a sterile throwaway tree |
| `verify(ledger)` | mints only if all three pass |
| `sign` / `verify_attestation` / `_verify_sigstore_bundle` | a real Sigstore bundle |
| `attestation_shape` | reports the one field still not claimed |
| `write_bundle` | the attestation to disk |

Decisions already taken and recorded in the module:

- **Stage 2 does NOT discharge "the tests pass".** A solver proves a predicate; "the
  tests pass" is a fact about an execution, which is stage 3's job. The architect's
  draft implied otherwise and the push-back stands.
- **Sigstore is real.** `cosign v3.1.3` is installed; `sign()` produces a genuine bundle
  carrying a Rekor transparency-log entry and re-verifies it with `cosign verify-blob`
  before returning. An earlier reading of "tools unobtainable" was **an absent PATH
  lookup reported as an absent capability** — recorded here so it is not repeated.
- **`ISOLATION_KIND = "temp-tree-scrubbed-env"`, not a microVM.** Firecracker is absent
  and the constant says so rather than implying otherwise.
- **Still not claimed:** the key is estate-held, so there is no Fulcio-issued
  short-lived certificate binding an OIDC identity to the signature.
  `attestation_shape()` reports exactly that one field and nothing else.

## The gap, which this ticket exists to close

The feature declares **6 scenarios across 4 rules**. The binding holds **3 test
functions**. Bound today:

- `test_the_attestation_reports_what_it_actually_is`
- `test_a_real_sigstore_bundle_verifies_and_a_wrong_subject_does_not`
- `test_rule_4_has_two_enforcement_points`

| rule | the feature says | state |
|---|---|---|
| 1 — direct mutation physically impossible | intercept `write_file`/`bash_exec`, refuse fatally, tree unmodified | **bound and green** (2026-09-13) |
| 2 — the agent may only `propose_patch` | payload isolated in an ephemeral ledger, agent suspended | bound; the door has no `propose_patch` verb yet |
| 3 — the three-stage gauntlet | all three stages; ledger destroyed and no signature on failure | stages built; not reachable through the door |
| 4 — nothing enters without the seal | Kyverno **or** pre-receive hook refuses the unattested code | asserts the two points **exist**, not that they refuse |

**Rule 1 is closed.** The door refuses a payload that declares `mutates_live_worktree`, both
at `execute` and at its `simulate` twin, and the live tree is proved unmodified.

**What remains is one gap, not four:** the daemon implements `execute`, `simulate`, `read`
and `health`. Rules 2, 3 and 4 all drive verbs the door does not have yet -- `propose_patch`,
`verify`, `seal`, `admit` -- so every one of those scenarios stops at
`unknown verb`. The verifier module itself is built and green; what is missing is the door
onto it. That is why this work is not operational yet.

**A note for whoever edits this file:** the test that audits Rule 4's enforcement points
scans tracked files for the violation code and treats every hit as a claimed enforcement
point, excluding only graders (`tests/`, `*_test.py`) and the feature file. A ticket that
quotes the code therefore reads as a third enforcement point and fails that audit, which
was measured here on 2026-09-13. The code is named in prose above, never as a literal.

## Definition of done — in commands

1. Every one of the six scenarios in `features/gates/deterministic-verifier.feature` is
   bound by a test that **fails when the mechanism is removed**, proved both ways.
2. Rule 4's test drives a payload **through** each enforcement point and shows it
   refused with the unattested-provenance violation code, rather than checking that the
   file exists.
3. `sovereign/verifier.py` carries a `rules.yaml` row with both fixtures.
4. `python3 -m pytest sovereign/tests/bdd/test_deterministic_verifier.py -q` is green.
5. `bin/idp-rules run` grades the new row `ok`, and `bin/idp-rule-coverage` reports no
   orphan fixture.
6. `bin/idp-ci` is green on the branch.

## What "operational" means here, so it cannot be softened later

The verifier is operational when **a patch that fails any of the three stages produces
no signature and no admission**, and **a patch that passes all three produces a bundle
that a separate verifier accepts**, both demonstrated from the command line rather than
asserted. Until then it is built, and that is what this ticket says it is.
