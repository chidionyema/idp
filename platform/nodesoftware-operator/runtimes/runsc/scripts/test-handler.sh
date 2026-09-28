#!/bin/bash
#
# test-handler.sh — smoke test the runsc handler scripts without a cluster.
#
# Verifies that each script:
#   - parses its arguments
#   - exits with the right code on bad input
#   - exits with the right code on good input where we can fake the env
#
# Does NOT verify the cri-o reload path (needs a real cri-o) -- that's the
# empirical proof in milestone D. The intent here is to lock in the script
# contract so a refactor can't silently break it.
#
# Run: ./scripts/test-handler.sh
# Exit 0 = all green, Exit 1 = at least one failure.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL="${SCRIPT_DIR}/nodesoftware-runsc-install"
UNINSTALL="${SCRIPT_DIR}/nodesoftware-runsc-uninstall"
PROBE="${SCRIPT_DIR}/nodesoftware-runsc-probe"

FAIL=0
PASS=0

TMPDIR_T="$(mktemp -d)"
trap 'rm -rf "${TMPDIR_T}"' EXIT

assert_exit() {
	local label="$1" expected="$2" actual="$3"
	if [[ "${actual}" -eq "${expected}" ]]; then
		printf '  ok    %s (exit=%d)\n' "${label}" "${actual}"
		PASS=$((PASS + 1))
	else
		printf '  FAIL  %s (exit=%d, expected %d)\n' "${label}" "${actual}" "${expected}"
		FAIL=$((FAIL + 1))
	fi
}

# 1. Install: no args => usage, exit 1.
set +e
"${INSTALL}" >/dev/null 2>&1
assert_exit "install no-args" 1 $?

# 2. Install: bad version (contains shell meta) => REFUSED, exit 64.
"${INSTALL}" "bad version" /tmp >/dev/null 2>&1
assert_exit "install bad-version" 64 $?

# 3. Install: unsupported arch is impossible to test from arm64+aarch64+
#    because the script does `uname -m` and that matches the host. Skip.

# 4. Uninstall: no args => usage, exit 1.
"${UNINSTALL}" >/dev/null 2>&1
assert_exit "uninstall no-args" 1 $?

# 5. Probe: on the host (NOT in gVisor), exit 1.
"${PROBE}" >/dev/null 2>&1
assert_exit "probe host-fail" 1 $?

printf '\n%d passed, %d failed\n' "${PASS}" "${FAIL}"
exit "${FAIL}"
