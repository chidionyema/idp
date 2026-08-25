@cp13 @v2
Feature: Auto-distillation — every frontier success is a training row; routing follows measured accuracy
  Master Spec v1.0 §3.3. Traces live in Langfuse datasets; the local model is
  graded by a deterministic grader; LiteLLM routing changes only on a measured
  number, and the change is a receipt.

  Scenario: A successful frontier step lands in the dataset
    Given a session step ran on a frontier model and finished "done"
    Then a Langfuse dataset item exists with prompt, completion and tool calls, tagged with the task class

  Scenario: Routing flips on measurement, not on hope
    When I run "bin/sb distill --task-class git_rebase --json"
    Then the output has "local_accuracy" measured over at least 20 dataset items
    And if local_accuracy ≥ 0.9 the LiteLLM route for that class is set to the local model
    And a receipt "[✓] DISTILL | task:git_rebase | local_accuracy:<n> | routing:<model>" is written
