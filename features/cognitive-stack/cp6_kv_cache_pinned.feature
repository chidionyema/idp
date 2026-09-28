# idp#3448 CP6. Founder: "Engine: vLLM or SGLang, both supporting RadixAttention (prefix
# caching). Setup: on deploy, the engine processes the estate's non-negotiable enterprise
# constraints once, computing a KV-cache matrix pinned in GPU VRAM."
@cp6
Feature: Inference Engine setup — the enterprise-constraints prefix is computed once and pinned

  Scenario: Deploy computes and pins the constraints prefix exactly once
    Given the inference engine (vLLM or SGLang) deploying with RadixAttention enabled
    And the estate's non-negotiable enterprise constraints document
    When the engine starts
    Then it processes the constraints document once and pins the resulting KV-cache matrix in GPU VRAM
    And a second warmup call against the same prefix hits the radix cache rather than recomputing it

  Scenario: Prefix cache hit rate is observable from the door
    Given Backstage Catalog component inference-engine, link "Open metrics"
    When the founder opens the vLLM/SGLang dashboard after one warmup call
    Then prefix_cache_hit_rate is greater than zero

  Scenario: The engine stays provider/model agnostic
    Given the inference engine deployment
    Then it serves an open-weight model, not a single vendor's hosted API
    And its namespace carries a default-deny NetworkPolicy, a ResourceQuota and a LimitRange
    And its healthcheck names an object the row itself creates
