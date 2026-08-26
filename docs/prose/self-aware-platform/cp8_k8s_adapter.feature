@cp8
Feature: k8s adapter — the same desired-vs-actual interface, deferred until a cluster exists
  Substrate is the laptop until k8s (Fly destroyed 2026-08-25, OKE planned
  but not live). cp4's drift tool and cp2's fat tool stand in launchd and
  colima state for "desired vs actual" today. This checkpoint proves the
  adapter interface without a live cluster call, so swapping in Flux/k8s
  later touches one adapter, not every caller.

  Scenario: Desired-vs-actual is read through one interface, not two code paths
    Given the get_workload_state and get_catalog_drift implementations
    Then both call a single "desired_vs_actual" interface function
    And neither contains launchd- or colima-specific logic inline outside
      that interface's laptop implementation

  Scenario: A k8s implementation of the interface can be registered without
    touching the callers
    Given a stub Flux/k8s implementation of the desired_vs_actual interface
    When it is registered in place of the laptop implementation
    Then get_workload_state and get_catalog_drift run unchanged
    And their output shape (fields and types) is identical to the laptop path

  Scenario: The adapter is not activated against a live cluster yet
    Given no OKE or other k8s cluster is reachable from this estate
    When the k8s desired_vs_actual implementation is exercised
    Then it runs only against a recorded fixture or a documented stub
    And the checkpoint does not claim a live cluster call succeeded
