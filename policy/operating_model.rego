# The Estate-as-Platform operating model, as a gate rather than a paragraph.
#
# Founder, 2026-08-26 (crew#286): "The founder is the approving authority, never the
# implementing operator. Agents are platform engineers with scoped credentials. Every change
# is a PR. Every approval is a structured message. Nothing touches a GUI."
#
# Input is reports/pr.json from bin/pr-report:
#
#   {"pr": {"number": 154, "files": ["platform/oci/identity/main.tf"], "added": "<added lines>",
#           "body": "<PR body>", "labels": ["canary"]},
#    "budget_monthly_usd": 50}
#
# Every deny message has the shape "rule=<name> | <what is wrong> | fix: <what to change>",
# so the CI comment that carries it back to the author is the structured rejection the
# spec asks for (crew#286 CP10), not a red cross.
#
# DENY only. Each rule is paired in policy/fixtures (opmodel-*.json) with a case it must
# permit, because a gate that refuses correct work is an outage (LAW 38).

package main

import rego.v1

# --- provisioning_complete (ZCP) ---------------------------------------------------------
# An identity created in a PR carries its role, policy or grant in the same PR. Incident:
# estate-tofu was created (bin/idp-oci-bootstrap) without `manage domains`, and the first
# apply that needed it was a 401 and a founder step (crew#287).

identity_resources := {
	"oci_identity_user",
	"oci_identity_domains_user",
	"oci_identity_domains_app",
	"oci_identity_domains_group",
	"github_app",
}

binding_resources := {
	"oci_identity_policy",
	"oci_identity_user_group_membership",
	"oci_identity_domains_grant",
	"oci_identity_domains_group",
	"oci_identity_domains_user_group_membership",
	"oci_identity_domains_app_role",
	"github_app_installation",
}

adds_resource(kind) if {
	regex.match(sprintf(`(?m)^\+\s*resource\s+"%s"`, [kind]), input.pr.added)
}

deny contains msg if {
	some kind in identity_resources
	adds_resource(kind)
	not any_binding_added
	msg := sprintf("rule=provisioning_complete | %s is created without a role, policy or grant in the same PR | fix: add the oci_identity_domains_grant / oci_identity_policy / group membership that gives it its scope, in this PR", [kind])
}

any_binding_added if {
	some kind in binding_resources
	adds_resource(kind)
}

# --- no_gui_actions ----------------------------------------------------------------------
# A PR body, a handoff or a runbook line that tells a person to sign in, click or open a
# console is refused. Incident: Telegram 13994 asked the founder to create an OAuth App in a
# browser; 14017 asked for a console group edit that one policy statement replaces.

gui_words := `(?i)(sign in to|log in to|click|in the browser|console|dashboard|web ui|settings page|developer settings)`

instruction_lines := [l |
	some l in split(input.pr.body, "\n")
	regex.match(`(?i)^\s*(FOUNDER ACTION|STAGED|Use|Founder step|Manual step)\s*:`, l)
]

deny contains msg if {
	some l in instruction_lines
	regex.match(gui_words, l)
	msg := sprintf("rule=no_gui_actions | an instruction line asks for a GUI step: %q | fix: express the step as a command, a Terraform block or an APPROVE: word; if privilege is missing, open a privilege-elevation issue (crew#287 shape)", [trim_space(l)])
}

# --- founder_approval_required -----------------------------------------------------------
# A change to a founder-facing system declares the word he replies with. The merge gate
# (bin/pr-report --approval) then looks for `APPROVE: <word>` from his login on the PR or
# on Telegram; this rule only guarantees there is a word to look for.

founder_facing_prefixes := {"backstage/", "platform/identity/", "platform/edge/", "docs/policy/", "estate-defaults.yaml"}

touches_founder_facing if {
	some f in input.pr.files
	some p in founder_facing_prefixes
	startswith(f, p)
}

has_approval_word if {
	regex.match(`(?m)^Approval-word:\s*\S+`, input.pr.body)
}

deny contains msg if {
	touches_founder_facing
	not has_approval_word
	msg := "rule=founder_approval_required | the PR changes a founder-facing surface (backstage/, platform/identity/, platform/edge/, docs/policy/, estate-defaults.yaml) and names no approval word | fix: add a line `Approval-word: <word>` to the PR body; the founder replies `APPROVE: <word>` or `DENY: <word>`"
}

# --- cost_budget -------------------------------------------------------------------------
# A platform/oci change declares its monthly cost delta; over budget is a refusal, not a
# review comment. The budget is estate-defaults.yaml cost.budget_monthly_usd, passed in.

infra_change if {
	some f in input.pr.files
	startswith(f, "platform/oci/")
}

cost_line := to_number(m[0][1]) if {
	m := regex.find_all_string_submatch_n(`(?m)^Cost-delta-usd-month:\s*(-?[0-9]+(?:\.[0-9]+)?)`, input.pr.body, 1)
	count(m) == 1
}

deny contains msg if {
	infra_change
	not cost_line
	msg := "rule=cost_budget | a platform/oci change declares no monthly cost delta | fix: add `Cost-delta-usd-month: <number>` to the PR body (0 for a no-cost change), priced from ADR 0004"
}

deny contains msg if {
	infra_change
	cost_line > input.budget_monthly_usd
	msg := sprintf("rule=cost_budget | monthly cost delta %v USD exceeds the budget %v USD | fix: reduce the change, or raise cost.budget_monthly_usd in estate-defaults.yaml in its own PR with the founder's APPROVE: budget", [cost_line, input.budget_monthly_usd])
}

# --- canary ------------------------------------------------------------------------------
# An infra plan is applied to the canary target first. The label is what the merge gate
# can see; the workflow that honours it (apply canary, verify, apply the rest) is
# access-apply.yml's shape.

deny contains msg if {
	infra_change
	not "canary" in input.pr.labels
	msg := "rule=canary | a platform/oci change carries no `canary` label | fix: `gh pr edit <n> --add-label canary` once the plan names its canary step (dev subnet, one node, or `--check` only)"
}
