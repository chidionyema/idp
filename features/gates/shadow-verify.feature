Feature: Shadow verify — workload convergence assertion after change applied in vcluster
  As the shadow dimension gate (spec W2.2)
  A change applied in the sandbox vcluster must produce a verifiable convergence observation
  So that changes are proven against something that can run them before meeting the real gate

  Background:
    Given the shadow-verify tool exists at bin/idp-shadow-verify

  Scenario: A ready Deployment with matching replicas passes
    Given an observation where ready is true, kind is Deployment, requiredReplicas is 2, availableReplicas is 2, readyReplicas is 2
    When idp-shadow-verify grades the observation
    Then the grade is pass
    And there are no failure reasons

  Scenario: A Deployment that is not ready fails
    Given an observation where ready is false, kind is Deployment
    When idp-shadow-verify grades the observation
    Then the grade is fail
    And the failure reason mentions "not Ready"

  Scenario: An observation silent about readiness fails closed
    Given an observation where ready is absent, kind is Deployment
    When idp-shadow-verify grades the observation
    Then the grade is fail
    And the failure reason mentions "silent about readiness"

  Scenario: A Deployment with fewer available replicas than required fails
    Given an observation where ready is true, kind is Deployment, requiredReplicas is 3, availableReplicas is 2, readyReplicas is 2
    When idp-shadow-verify grades the observation
    Then the grade is fail
    And the failure reason mentions "replica"

  Scenario: An observation for an unverified kind fails closed
    Given an observation where kind is Pod
    When idp-shadow-verify grades the observation
    Then the grade is fail
    And the failure reason mentions "unverified kind"

  Scenario: An observation without requiredReplicas fails closed
    Given an observation where ready is true, kind is Deployment without requiredReplicas
    When idp-shadow-verify grades the observation
    Then the grade is fail
    And the failure reason mentions "requiredReplicas"

  Scenario Outline: All supported workload kinds are accepted
    Given an observation where ready is true, kind is <kind>, requiredReplicas is 1, availableReplicas is 1, readyReplicas is 1
    When idp-shadow-verify grades the observation
    Then the grade is pass

    Examples:
      | kind        |
      | Deployment  |
      | StatefulSet |

  Scenario: A StatefulSet with probe failures fails
    Given an observation where ready is true, kind is StatefulSet, requiredReplicas is 1, availableReplicas is 1, readyReplicas is 1, probesPassing is false
    When idp-shadow-verify grades the observation
    Then the grade is fail
    And the failure reason mentions "probe"
