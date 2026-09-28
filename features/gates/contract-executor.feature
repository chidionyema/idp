# Founder essay, 2026-09-14, "PhD cold military surgeon": "Design-by-Contract for Tool
# Calls... A deterministic script (NOT the agent) checks the post-condition against the live
# system. If it fails, the PRM penalises the trajectory and the agent is forced to adapt
# before continuing."
#
# Ticket: docs/tickets/2026-09-14-reasoning-gateway.md, deliverable D3. Gate: bin/idp-contract,
# a small condition grammar over declared observations (no frontier LLM judge, no second live
# prober -- R43); a subject with no observation is BLIND, never assumed to hold.
Feature: A tool call's post-condition is checked by a deterministic script, not the agent

  Scenario: The post-condition never holds by its deadline
    Given a contract whose pre-condition holds and whose post-condition never passes within its deadline
    When bin/idp-contract runs it
    Then it exits 1 and names the post-condition as the cause

  Scenario: Both conditions hold
    Given a contract whose pre-condition holds and whose post-condition passes before its deadline
    When bin/idp-contract runs it
    Then it exits 0, because the post-condition was confirmed by a real observation

  Scenario: A subject has no observation at all
    Given a contract whose post-condition names a subject with no observation
    When bin/idp-contract runs it
    Then it exits 2, because a missing observation is BLIND, never assumed to hold

  Scenario: The contract file cannot be read
    Given a contract file that does not exist
    When bin/idp-contract runs it
    Then it exits 2, because an unreadable contract is never a clean bill
