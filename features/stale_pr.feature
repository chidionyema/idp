Feature: a pull request with no live owner does not sit in the queue
  crew#299, 2026-08-26: 66 open PRs, 0 mergeable, most red for days after their
  author session ended. crew#504, 2026-08-27: 113 open PRs thrashed the runners; the
  window is now 24 hours, hourly, and a closed PR keeps its branch and two ways back.
  The stale workflow (.github/workflows/stale.yml) owns this rule.
  # Bound by sovereign/tests/bdd/test_stale_pr.py over the workflow's inputs to actions/stale.

  Scenario: a pull request idle for a day is closed
    Given a pull request with no push, comment or label change for 1 day
    And it does not carry the label "keep-open"
    When the stale workflow runs
    Then the pull request is labelled "stale" and closed in the same run
    And the branch is kept

  Scenario: the close message names both ways back
    Given a pull request closed by the stale workflow
    When its author reads the close message
    Then it names "gh pr reopen" and "Blocked-by"

  Scenario: activity or keep-open cancels the clock
    Given a pull request labelled "stale"
    When someone pushes, comments, or adds the label "keep-open"
    Then the "stale" label is removed and the pull request stays open

  Scenario: issues are never touched
    Given an issue with no activity for 60 days
    When the stale workflow runs
    Then the issue is unchanged
