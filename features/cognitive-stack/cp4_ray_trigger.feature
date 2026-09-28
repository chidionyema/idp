# idp#3448 CP4. Founder: "Pipeline: Ray for distributed orchestration, Unsloth for training.
# Trigger: when a major node changes in the Knowledge Graph (e.g. a core API schema updates),
# Ray kicks off a background job."
@cp4
Feature: Neural Compiler trigger — a major graph node change kicks off a Ray job

  Scenario: A core API schema node change submits a Ray job
    Given a node in Memgraph tagged major (e.g. a core API schema node)
    When that node's version property changes
    Then a Ray job is submitted within one healer cycle
    And the job's metadata names the triggering node and its prior and new version

  Scenario: A minor node change does not trigger training
    Given a node in Memgraph not tagged major
    When that node's property changes
    Then no Ray job is submitted for that change

  Scenario: The trigger's own workload is fenced and health-checked
    Given the neural-compiler namespace
    Then it carries a default-deny NetworkPolicy, a ResourceQuota and a LimitRange
    And its healthcheck names an object the row itself creates
