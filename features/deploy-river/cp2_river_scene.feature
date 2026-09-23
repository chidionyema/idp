Feature: CP2 Deploy River scene
  crew#973 done-means: a live push visibly flies; a forced failure visibly cracks its
  gate. The River reads deploy_journeys (CP1) and renders one comet per journey through
  one gate ring per Definition-of-Done stage.

  Scenario: a fresh push ignites a comet at the source gate
    Given the user is on /fleetview/river
    And a push happened 0.5 seconds ago with sha "<sha>"
    When the River's live tail sees the new pr_opened event
    Then a comet appears at the push gate with sha "<sha>" rendered on it
    And the comet's velocity is non-zero

  Scenario: a green gate flashes the ring and accelerates the comet
    Given comet "<sha>" is travelling past the fast-gate ring
    When the live tail sees check:fast-gate status pass
    Then the fast-gate ring flashes green
    And comet "<sha>" accelerates past the gate

  Scenario: a red gate cracks the ring and the comet falls into the rejection basin
    Given comet "<sha>" is travelling past the bdd gate
    When the live tail sees check:bdd status fail
    Then the bdd gate's ring visibly cracks
    And comet "<sha>" falls into the rejection basin below the river
    And the basin glows at the discordant frequency reserved for stuck things

  Scenario: a docked comet shows the receipt (proof, not assertion)
    Given comet "<sha>" has reached the final gate
    When the user holds focus on comet "<sha>"
    Then the receipt hologram renders with: sha, PR number, every check-run name+conclusion, image digest, cosign signature, reconcile revision, first log line
    And every field is sourced from deploy_journey_events rows (no LLM)

  Scenario: the Andon ambient light shifts amber while main is red
    Given the deploy_journeys table has at least one row with state "failed" merged within the last hour
    When the user enters /fleetview/river
    Then the scene's ambient light is amber
    And the shift is felt peripherally, not via a status banner

  Scenario: focusing a gate unfolds its data hologram and focus moves collapses it
    Given the user is on /fleetview/river
    When the user focuses the fast-gate ring
    Then the gate hologram unfolds showing real check-run output for the comet nearest the ring
    When the user moves focus to the bdd ring
    Then the fast-gate hologram collapses
    And the bdd hologram unfolds

  Scenario: a comet's road is read-only; the renderer never invents stages
    Given the user holds focus on comet "<sha>"
    When the receipt hologram renders
    Then every event shown comes from deploy_journey_events for "<sha>" in seq order
    And no LLM interpolates between events
    And a missing stage (no row) renders as a dark ring, not a guessed name

  Scenario: zero chrome — no sidebar, no breadcrumbs, no card floating in space
    Given the user is on /fleetview/river
    When the scene renders
    Then no Backstage sidebar is visible
    And no breadcrumb bar is visible
    And no material-design card floats in front of the river
    And the room is the interface; the whites stay dead

  Scenario: presence — the scene knows being-watched from being-used
    Given the scene has been idle for 30 seconds with no input
    When the user has not spoken, clicked, or moved the pointer
    Then the scene plays ambient mode (slow, beautiful, silent motion)
    When the user speaks or touches the scene
    Then the scene swings to command mode within one frame
    And the renderer never confuses watched for used

  Scenario: a green gate rings consonance; a cracked gate is a dissonance you feel
    Given the river is rendering live
    When a green gate passes
    Then a consonance note plays in the soundtrack
    When a gate fails and cracks
    Then a dissonance note plays at the discordant frequency reserved for stuck things
    And you can hear main go red from the next room

  Scenario: the River reads from CP1, full-bleed to the bezel
    Given the River scene is mounted at /fleetview/river
    When the scene renders its first frame
    Then the scene fills the viewport to the bezel (no margin around the canvas)
    And the data shown comes from get_deploy_journey() / list_deploy_journeys() (CP1)
    And no other data source is consulted by the River
