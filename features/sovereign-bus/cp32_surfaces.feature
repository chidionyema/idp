@cp17
Feature: Surfaces — Haptic, Spatial, Converse and Voice
  Master Spec v1.0 §2.1, §2.6. Spatial = force-directed estate graph in the
  cockpit. Haptic = Apple Watch / phone taps through the estate's notification
  path. Voice = Siri Shortcuts on the local kernel API. None of them can move
  the founder from Ghost to Converse.

  Scenario: Spatial graph reflects Temporal truth
    When I open the cockpit "Spatial" view
    Then every running session is a node coloured by health and sized by burn rate
    And hovering a node shows hash, budget and last heartbeat
    And right-click → Halt sends the stop signal

  Scenario: Haptic patterns map to states
    Given the haptic channel is configured
    When a state commits, a boundary approaches, and a halt is required
    Then one tap, two taps and a sustained buzz are sent, respectively
    And no chat message is sent for any of them

  Scenario: Siri status is read from the kernel
    When the shortcut "estate status" runs
    Then it speaks the running, waiting and burn counts from GET /api/status

  Scenario: The system never opens Converse
    When any surface fires
    Then no message is sent to the chat that asks the founder a question
