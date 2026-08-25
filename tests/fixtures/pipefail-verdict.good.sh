#!/usr/bin/env bash
# Fixture: the output is captured first, so the conditional grades the text and
# the left-hand command's exit status cannot silently invert the verdict.
set -uo pipefail
out=$(some-command --that-may-fail 2>&1)
if printf '%s' "$out" | grep -q 'expected'; then
  echo "matched"
fi
# Also legal: a pipeline inside $( ) whose value, not whose status, is the test.
if [ "$(printf '%s' "$out" | grep -c 'expected')" = 1 ]; then
  echo "counted"
fi
