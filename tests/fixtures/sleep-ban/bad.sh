#!/usr/bin/env bash
# A wait on a clock. This is the shape the rule refuses.
set -euo pipefail
trap "exit 1" ERR
gh pr checks 1
sleep 420
gh pr merge 1 --squash
