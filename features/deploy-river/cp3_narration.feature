Feature: CP3 narration engine
  crew#973 done-means: story mode speaks a real deploy, timestamps correct. Narration is
  template-over-ledger: deterministic text from real timestamps, spoken by the sovereign
  voice service. No LLM narrates the pipeline.

  Scenario: story mode names the journey's actual push time, gates, and merge time
    Given a journey row for sha "<sha>" with these events in order:
      | stage            | status | ts                    |
      | pr_opened        | pass   | 2026-09-23T08:00:00Z  |
      | check:fast-gate  | pass   | 2026-09-23T08:01:00Z  |
      | check:bdd        | pass   | 2026-09-23T08:05:00Z  |
      | merged           | pass   | 2026-09-23T08:07:00Z  |
      | reconcile        | pass   | 2026-09-23T08:09:00Z  |
    When story mode renders the journey
    Then the spoken text contains "pushed at 08:00"
    And the spoken text contains "fast-gate passed in one minute"
    And the spoken text contains "merged at 08:07"
    And the spoken text contains "reconciled at 08:09"

  Scenario: live commentary speaks only at transitions, never speculates
    Given a journey row for sha "<sha>" with the same events
    When live commentary watches for transitions
    Then no commentary is spoken between events
    And one line is spoken per status change
    And each line names the stage and the new status (pass / fail / unknown)

  Scenario: a failed gate is named, never glossed over
    Given a journey with a check:bdd event whose status is "fail"
    When story mode renders the journey
    Then the spoken text names the failed gate by stage name
    And the spoken text says "failed" not "took a moment"

  Scenario: unknown stages are read as unknown, never guessed
    Given a journey where reconcile has status "unknown"
    When story mode renders the journey
    Then the spoken text says "reconcile: unknown" verbatim
    And no sentence fills in "and then it was running"

  Scenario: a sha with no recorded journey is BLIND, never a fabricated story
    Given sha "<sha>" has no deploy_journeys row
    When story mode is invoked for "<sha>"
    Then narration is BLIND with a named error
    And no template is rendered

  Scenario: timestamps are deterministic; two runs produce byte-identical text
    Given the same journey row
    When story mode renders it twice
    Then both renderings are byte-identical
    And sha256 of both renderings is equal

  Scenario: the narration engine never imports an LLM client
    Given the narration engine source tree
    When the imports are read
    Then no module in the LLM-provider tree is imported
    And the only network call is to the sovereign voice service, never to a model

  Scenario: narration speaks in one or two sentences, no markdown, no lists
    Given any rendered journey
    When the spoken text is measured
    Then it has at most two sentences
    And it contains no markdown (no `**`, no `##`, no `-` list markers)
    And it contains no code-block fences

  Scenario: live commentary speaks only at transitions and never wakes the room
    Given the scene is in ambient mode (CP2 / CP5 presence rule)
    When a transition lands
    Then exactly one line is spoken for the transition
    And nothing else is spoken between transitions
    And the ambient scene is not interrupted for any other reason
