@cp1
Feature: Durable session — a session outlives the process that runs it
  Founder: "I want everything at once." The first thing is a session that
  cannot be lost. A session is a Temporal workflow; the laptop sleeping, the
  worker dying or the gateway restarting changes nothing about where it is.

  Scenario: A session survives its worker being killed
    Given the Temporal dev server and the sovereign worker are running
    When I run "bin/sb start --runner echo --task 'count to 5' --json"
    Then the output has a "session_id"
    When the sovereign worker is killed with SIGKILL
    And the sovereign worker is started again
    And I run "bin/sb show <session_id> --json"
    Then the output "status" is "running" or "done"
    And the output "step" is never lower than it was before the kill

  Scenario: A session id is stable and listable
    When I run "bin/sb list --json"
    Then every row has "session_id", "repo", "task", "step", "status", "runner"
