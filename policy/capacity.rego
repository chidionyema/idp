# Paid capacity is auto-defaulted up to the cap the founder wrote, never asked and never
# unbounded.
#
# estate-defaults.yaml (crew#281, founder 2026-08-26): `compute_tier: auto-scale-paid` and
# `monthly_cap_usd: 50`. Ruling R14 (2026-08-24) said no paid infra without explicit founder
# sign-off; the cap is that sign-off, written once, so a session stops asking him about a
# node pool he has already priced. Under the cap a pool change is STAGED (60 minutes, 'hold'
# cancels). Over it, the change is a paid billing authorisation: FOUNDER ACTION, not STAGED.
#
# Input is reports/capacity.json, written by `tofu output -json capacity` in platform/oci,
# which computes the same estimate from the same variables (one rule, two executable copies
# that must agree; the fixtures pin both):
#
#   {"capacity": {"ocpus": 4, "memory_gb": 24,
#                 "free": {"ocpus": 2, "memory_gb": 12},
#                 "price_usd_hr": {"ocpu": 0.01, "memory_gb": 0.0015},
#                 "monthly_cap_usd": 50}}
#
# Prices are Oracle's public price list, parts B93297 (A1 OCPU, USD 0.01/h) and B93298
# (A1 memory, USD 0.0015/GB/h), read 2026-08-26 from
# apexapps.oracle.com/pls/apex/cetools/api/v1/products/. The free allowance is ADR 0004:
# 2 OCPU / 12 GB since 2026-06-15. A month is 730 hours.
#
# No price row or no cap means the estimate is BLIND, and BLIND refuses; it never rounds to
# zero (the silent-miss case in the lane notes).

package main

import rego.v1

hours_per_month := 730

paid_ocpus := max([0, input.capacity.ocpus - input.capacity.free.ocpus])

paid_memory_gb := max([0, input.capacity.memory_gb - input.capacity.free.memory_gb])

monthly_usd := ((paid_ocpus * input.capacity.price_usd_hr.ocpu) + (paid_memory_gb * input.capacity.price_usd_hr.memory_gb)) * hours_per_month

deny contains msg if {
	input.capacity
	monthly_usd > input.capacity.monthly_cap_usd
	msg := sprintf(
		"node pool %v OCPU / %v GB is an estimated USD %.2f a month, over the estate-defaults cap of USD %v. That is a paid billing authorisation: FOUNDER ACTION, not STAGED.",
		[input.capacity.ocpus, input.capacity.memory_gb, monthly_usd, input.capacity.monthly_cap_usd],
	)
}

deny contains msg if {
	input.capacity
	not input.capacity.price_usd_hr.ocpu
	msg := "capacity input carries no price rows; the estimate is BLIND, and BLIND is refused rather than read as zero"
}

deny contains msg if {
	input.capacity
	not input.capacity.monthly_cap_usd
	msg := "capacity input carries no monthly_cap_usd; read it from estate-defaults.yaml, never default it"
}
