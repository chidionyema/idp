crew#561: the Mac adopter reads Otto's key from any dispatched run that minted it, not only a fully green one

Dispatched oke-check runs are titled "oke-check", so `displayTitle | test("apply")` matched nothing; and `--status success` hid run 33280019151, which minted the key and then failed on steps other lanes own (iam-policy, vault tenancy limit, minimax key shape). `bin/idp-mac-adopt-otto` could never find the key. It now walks the last ten dispatched runs for the `public key:` line, and `IDP_APPLY_RUN` names one run outright. A test pins both.

Optimised: 10 -> 1 steps, 10 -> 1 round trips; cut: one log download per candidate run, newest first, stop at the first key line; memoised: IDP_APPLY_RUN names the run and skips the list call

Drill: oke-check
Lifecycle: hermes-mac-run row on docs/reference/policy/credential-lifecycle.md

## Definition of done
1. Founder used it — not yet; this is INVENTORY until `bin/idp-mac-adopt-otto` runs on his Mac and otto-parity is green
2. Green CI — this PR's checks
3. Gate proved both ways — the test fails on the old selector text and passes on the new (35 passed)
4. Demo — `IDP_APPLY_RUN=33280019151 bin/idp-mac-adopt-otto --check` on the Mac now reaches the key and reports the honest state (authorized_keys does not hold it yet)
5. Onboarding — docs/founder/otto-on-the-mac.md unchanged; the command is the same
6. Runbook — none; no human step
7. Standard row — none changed
8. Telemetry — none; a laptop-side script
9. Root cause — a selector written against an assumed title and an assumed all-green run; the class is "reading another job's outcome as this step's evidence"
10. Board — crew#561

## Options considered
- Make the adopter wait for a fully green apply run: rejected, it couples Otto's key to every other lane's step in the same workflow.
- Read the key line from any dispatched run's log, newest first (chosen).

## Architecture laws
- LAW 1 zero-gravity: `gh run list --event workflow_dispatch` -> the newest run log carrying `public key:` -> `~/.ssh/authorized_keys`
- LAW 2 fractal: `python3 -m pytest -q tests/test_incident_crew516_otto_hands_on_the_mac.py`
- LAW 3 nervous system: `tests/test_incident_crew516_otto_hands_on_the_mac.py::test_mac_adopt_reads_the_key_from_any_dispatched_run_not_only_a_green_one` (no `--status success`, no title test, `--event workflow_dispatch`, `IDP_APPLY_RUN`)
- LAW 4 calibration: `n/a: the key line is exact (ssh-ed25519, one line per run)`

## Verify
Verify: `python3 -m pytest -q tests/test_incident_crew516_otto_hands_on_the_mac.py`

No-Issue: crew#561 (crew repo issue; idp closes none)
