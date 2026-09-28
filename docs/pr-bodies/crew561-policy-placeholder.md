No-Issue: crew#561 (Otto fully enabled) is the tracked item on the crew board; this repo has no issue for it.

oke-check apply run 33280019151 (2026-08-29 23:08Z) minted Otto's key (`bin/idp-bootstrap-macrun` ok) and then refused its own tailnet policy: `FAIL tailscale-policy a ${...} placeholder survived substitution`. The applier greps the whole rendered file for `${` after envsubst, comments included, and the header comment idp#876 added spelled the placeholder shape out literally. The rule for Otto never reached the tailnet.

Fix: two comment lines reworded so the only `${` in the file is the group:founder member; a test pins that (exactly one placeholder, none in a comment) so the shape cannot come back.

## Options considered
- Teach the applier to strip comments before the grep: a second parser of hujson comments in shell for one file; rejected on LAW 23 (smaller road).
- Chosen: the file carries one placeholder and the test says so.

## Architecture laws
- LAW 1 zero-gravity: `platform/tailscale/policy.hujson` -> `bin/idp-tailscale-policy apply` (oke-check apply job) -> tailnet ACL
- LAW 2 fractal: `python3 -m pytest -q -p no:cacheprovider tests/test_incident_crew562_the_tailnet_acl_must_not_lock_the_founder_out_of_his_mac.py`
- LAW 3 nervous system: `tests/test_incident_crew562_the_tailnet_acl_must_not_lock_the_founder_out_of_his_mac.py::test_the_file_carries_exactly_one_placeholder_and_only_in_the_body`
- LAW 4 calibration: `n/a: count is exact (1)`
Cost-delta-usd-month: 0
Drill: oke-check

## Definition of done
1. Tracked item — crew#561
2. Code or config — `platform/tailscale/policy.hujson` (two comment lines), the test above
3. Gate proved both ways — the test fails on the merged file from idp#876 (two `${`) and passes on this one
4. Reference doc — header of `platform/tailscale/policy.hujson` names the incident and the run
5. How-to and demo — merge; `gh workflow run oke-check.yml -f mode=apply`; the check job's tailscale-policy step prints `ok tailscale-policy applied`
6. Catalog entity — existing hermes-agent component
7. Operational proof — the apply run's step line, then otto-parity
8. Scheduled re-grade — the daily oke-check apply
9. Standard row — identity; unchanged
10. Evidence block — below, attached by pr-evidence
Standard: Identity
Optimised: 2 -> 1 steps; cut: an applier change; batched: the guard test lands with the fix

Author-session: 80471694

## Verify

Verify: `python3 -m pytest -q -p no:cacheprovider tests/test_incident_crew562_the_tailnet_acl_must_not_lock_the_founder_out_of_his_mac.py`
Verify: `python3 -c "import pathlib,sys; sys.exit(pathlib.Path('platform/tailscale/policy.hujson').read_text().count('\${')!=1)"`
