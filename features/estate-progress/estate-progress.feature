Feature: The estate's progress report
  The estate's delivery chain already records what it did: the Greenlane state holds per-lane
  timings and failure reasons, CI holds every run, the claims hold who is working what, the
  decision door holds what the founder was asked, the cluster receipt holds what became live.
  Nothing joined them, so the estate could not see itself.

  One report joins them. One writer writes it. Every surface renders it. A source that cannot be
  read is blind, never zero, and the verdict is a deterministic function of the signals.

  Scenario: A chain that landed something is progressing
    Given a delivery chain with one lane landed in the window
    When the progress report is built
    Then the verdict is PROGRESSING

  Scenario: A source that cannot be read is blind and never zero
    Given a delivery chain with one lane landed in the window
    And a source that cannot be read
    When the progress report is built
    Then that source is marked blind with a reason
    And the report does not claim zero for the unread source
    And the verdict is not a clean PROGRESSING

  Scenario: A third of the batches in conflict is slipping
    Given a delivery chain with a third of its batches ending in conflict
    When the progress report is built
    Then the verdict is SLIPPING

  Scenario: Nothing landed while a lane sits old is stuck
    Given a delivery chain with nothing landed and a lane three hours old
    When the progress report is built
    Then the verdict is STUCK

  Scenario: Progress is a delta against the previous report
    Given a delivery chain with one lane landed in the window
    And a previous report that recorded three lanes landed in the window
    When the progress report is built
    Then the delta on lanes landed is minus two

  Scenario: The spoken answer carries the verdict and the blindness
    Given a delivery chain with one lane landed in the window
    And a source that cannot be read
    When the progress report is spoken
    Then the spoken answer names the verdict
    And the spoken answer names the blind source

  Scenario: Every surface renders the same signal set
    Given a delivery chain with one lane landed in the window
    When the progress report is written
    Then the json report and the prometheus file and the markdown carry the same number of landed lanes
