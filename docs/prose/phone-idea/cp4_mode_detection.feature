@cp4
Feature: Mode detection — exploring stays talk, building drafts a feature
  The founder: "what if I just want to explore an idea." Exploratory phrasing
  must never produce a card or a file; build phrasing must draft one.

  Scenario: Exploratory phrasing enters sounding-board mode
    When he sends "what if we tried X" to hermes-v2
    Then hermes-v2 replies with discussion only
    And it creates zero board cards
    And it writes zero files

  Scenario: Build phrasing enters PM mode
    When he sends "build this: X" to hermes-v2
    Then hermes-v2 drafts a BDD feature file for X
    And the draft is not yet written to idp/board or to disk
