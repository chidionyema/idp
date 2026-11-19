@assurance @pre_pr
Feature: Recursive adversarial verification before estate effects
  Background:
    Given an immutable candidate and independently owned acceptance contract

  Scenario Outline: Mandatory evidence cannot be replaced by a claim
    Given the candidate evidence has "<defect>"
    When the trusted admission authority evaluates the candidate
    Then admission is refused or inconclusive
    And no pull request creation is attempted
    And the existing obligation retains its owner or recovery custody
    Examples:
      | defect                            |
      | missing receipt                   |
      | forged signature                  |
      | builder signer                    |
      | wrong repository                  |
      | stale base                        |
      | changed head                      |
      | wrong test contract               |
      | narrower scope                    |
      | expired receipt                   |
      | stale fence                       |
      | replayed nonce                    |
      | empty required tests              |
      | mandatory skipped check           |
      | runner error                      |
      | surviving required mutant         |
      | candidate suppresses test process |

  Scenario: Valid independent evidence permits precisely one PR
    Given all mandatory predicates passed with independently authenticated fresh evidence
    When two concurrent promotion attempts target the same candidate
    Then at most one pull request is created
    And the resulting PR head is the verified candidate

  Scenario: A new base invalidates old evidence
    Given the candidate passed against base A
    When main moves to base B before the creation effect
    Then admission is refused until the candidate is verified against base B

  Scenario Outline: Judge calibration must discriminate real outcomes
    Given gold observations with "<population>"
    When calibration is calculated
    Then the calibration status is "<status>"
    Examples:
      | population                   | status       |
      | both classes correctly judged| calibrated   |
      | only one gold class          | inconclusive |
      | missing or malformed scores  | inconclusive |
      | insufficient class support   | inconclusive |

  Scenario: Failed mandatory verifier is not a passing candidate
    Given verification infrastructure is unavailable
    When a privileged effect is requested
    Then the effect is refused pending independent recovery
    And safe diagnosis remains available

  Scenario: A pre-existing base failure does not strand a recovery
    Given the base and candidate have measured outcomes against the same contract
    When an authorized recovery candidate eliminates the baseline defect without new violations
    Then the bounded recovery policy may admit it with independent signed evidence

  Scenario: Red team and solver protect security and utility
    Given the same protected contract and isolated environment
    When the red team executes an invalid transition and the solver executes a legitimate transition
    Then the former is refused and the latter succeeds
    And any confirmed counterexample becomes an owned KARMA obligation

  Scenario: No statistical difference is not equivalence
    Given an inconclusive matched comparison and a preregistered equivalence margin
    When the evaluator considers promotion
    Then it abstains unless the specified statistical rule establishes the margin

  Scenario: Operational closure requires real effects
    Given the PR has landed but no independent operation and objective evidence exists
    When FLOW evaluates completion
    Then the obligation remains open
