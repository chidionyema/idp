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
#
# PAUSED 2026-08-28 (founder, crew#254 5456132029, after the gate refused idp#625 twice): "lets pause
# this for now", "causing delivery friction, needs to be betetr designed", "agents dont undertnd the
# languae used", "needs nore precision". The section is still read and printed as a warning; it
# never blocks a merge until the four laws are rewritten as one command each, in plain words.

laws := {"1": "zero-gravity", "2": "fractal", "3": "nervous system", "4": "calibration"}

has_laws_heading if regex.match(`(?m)^## Architecture laws\s*$`, input.pr.body)

law_line_ok(n) if {
	regex.match(sprintf(`(?m)^- LAW %s %s: (n/a: \S.*|[^\n]*[/\x60][^\n]*|[^\n]*->[^\n]*)$`, [n, laws[n]]), input.pr.body)
}

# Only a PR input is graded: the other fixtures in policy/fixtures (node pools, placement,
# commands) carry no pr at all and are not pull requests.
warn contains msg if {
	is_string(input.pr.body)
	not has_laws_heading
	msg := "rule=architecture_laws | the PR body has no `## Architecture laws` section | fix: copy the four-line checklist from crew/docs/ARCHITECTURE_LAWS.md into the body; each line a command, a path or `n/a: <reason>`"
}

warn contains msg if {
	is_string(input.pr.body)
	has_laws_heading
	some n, slug in laws
	not law_line_ok(n)
	msg := sprintf("rule=architecture_laws | `- LAW %s %s:` is missing or is a sentence | fix: make it the command or path that proves the law for this change, or `n/a: <reason>`", [n, slug])
}

# --- matrix_cited (ADR 0009, crew#562) ------------------------------------------------------
# Founder, 2026-08-28: "we need a matrix for decision making — rather than asking these
# questions it should be auto — for all requirements" and "i like the matrix, enforce it".
# A pull request that makes a build-or-buy decision names the scored entry in
# docs/decisions/decision-matrix.yaml with a `Matrix: <slug>` line. Two shapes of PR are that
# decision: one that adds an ADR (a `# NNNN.` title line under docs/decisions/), and one that
# brings a new chart onto a platform layer (an added `kind: HelmRelease`). input.matrix is the
# slug list bin/matrix-gate --slugs prints from idp main; a slug the PR itself adds counts.

adds_adr if {
	some f in input.pr.files
	regex.match(`^docs/decisions/\d{4}-.+\.md$`, f)
	regex.match(`(?m)^\+# \d{4}\. `, input.pr.added)
}

adds_helmrelease if {
	touches_drilled_layer
	regex.match(`(?m)^\+kind:\s*HelmRelease\s*$`, input.pr.added)
}

decides if adds_adr
decides if adds_helmrelease

matrix_line := m[0][1] if {
	m := regex.find_all_string_submatch_n(`(?m)^Matrix:\s*(\S+)`, input.pr.body, 1)
}

slugs_added_in_pr contains s if {
	"docs/decisions/decision-matrix.yaml" in input.pr.files
	some m in regex.find_all_string_submatch_n(`(?m)^\+\s*-\s*slug:\s*(\S+)`, input.pr.added, -1)
	s := m[1]
}

deny contains msg if {
	decides
	not matrix_line
	msg := "rule=matrix_cited | the PR adds an ADR or a new HelmRelease and names no scored decision | fix: add `Matrix: <slug>` to the PR body, naming an entry in docs/decisions/decision-matrix.yaml (score it in this PR if none covers the choice; every cell needs evidence)"
}

deny contains msg if {
	decides
	matrix_line
	not matrix_line in input.matrix
	not matrix_line in slugs_added_in_pr
	msg := sprintf("rule=matrix_cited | `Matrix: %s` names no entry in docs/decisions/decision-matrix.yaml | fix: use a scored slug, or add the decision to the matrix in this PR", [matrix_line])
}

# --- optimised_plan (LAW 51, crew#584) ------------------------------------------------------
# Founder, 2026-08-29: "optimise before build ... note this process down as it will become law ...
# how to plan and optimise before starting any execution ... i want to trial and if successful to
# enforce this process". Trial measured on crew#584 5459773413: go -> three PRs merged in 12 min
# against a 45-minute estimate. The body carries one `Optimised:` line of the shape the procedure
# fixes (~/AGENTS-FULL.md): `Optimised: <steps before> -> <after>, <round trips before> -> <after>;
# cut: <what, why>`. The gate grades the shape: a number on each side of an `->` and a `cut:` clause.
# A sentence ("we made it faster") is not a plan that was counted.

optimised_line_ok if {
	regex.match(`(?m)^Optimised: [^\n]*\d[^\n]*->[^\n]*\d[^\n]*; *cut: \S[^\n]*$`, input.pr.body)
}

