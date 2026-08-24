@cp6
Feature: Icebox — kept ideas do not enter the work queue
  An idea he wants to keep without building now goes to Icebox as a Markdown
  RFC, and the dispatcher watching for new work is blind to that column.

  Scenario: An Icebox card is never claimed
    Given a card sits in the Icebox column as a Markdown RFC
    When a full dispatcher poll cycle runs
    Then the card is still in Icebox
    And no worktree or branch was created for it
    And no agent session was started for it
