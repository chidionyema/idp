@cp8
Feature: Welcome back — the two branches never conflict
  He returns to find the original session untouched and the phone idea
  visible as its own piece of work, with no collision between them.

  Scenario: Both branches coexist without conflict
    Given a laptop session was running on branch A before he left
    And a phone-originated card was dispatched to branch B while he was away
    When he returns
    Then branch A is exactly where the session left it, or has an opened PR
    And branch B is a PR or an in-progress card
    And a merge check between A and B reports no conflict
    And the board shows both cards in a state matching each branch
