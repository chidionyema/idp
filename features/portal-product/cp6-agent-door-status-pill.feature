@cp6
Feature: the agent doors show a live status pill, not a manifest link
  docs/specs/backstage-as-a-product.md CP6. founder-otto-door links to a raw /healthz JSON
  response; founder-mcp-gateway, founder-otto and founder-cursor link to manifests. Each gets a
  status pill read through a proxy to its own health endpoint.

  Scenario: the Otto door's pill reflects its own healthz answer
    Given founder-otto-door's proxy target is Otto's /healthz endpoint
    When the founder-otto-door card loads
    Then the pill shows up when /healthz answers 200
    And the pill shows down or degraded when it does not, with the reason it read

  Scenario: the MCP gateway's pill is read through a proxy, never a hardcoded host
    Given app-config.yaml declares the MCP gateway's proxy endpoint
    When the founder-mcp-gateway card loads
    Then the status pill's value came from that proxy call in this page load
    And no file in backstage/founder names the gateway's host as a literal
