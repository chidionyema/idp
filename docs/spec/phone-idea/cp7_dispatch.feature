@cp7
Feature: Dispatch — the watched column starts work when the laptop is awake
  A card confirmed to "To Do" must start work while the laptop is awake, and
  wait, not vanish, while it is asleep.

  Scenario: A card starts within one poll cycle while awake
    Given the laptop is awake
    When a new card appears in the To Do column
    Then within one poll cycle a new git worktree exists for it
    And a new branch exists for it
    And a new agent session is running against that worktree

  Scenario: A card waits while the laptop sleeps
    Given the laptop is asleep
    When a new card appears in the To Do column
    Then the card remains present and unclaimed
    When the laptop wakes
    Then the card starts within one poll cycle
