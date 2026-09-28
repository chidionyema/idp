Feature: Flux reconciles a template-created service
  As the platform
  I want Flux to be the only thing that applies a new service's infra
  So that nothing is applied by hand or by the template directly

  Scenario: Merging the platform pull request brings the service up
    Given the pull request adding "platform/<service>/" has been merged to idp
    When Flux reconciles "idp/clusters/oke"
    Then "flux get kustomizations platform-<service>" reports Ready
