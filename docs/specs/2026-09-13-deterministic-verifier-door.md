# Spec — the door onto the Deterministic Verifier

**STATUS: OPERATIONAL, measured 2026-09-14.** This spec was written 2026-09-13 as the plan for
work that did not exist yet, and everything below was true of the tree that day. It is kept
because it is the contract the door was built to, not because it describes a gap. Read the
status block immediately after this paragraph before acting on any sentence in this file.

**Why it was written.** `sovereign/verifier.py` was built, green and green-proved, and the daemon
(`platform/executor/daemon.py`) exposed only four verbs: `execute`, `simulate`, `read`, `health`.
The feature `features/gates/deterministic-verifier.feature` drives four more -- `propose_patch`,
`verify`, `seal`, `admit` -- so Rules 2, 3 and 4 stopped at `unknown verb` and the verifier was
unreachable from the agent's own door. Built, not operational.

---

## STATUS, measured 2026-09-14 (supersedes every baseline in the text below)

Merged to `main` in `65588127` (PR #3376). Re-measured, not remembered:

| claim in this spec | measured 2026-09-14 |
|---|---|
| `sovereign/verifier.py` is 667 lines | **745** (`git show origin/main:sovereign/verifier.py \| wc -l`) |
| acceptance suite is 6 failed, 3 passed | **9 passed in 12.90s**, exit 0 |
| the four verbs stop at `unknown verb` | **all four answer** -- see the replies below |
| built, not operational | **operational** |

The four verbs were then driven from the command line against the LIVE daemon (not the test
handler), and these are the daemon's own replies:

* `propose_patch` -> `ok: true`, `ledger_id: ldg-749c76da706c`, `suspended: true`, ledger under
  `~/.estate/runs/ledgers/` -- outside the live worktree, as the boundary requires.
* `verify` on a refutable patch -> `ok: false`, `claim_verdict: "FAILED"`, `attestation: null`,
  ledger destroyed, and the stage's own real message:
  ``greeting.py:2: guard `assert n >= 0` does not hold for all inputs; counterexample n = -1``
* `verify` on a provable patch -> `ok: true`, all three stages passed, `claim_verdict: "VERIFIED"`,
  `receipt: "VERIFIED"`, `staged_path` present, `admissible: true`.
* `seal` -> `ok: true`, `scheme: sigstore-bundle`. The bundle is a REAL Sigstore bundle with a
  Rekor transparency-log entry (logIndex 2825089704, kind hashedrekord, treeSize 2703185443) and
  an RFC-3161 signed timestamp from rekor.sigstore.dev -- not a local stub.
* `admit` with no attestation -> `ok: false`, `intercepted: true`, `violation_code: "UNATTESTED"`,
  no `admitted_path`. With the seal -> `ok: true`, `validated: true`, `admitted_path` present and
  its bytes equal to the sealed payload's.
* `health` after -> `ledgers_pending: 0`.

**Acceptance test (the ONLY definition of done).** Every scenario in the suite:

```
cd sovereign && python3 -m pytest tests/bdd/test_deterministic_verifier.py -q -p no:cacheprovider
```

must exit 0. Measured 2026-09-14: **9 passed in 12.90s.** The three honesty assertions that were
green at baseline must STAY passing.

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
