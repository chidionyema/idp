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

# --- founder_denied ----------------------------------------------------------------------
# Founder, 2026-08-27: "you need to approve all / no founder friction if can be avoided / yes
# portal". Until then a change under a founder-facing prefix waited for `APPROVE: <word>` from
# his login; 8 green PRs sat a median 6.1h (44h total) on that word alone. The word is now
# optional and only his veto reads it: a PR that declares `Approval-word: <word>` and carries a
# `DENY: <word>` comment from the repository owner's login (bin/pr-report pr.denials) is refused.
# No word, no APPROVE, and a green PR merges. The word said on Telegram is still not evidence.

founder_facing_prefixes := {"backstage/", "platform/identity/", "platform/edge/", "docs/policy/", "estate-defaults.yaml"}

touches_founder_facing if {
	some f in input.pr.files
	some p in founder_facing_prefixes
	startswith(f, p)
}

approval_word := w if {
	m := regex.find_all_string_submatch_n(`(?m)^Approval-word:\s*(\S+)`, input.pr.body, 1)
	count(m) == 1
	w := m[0][1]
}

deny contains msg if {
	approval_word in object.get(input.pr, "denials", [])
	msg := sprintf("rule=founder_denied | the founder replied `DENY: %s` on this PR | fix: do not merge; address his reason and open a new PR with a new word", [approval_word])
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
# oke-check.yml's shape (mode=apply after the STAGED timer).

deny contains msg if {
	infra_change
	not "canary" in input.pr.labels
	msg := "rule=canary | a platform/oci change carries no `canary` label | fix: `gh pr edit <n> --add-label canary` once the plan names its canary step (dev subnet, one node, or `--check` only)"
}

# --- drill_named -------------------------------------------------------------------------
# Founder, 2026-08-26, after the front door failed three times in a row on first use: "we need
# test discipline". A platform layer is not changed on the strength of a plan and a green unit
# suite; the PR names the drill in drills/catalogue.yaml that signs in, rebuilds or restores
# through the layer it touches. A layer no drill covers gets its drill in the same PR.

drilled_prefixes := {"platform/", "clusters/"}

touches_drilled_layer if {
	some f in input.pr.files
	some p in drilled_prefixes
	startswith(f, p)
}

drill_line := m[0][1] if {
	m := regex.find_all_string_submatch_n(`(?m)^Drill:\s*(\S+)`, input.pr.body, 1)
	count(m) == 1
}

deny contains msg if {
	touches_drilled_layer
	not drill_line
	msg := "rule=drill_named | the PR changes a platform layer (platform/, clusters/) and names no drill that exercises it | fix: add `Drill: <name>` to the PR body, naming an entry in drills/catalogue.yaml (add the drill in this PR if none covers the layer)"
}

# The gate reads drills/catalogue.yaml from idp main, so a drill the PR itself adds is not in
# input.drills yet (idp#191 was refused for naming the row it created). A `- name:` line added
# to the catalogue in this PR's diff counts.
drills_added_in_pr contains name if {
	"drills/catalogue.yaml" in input.pr.files
	some m in regex.find_all_string_submatch_n(`(?m)^\+\s*-\s*name:\s*(\S+)`, input.pr.added, -1)
	name := m[1]
}

deny contains msg if {
	touches_drilled_layer
	drill_line
	not drill_line in input.drills
	not drill_line in drills_added_in_pr
	msg := sprintf("rule=drill_named | `Drill: %s` names no entry in drills/catalogue.yaml | fix: use a catalogued drill name, or add the drill to the catalogue in this PR", [drill_line])
}

# --- architecture_laws (crew#254) --------------------------------------------------------
# Founder, 2026-08-25 (crew#250): every PR passes the four Living Estate laws before merging
# (crew/docs/ARCHITECTURE_LAWS.md "The pull-request checklist"). The body carries a
# `## Architecture laws` section with one line per law; each line is a command or a path that
# proves the law for this change, or `n/a:` with a reason. A sentence is neither. The gate
# grades the shape of the line (a `/`, a backtick, an `->`, or `n/a: <reason>`); whether the
# command proves the law is the reviewer's job, and the per-law mechanical gates land as the
# layers do (LAW 1 bin/cloud-agnostic-gate is live).

laws := {"1": "zero-gravity", "2": "fractal", "3": "nervous system", "4": "calibration"}

has_laws_heading if regex.match(`(?m)^## Architecture laws\s*$`, input.pr.body)

law_line_ok(n) if {
	regex.match(sprintf(`(?m)^- LAW %s %s: (n/a: \S.*|[^\n]*[/\x60][^\n]*|[^\n]*->[^\n]*)$`, [n, laws[n]]), input.pr.body)
}

# Only a PR input is graded: the other fixtures in policy/fixtures (node pools, placement,
# commands) carry no pr at all and are not pull requests.
deny contains msg if {
	is_string(input.pr.body)
	not has_laws_heading
	msg := "rule=architecture_laws | the PR body has no `## Architecture laws` section | fix: copy the four-line checklist from crew/docs/ARCHITECTURE_LAWS.md into the body; each line a command, a path or `n/a: <reason>`"
}

deny contains msg if {
	is_string(input.pr.body)
	has_laws_heading
	some n, slug in laws
	not law_line_ok(n)
	msg := sprintf("rule=architecture_laws | `- LAW %s %s:` is missing or is a sentence | fix: make it the command or path that proves the law for this change, or `n/a: <reason>`", [n, slug])
}
