# crew#292 CP4, 2026-08-26: the chaos and chaos-mesh Flux rows read Ready, the Schedule
# backstage-pod-kill was 5h old with status.time null, and the backstage namespace carried no
# chaos-mesh.org/inject label while the chart ran with enableFilterNamespace: true. A weekly
# experiment that the controller ignores looks exactly like one that passes.
Feature: A chaos experiment targets a namespace Chaos Mesh is allowed to inject into
  # Bound by sovereign/tests/bdd/test_gate_chaos_target_namespace.py. The first-run receipt scenario lives in
  # docs/prose/chaos-live.feature until a drill runs it.

  Scenario: The backstage namespace is labelled for injection
    Given platform/chaos/mesh/helmrelease.yaml sets enableFilterNamespace true
    And platform/chaos/backstage-pod-kill.yaml selects namespace backstage
    Then platform/backstage/base/namespace.yaml carries chaos-mesh.org/inject: enabled
    And tests/test_incident_chaos_target_namespace_unlabelled.py refuses a target namespace without it
