# Pins for the review of 2026-08-30 (founder: "review the regos carefully"). Run: opa test policy/*.rego
package main

import rego.v1

# lifecycle_row's workflow rule read input.pr.diff, a key bin/pr-report never writes, so a
# workflow that added a secrets.SEED_ line was never graded. It reads input.pr.added now.
test_seed_line_in_a_workflow_needs_a_lifecycle_row if {
	some msg in deny with input as {"pr": {
		"files": [".github/workflows/x.yml"],
		"added": "+        token: ${{ secrets.SEED_GITHUB_APP }}\n",
		"body": "Optimised: 1 -> 1, 1 -> 1; cut: none\n",
		"createdAt": "2026-08-30T00:00:00Z",
	}}
	startswith(msg, "rule=lifecycle_row")
}

test_seed_line_with_a_lifecycle_row_passes if {
	msgs := [m | some m in deny; startswith(m, "rule=lifecycle_row")] with input as {"pr": {
		"files": [".github/workflows/x.yml"],
		"added": "+        token: ${{ secrets.SEED_GITHUB_APP }}\n",
		"body": "Optimised: 1 -> 1, 1 -> 1; cut: none\nLifecycle: SEED_GITHUB_APP row on docs/reference/policy/credential-lifecycle.md\n",
		"createdAt": "2026-08-30T00:00:00Z",
	}}
	count(msgs) == 0
}
