# Onboarding: The prose-pin gate

What the gate is, where it runs, and how to write a test that passes it.

## What it is

`bin/test-prose-gate` reads a Python test file and refuses any test function whose every
assertion is a string pin — a check that a file's text contains an exact sentence, phrase or
substring. Those tests grade wording, not behavior: rewording a comment turns the build red
while a real defect keeps it green. The policy behind it is
[the test strategy](../../reference/policy/test-strategy.md).

## Where it runs

- `bin/idp-ci` runs the gate over every `tests/test_*.py` file in the repository on every
  pull request, and proves the gate itself both ways against its two fixtures
  (`tests/fixtures/prose-pin/bad.py` must be refused, `tests/fixtures/prose-pin/good.py`
  must pass) in the same run.
- The `prose_pin_scan` row in `AGENTS.md` records the rule beside the other machine-checked
  rules of this repository.

## Writing a test that passes

Assert what the system does. Run the command and check its exit code. Parse the config and
check the parsed value. Call the gate on a fixture and check the refusal. A test may read a
file to feed a parser or a subprocess; it may not read a file to assert that a sentence is
still in it. If the thing you want to protect is wording on a founder-facing surface, the
plain-language checker owns that, not a test.
