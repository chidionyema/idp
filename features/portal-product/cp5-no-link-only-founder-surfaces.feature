@cp5
Feature: no founder-surface entity ships with zero live content
  docs/specs/backstage-as-a-product.md CP5. 20 founder-surface entities carry only a GitHub
  manifest link today (founder-gitops through founder-cluster-plumbing and others named in the
  spec's inventory table). Each gains a kubernetes-label-selector and the CP4 layer card.

  Scenario: every founder-surface entity carries a kubernetes-label-selector
    Given the list of founder-surface entities named level 1 in the spec's inventory table
    When backstage/founder/catalog-info.yaml is read after this checkpoint
    Then every one of those entities carries a backstage.io/kubernetes-label-selector annotation
    And the selector matches at least one real workload in the cluster

  Scenario: the previously link-only entities render the layer card
    Given a founder-surface entity that was level 1 before this checkpoint
    When its entity page loads
    Then it renders the same layer-card component CP4 built
    And it is no longer counted as level 1 in a re-run of the inventory
