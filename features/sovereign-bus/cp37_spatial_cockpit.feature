@cp37
Feature: The cockpit page is the presence model, not a log dump
  Founder: "this ui is terrible" (crew#284 CP4). Master Spec v1.0 §2.1: Ghost
  is the default and nothing else renders until the founder clicks; Spatial
  is a force-directed estate topology entered only by that click or by a
  catastrophe; the inbox is not a fourth column dumping every tick.

  Scenario: Page in Ghost renders no session text and no inbox lines
    Given a session with task "SEED_TASK_MARKER_XYZ" is running
    And the inbox contains the line "SEED_INBOX_MARKER_XYZ"
    When I GET "/"
    Then the response does not contain "SEED_TASK_MARKER_XYZ"
    And the response does not contain "SEED_INBOX_MARKER_XYZ"
    And the response contains "ghost-dot"

  Scenario: Presence red renders the red dot and one emergency line
    Given the presence state is a catastrophe
    When I GET "/api/status"
    Then the JSON field "dot" is "red"
    And the JSON field "emergency" is one line with no question mark
