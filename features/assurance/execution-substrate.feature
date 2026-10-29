Feature: The estate's execution substrate
  The queue hands an agent a task and a workspace to do it in, and it never loses the work.

  Scenario: A task that is running is not re-queued by the sweep
    Given a task that has been waiting in the queue for two hours
    When an agent claims it
    And the zombie sweep runs
    Then the task is still running with the agent that claimed it

  Scenario: A claim that cannot get a workspace gives the task back
    Given a queue whose repository does not exist
    When an agent claims the oldest task
    Then the task is pending again and no agent holds it

  Scenario: The work in a worktree survives the task that made it
    Given a claimed task with an uncommitted change and an untracked file
    When the task completes
    Then the worktree is gone
    And the change and the file are in the archive
