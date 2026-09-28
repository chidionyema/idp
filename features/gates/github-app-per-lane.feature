# crew#286 CP7: agent sessions act as a GitHub App installation, one token per lane, never the
# founder's personal token. GitHub creates Apps only from a manifest, which ends in a browser
# redirect (crew#288), so the founder taps Create once; everything else is bin/idp-github-app.
Feature: Agents act as a GitHub App, one narrowed token per lane
  # Bound by sovereign/tests/bdd/test_gate_github_app.py. The manifest and status scenarios need gh
  # against GitHub and live in docs/prose/github-app-online.feature until a drill runs them.

  Scenario: A lane never gets more than the App holds
    Given every lane in platform/github-app/lanes.json
    Then each permission it names is in manifest.json default_permissions at the same or a lower level

  Scenario: An unknown lane is refused
    When bin/idp-github-app token no-such-lane runs
    Then it prints REFUSED and exits 2 before touching the vault
