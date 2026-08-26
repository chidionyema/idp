# crew#292 CP4, 2026-08-26: the chaos and chaos-mesh Flux rows read Ready, the Schedule
# backstage-pod-kill was 5h old with status.time null, and the backstage namespace carried no
# chaos-mesh.org/inject label while the chart ran with enableFilterNamespace: true. A weekly
# experiment that the controller ignores looks exactly like one that passes.
Feature: A chaos experiment targets a namespace Chaos Mesh is allowed to inject into
  Scenario: The backstage namespace is labelled for injection
    Given platform/chaos/mesh/helmrelease.yaml sets enableFilterNamespace true
    And platform/chaos/backstage-pod-kill.yaml selects namespace backstage
    Then platform/backstage/base/namespace.yaml carries chaos-mesh.org/inject: enabled
    And tests/test_incident_chaos_target_namespace_unlabelled.py refuses a target namespace without it

  Scenario: The first run is a receipt, not a promise
    Given the label has been applied by Flux
    When a one-off Workflow with the Schedule's templates is created in namespace backstage
    Then its Accomplished condition is True within 90s
    And backstage answered /healthcheck 200 throughout (StatusCheck did not abort)
