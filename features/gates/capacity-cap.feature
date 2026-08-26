Feature: paid capacity is auto-defaulted up to the founder's cap and refused above it
  estate-defaults.yaml (crew#281) says compute_tier auto-scale-paid; crew#289 adds node_pool.prefer_free and
  node_pool.budget_monthly_usd 50.
  Ruling R14 said no paid infra without explicit sign-off; the cap is that sign-off, written
  once. The gate is policy/node_pool.rego over reports/capacity.json, which
  `bin/idp-oke-rebuild --plan-pool` writes from platform/oci's own estimate, so the two cannot drift without a fixture
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

  Scenario: the STAGED node-pool change is applied from GitHub, never from a laptop
    Given oke-check.yml has a workflow_dispatch input "mode" with the choice "apply"
    When the apply mode is dispatched after the STAGED timer
    Then bin/idp-oke-rebuild --apply runs tofu apply under the estate-ci session token
    And the flux-bootstrap step is reported n/a on a runner
    And main.tf refuses the apply when capacity_monthly_usd exceeds node_pool.budget_monthly_usd

  Scenario: a shape change reaches the running node, not only the pool template (incident 2026-08-26, crew#289)
    Given the node pool template moved to 4 OCPU / 24 GB in apply run 32926017634
    And the running node stayed at 2 OCPU / 12 GB because OCI applies shape changes to new nodes only
    When the pool has node cycling enabled with surge 1 and unavailable 0
    Then a 4 OCPU / 24 GB node is Ready before the 2 / 12 node drains
    And kubectl reports the node allocatable above 3500m cpu
