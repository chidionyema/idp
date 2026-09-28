Feature: CP4 time-scrub and Holmes interrogation
  crew#973 done-means: "why did this fail" answers from a real red run, by voice. The
  River's left-edge drag scrolls back through the deploy_journeys ledger; gate holograms
  unfold on focus; Holmes interrogation answers from the real estate MCP, never from
  memory.

  Scenario: dragging the river's edge back replays last week's deploys at 60x
    Given the user is on /fleetview/river
    And deploy_journeys has 14 rows with started_at spread over the last seven days
    When the user drags the river's left edge back to "one week ago"
    Then the scene renders all 14 comets in formation over the scrubbed timeline
    And the playback advances at 60x real time
    And the Andon ambient colour reflects each comet's state at its docked time

  Scenario: focusing a comet stops the replay and opens the receipt
    Given the replay is playing
    When the user focuses comet "<sha>"
    Then the replay pauses at that comet's ts
    And the receipt hologram opens with the journey's events in seq order

  Scenario: "why did this fail" routes the question to ask_holmes and speaks the answer
    Given the user has focused a comet whose check:bdd event has status "fail"
    When the user asks "why did this fail"
    Then the question is routed to ask_holmes on the estate MCP server (ADR 0006)
    And the spoken answer is the response from ask_holmes, not from a local heuristic
    And the spoken answer is shown as an ephemeral subtitle that fades after 3 seconds
    And the heard-transcript proof renders once and disappears (the HUD spec's rule)

  Scenario: "why did this fail" on a green comet is BLIND, never a forced answer
    Given the focused comet has no failed event
    When the user asks "why did this fail"
    Then the response is "no failed gate on this journey" verbatim
    And ask_holmes is not called

  Scenario: a failed gate hologram names the check-run and the conclusion verbatim
    Given comet "<sha>" with check:bdd status fail
    When the user focuses the bdd gate
    Then the hologram renders the check-run name, conclusion ("failure"), and the
    conclusion timestamp as recorded in deploy_journey_events
    And no other source of truth is consulted (the hologram is the ledger row)

  Scenario: scrubbing past the latest ledger row is BLIND, not an extrapolation
    Given the latest deploy_journeys row's started_at is "T"
    When the user drags past T
    Then the scene shows a named "no journeys past T" gap
    And no comet is fabricated for the empty region

  Scenario: Holmes is called once per question; the same question is not re-routed
    Given the user has asked "why did this fail" once
    When the user asks it again on the same gate within 5 seconds
    Then ask_holmes is called only once
    And the cached answer is replayed verbatim

  Scenario: the subtitle proof is shown, not hidden, on every answer
    Given any Holmes answer is spoken
    When the answer finishes
    Then a subtitle line with the spoken text appears in the scene
    And the subtitle fades after 3 seconds
    And the transcript is not hidden by chrome

  Scenario: time machine — "take me to last Thursday 4pm" flies the camera into the past
    Given the user says "take me to last Thursday at 4pm"
    When the Observatory camera receives the spatial-temporal intent
    Then the scene animates to a snapshot of the estate at that timestamp
    And every named source (deploy_journeys, jev_decisions, red-team catalog, Aevum) is
    shown as it was at that timestamp, never as it is now
    And the rendering is read-only — no ring can be steered into the past
