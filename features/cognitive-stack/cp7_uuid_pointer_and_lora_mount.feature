# idp#3448 CP7. Founder: "Execution: a new agent passes a UUID pointer to that cache,
# inheriting full enterprise context at zero input-token cost, and dynamically mounts the
# relevant LoRA (e.g. auth_api_v3_lora) in milliseconds to execute a patch, then unmounts it."
@cp7
Feature: Inference Engine execution — UUID cache inheritance and dynamic LoRA mount/unmount

  Scenario: A new agent inherits the pinned cache at zero input-token cost
    Given the pinned enterprise-constraints KV-cache from CP6 and its UUID pointer
    When a new agent's request carries that UUID pointer
    Then the response usage reports prefix_tokens_billed equal to zero for the constraints prefix
    And the agent's context includes the full enterprise constraints without re-sending them

  Scenario: The relevant LoRA mounts, executes one patch, and unmounts
    Given an agent request naming the auth_api_v3_lora adapter and a UUID cache pointer
    When the engine executes the request
    Then a "lora mounted" log line appears before the patch executes
    And the patch executes using the mounted adapter
    And a "lora unmounted" log line appears after the patch completes
    And the mount-to-unmount interval is measured in milliseconds

  Scenario: The trace is visible from the door
    Given Backstage Catalog component inference-engine, link "Open agent trace"
    When the founder opens the trace for that request
    Then it shows the UUID cache pointer, the LoRA mount event, the patch execution and the LoRA unmount event
