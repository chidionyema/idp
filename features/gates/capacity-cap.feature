Feature: paid capacity is auto-defaulted up to the founder's cap and refused above it
  estate-defaults.yaml (crew#281) says compute_tier auto-scale-paid with monthly_cap_usd 50.
  Ruling R14 said no paid infra without explicit sign-off; the cap is that sign-off, written
  once. The gate is policy/capacity.rego over reports/capacity.json, and platform/oci computes
  the same estimate as `tofu output -json capacity`, so the two cannot drift without a fixture
  failing. bin/idp-ci proves the row both ways from the AGENTS.md table.

  Scenario: a node pool under the cap is STAGED, never asked
    Given the node pool is 4 OCPU and 24 GB with 2 OCPU and 12 GB free
    And Oracle's A1 price list is USD 0.01 per OCPU-hour and USD 0.0015 per GB-hour
    When conftest tests policy/fixtures/capacity-under-cap.json against policy/
    Then the estimate is USD 27.74 a month and the gate passes

  Scenario: a node pool over the cap is a paid billing authorisation
    Given the node pool is 8 OCPU and 48 GB with the same free allowance and prices
    When conftest tests policy/fixtures/capacity-over-cap.json against policy/
    Then the gate refuses with an estimate of USD 83.22 a month and the words FOUNDER ACTION

  Scenario: a missing price row or cap is BLIND, not zero
    Given a capacity input without price_usd_hr or without monthly_cap_usd
    When conftest tests it against policy/
    Then the gate refuses and names the missing field
