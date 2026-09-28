# A registry timeout is not an advisory

2026-09-04. `bin/estate-security-scan` refused hermes-v2#71 three times with

```
FAIL  npm       lsp: high or critical advisories in shipped dependencies
```

and nothing underneath it. The same command outside CI answered `found 0 vulnerabilities`
with status 0, so the branch was clean and the gate was wrong.

## What was actually wrong

Two faults, one on top of the other.

The probe never finished. The step ran for 131.6 seconds against a 120-second timeout, so
`timeout` killed `npm audit` before the registry answered. That is a network condition and
says nothing about the dependencies.

The scanner could not tell, because it read the wrong status:

```sh
if ! out=$(cd "$d" && timeout 120 npm audit ... 2>&1); then
  rc=$?
```

`$?` after an `if ! cmd` test is the status of the negation, which is 0 whenever the branch
is taken. So `rc` was always 0, the `rc = 124` timeout branch could never run, and every
killed probe fell through to the advisory message with an empty report under it.

## The change

The status is captured before anything else runs:

```sh
out=$(cd "$d" && timeout 300 npm audit ... 2>&1) && rc=0 || rc=$?
```

The window is 300 seconds, and a timeout is now `WARN` — reported in the scan output, not
gating. The flake protocol already says an unrelated infrastructure timeout must not hold a
correct change. A real advisory prints its report and still fails; a non-zero exit with no
output at all is still `BLIND`.

## Evidence

Run 33836031999 on `chidionyema/hermes-v2`, step `Run chidionyema/idp/.github/actions/security-scan@main`,
2026-09-04T05:31:06Z: `BLIND npm lsp: npm audit exited 0 and printed nothing` — exit 0 is the
symptom of the status bug, printed by the change merged as idp#1384 minutes earlier. Step
duration 131,661 ms against the 120,000 ms timeout.

`tests/test_security_scan_npm_blind.py` pins all three outcomes: an advisory fails, a silent
non-zero exit is blind, a 124 is a warning.
