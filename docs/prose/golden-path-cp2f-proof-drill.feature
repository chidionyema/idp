Feature: End-to-end proof drill for self-service golden paths
  As the founder
  I want proof that a throwaway service can be provisioned and torn down cleanly on every stack
  So that the self-service path is trusted before real services use it

  Scenario Outline: Provision, sign in, and tear down a throwaway service
    Given a throwaway service is provisioned using the "<stack>" golden path
    And its platform pull request has merged and Flux reports it Ready
    When I sign in on the throwaway service's hostname
    Then I get a real response from the service
    When the platform pull request is reverted and the repository is deleted
    Then "flux get kustomizations" shows no trace of the throwaway service

    Examples:
      | stack  |
      | Python |
      | .NET   |
      | Node   |
