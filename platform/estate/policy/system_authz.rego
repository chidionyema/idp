package system.authz

import rego.v1

# Permanent API safety floor: OPA is an evaluator, not a policy publisher.
# No agent/API caller may upload, edit or remove policy or bundle data.
# Rules/data arrive only from independently verified signed bundles.
default allow := false

# The sole externally queryable decision: restrictive estate effect overlay.
allow if {
    input.method == "POST"
    input.path == ["v1", "data", "estate", "fleet", "decision"]
}

# Health and readiness are read-only; never authorise /v1/policies or
# /v1/data mutation endpoints. Network isolation is still mandatory.
allow if {
    input.method == "GET"
    input.path == ["health"]
}
