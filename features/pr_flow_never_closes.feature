Feature: a pull request is never closed to make room; it lands on GitHub's own verdict
  Founder, 2026-09-29: "autuo closing prs is void, pr just disapears andwork foesmissing ...
  we are ai ing to run up tp 20 agnects concurrently". Measured that day: 99 PRs closed unmerged in
  a fortnight, 10 of them holding commits main never received. The closers were pr-cap (a sixth PR
  closed on open), pr-consolidate (merged with -X theirs, closed the originals, deleted the
  branches), stale (closed at 24h idle) and the red clock in bin/idp-pr-age (closed at six bounds).
  All four are gone. The pile grew because one advisory check (shadow-verify) made every PR read
  red, so none was armed; bin/idp-pr-age now reads red only where GitHub refuses the merge.
  # Bound by sovereign/tests/bdd/test_pr_flow_never_closes.py over bin/idp-pr-age and the workflows.

  Scenario: a PR whose only failing check is advisory is armed to merge
    Given an open PR whose required checks pass and whose shadow-verify check failed
    When bin/idp-pr-age grades it
    Then its reason is "green"

  Scenario: a PR GitHub refuses names the refusing check
    Given an open PR that GitHub blocks and whose bdd check failed
    When bin/idp-pr-age grades it
    Then its reason is "red:bdd"

  Scenario: an old red PR is commented on, never drafted or closed
    Given an open PR that GitHub blocks, 100 hours old
    When bin/idp-pr-age acts on it
    Then no close and no draft is sent to GitHub

  Scenario: a green PR is armed as a squash, the only merge main's linear history accepts
    Given an open PR whose required checks pass and whose shadow-verify check failed
    When bin/idp-pr-age arms it
    Then bin/idp-pr-arm is asked for a squash merge

  Scenario: no workflow closes a pull request
    Given every workflow under .github/workflows
    When each is read
    Then none runs "gh pr close", closes a pull request through the API, or runs actions/stale

  Scenario: a green PR whose checks have already settled is merged, not left unarmed
    Given GitHub refuses to arm auto-merge because the PR is in unstable status
    When bin/idp-pr-arm runs on it
    Then it merges the PR as a squash and says so
