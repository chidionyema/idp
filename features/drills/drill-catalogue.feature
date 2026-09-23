# crew#292 CP2. Founder 2026-08-26: "we have drills? ... when we get it working we need to drill".
# Probe: the `drills` row of bin/idp-verify, which reads drills/catalogue.yaml and asks GitHub for
# the last successful run of each workflow. Every row above it in idp-verify grades something
# static; this one grades whether the scheduled drills actually fired.
Feature: Every scheduled drill has run recently, and the catalogue says which drills exist
  A workflow whose schedule silently stops firing looks exactly like one that passes every night:
  the file is still in .github/workflows, the cron line is still there, and nothing goes red. The
  catalogue is the list of drills the estate claims to run; the drills row is the grade.
  # Bound by sovereign/tests/bdd/test_gate_drill_catalogue.py. The scenarios that grade live GitHub runs
  # through bin/idp-verify live in docs/prose/drill-catalogue-live.feature until a drill runs them.

  Scenario: The catalogue names only drills that are really scheduled
    Given drills/catalogue.yaml
    Then every entry names a file that exists under .github/workflows
    And each entry's schedule string is the cron line that workflow declares
    And no entry exists for a workflow that has no schedule block

