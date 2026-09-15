# docs/specs/2026-09-15-asymmetric-compute-leverage-spec-v0.1.md, section 5
# (OFF-01/02, GRIND-01, DARWIN-01, ORCH-01..03), tracked by idp#3525 CP5.
# Scenarios are the spec's own ACCEPT lines, not new criteria.

@cp5
Feature: Offload, grind, darwin and orchestration — no tokens on deterministic ops, unkillable grind, confirmed darwin loop, Temporal only

  Scenario: OFF-01 — deterministic operations never execute as a model call
    Given a set of traces from operations classified math/string/date/aggregation
    When the traces are statically scanned
    Then zero model tokens are attributable to those deterministic ops

  Scenario: OFF-02 — the CPU-sandbox execute_python tool excludes offloadable raw data from the prompt, when built
    Given the execute_python CPU-sandbox tool is a named gap
    When it is built
    Then prompt payloads exclude raw data the tool can compute the result for

  Scenario: GRIND-01 — the overnight grind worker cannot terminate before its test passes or the 4h wall-clock limit
    Given the overnight grind worker running against its deterministic test
    When a kill-signal fault is injected at hour 2
    Then the worker resumes or rejects termination
    And termination is refused until the test passes or the 4h limit is reached

  Scenario: DARWIN-01 — the weekly meta-optimizer loop is confirmed against the repo, or recorded as a gap
    Given sovereign/shadow/distill.py and sovereign/shadow/branching.py
    When a code review checks for the generate/eval/auto-deploy loop
    Then file-level evidence of the loop is produced, or the gap is scheduled and recorded as a named gap

  Scenario: ORCH-01 — orchestration reuses Temporal child workflows, no second framework
    Given the dependency manifest
    When it is reviewed
    Then it contains no CrewAI or LangGraph dependency

  Scenario: ORCH-02 — flat-rate tiers are governed by a time budget, metered tiers by a dollar budget
    Given a flat-rate tier
    When candidate generation runs on it
    Then branch.budget_pct is ignored and the time-box is honored
    Given a metered tier
    When candidate generation runs on it
    Then the dollar budget is honored

  Scenario: ORCH-03 — every routed call carries a config_id, answerable as a Langfuse query
    Given two different configs run against the router
    When a Langfuse query is issued over the resulting traces
    Then it returns a per-config cost/pass/latency table
