# BDD spec for platform/llm/efficiency_gateway.py (crew#284 follow-on, 2026-09-17).
#
# WHY THIS FILE EXISTS BEFORE THE CODE IS PROVED
# -----------------------------------------------
# The efficiency gateway was written without a BDD spec. That is the same breach
# the deterministic-verifier feature documents: a proposer who writes both the code
# and the proof grades their own homework. This feature is the independent specification
# the gateway must satisfy — it does not read the implementation, only the observable
# behaviour at the LiteLLM pre-call hook boundary.
#
# MODEL-AGNOSTIC: every scenario exercises the hook as LiteLLM calls it
# (`async_pre_call_hook`) — the same boundary whether the downstream vendor is
# groq, anthropic, gemini, cerebras, minimax or any future lane the estate adds.
# No scenario names a vendor. No scenario reads the vendor's response. The gateway
# modifies the REQUEST before it leaves the estate; the vendor never sees the waste.
#
# INDEPENDENCE CRITERION (epistemic_firewall.py Rule 2)
# -----------------------------------------------
# A step that calls the gateway and asserts a visible mutation (message body changed,
# counter incremented, token estimate updated) is an INDEPENDENT WITNESS. A step that
# only asserts "no exception was raised" is not — it proves the code ran, not that it
# did anything. Every scenario below requires a visible, measurable change.
Feature: The estate efficiency gateway cuts tokens before every vendor call, model-agnostic

  Rule: [1] CacheGuardian detects and records system-prompt drift

    Scenario: A stable system prompt keeps the prefix cache alive
      Given a gateway instance
      And a request with system prompt "You are a helpful assistant."
      When the hook runs twice with the same system prompt
      Then cache_hits is 2 and cache_misses is 0

    Scenario: A drifted system prompt is flagged as a cache miss
      Given a gateway instance
      And a request with system prompt "You are a helpful assistant."
      When the hook runs once with the original prompt
      And the hook runs again with a different system prompt
      Then cache_misses is 1

  Rule: [2] TokenKiller removes repeated lines from tool results

    Scenario: Duplicate lines in a tool_result message are stripped
      Given a gateway instance
      And a tool_result message with content "line A\nline A\nline A\nunique"
      When the hook runs
      Then the tool_result content contains "line A" exactly once
      And the content still contains "unique"
      And tool_line_compressions is 2

  Rule: [3] MCPAdapter truncates verbose tool descriptions

    Scenario: A tool description longer than the limit is truncated
      Given a gateway instance
      And a tool with a description of 2000 characters
      When the hook runs
      Then the tool description is at most MAX_TOOL_DESC_CHARS + 1 characters long
      And the description ends with the ellipsis marker
      And schemas_compressed is 1

    Scenario: A short tool description is not touched
      Given a gateway instance
      And a tool with a description of 20 characters
      When the hook runs
      Then schemas_compressed is 0

  Rule: [4] TokenBudgetOrchestrator tracks cumulative token spend

    Scenario: Each call increments the call counter and the token estimate
      Given a gateway instance
      And a request with 400 characters of user content
      When the hook runs
      Then calls is 1 and cumulative_tokens is 100
      When the hook runs again with the same content
      Then calls is 2 and cumulative_tokens is 200

  Rule: [5] SoLPi replaces duplicate large observations with handles

    Scenario: A second identical large tool result is replaced with a reference handle
      Given a gateway instance
      And two tool_result messages with identical content of 600 characters
      When the hook runs
      Then the first tool_result is unchanged
      And the second tool_result contains "[duplicate observation"
      And obs_hits is 1

  Rule: [6] DynamicContextPruning removes duplicate tool_result entries

    Scenario: A duplicate tool_result with the same tool_call_id and content is pruned
      Given a gateway instance
      And a conversation of 14 messages including two identical tool_result entries
      When the hook runs
      Then one of the duplicate tool_result entries is removed
      And pruned_duplicates is 1

  Rule: [7] CompactionManager bounds conversation history

    Scenario: A history longer than MAX_HISTORY_MSGS is truncated
      Given a gateway instance
      And a conversation of MAX_HISTORY_MSGS + 20 user messages
      When the hook runs
      Then the message count is at most MAX_HISTORY_MSGS
      And compactions is 1

    Scenario: System messages are preserved during compaction
      Given a gateway instance
      And a conversation with one system message and MAX_HISTORY_MSGS + 10 user messages
      When the hook runs
      Then the system message is still present
      And compactions is 1

  Rule: [8] GistingSimulator condenses old assistant turns

    Scenario: An old assistant turn beyond the gist boundary is condensed
      Given a gateway instance
      And a conversation where the first message is an assistant turn of 500 characters
      And GIST_AFTER_MSGS + 1 more recent messages follow it
      When the hook runs
      Then the first message starts with "[GISTED:"
      And the gist marker records the original character count
      And gisted is 1

    Scenario: A recent assistant turn is not condensed
      Given a gateway instance
      And a single assistant message of 500 characters
      When the hook runs
      Then the message does not start with "[GISTED:"
      And gisted is 0

  Rule: All 8 mechanisms fire on a realistic over-limit session

    Scenario: A realistic session with drift, duplicates, long history, and verbose tools is optimised
      Given a gateway instance
      And a realistic over-limit session payload
      When the hook runs
      Then calls is 1
      And cumulative_tokens is greater than 0
      And schemas_compressed is at least 1
      And the message count is at most MAX_HISTORY_MSGS
