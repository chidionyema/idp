package estate.fleet

import rego.v1

# A restrictive overlay: OPA never grants a capability absent from the
# existing estate identity, lease, budget, claim and protected action doors.
# data.fleet is an upstream signed founder-governed bundle/OPAL projection.
default decision := {"allow": false, "revision": "unavailable", "reason": "fleet-policy-data-unavailable"}

has_policy if {
    data.fleet.schema_version == "fleet.v1"
    is_string(data.fleet.active_revision)
    count(data.fleet.active_revision) > 0
    is_array(data.fleet.denials)
}

selector_matches(selector, observed) if {
    selector == "*"
}
selector_matches(selector, observed) if {
    selector == observed
}

matched_denials contains reason if {
    some rule in data.fleet.denials
    is_string(rule.id)
    is_string(rule.intent)
    is_string(rule.step)
    selector_matches(rule.intent, input.intent)
    selector_matches(rule.step, input.step)
    reason := rule.id
}

reason := "allowed" if {
    count(matched_denials) == 0
}
reason := "founder-policy-denied" if {
    count(matched_denials) > 0
}

decision := {
    "allow": count(matched_denials) == 0,
    "revision": data.fleet.active_revision,
    "reason": reason,
    "denials": matched_denials,
} if {
    has_policy
    input.contract_version == "estate.effect.v1"
    is_string(input.intent)
    is_string(input.step)
    is_string(input.command_sha256)
    count(input.command_sha256) == 64
}
