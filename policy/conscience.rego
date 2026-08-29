# The founder's ethos judging a pull request, one rule per tenet row (crew#586 CP2).
#
# Every rule here is named by `pr_rule:` in conscience/tenets.yaml; a row's `mode:` says
# whether the rule is `warn` or `deny`. A rule is born `warn` and earns `deny` only at zero
# false positives (LAW 38: a guard that refuses correct work is an outage). Two tenet rows
# are judged by rules that already exist: `secure` by no_secret_added (bin/pr-report) and
# `survivable` by drill_named (operating_model.rego). bin/pr-report counts the conscience
# rules that fired and posts `🧠 n/7` on the PR.
package main

import rego.v1

provider_pattern := `(?m)^\+.*(oraclecloud\.com|oci-load-balancer|objectstorage\.|service\.beta\.kubernetes\.io/aws-|alb\.ingress\.kubernetes\.io|eks\.amazonaws\.com|cloud\.google\.com/|pubsub\.googleapis)`

# The three places a cloud may be named (bin/cloud-agnostic-gate EXEMPT).
provider_allowed_prefixes := {"platform/oci/", "platform/secret-store/", "clusters/"}

touches_allowed_provider_path if {
	some f in input.pr.files
	some p in provider_allowed_prefixes
	startswith(f, p)
}

# --- portable: no_provider_in_diff (deny) ------------------------------------------------
deny contains msg if {
	regex.match(provider_pattern, input.pr.added)
	not touches_allowed_provider_path
	msg := "rule=no_provider_in_diff | tenet=portable | an added line names a cloud provider outside platform/oci, platform/secret-store or clusters/ | fix: move the provider-specific line into the compute provisioner or the cluster row, and keep the platform blind to who owns the servers (R36)"
}

# --- future-looking: no_floating_tag (warn) -----------------------------------------------
warn contains msg if {
	regex.match(`(?m)^\+\s*(-\s*)?image:\s*\S+:latest\b`, input.pr.added)
	msg := "rule=no_floating_tag | tenet=future-looking | an added image line floats on :latest | fix: pin the tag and let Flux image automation (idp#222) roll it"
}

# --- enterprise: new_script_has_a_test (warn) ---------------------------------------------
adds_bin_script if {
	some f in input.pr.files
	startswith(f, "bin/")
}

touches_tests if {
	some f in input.pr.files
	startswith(f, "tests/")
}

warn contains msg if {
	adds_bin_script
	not touches_tests
	msg := "rule=new_script_has_a_test | tenet=enterprise | the PR changes a bin/ script and no file under tests/ | fix: add the test that proves the script both ways, or a --selftest wired into bin/idp-ci"
}

# --- better: incident_has_a_guard (warn) --------------------------------------------------
names_incident if regex.match(`(?mi)^Incident:`, input.pr.body)

adds_incident_guard if {
	some f in input.pr.files
	contains(f, "tests/test_incident_")
}

warn contains msg if {
	names_incident
	not adds_incident_guard
	msg := "rule=incident_has_a_guard | tenet=better | the body names an Incident: and the PR adds no tests/test_incident_* guard | fix: pin the mistake as a test no session can walk past (LAW 45)"
}

# --- research: new_dependency_has_a_ledger_entry (warn) -----------------------------------
dependency_files := {"package.json", "pyproject.toml", "go.mod", "Cargo.toml"}

adds_dependency_file if {
	some f in input.pr.files
	some d in dependency_files
	endswith(f, d)
}

adds_dependency_file if {
	some f in input.pr.files
	regex.match(`(^|/)requirements[^/]*\.txt$`, f)
}

names_ledger if regex.match(`(?mi)^Ledger:`, input.pr.body)

warn contains msg if {
	adds_dependency_file
	not names_ledger
	msg := "rule=new_dependency_has_a_ledger_entry | tenet=research | the PR changes a dependency file and the body has no Ledger: line | fix: add `Ledger: <crew/science/RESEARCH-LEDGER.jsonl question>` naming the research that chose it, or `Ledger: n/a: version bump only`"
}
