Feature: Python golden path scaffolding
  As a person standing up a new service
  I want a Python template with standards, tests, CI and the estate guard baked in
  So that the new repo starts compliant instead of drifting

  Scenario: Provisioning a Python service produces a compliant repo
    Given the "estate-service-python" template is available in Backstage Scaffolder
    When I run the template with a service name
    Then a GitHub repository is created with a Poetry project, ruff config and pre-commit hooks
    And the repository's GitHub Actions run ruff, pytest and a build step
    And the SessionStart hook installs the "~/.estate" guard from git
    And the CI run on the new repository reports green
