#!/usr/bin/env bash
# The event-driven form. No wait at all.
set -euo pipefail
trap "exit 1" ERR
gh pr merge 1 --squash --auto
sleep 1
