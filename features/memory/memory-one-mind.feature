Feature: One mind: memory is delivered just in time and shared in real time, without becoming one point of failure
  Adds to memory.feature. Same rule (AGENTS.md section 11): each scenario lands with its bound test and implementation.

  Background:
    Given agents A and B hold live claims on overlapping paths
    And agent C holds a live claim on unrelated paths

  @memory @one-mind @edge-propagation
  Scenario: A lesson captured by A reaches B within 30 seconds
    When A's capture records a lesson on a shared path
    Then B's inbox holds it within 30 seconds
    And B's next model call through the router carries it

  @memory @one-mind @edge-scoped-push
  Scenario: A lesson is not broadcast to an agent with no overlap
    When A's capture records a lesson on a shared path
    Then C receives nothing
    And the push is counted against B's token budget

  @memory @one-mind @edge-gate-failure-lesson
  Scenario: A failing gate is answered with the lesson that matches the failure
    Given a recorded lesson whose failure text matches the gate's output
    When a gate fails for B with that output
    Then the gate output includes the lesson, its source and its trust tier

  @memory @one-mind @edge-unverified-label
  Scenario: A new fact is labelled unverified until corroborated
    When a fact is captured
    Then every delivery of it is labelled "unverified"
    And the label clears only when an outcome or a passing probe corroborates it

  @memory @one-mind @edge-poison-canary
  Scenario: A planted false fact is never served as current
    Given the poison canary plants a false fact on a shared path
    When B and C start tasks
    Then the fact is delivered only as unverified, or not at all
    And the canary fails the audit if it is ever served as current

  @memory @one-mind @edge-conflict-visible
  Scenario: Conflicting facts are shown together
    Given two stored facts about the same path contradict each other
    When a brief is built
    Then both are shown with their sources and a conflict marker
    And neither silently replaces the other

  @memory @one-mind @edge-no-recapture-loop
  Scenario: Delivered memory is not recaptured as a new fact
    Given a brief was injected into B's model call
    When B's exchange is captured
    Then the injected block is excluded from the capture

  @memory @one-mind @edge-secret-scrub
  Scenario: Secrets never enter the shared mind
    Given an exchange contains a token-shaped string
    When it is captured
    Then the stored record holds a redaction marker and no secret

  @memory @one-mind @edge-tenant-boundary
  Scenario: One mind does not cross tenants
    Given a fact belongs to tenant X
    When an agent working for tenant Y builds a brief
    Then the fact is absent

  @memory @one-mind @edge-merged-read
  Scenario: A read unions every live store and removes duplicates
    Given the same lesson exists in growmos and in the spool
    When recall runs
    Then it is returned once, tagged with both lanes

  @memory @one-mind @edge-store-down-read
  Scenario: A store being down degrades the read, loudly
    Given the door does not answer
    When recall runs
    Then results come from the remaining stores
    And the first line states which stores answered and which did not
