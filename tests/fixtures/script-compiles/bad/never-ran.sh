#!/usr/bin/env bash
# --self-test
# Fixture for bin/idp-script-compiles: a script that claims a probe and cannot run it.
# The whole point is the undefined command below; the trap is the estate shell
# standard (crew#620 row 2) and must not change the verdict -- this file still fails.
set -euo pipefail
on_exit() {
	local e=$?
	[ "$e" -eq 0 ] || echo "never-ran.sh: exit $e" >&2
}
trap on_exit EXIT
undefined_command_that_does_not_exist
exit 0
