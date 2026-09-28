Feature: Forge guard — model training runs are budget-gated and quality-gated
  As the forge execution invariant
  Training runs must not exceed their declared budget and datasets must meet minimum quality bars
  So that expensive GPU training neither exceeds spend limits nor trains on insufficient data

  Background:
    Given the forge common module exists at forge/common.py
    And the forge task contract exists at forge/task.yaml

  Scenario: task.yaml carries all required contract fields
    When the task file is loaded
    Then it contains the key "task"
    And it contains the key "base"
    And it contains the key "kind"
    And it contains the key "prompt_template"
    And it contains the key "labels"
    And it contains the key "abstain_below"
    And it contains the key "min_agreement"
    And it contains the key "kv_cache_prefix"
    And it contains the key "compute"
    And the prompt_template contains "{input}"
    And the abstain_below is between 0 and 1 exclusive

  Scenario: Shipped task.yaml fits within its own declared budget
    When the cost gate is applied to the shipped task.yaml
    Then the cost gate returns no refusal reason

  Scenario: A run within budget is not refused by the cost gate
    Given a compute plan with GPU "H100", timeout 1800 seconds, budget USD 2.00
    When the cost gate is applied
    Then the cost gate returns no refusal reason

  Scenario: A run over budget is refused with the spend numbers in the reason
    Given a compute plan with GPU "H100", timeout 3600 seconds, budget USD 2.00
    When the cost gate is applied
    Then the cost gate returns a refusal reason
    And the refusal reason contains the expected cost "3.95"
    And the refusal reason contains the declared budget "2.00"

  Scenario: An unpriced GPU is refused as un-budgetable
    Given a compute plan with GPU "TPU" and budget USD 100.00
    When the cost gate is applied
    Then the cost gate returns a refusal reason
    And the refusal reason contains "no price"

  Scenario: A compute plan with no GPU block defaults to T4
    Given a compute plan with no GPU block
    When the default compute plan is resolved
    Then the GPU is "T4"
    And the cost gate returns no refusal reason

  Scenario: T4 GPU cost per hour is accurate
    When the T4 hourly cost is looked up for 3600 seconds
    Then the cost is 0.59 USD

  Scenario: Dataset split is refused below 500 rows
    Given a dataset with 499 rows
    When the split function is called
    Then a ValueError is raised

  Scenario: Dataset split at 500 rows is deterministic and 80/20
    Given a dataset with 500 rows
    When the split function is called twice
    Then both results are identical
    And 400 rows are labelled "train"
    And 100 rows are labelled "eval"

  Scenario: Label probability abstain triggers when margin is below threshold
    Given logit scores where both labels are equal
    When label_probs is called
    Then the margin is 0.0
    And the probability is 0.5

  Scenario: Grade counts only answered rows, not abstentions
    Given a set of predictions where 1 of 3 rows abstains below margin 0.8
    When grade is applied
    Then held_out is 3
    And agreement is 0.5
    And abstain_rate is approximately 0.333
