# The executor records what it measured, so a bound can be learned instead of guessed

Date: 2026-10-30
Status: accepted (implementation landed with this decision)
Issue: the executor's own slice (the receipt writer), claim recorded on the issue
Relates to: `docs/proposals/2026-10-30-adaptive-executor-timeout-bounds.md`,
`docs/decisions/2026-10-30-two-decision-cores-review-gate-and-bound-resolver.md`

## The gap

`platform/executor/bounds.py` resolves a bound string into a decision, and it learns from
receipts: `(shape, elapsed_sec, exit_code, killed_at_ceiling, repo)`. Until now nothing produced
those receipts. The executor wrote `<job>.log`, `<job>.pid` and `<job>.exit`, and the exit file
carries a status and no duration. "Learn from the past" was therefore a slogan: there was no
past to learn from, only the number of jobs that had died at the ceiling.

This decision lands the missing half: the executor writes a receipt for every job it supervises.

## The decision

**The executor is the only writer of receipts.** A caller that could write its own receipt could
write its own permission, so the receipt is written by the process that is the command's parent
(`platform/executor/run.py`), the one that already knows the start time, the ceiling, the exit
code and the argv.

**The receipt records the SHAPE of the command, never its content.** The shape is the
executable's name plus the flag names, with every value replaced by `<arg>`. Two runs of
`pytest tests/test_x.py -k alpha` and `pytest tests/test_y.py -k beta` are one shape, so their
durations pool; `pytest --json` is another. A value can be a secret, and a receipt outlives the
job that carried it. The shape is readable as well as stable -- the canonical form is the key,
with a digest of it appended -- because evidence that can be audited is evidence, and a bare hash
is a promise.

**A receipt is written on every path.** A command that cannot start leaves a receipt with exit
code 127; a command killed at the ceiling leaves one with `killed_at_ceiling: true` and exit
code 124; a command that succeeded leaves one with its duration. Evidence that is missing is not
evidence that nothing happened.

**A kill at the ceiling is never evidence that a bigger ceiling would have worked.** The
receipt says the job was killed; `bounds.measured_bound` excludes those runs from the
distribution it learns from. What they are evidence of -- the ceiling was too small -- is an
obligation, and obligations belong in the incident plane, not in a retry.

**A receipt that cannot be written must never fail the job.** The work happened; losing the
evidence is a smaller harm than losing the work. The failure is printed, not swallowed.

**The repository is part of the evidence key.** A fast repository must not teach a slow one, so
the receipt carries the job's working directory and the resolver refuses to pool across it.

## What is still not done

This decision lands the evidence, not the learning. The door does not yet resolve a named bound
from these receipts: `bounds.resolve` is landed and pure, but nothing calls it with a real
receipt list yet. Until that wiring exists, the executor's behaviour is unchanged -- it writes
one more file per job and nothing reads it.

The truth is recorded in the proposal: a resolver that is wired without evidence learns from
nothing and grants nothing, and a receipt that is written without a reader is a note, not
evidence. Both halves now exist as code; the wire between them is the next slice, and it lands
with its own falsifiers.

## Falsifiers

The receipt is proved by `tests/test_executor_elapsed_receipt.py`:

| # | falsifier | test |
|---|-----------|------|
| F1 | a value never reaches the shape | `test_shape_never_carries_a_value` |
| F2 | values do not split a shape; flags do | `test_shape_ignores_values_but_not_flags` |
| F3 | a successful job leaves a receipt with its duration | `test_successful_job_writes_a_receipt` |
| F4 | a job killed at the ceiling says so | `test_a_job_killed_at_the_ceiling_says_so` |
| F5 | a command that cannot start still leaves a receipt | `test_a_command_that_cannot_start_still_leaves_a_receipt` |
| F6 | a corrupt receipt does not stop the reader | `test_read_receipts_skips_a_corrupt_file` |
| F7 | what the executor writes is what the resolver reads | `test_the_resolver_can_learn_from_a_receipt` |
| F8 | a ceiling kill is not evidence for a bigger ceiling | `test_a_ceiling_kill_is_not_evidence_that_a_bigger_ceiling_would_have_worked` |
