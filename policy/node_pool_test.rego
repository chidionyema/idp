# Pins for the review of 2026-08-30. Run: opa test policy/*.rego
package main

import rego.v1

base := {"ocpus": 4, "memory_gb": 24, "free": {"ocpus": 2, "memory_gb": 12}, "price_usd_hr": {"ocpu": 0.01, "memory_gb": 0.0015}, "monthly_cap_usd": 50}

# A spot pool with no burst rows used to make the spot sum undefined, so an over-cap spot pool
# passed in silence. Base here is USD 27.74; 3 spot nodes at 0.05/h for 730 h is USD 109.50.
test_spot_over_cap_with_no_burst_rows_is_refused if {
	some msg in deny with input as {"capacity": object.union(base, {"spot": {"max_nodes": 3, "node_usd_hr": 0.05, "hours_monthly": 730}})}
	contains(msg, "preemptible")
}

test_spot_under_cap_with_no_burst_rows_passes if {
	msgs := deny with input as {"capacity": object.union(base, {"spot": {"max_nodes": 1, "node_usd_hr": 0.005, "hours_monthly": 100}})}
	count(msgs) == 0
}
