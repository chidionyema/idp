Feature: a pull request with no live owner does not sit in the queue
  crew#299, 2026-08-26: 66 open PRs, 0 mergeable, most red for days after their
  author session ended. The stale workflow (.github/workflows/stale.yml) owns this rule.
  # Bound by sovereign/tests/bdd/test_stale_pr.py over the workflow's inputs to actions/stale.

  Scenario: a pull request idle for seven days is warned
    Given a pull request with no push, comment or label change for 7 days
    And it does not carry the label "keep-open"
    When the stale workflow runs
    Then the pull request is labelled "stale"
    And a comment says it closes in 7 more days

  Scenario: a warned pull request idle for seven more days is closed
    Given a pull request labelled "stale" with no activity for a further 7 days
    When the stale workflow runs
    Then the pull request is closed and its branch deleted

  Scenario: activity or keep-open cancels the clock
    Given a pull request labelled "stale"
    When someone pushes, comments, or adds the label "keep-open"
    Then the "stale" label is removed and the pull request stays open

  Scenario: issues are never touched
    Given an issue with no activity for 60 days
    When the stale workflow runs
    Then the issue is unchanged
