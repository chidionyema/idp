Feature: Judge drift — continuous calibration sentinel detects distribution shift
  As the judge reliability invariant
  The JudgeDriftSentinel must detect when recent verdicts diverge from the baseline distribution
  So that a drifting judge is caught and recalibrated before it silently mis-grades agent output

  Background:
    Given the judge drift module exists at platform/eval/judge_drift.py
    And the JudgeDriftLoop module exists at platform/eval/judge_drift_loop.py

  Scenario: Jensen-Shannon divergence is zero for identical distributions
    Given a baseline distribution of all 0.8 scores
    And a current window of all 0.8 scores
    When JS divergence is computed
    Then the divergence is approximately 0.0

  Scenario: JS divergence is non-zero for different distributions
    Given a baseline distribution of all 0.8 scores
    And a current window of all 0.2 scores
    When JS divergence is computed
    Then the divergence is greater than 0.1

  Scenario: Partial window does not trigger a drift alert
    Given a JudgeDriftSentinel with a current window of size 100
    When fewer than 100 scores are recorded
    Then no drift alert is returned

  Scenario: Drift alert fires when JS divergence exceeds threshold
    Given a JudgeDriftSentinel with threshold 0.15 and baseline of 500 high scores
    When 100 low scores are recorded filling the window
    Then a drift alert is returned
    And the alert action is "judge_drift_detected"
    And the alert names the divergence value

  Scenario: JudgeDriftLoop pre_llm always allows (not a blocking gate)
    Given a JudgeDriftLoop instance
    When pre_llm is called with any state
    Then the GateDecision action is "allow"

  Scenario: JudgeDriftLoop reports shadow mode in health check
    Given a JudgeDriftLoop instance
    When health is called
    Then the mode is "shadow"
    And is_healthy is true before any errors

  Scenario: ParEval loop halts when max_tasks turns are reached
    Given a ParEvalLoop with max_tasks set to 3
    And an agent state with 3 AI messages
    When pre_llm is called
    Then the GateDecision action is "halt"
    And the evidence names max_tasks

  Scenario: ParEval loop allows when turn count is below max_tasks
    Given a ParEvalLoop with max_tasks set to 3
    And an agent state with 1 AI messages
    When pre_llm is called
    Then the GateDecision action is "allow"
