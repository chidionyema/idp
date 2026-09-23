@cp7
Feature: drills and the crew board show live counts, not bare links
  docs/specs/backstage-as-a-product.md CP7. founder-drills lists nine Actions links;
  founder-crew-board lists four GitHub links. Both already have live data behind them
  (verdict-* workflows' signed verdicts; the GitHub issues API crew status already reads).

  Scenario: the drills card shows the last verdict per drill
    Given the verdict-backstage, verdict-langfuse and verdict-signoz workflows have each run
    When the founder-drills card loads
    Then it lists each drill with its most recent signed verdict and the time it was signed
    And it does not require a click through to Actions to know the last result

  Scenario: the crew board card shows live issue counts
    Given the chidionyema/crew repository has open issues, some labelled P1
    When the founder-crew-board card loads
    Then it shows the open issue count and the P1 count read in this page load
    And the two numbers match a fresh query against the GitHub issues API
