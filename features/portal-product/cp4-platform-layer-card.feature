@cp4
Feature: every platform layer's entity page draws its own live state
  docs/specs/backstage-as-a-product.md CP4. All 64 type: platform-layer entities carry a
  kubernetes-label-selector and a Signoz link; none draws anything on the card itself. One
  shared component, rendered on all 64 at once.

  Scenario: the layer card is one component reused by every platform layer
    Given the catalogue lists every entity of type platform-layer
    When any one of their entity pages loads
    Then the same layer-card component renders on all of them
    And the component reads Flux Ready state, pod count and last-deploy time for that entity

  Scenario: the layer card's Ready state matches the cluster, not the manifest
    Given a platform-layer entity whose Flux Kustomization is not Ready
    When its entity page loads
    Then the layer card shows not-Ready
    And it shows the reason string the Kustomization itself carries

  Scenario: adding the card to one layer adds it to all
    Given the layer-card component is added to the platform-layer entity page template
    When a new platform-layer entity is added to the catalogue with no extra code
    Then its entity page also renders the layer card
