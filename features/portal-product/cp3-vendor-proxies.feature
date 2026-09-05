@cp3
Feature: the vendor dashboards show one live fact on the card, not only a link
  docs/specs/backstage-as-a-product.md CP3. founder-traces, founder-telemetry and
  founder-dashboards carry an external link and nothing else today; the vendor answers are real
  and live, only unread by the portal.

  Scenario: a Langfuse proxy exists and answers
    Given app-config.yaml declares a proxy endpoint for Langfuse
    When the founder-traces card loads
    Then it shows a trace count read through that proxy in the same page load
    And the proxy target is not typed as a literal host anywhere but the proxy config

  Scenario: a SigNoz proxy exists and answers
    Given app-config.yaml declares a proxy endpoint for SigNoz
    When the founder-telemetry card loads
    Then it shows a value read through that proxy in the same page load

  Scenario: a Superset proxy exists and answers
    Given app-config.yaml declares a proxy endpoint for Superset
    When the founder-dashboards card loads
    Then it shows a value read through that proxy in the same page load

  Scenario: a proxy failure is shown, not hidden
    Given one of the three vendor proxies answers with an error
    When its card loads
    Then the card states the fact could not be read and why
    And it does not fall back to showing a stale number as if it were current
