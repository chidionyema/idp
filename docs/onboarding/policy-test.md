# Onboarding: policy-test

## What it is

`bin/policy-test` runs `policy/` (the Rego licence and placement rules) through
`conftest` against six fixtures under `policy/fixtures`, and checks each
fixture's exit code against the expected one. It prints a table naming what
each fixture proves and exits non-zero on any mismatch.

## Why it exists

LAW 38: a guard that refuses correct work is an outage, and a gate proved only
by fixtures that must fail has never been shown to permit anything. The six
fixtures cover both licence policy — allow an ordinary permissive dependency
tree, refuse copyleft-adjacent licences (AGPL, SSPL, BUSL, Elastic, non-
commercial CC, Commons Clause), refuse a scan with no licence terms recorded
at all rather than treating "unknown" as "clean" — and placement policy — allow
a monitored, awake-hours desk job, refuse a sleep-window schedule, refuse a
job whose monitoring check could not itself be read, so a monitoring outage
cannot masquerade as a pass.

`conftest` is used as the runner deliberately rather than a bespoke test
harness: the tool under test is the Rego policy itself, and the tool that
enforces it in real gates should be the same tool that proves it here.

## When it runs

Inside `bin/idp-ci`. It also runs standalone whenever `policy/` or its
fixtures change.

## Related files

```
bin/policy-test           the runner
policy/                    the Rego rules under test
policy/fixtures/           the six fixtures, three must-pass, three must-fail
```
