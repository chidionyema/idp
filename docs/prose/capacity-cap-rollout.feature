# Prose until a drill runs them: these need the GitHub apply job and a live node pool (crew#289).
Feature: paid capacity reaches the running node from GitHub
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
