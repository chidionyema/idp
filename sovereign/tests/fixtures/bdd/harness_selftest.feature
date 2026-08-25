Feature: The acceptance harness itself
  Not an acceptance criterion of the Sovereign Bus. This feature exists so the
  `bin/idp-ci` bdd leg is proved in the direction that matters least often and
  is wrong most often: that it PASSES on correct work. Its twin,
  sovereign/tests/fixtures/bdd/unbound/, proves it refuses a feature whose step
  has no definition. A guard only ever seen refusing has never been shown to
  permit (LAW 38).

  Every shared fixture in sovereign/tests/bdd/conftest.py is exercised here, so
  a fixture that stops working is a failing scenario rather than a surprise in
  five other builders' modules.

  Scenario: The temporary estate is real, isolated and configured
    Given a temporary estate
    Then the DAG root exists and is empty
    And the receipts path is inside the temporary estate
    And "sovereign.config" resolves "estate.home" to the temporary estate

  Scenario: The clock only moves when a step moves it
    Given a fake clock
    When the clock advances 300 seconds
    Then 300 seconds have elapsed
    And the clock did not move on its own

  Scenario: A budget cannot be overdrawn by two concurrent spends
    Given a session with budget 2000 tokens
    When 8 threads each spend 250 tokens at the same time
    Then the balance is 0
    And no spend took the balance below zero

  Scenario: An unsigned refill is refused
    Given a session with budget 2000 tokens
    When the budget is exhausted
    Then an unsigned refill of 10000 tokens is refused
    And a signed refill of 10000 tokens restores the balance

  Scenario: Ghost silence is observable
    Given a captured-messages sink
    Then zero messages were sent to the chat
    When a catastrophe is reported
    Then exactly one message was sent to the chat

  Scenario: The scratch repository is a real git repository
    Given a scratch repo
    Then HEAD names a commit that exists in the repo
