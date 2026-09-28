# idp#3448 CP2. Founder: "Storage: Memgraph (memory-first graph database, not a vector DB).
# Structure: every piece of data becomes a node with causal edges (e.g. PR #124 fixes
# Jira-99 -> temporal edge)."
@cp2
Feature: Storage — Memgraph holds every ingested fact as a node with a causal edge

  Scenario: A consumed topic message becomes a node with a causal edge
    Given a message consumed from the github topic naming a PR that closes a Jira issue
    When the graph writer processes it
    Then a node exists for the PR and a node exists for the issue
    And a causal edge (e.g. FIXES) with a timestamp joins them
    And no fact from the four ingestion topics is stored without becoming a node

  Scenario: The graph is queryable from its own door
    Given Backstage Catalog component epistemic-fabric, link "Open graph"
    When the founder runs MATCH (n)-[e]->(m) RETURN count(e) in Memgraph Lab
    Then the count is greater than zero
    And at least one edge type is a causal/temporal relationship, not a bare co-occurrence

  Scenario: The namespace is fenced like every other workload
    Given the epistemic-fabric/memgraph namespace
    Then it carries a default-deny NetworkPolicy, a ResourceQuota and a LimitRange
    And its healthcheck names an object the row itself creates
