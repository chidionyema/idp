# The Estate-as-Platform operating model, as a gate rather than a paragraph.
#
# Founder, 2026-08-26 (crew#286): "The founder is the approving authority, never the
# implementing operator. Agents are platform engineers with scoped credentials. Every change
# is a PR. Every approval is a structured message. Nothing touches a GUI."
#
# Input is reports/pr.json from bin/pr-report:
#
#   {"pr": {"number": 154, "files": ["platform/oci/identity/main.tf"], "added": "<added lines>",
#           "body": "<PR body>", "labels": ["canary"]}}
#
# Every deny message has the shape "rule=<name> | <what is wrong> | fix: <what to change>",
# so the CI comment that carries it back to the author is the structured rejection the
# spec asks for (crew#286 CP10), not a red cross.
#
# DENY only. Each rule is paired in policy/fixtures (opmodel-*.json) with a case it must
# permit, because a gate that refuses correct work is an outage (LAW 38).
#
# WHAT IS NOT HERE, AND WHY IT MAY NOT COME BACK. Eight rules graded the WORDING of a pull
# request body: Cost-delta-usd-month:, Drill:, Matrix:, Optimised:, Lifecycle:, Breaker:,
# Control:, and four Architecture-law lines. The founder ordered them cut on 2026-09-04
# ("sorry we need tto cutr all thid crap, wate of tine, renive it"; "dot need all this waste
# and friction"; "addingzero value, paper work for nothing") because, in his words as the
# commit that removed the workflow recorded them, "nothing they check is measured against the
# running estate". That commit (7d27292f) deleted the workflow and left the rules, the
# fixtures and the pre-push hook rung standing, so the paperwork went on refusing local
# pushes for four more days. This commit finishes the deletion.
#
# The five rules that remain read the world, never the prose: the files a PR changes, the
# lines it adds, the labels on it, and the founder's own DENY: word.

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

founder_facing_prefixes := {"backstage/", "platform/identity/", "platform/edge/", "docs/reference/policy/", "estate-defaults.yaml"}

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

# `canary` is the one survivor of the cost/canary pair, so infra_change is defined here now;
# it lived in the cost_budget section this commit deleted. It reads the files a PR changes,
# never its prose.
infra_change if {
	some f in input.pr.files
	startswith(f, "platform/oci/")
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

# --- no_zone_literal_added ---------------------------------------------------------------
# Founder, 2026-09-01 (crew#796), on the store carrying 61 live lines of the zone name while
# the platform had one configurable value since crew#269: "THAT SHOULD NEVER HAPPEN, P0 ...
# CAN'T EVER HAPPEN AGAIN ... needs monitoring for any drift ... and PR rejection". The
# lines come from bin/estate-zone-gate --diff (one exemption list, proved both ways in
# bin/idp-ci); this rule only refuses. An exemption marker is a line like any other until the
# founder writes APPROVE: zone-exempt on the PR.

deny contains msg if {
	some hit in input.pr.zone_literals
	not "zone-exempt" in input.pr.approvals
	msg := sprintf("rule=no_zone_literal_added | %s | fix: write the host as <service>.${ESTATE_ZONE} (Flux substitutes it on the cluster; compose, shell and Python read ESTATE_ZONE from the environment; workflows read vars.ESTATE_ZONE); the zone is declared once, in clusters/<cluster>/estate-config.yaml", [hit])
}
