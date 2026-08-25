@cp6
Feature: propose_action / execute_action carry a state hash, refuse on TOCTOU
  Founder's pasted design: "split propose_action() from execute_action():
  agent proposes, founder approves from the phone. Failure: TOCTOU, the
  cluster changed between proposal and approval. Fix: the proposal carries a
  state hash; execute refuses if the current hash differs and forces
  re-evaluation." This lands on the existing Sovereign Bus propose/approve
  path (crew#213); the state hash goes into the signed receipt it already
  writes.

  Scenario: A proposal carries the state hash it was computed against
    When an agent calls propose_action for a change to workload "app-x"
    Then the proposal includes a hash of app-x's current state
    And that hash is written into the signed receipt for the proposal

  Scenario: Execute succeeds when state has not changed
    Given a proposal was made with state hash H for app-x
    And app-x's state hash is still H at approval time
    When the founder approves via /sb-approve
    Then execute_action runs the change
    And the receipt chain records the same hash H for propose and execute

  Scenario: Execute refuses when state changed between propose and approve — TOCTOU
    Given a proposal was made with state hash H for app-x
    And app-x's state hash changes to H2 before the founder approves
    When the founder approves via /sb-approve
    Then execute_action refuses to run
    And the response states the proposal's hash H and the current hash H2
    And the agent is told to re-propose against the current state

  Scenario: A stale approval never mutates anything
    Given execute_action has refused a stale-hash approval
    Then no write was made to app-x
    And the refusal itself is written to the signed receipt chain
