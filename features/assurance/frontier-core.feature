Feature: Frontier assurance core falsifiers
  Independently observed outcomes and authenticated evidence are required.
  These component scenarios do not claim live promotion or operational closure.

  Scenario Outline: Only independently authenticated candidate evidence is accepted
    Given a signed candidate receipt with "<condition>"
    When the admission receipt is validated
    Then the evidence decision is "<decision>"
    Examples:
      | condition        | decision |
      | valid            | accepted |
      | forged signature | refused |
      | stale base        | refused |
      | replayed nonce    | refused |
      | builder signer    | refused |
      | empty tests       | refused |
      | skipped check     | refused |
      | malformed scope   | refused |
      | malformed roster  | refused |

  Scenario Outline: Observable function results are judged outside the candidate
    Given a pure function candidate with "<behavior>"
    When the independent observable oracle executes the case
    Then the verification report status is "<status>"
    And the expected answer is not sent to the candidate
    Examples:
      | behavior        | status    |
      | correct         | VERIFIED  |
      | wrong result    | EXHAUSTED |
      | early exit      | EXHAUSTED |
      | extra output    | EXHAUSTED |

  Scenario Outline: Calibration requires valid observations of both classes
    Given calibration observations with "<population>"
    When the binary calibration is evaluated
    Then the calibration decision is "<status>"
    Examples:
      | population           | status       |
      | both correct classes | calibrated   |
      | single class         | inconclusive |
      | missing score        | inconclusive |
      | minority unsupported | inconclusive |

  Scenario: A timeout cannot hide a surviving mutant
    Given mutant evidence with a timeout and a known survivor
    When both inventory orders are graded
    Then both mutation decisions are "FAIL"

  Scenario: An unfinished comparison is not statistical equivalence
    Given a fixed-horizon comparison with equal scores and insufficient observations
    When the fixed-horizon evaluator runs
    Then the comparison decision is "INCONCLUSIVE"
