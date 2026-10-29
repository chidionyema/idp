Feature: The department contract refuses the moves a department may not make
  The Media Department advances on its own, inside delegated authority (charter v1, idp#7395).
  Every write it proposes passes one admission function over the department.v1 schemas; a write
  that is not provable is refused with a typed reason, and nothing is admitted twice.

  Background:
    Given the media department contract with a granted worker for every role
    And objective "obj-live-film" is admitted with a cap of 5 USD
    And run "run-film-1" is opened as a new opportunity

  Scenario: A complete record on a legal transition is admitted
    When the governor triages run "run-film-1" from source "idp#7395" at revision "r1"
    Then the write is admitted

  Scenario: A record with no source reference is refused
    When the governor triages run "run-film-1" with an empty source_ref
    Then the write is refused as "missing_source_ref"

  Scenario: Research cannot jump straight to shipping
    Given run "run-film-1" has reached RESEARCHING
    When the delivery worker moves run "run-film-1" to SHIPPING
    Then the write is refused as "illegal_transition"

  Scenario: A proposal cannot approve itself without the authorization door
    Given run "run-film-1" has reached PROPOSED
    When the door writes APPROVED for run "run-film-1" citing door "self-approval"
    Then the write is refused as "missing_authorization"

  Scenario: Spend beyond the objective's cap is refused
    When the governor triages run "run-film-1" spending 6 USD
    Then the write is refused as "budget_overflow"

  Scenario: A record derived from an old revision is refused
    Given source "idp#7395" is now at revision "r2"
    When the governor triages run "run-film-1" from source "idp#7395" at revision "r1"
    Then the write is refused as "stale_provenance"

  Scenario: The same action on the same input is admitted once
    When the governor triages run "run-film-1" from source "idp#7395" at revision "r1"
    And the governor triages run "run-film-1" from source "idp#7395" at revision "r1" again
    Then the second write is refused as "duplicate_idempotency_key"

  Scenario: A writer outside its granted role is refused
    When an ungranted agent triages run "run-film-1"
    Then the write is refused as "unauthorized_write"

  Scenario: An evaluator cannot certify its own prototype
    Given run "run-film-1" has reached PROTOTYPING
    When the prototype's author reviews its own prototype for run "run-film-1"
    Then the write is refused as "self_certification"

  Scenario: Operating needs an independent observation, not a generated assertion
    Given run "run-film-1" has reached VERIFYING
    When the verifier marks run "run-film-1" OPERATING on generated evidence only
    Then the write is refused as "missing_independent_evidence"

  Scenario: The shipped media config grants nobody yet
    Given the media department config as committed
    When any agent triages run "run-film-1"
    Then the write is refused as "unauthorized_write"
