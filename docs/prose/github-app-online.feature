# Prose until a drill runs them: these call GitHub through gh (crew#286 CP7).
Feature: The GitHub App manifest and the identity gh acts as
  Scenario: The manifest is a one-tap page with no webhook and no public listing
    Given platform/github-app/manifest.json
    When bin/idp-github-app manifest runs
    Then it prints one data: URL whose form posts the manifest to github.com/settings/apps/new
    And the manifest has public false, no events and an inactive hook

  Scenario: A session on a personal token is a FAIL
    Given gh answers /user with a login
    When bin/idp-github-app status runs
    Then it prints FAIL naming the person and exits 1
