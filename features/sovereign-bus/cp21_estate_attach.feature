@cp21
Feature: Estate attach — point the OS at any repo, directory or workspace
  Founder, 2026-08-25: estate-agnostic. `sb attach <path>` mounts a target;
  state lives in the target's .estate/ or a global cache keyed by path hash;
  a missing AGENTS.md is scaffolded conservatively in memory.

  Scenario: Attach a fresh repo
    Given a git repo with no .estate and no AGENTS.md
    When I run "bin/sb attach <path> --json"
    Then the output has "root", "nodes", "hash"
    And a receipt "[✓] ESTATE_MOUNTED | root:<path> | nodes:N | hash:<h>" is written
    And a receipt "[✓] POLICY_INHERITED | policy:AGENTS.md (auto-scaffolded) | mode:Ghost" follows

  Scenario: The scaffolded policy is conservative
    Given an attached estate with a scaffolded policy
    Then read operations are allowed
    And write and git operations require a receipt commit
    And "rm -rf", "git push --force" require quorum and a hardware signature

  Scenario: Sessions run inside the attached estate
    When I run "bin/sb start --estate <path> --runner echo --task x --budget 100 --json"
    Then the session's repo is <path>
    And its receipts are chained under that estate's .estate/

  Scenario: Global commands
    When I run "bin/sb status" and "bin/sb halt --all --by founder --signed"
    Then status lists every attached estate and its running sessions
    And halt stops every running session with one receipt each
