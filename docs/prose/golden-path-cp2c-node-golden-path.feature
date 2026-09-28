Feature: Node golden path scaffolding
  As a person standing up a new service
  I want a Node template with standards, tests, CI and the estate guard baked in
  So that the new repo starts compliant instead of drifting

  Scenario: Provisioning a Node service produces a compliant repo
    Given the "estate-service-node" template is available in Backstage Scaffolder
    When I run the template with a service name
    Then a GitHub repository is created with an npm or pnpm workspace, ESLint and Prettier config
    And the repository's GitHub Actions run lint, test and build steps
    And the SessionStart hook installs the "~/.estate" guard from git
    And the CI run on the new repository reports green
