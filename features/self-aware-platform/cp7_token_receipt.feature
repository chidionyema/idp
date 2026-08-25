@cp7
Feature: Token receipt — the waste the founder named, measured before and after
  Founder: "think of all the tool calls and tokens wasted repeating the same
  actions." This checkpoint is a script that measures three recurring
  questions against the old path (shell commands, repeated probes) and the
  new path (this MCP surface) and prints both numbers, so the claim is a
  measured number, not an assertion.

  Scenario: The script defines three recurring questions
    Given a script "bin/self-aware-token-receipt"
    Then it names three recurring questions agents ask today, for example
      "why is X down", "what is running that isn't cataloged", and
      "what changed since the last approval"

  Scenario: Before numbers are measured, not remembered
    When the script runs the "before" path for each question using the
      pre-existing shell-command chain
    Then it prints the tool-call count and token count actually consumed for
      each question, sourced from a fresh run, not a prior log line

  Scenario: After numbers are measured against the new MCP surface
    When the script runs the "after" path for each question using
      get_estate_inventory, get_workload_state, get_workload_logs, or
      get_catalog_drift as appropriate
    Then it prints the tool-call count and token count actually consumed for
      each question from that same fresh run

  Scenario: The receipt is the number, not a claim
    When bin/self-aware-token-receipt runs end to end
    Then its final output is a table with one row per question and columns
      for before-tool-calls, after-tool-calls, before-tokens, after-tokens
    And the script's exit code is nonzero if any "after" row fails to
      complete, so a broken measurement cannot print a comparison
