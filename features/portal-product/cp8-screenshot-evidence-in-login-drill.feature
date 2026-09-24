@cp8
Feature: the hourly login drill is the standing screenshot evidence for this spec
  docs/specs/backstage-as-a-product.md CP8. login-drill.yml already accepts evidence_paths and
  bin/idp-login-drill already screenshots every path it is given; this checkpoint only changes
  the default so the evidence exists on every scheduled run, not only on demand.

  Scenario: the scheduled login drill captures the showcase, tools and ops pages
    Given login-drill.yml runs on its hourly schedule with no manual input
    When the run completes
    Then its screenshot evidence includes /showcase, /tools and /ops
    And each screenshot is younger than the run's own start time

  Scenario: a red login drill is a red Demo gate
    Given the login drill fails to sign in or fails to load one of the three pages
    When docs/reference/policy/definition-of-done.md Gate 2's Demo row is checked for this spec
    Then it reads not-done
    And it names the login-drill run that failed as the evidence
