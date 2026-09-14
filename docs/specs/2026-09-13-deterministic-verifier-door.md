# Spec — the door onto the Deterministic Verifier

**Why.** `sovereign/verifier.py` (667 lines) is built, green and green-proved. The daemon
(`platform/executor/daemon.py`) exposes four verbs: `execute`, `simulate`, `read`, `health`.
The feature `features/gates/deterministic-verifier.feature` drives four more -- `propose_patch`,
`verify`, `seal`, `admit` -- so Rules 2, 3 and 4 stop at `unknown verb` and the verifier is
unreachable from the agent's own door. Built, not operational.

**Acceptance test (the ONLY definition of done).** Every scenario in the existing, already
written and already failing suite:

```
cd sovereign && python3 -m pytest tests/bdd/test_deterministic_verifier.py -q -p no:cacheprovider
```

must exit 0. Measured baseline 2026-09-13: **6 failed, 3 passed.** The three that pass are the
module's own honesty assertions and must STAY passing. The six red are the acceptance test.

**Boundary.** Do not edit `sovereign/tests/bdd/test_deterministic_verifier.py`. Do not edit
`sovereign/verifier.py` unless a step genuinely cannot be satisfied by wiring, and say so in
the summary if you do. The work is the door, not the verifier.

---

## The four verbs, and the exact contract each must satisfy

All four are new branches in `Handler.handle`'s verb dispatch in `platform/executor/daemon.py`,
in the same place and the same shape as the existing `execute`/`simulate`/`read`/`health`
branches. An unknown verb still falls through to the existing refusal -- do not remove it.

### 1. `propose_patch`

Request: `{"verb": "propose_patch", "patch": <unified diff str>, "tests": <str>, "claim": <str>}`

Reply must carry:
- `ok: True`
- `ledger_id`: a non-empty string
- `ledger_dir`: a path that **is a directory**
- `suspended: True`

Constraints the test grades:
- The ledger directory must NOT contain a `.git` entry -- it is "sterile", never a worktree of
  the live repo. Use a fresh temp tree.
- The ledger must NOT live inside the live worktree, and the proposed file (`greeting.py` in the
  step's patch) must NOT appear in the live worktree.
- `{"verb": "health"}` must then report `ledgers_pending >= 1`.
- `sovereign.verifier.parse_unified_diff` already returns `ProposedFile(path, lines)`. Use it.
  Write the proposed files into the ledger tree.

### 2. `verify`

Request: `{"verb": "verify", "ledger_id": <str>}`

Reply must carry:
- on failure: `ok: False`, `stderr` (the stage's OWN real message -- see below), `attestation: None`,
  `ledger_dir`, `claim_verdict`
- on success: `ok: True`, `subject_digest`, `attestation` (non-None), `admissible: True`,
  `staged_path` (an existing file), `receipt` (a string), `claim_verdict`

Constraints the test grades:
- **The ledger directory is destroyed afterwards in BOTH cases.** The test asserts it does not
  exist after `verify` returns, for every failing stage.
- `stderr` must carry the real cause, not a paraphrase:
  - the structural stage's message must contain `SyntaxError` or `invalid syntax`
  - the **symbolic** stage's message must contain the literal word `counterexample` -- Z3 must
    genuinely refute the guard. `sovereign/verifier.py:stage_symbolic` already does this.
- `claim_verdict` must be exactly `"refuted"` when the patch failed and the claim was disproved
  (the test parses the expected verdict from the feature file -- read the scenario text and match
  it; `verifier.verify()` already returns a `claim_verdict` key, so prefer relaying it verbatim
  over inventing one).
- All three stages must be reachable and must fail for the three separate broken inputs the test
  submits. A design where the first failing stage removes the ledger such that the other two can
  never be exercised is what the test's `set(...) == {structural, symbolic, execution}` assertion
  exists to refuse -- so each `propose_patch` gets its OWN ledger and `verify` is called once per
  ledger.
- After a successful `verify`, `{"verb": "health"}` must report `ledgers_pending == 0`.

### 3. `seal`

Request: `{"verb": "seal", "payload_path": <str>, "tests": <str>, "stages": {...}}`

Reply must carry `ok: True` and an `attestation` dict whose shape
`sovereign.verifier.verify_attestation(attestation, subject)` accepts. The test does not unpack
`seal`'s attestation beyond `ok` and `attestation`, so relay the verifier's own envelope.

### 4. `admit`

Request: `{"verb": "admit", "payload_path": <str>}` and
`{"verb": "admit", "payload_path": <str>, "attestation": <dict>}`

Unattested (no `attestation`): reply must carry `ok: False`, `intercepted: True`,
`violation_code: "UNATTESTED"`, and NO `admitted_path`.
  -- This is the file that makes `platform/executor/daemon.py` an enforcement point. It is why
  the literal code appears in the daemon and why the daemon is listed twice in the audit below.

Attested and valid: reply must carry `ok: True`, `validated: True`, `admitted_path` -- a file that
**exists** and whose bytes equal the sealed payload's bytes. Use
`sovereign.verifier.verify_attestation`. A tampered or wrong-subject attestation must NOT admit.

---

## The second red test: `test_rule_4_has_two_enforcement_points`

It builds `enforcing` by scanning tracked files for the violation code, keeping only files that:
are not `.feature`, do not start with `tests/`, do not end `_test.py`,
do not end `test_deterministic_verifier.py`. It then asserts:

```python
enforcing == [
    "platform/executor/daemon.py",
    "platform/verification/refuse-unattested-provenance.yaml",
]
```

So **exactly two** files may carry that literal. The daemon gains it as a real refusal (verb 4
above). Every OTHER file that mentions it must be a grader or be reworded. The ticket
`docs/tickets/2026-09-13-deterministic-verifier.md` was measured quoting the code twice and has
been reworded in this branch -- **if you add prose anywhere, do not type the code.**

The test also asserts, both parsed as YAML:
- `platform/verification/kustomization.yaml`'s `resources` list names the policy file
- that policy's `spec.validationFailureAction == "Enforce"`

---

## What is NOT in scope

- The Git pre-receive arm. It is server-side GitHub configuration, not a file this tree can hold.
  The test's own docstring names it as absent on purpose. Do not mock it.
- A separate uid for the daemon. That is a machine-identity change and waits on the founder.
- Any change to `INDEPENDENT_EVIDENCE_MIN` or the epistemic gate.

## Evidence required in the summary

1. `cd sovereign && python3 -m pytest tests/bdd/test_deterministic_verifier.py -q -p no:cacheprovider` -- full tail, showing `9 passed`.
2. Each of the four verbs exercised once from the command line against a running daemon, quoting the reply JSON.
3. `git status --porcelain` clean of unintended files.
