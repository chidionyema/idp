# crew#286 CP7: agent sessions act as a GitHub App installation, one token per lane, never the
# founder's personal token. GitHub creates Apps only from a manifest, which ends in a browser
# redirect (crew#288), so the founder taps Create once; everything else is bin/idp-github-app.
Feature: Agents act as a GitHub App, one narrowed token per lane

  Scenario: The manifest is a one-tap page with no webhook and no public listing
    Given platform/github-app/manifest.json
    When bin/idp-github-app manifest runs
    Then it prints one data: URL whose form posts the manifest to github.com/settings/apps/new
    And the manifest has public false, no events and an inactive hook

  Scenario: A lane never gets more than the App holds
    Given every lane in platform/github-app/lanes.json
    Then each permission it names is in manifest.json default_permissions at the same or a lower level

  Scenario: An unknown lane is refused
    When bin/idp-github-app token no-such-lane runs
    Then it prints REFUSED and exits 2 before touching the vault

  Scenario: A session on a personal token is a FAIL
    Given gh answers /user with a login
    When bin/idp-github-app status runs
    Then it prints FAIL naming the person and exits 1
