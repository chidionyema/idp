Feature: CP5 Three Planes Observatory
  crew#973 done-means: jev decisions, judge drift and Aevum seals all animate in one
  view. The Observatory is three concentric rings, one plane each, and work passes
  outward through them. Where a plane emits nothing, the ring shows a named gap; UNKNOWN
  is the default, never a failure.

  Scenario: ring 1 (Generative Swarm) animates every live agent as a star
    Given the jev_decisions table has rows for the last 60 seconds
    When the user enters /fleetview/planes
    Then ring 1 has one star per row
    And each star's burn is sized by the row's cost_usd
    And CRDT shadow-memory edits fire as synapses between stars

  Scenario: ring 2 (Adversarial Crucible) renders JudgeWorker scores as scales
    Given the red-team catalog has rows with JudgeWorker four-dim scores
    When ring 2 renders
    Then four scales turn, one per dimension (tool_f1 / arg_validity / result_utilization / error_recovery)
    And JudgeDriftSentinel's JS-divergence value balances the ring
    When the divergence exceeds 0.15
    Then the ring visibly wobbles

  Scenario: ring 3 (Physics Engine) renders Z3 proofs and Aevum seals
    Given verifier gauntlet verdicts and Aevum receipts are recorded
    When ring 3 renders
    Then Z3 proofs grow as crystal lattices over the verdict rows
    And Aevum attestations appear as seals stamped in light, hash-chained
    And every seal names its Ed25519 + ML-DSA-65 dual signature and timestamp

  Scenario: work passes outward through the three rings
    Given a single decision lands on the Swarm
    When the user watches for one minute
    Then a representation of that decision moves outward through ring 1 to ring 2
    And through ring 2 to ring 3 if and only if the Crucible accepts it
    And a rejected work item falls back inward as an ember into ring 1
    And nothing passes ring 3 without a recorded Aevum seal

  Scenario: a plane with no data shows a named gap, not a green tick
    Given jev_decisions is empty for the current window
    When ring 1 renders
    Then ring 1 shows "no jev decisions in window" named in the scene
    And the ring is dark, not green
    And no star is fabricated

  Scenario: the Universal Write Boundary is drawn as a crack
    Given the unsealed gap at platform/idp_agent/engine.py:311 still writes via open().write()
    When the Observatory renders
    Then a visible crack appears in the ring wall, named "unsealed write boundary"
    And the crack glows until the gap is sealed
    And the page ships with the crack, never hides it

  Scenario: the Observatory reads only from the one estate MCP server
    Given the Observatory's data sources are listed
    When the imports of the Observatory's data layer are read
    Then every data call goes through the estate MCP server (ADR 0006)
    And no second server, no second store, no second bus is added

  Scenario: zero chrome — the rings are the page
    Given the user is on /fleetview/planes
    When the scene renders
    Then no Backstage sidebar, no breadcrumb, no floating card is visible
    And the three rings fill the viewport to the bezel
    And the room is the interface

  Scenario: presence — the rings idle until interrogated
    Given the Observatory has been idle for 30 seconds
    When no input has arrived
    Then the rings rotate slowly and silently
    When the user speaks or targets a ring
    Then that ring swings into command mode within one frame

  Scenario: every named gap renders as a dark segment with a name, never a green tick
    Given any ring whose plane data is empty or BLIND
    When the ring renders
    Then that arc of the ring is dark with a label naming the missing source
    And no green status is rendered
    And the renderer does not invent data to fill the gap

  Scenario: the soundtrack binds each plane to an instrument family
    Given the Observatory is rendering live
    When a jev_decision lands
    Then ring 1 emits a note from the Swarm's instrument
    When a JudgeWorker verdict lands
    Then ring 2 emits a note from the Crucible's instrument
    When an Aevum seal is stamped
    Then ring 3 emits a note from the Physics instrument
    And you can hear the planes argue with each other
