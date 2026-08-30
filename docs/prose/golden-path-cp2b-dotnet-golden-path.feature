Feature: .NET golden path scaffolding
  As a person standing up a new service
  I want a .NET template with standards, tests, CI and the estate guard baked in
  So that the new repo starts compliant instead of drifting

  Scenario: Provisioning a .NET service produces a compliant repo
    Given the "estate-service-dotnet" template is available in Backstage Scaffolder
    When I run the template with a service name
    Then a GitHub repository is created with a dotnet project and an EditorConfig
    And the repository's GitHub Actions run dotnet build, dotnet test and dotnet format
    And the SessionStart hook installs the "~/.estate" guard from git
    And the CI run on the new repository reports green
