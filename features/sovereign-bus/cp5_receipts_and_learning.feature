@cp5
Feature: Receipts and learning — every founder touch is recorded so Otto can learn from it
  Founder: "prove it, don't tell me." Every start, stop, steer, approve and
  deny is a receipt on disk and a trace in Langfuse. Receipts are the
  training set for Otto's next version; a session without a trace did not
  happen.

  Scenario: Every signal is a receipt
    Given a session started with "--runner ask --task 'needs: x'"
    When I run "bin/sb steer <session_id> --by founder --text 'use the other branch'"
    And I run "bin/sb deny <session_id> --by founder"
    Then the receipts file has lines with kind "start", "steer", "deny" for <session_id>
    And each line has "ts", "session_id", "kind", "by"

  Scenario: Every session is a Langfuse trace
    Given a completed session
    When I query Langfuse for traces tagged with <session_id>
    Then at least one trace is returned

  Scenario: Failure episodes are queryable
    When I run "bin/sb episodes --kind stop --json"
    Then every row has "session_id", "task", "reason", "step"
