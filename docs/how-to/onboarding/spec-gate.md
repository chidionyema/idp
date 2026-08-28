# Onboarding: spec-gate

## What it is

`bin/spec-gate [BASE_REF]` lists the files changed between the merge base of
`BASE_REF` (default `origin/main`) and `HEAD`, and applies one rule:

- **code**: `.py .ts .tsx .js .jsx .go .rs .sh .rb .java .kt .swift` files and
  anything under `bin/` that is not itself a spec
- **spec**: `*.feature` files; anything under `tests/`, `test/`, `spec/` or
  `features/`; `test_*.py`, `*_test.*`, `*.test.*`, `*.spec.*`; the live
  diagram generator `bin/estate-diagram`

Code changed and no spec changed: exit 1, the code files are printed. No code
changed, or a spec changed with it: exit 0. Base ref not found: exit 3, BLIND.

## Why it exists

Founder ruling R29, 2026-08-25, after a peer agent answered "can you
guarantee the documentation stays current" with "no": documentation that lives
outside the execution path rots, so the only spec that counts is one CI runs.
"Every PR must update the BDD scenario or the auto-gen script. If the PR
changes code but not the executable spec, the CI blocks merge. No manual doc
updates." Tracked on crew#236.

## Where it runs

- idp: the `spec-gate` job in `.github/workflows/ci.yml`, required by ruleset
  `idp-required-checks`.
- Every repository pushed in the last 30 days: the same job from
  `.github/workflows/security-scan.yml` (installed by
  `bin/estate-security-rollout`), required by ruleset `estate-security-scan`.
- By hand before pushing: `bin/spec-gate` on the branch.

## What it cannot see

It grades file names, not content. A one-line no-op edit to a `.feature` file
satisfies it. The reviewer session (crew review-gate) is the check on that;
this gate removes the case where nobody touched the spec at all.

## Related files

```
bin/spec-gate                                   the rule
.github/actions/spec-gate/action.yml            the composite action other repos call
sovereign/tests/test_incident_r29_spec_gate.py  proves refuse and permit in one run
features/gates/estate_gates.feature             the scenarios
platform/github/ruleset.@active.security-scan.json
                                                required checks for active repos
```
