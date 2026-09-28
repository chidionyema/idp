Feature: Egress block — direct AI vendor egress denied at the network layer
  As the estate security invariant
  All pods outside the LLM proxy namespace must be unable to reach AI vendor APIs
  So that no code path, SDK, or subprocess can bypass the efficiency mechanisms

  Background:
    Given the Calico GlobalNetworkPolicy manifest exists at platform/calico/raw/deny-direct-ai-vendor-egress.yaml
    And the GlobalNetworkSet manifest exists in the same file

  Scenario: GlobalNetworkPolicy has correct name and order
    When the policy manifest is parsed
    Then the GlobalNetworkPolicy name is "deny-direct-ai-vendor-egress"
    And the policy order is 1
    And the policy type includes "Egress"

  Scenario: GlobalNetworkSet covers all current AI vendor endpoints
    When the GlobalNetworkSet manifest is parsed
    Then the allowedEgressDomains includes "api.anthropic.com"
    And the allowedEgressDomains includes "api.openai.com"
    And the allowedEgressDomains includes "api.groq.com"
    And the allowedEgressDomains includes "api.deepseek.com"
    And the allowedEgressDomains includes "generativelanguage.googleapis.com"
    And the allowedEgressDomains includes "api.mistral.ai"
    And the GlobalNetworkSet label "estate.internal/role" is "ai-vendor-endpoint"

  Scenario: Policy blocks all namespaces except the approved exempt set
    When the namespaceSelector is parsed from the GlobalNetworkPolicy
    Then the selector uses "not in" logic
    And "llm" is in the exempt namespaces
    And "kube-system" is in the exempt namespaces
    And "flux-system" is in the exempt namespaces
    And "kube-public" is in the exempt namespaces
    And "kube-node-lease" is in the exempt namespaces
    And exactly 5 namespaces are exempt

  Scenario: Egress rule targets the vendor endpoint GlobalNetworkSet by label
    When the egress rules are parsed
    Then there is exactly 1 egress rule
    And the egress action is "Deny"
    And the egress protocol is "TCP"
    And the destination selector references 'estate.internal/role == "ai-vendor-endpoint"'
    And the destination port is 443

  Scenario Outline: A non-exempt namespace has no allow-egress rule to vendor endpoints
    When checking namespace "<namespace>"
    Then the namespace is not in the exempt list
    And a pod in that namespace would be subject to the deny rule

    Examples:
      | namespace       |
      | default         |
      | backstage       |
      | hermes-agent    |
      | agent-workforce |
      | otto-gateway    |
      | research        |
      | epistemic-fabric|

  Scenario: Policy manifest is valid YAML and passes structural schema check
    When the manifest file is read
    Then it parses as valid YAML
    And it contains exactly 2 documents
    And the first document kind is "GlobalNetworkSet"
    And the second document kind is "GlobalNetworkPolicy"
