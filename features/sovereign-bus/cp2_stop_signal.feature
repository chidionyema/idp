@cp2
Feature: Stop — the founder's 🛑 lands even when nothing is awake to hear it
  Founder: "no more things getting lost." A stop is a Temporal signal on the
  session workflow. It is durable: sent while the worker is down, it is
  applied the moment the worker returns.

  Scenario: Stop while the worker is alive
    Given a running session started with "--runner sleep --task 'sleep 60'"
    When I run "bin/sb stop <session_id> --by founder --reason 'wrong branch'"
    And I run "bin/sb show <session_id> --json" within 5 seconds
    Then the output "status" is "stopped"
    And the output "stopped_by" is "founder"

  Scenario: Stop while the worker is dead
    Given a running session started with "--runner sleep --task 'sleep 60'"
    And the sovereign worker is killed with SIGKILL
    When I run "bin/sb stop <session_id> --by founder --reason 'laptop asleep'"
    And the sovereign worker is started again
    And I run "bin/sb show <session_id> --json" within 10 seconds
    Then the output "status" is "stopped"
