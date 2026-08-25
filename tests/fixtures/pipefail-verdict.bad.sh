#!/usr/bin/env bash
# Fixture: the verdict of this conditional is the PIPELINE's status, not grep's.
# Under `set -o pipefail` a non-zero exit from the left-hand command wins, so
# this branch is not taken even when the pattern is present.
set -uo pipefail
if some-command --that-may-fail 2>&1 | grep -q 'expected'; then
  echo "matched"
fi
