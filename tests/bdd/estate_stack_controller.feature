Feature: One signed estate stack control loop
  Every instruction becomes a versioned stack intent. The controller measures
  each stage, emits one signed receipt and closes yield only on the real user path.

  Scenario: an unmeasured stage never closes yield
    Given an approved stack intent with a live claim lease
    When one required stage is BLIND
    Then the receipt records BLIND rather than PASS
    And the yield remains OPEN

  Scenario: exactly fourteen measured doors are required
    Given the router and DSH health contracts answer
    When the estate-doors board contains fewer than fourteen MEASURED_OK lanes
    Then the yield remains OPEN
    And the receipt names the measured door count

  Scenario: apply is cloud-only and lease-bound
    Given an apply intent outside GitHub Actions
    When the controller starts
    Then it refuses every mutation
    And the receipt binds intent, claim, fencing token and idempotency key

  Scenario: a replay cannot repeat a mutation
    Given a cloud apply intent using an idempotency key that already ran
    When the controller starts
    Then it refuses the replay before the capability handler
    And the yield remains OPEN

  Scenario: a signed receipt cannot bless a false closed yield
    Given a signer with a valid pinned Ed25519 key
    When the receipt says CLOSED while a required stage or door is not measured
    Then verification rejects the receipt
