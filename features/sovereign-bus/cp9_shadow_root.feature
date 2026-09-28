@cp9 @phase2
Feature: Shadow root — a branch pointer that tracks legacy state one to one
  .estate/heads/shadow_main always points at the Merkle root equal to the
  legacy DB's current state. The root hash IS the checkpoint.

  Scenario: Root advances with every write
    When N writes go through the sidecar
    Then .estate/heads/shadow_main changed N times
    And walking the DAG from genesis to shadow_main reproduces the legacy DB exactly

  Scenario: Root is verifiable
    When I run "bin/sb root --json"
    Then the output has "root", "parent", "nodes", "verified" true
