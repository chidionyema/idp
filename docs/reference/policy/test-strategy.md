# Test strategy: tests grade behavior, never prose (R76)

Founder mandate, 2026-09-03 (R76): the test architect owns test strategy, and the
fire-to-test reflex is over. A test asserts what the system does, never what a file says.

## The rule

A test function whose every assertion is a string pin — an exact sentence, a substring
membership in a file's text, a pinned line of prose — is theatre: a reworded comment fails
CI while a broken behavior passes it. Such tests are forbidden. The gate is
`bin/test-prose-gate`, wired as the `prose_pin_scan` row in `AGENTS.md` and run by
`bin/idp-ci` over every `tests/test_*.py` file, with both fixtures
(`tests/fixtures/prose-pin/bad.py` must fail, `tests/fixtures/prose-pin/good.py` must pass)
proved in the same run.

## What a test may do

- Run the thing and assert its exit code, output shape, or state change.
- Parse a config and assert the parsed value, never the raw line.
- Call a gate on a fixture and assert refusal or acceptance.

## What a test may not do

- Assert that a file contains an exact sentence or phrase.
- Pin a comment, a docstring, a heading, or any wording that a legitimate rewording breaks.
- Grade look and feel: no selector, test id, or layout word (R53 already forbids this in
  drills; R76 extends the principle to the whole suite).

## What happened on 2026-09-03

434 of 482 test files were incident-reflex files and 374 of them pinned prose (1,939
standing prose asserts). The purge deleted 47 files whose every test was theatre, cut 405
prose-pinning functions from 214 mixed files while keeping their behavior tests, and added
the gate above so the class cannot return.
