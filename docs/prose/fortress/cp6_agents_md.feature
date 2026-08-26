@cp6
Feature: Living specs — AGENTS.md is the version-controlled boundary for this repo
  The founder: "AGENTS.md as the version-controlled boundary/rules format."

  Scenario: AGENTS.md is a committed file, not a convention in someone's head
    When I run "git -C idp show HEAD:AGENTS.md"
    Then the output is non-empty

  Scenario: A gate reads it both ways
    Given a pre-commit or CI gate checks an agent-authored diff against AGENTS.md
    When the gate runs once against a diff that violates a rule and once against one that does not
    Then the violating diff is refused and the compliant diff passes, in the same run
