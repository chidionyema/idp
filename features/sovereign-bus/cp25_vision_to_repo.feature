@cp10
Feature: Vision to repo — a photo becomes a committed markdown file and one receipt
  Master Spec v1.0 §2.3. Photo in, JSON out, commit, one line, back to Ghost.

  Scenario: Photo with caption is committed silently
    Given the founder sends a photo with caption "save this article"
    When hermes routes it to the vision model through LiteLLM with the strict JSON prompt
    Then a file docs/<slug>.md is committed in the knowledge repo
    And the reply in the thread is exactly one receipt line
    And no extracted text is echoed to the chat

  Scenario: Model is configuration
    When I run "grep -rn 'gemini\|gpt-4\|claude-' sovereign/vision"
    Then the output is empty
    And the model alias comes from SB_VISION_MODEL
