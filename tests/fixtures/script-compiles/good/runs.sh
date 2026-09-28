#!/usr/bin/env bash
# --self-test
# Fixture for bin/idp-script-compiles: a script that claims a probe and runs it.
# The trap is the estate shell standard (crew#620 row 2) and must not change the
# verdict -- this file still exits 0 and the grader still calls it OK.
set -euo pipefail
on_exit() {
	local e=$?
	[ "$e" -eq 0 ] || echo "runs.sh: exit $e" >&2
}
trap on_exit EXIT
echo "ok"
exit 0
