@cp11
Feature: Persistence — the platform holds the record, not vendor chat
  Standing founder ruling: nothing generated may live only in Telegram
  history. Every draft, RFC, card and decision has a row in idp/board or a
  GitHub issue/PR.

  Scenario: A draft survives losing the Telegram conversation
    Given a draft, an RFC, a card and a confirmation decision have all occurred
    When the Telegram conversation that produced them is deleted
    Then each of those four still has a corresponding row in idp/board's
      database or a GitHub issue or pull request in chidionyema/crew
