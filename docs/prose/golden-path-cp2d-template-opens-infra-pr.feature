Feature: Template opens the platform infra pull request
  As the platform
  I want the scaffolder to open a pull request against idp adding the service's platform folder
  So that infra is never hand-written per service

  Scenario: A scaffolder run opens a pull request touching only the new service's platform folder
    Given a scaffolder run for any of the three stacks has completed
    When I inspect the pull request opened against the "idp" repository
    Then the pull request adds a "platform/<service>/" folder only
    And the folder follows the "platform/prospector" shape of namespace and ExternalSecrets