# WHEN THE RULE STARTS JUDGING. LAW 51 landed on main in dca2a929 at 2026-08-29T02:28:20Z. Between
# that commit and the next hour the rule turned nine open pull requests red -- five on prospector,
# four here -- every one of them written, reviewed and green before the law existed. Their authors
# could only have cleared it by inventing a counted plan for work nobody counted, which is a
# fabricated receipt, and LAW 38 says a guard that refuses correct work is an outage. So the rule
# reads the PR's opening time: from the moment the law existed, the plan is a precondition; before
# it, there was nothing to precede. A report with no `createdAt` is judged -- the field is absent
# only on a hand-built fixture or an old report, and the safe default there is to grade, not skip.
law51_landed := "2026-08-29T02:28:20Z"

opened_before_law51 if {
	is_string(input.pr.createdAt)
	input.pr.createdAt < law51_landed
}

deny contains msg if {
	is_string(input.pr.body)
	not optimised_line_ok
	not opened_before_law51
	msg := "rule=optimised_plan | the PR body has no counted `Optimised:` line (LAW 51) | fix: plan first, then add `Optimised: <steps before> -> <after>, <round trips before> -> <after>; cut: <what, why>` — numbers on both sides of the arrow and a cut clause; the procedure is in ~/AGENTS-FULL.md"
}

# --- lifecycle_row (crew#618, founder 2026-08-29) -------------------------------------------
# "no PR covering critical infra like this can have setup going to void: reusable? expiration? we
# need policy." A pull request that touches a root credential's birth (bin/idp-bootstrap-*, the
# vendor registry, the GitHub App files, or any `secrets.SEED_*` line in a workflow) carries one
# `Lifecycle:` line naming the row on docs/reference/policy/credential-lifecycle.md. The test
# tests/test_incident_crew618_every_root_has_a_life_cycle.py grades the page itself; this grades
# that the author looked at it.

lifecycle_landed := "2026-08-29T09:30:00Z"

touches_a_root if {
	some f in input.pr.files
	regex.match(`^(bin/idp-bootstrap-|platform/vendors/|platform/github-app/)`, f)
}

touches_a_root if {
	some f in input.pr.files
	startswith(f, ".github/workflows/")
	regex.match(`(?m)^\+.*secrets\.SEED_`, input.pr.added)
}

lifecycle_line_ok if {
	regex.match(`(?m)^Lifecycle: \S[^\n]*$`, input.pr.body)
}

opened_before_lifecycle if {
	is_string(input.pr.createdAt)
	input.pr.createdAt < lifecycle_landed
}

deny contains msg if {
	is_string(input.pr.body)
	touches_a_root
	not lifecycle_line_ok
	not opened_before_lifecycle
	msg := "rule=lifecycle_row | the PR touches a root credential's birth and the body has no `Lifecycle:` line (crew#618) | fix: add `Lifecycle: <SEED_NAME> row on docs/reference/policy/credential-lifecycle.md` and make sure the row exists with expiry, rotation and revocation filled"
}

# --- self_heal_has_breaker (crew#678 CP2, founder 2026-08-30) --------------------------------
# Founder, 2026-08-30 (crew#678): self-healing needs a circuit breaker -- bounded attempts, a
# cool-off, a visible open state, and loud when open. The CP1 inventory on crew#678 found four
# repair loops with none (a browser bridge restarted every 60 s forever; a kickstart with no
# attempt count; `helm-retry` with no record of prior tries). A pull request that adds a
# self-healing verb (`flux reconcile ... --reset`, `delete pod`, `launchctl kickstart`,
# `rollout restart`, `systemctl restart`) in a script, a workflow or the healing layer carries
# one `Breaker:` line saying how many attempts, how long the cool-off is and where the open
# state can be seen, or `Breaker: n/a — <why this is an alarm, not a repair loop>`.

self_heal_prefixes := {"bin/", "scripts/", ".github/workflows/", "platform/healing/", "scheduler/"}

self_heal_verb := `(?m)^\+[^\n]*(flux reconcile [^\n]*--reset|delete pod\b|launchctl kickstart|rollout restart|systemctl restart)`

adds_self_heal if {
	some f in input.pr.files
	some p in self_heal_prefixes
	startswith(f, p)
	regex.match(self_heal_verb, input.pr.added)
}

breaker_line_ok if {
	regex.match(`(?m)^Breaker: \d+ attempts?, \d+ ?(s|m|h|min|minutes?|hours?) cool-off, open (state )?(at|in) \S[^\n]*$`, input.pr.body)
}

breaker_line_ok if {
	regex.match(`(?m)^Breaker: n/a [-—] \S[^\n]*$`, input.pr.body)
}

# Same shape as optimised_plan: a pull request opened before the rule existed is not refused
# for a line nobody could have known to write (LAW 38).
breaker_landed := "2026-08-30T04:40:00Z"

opened_before_breaker if {
	is_string(input.pr.createdAt)
	input.pr.createdAt < breaker_landed
}

deny contains msg if {
	adds_self_heal
	not breaker_line_ok
	not opened_before_breaker
	msg := "rule=self_heal_has_breaker | the PR adds a self-healing action (reconcile --reset, delete pod, kickstart, restart) and names no circuit breaker (crew#678) | fix: add `Breaker: <N> attempts, <M>h cool-off, open state at <where a person sees it>` to the body, or `Breaker: n/a — <why this is an alarm, not a repair loop>`"
}
