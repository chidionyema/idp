Feature: The event spine
  The environment emits a fact, the fabric carries it durably, the bridge turns it into a
  signal, the agent wakes and checks the fact against the cluster's own record, and a
  receipt is left.

  The founder's build kit is the reference; the estate's own rules are the arbiter. Where
  the two differ, the difference is named in docs/specs/2026-10-26-efda-spine.md rather
  than papered over: the subject is a D1 subject, the message id is derived when the
  publisher does not send one, and the dead-letter path is the estate's own.

  Scenario: A reconcile event travels on a subject the estate's grammar accepts
    Given a Provider with type "nats" and channel "flux.event.kustomization.reconciled.v1"
    And a bridge with a durable consumer on "flux.event.>"
    When Flux publishes a Kustomization reconciliation event for "efda" in "flux-system"
    Then the event is signalled to the workflow "spine-verify-kustomization-flux-system-efda"
    And the signal name is "flux.reconciled"
    And the subject "flux.event.kustomization.reconciled.v1" passes the estate's subject rules
    And the subject "evt.flux.kustomization.reconciled" fails the estate's subject rules

  Scenario: The same event twice signals once
    Given a bridge with a durable consumer on "flux.event.>"
    And the event "msg-1" has already been signalled
    When Flux publishes a Kustomization reconciliation event with the id "msg-1"
    Then the bridge does not signal again
    And the event is acknowledged

  Scenario: An event with no identity is not silently dropped
    Given a bridge with a durable consumer on "flux.event.>"
    When a message arrives that carries no parsable event body
    Then the message is terminated
    And nothing is signalled

  Scenario: A signal that cannot be delivered is retried, not lost
    Given a bridge with a durable consumer on "flux.event.>"
    And Temporal cannot be reached
    When Flux publishes a Kustomization reconciliation event with the id "msg-2"
    Then the message is negatively acknowledged
    And the event is not marked as processed

  Scenario: A reconciliation that failed is not a verified receipt
    Given an object "efda" in "flux-system" whose reconcile failed
    When the spine checks the reconciliation
    Then the outcome is "wait"
    And the receipt says the verdict was "failed"

  Scenario: An object that is gone is routed to a human
    Given an object "efda" in "flux-system" that no longer exists
    When the spine checks the reconciliation
    Then the outcome is "gap"
    And the receipt is routed to "human_review"

  Scenario: A reconciliation that succeeded leaves a receipt
    Given an object "efda" in "flux-system" whose reconcile succeeded
    When the spine checks the reconciliation
    Then the outcome is "complete"
    And the receipt carries a digest of its own body
    And the receipt is written into the evidence layer
