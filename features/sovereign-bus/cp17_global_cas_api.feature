@cp17 @phase2
Feature: Global CAS API — one local blob router for frontend, backend and agents
  Scenario: Put and get by hash
    When a client PUTs a blob to the local CAS API
    Then it is stored once under .estate/cas/<hash>
    And any client GETs it by hash, and a second PUT of the same bytes stores nothing new

  Scenario: No literal endpoints
    Then the CAS API host, port and path prefix are config keys
