# idp#3448 CP5. Founder: "Output: trains a Rank-16 LoRA adapter (e.g.
# auth_api_v3_lora.safetensors) overnight from the graph's delta."
@cp5
Feature: Neural Compiler output — Unsloth trains a named Rank-16 LoRA adapter from the graph delta

  Scenario: A triggered job produces a rank-16 adapter named after its trigger
    Given a Ray job submitted by CP4 for a triggering node named auth_api_v3
    When Unsloth completes training on the graph's delta for that node
    Then an adapter artifact named auth_api_v3_lora.safetensors exists in the adapter registry
    And its LoRA rank (lora_r) is exactly 16

  Scenario: The adapter is provider/model agnostic
    Given the trained adapter artifact
    Then it is trained against an open-weight base model
    And no checkpoint couples the adapter format to a single vendor's proprietary API

  Scenario: The door shows the new artifact
    Given Backstage Catalog component neural-compiler, link "Open adapter registry"
    When the founder opens it after an overnight training run
    Then the newest object is named <triggering-node>_lora.safetensors with an overnight timestamp
