Feature: CP4 every runtime, enriched
  Claude Code, Cyrus, Dagster and GitHub Actions sessions share the board with trace, spend, PR and ticket.

  Scenario: three runtimes on one board
    Given a Claude Code session, a Cyrus run and a bot pull request exist
    When I open the fleet page
    Then all three are listed
    And each shows a trace link, a spend figure and a pull request link

  Scenario: an adapter that breaks the schema fails CI
    Given an adapter emits a record missing "runtime"
    When the plugin tests run
    Then they fail naming the adapter and the field
