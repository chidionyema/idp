Feature: Zero-Repeat Headless Continuation, Superseded-Head Abort, and Durable Founder Inbox
  Enforces five non-advisory invariants across chidionyema/idp and chidionyema/argon:
  1. 1-Strike Failure-Class Circuit Breaker (no PR/lane/workflow class fails twice without immunization)
  2. Headless Worker Auto-Continuation (pushing to Greenlane never terminates to wait for Founder)
  3. Superseded-Head Watcher Abort (stale lane head stops immediately instead of polling pending forever)
  4. Durable Consumer-Ack Founder Inbox & Passkey Sink (no 24h TTL drop, no local Mac PID pollers, no terminal ESCALATE traps)
  5. Pre-Emit Workflow & Legion Admission Preflight (rejects 0-job workflows like incident-loop.yml and invalid legion-run contracts before push/dispatch)

  Scenario: Strike 1 blocks unimmunized retry and Strike 2 freezes the failure class
    Given failure class "bdd-suites::acceptance-render::platform/llm" has 0 prior failures
    When lane "lane/cutover-final" fails with signature "bdd-suites::acceptance-render::platform/llm"
    Then the circuit breaker transitions the class to "IMMUNIZATION_REQUIRED"
    And a blind retry "lane/cutover-final-r2" without an immunization commit is rejected with "ERR_UNIMMUNIZED_RETRY"
    And if the same signature occurs a second time before immunization, the class transitions to "CLASS_QUARANTINE"
    And further dispatches for that class are frozen until an immunization commit adds a local pre-emit check and failing-then-passing regression test

  Scenario: Unbounded bot auto-merge loop is terminated at cap=1
    Given PR "#8207" has 1 prior auto-merge of "main" onto "fix/lane-a-cloud-door" while CI remains red
    When "estate-agents[bot]" attempts a second auto-merge onto the same red branch without a new fix commit
    Then the guard rejects the sync with "ERR_BOT_SYNC_LOOP_QUARANTINED" and halts the branch

  Scenario: Worker pushing to Greenlane auto-continues instead of waiting for Founder
    Given worker "glm-5.3-pennyd" pushes head "cb47fac" on "lane/harness-rust-ci" for issue "#8395"
    And unblocked ticket "#8390" is available in the work queue
    When the worker completes the Greenlane handoff
    Then the handoff record is persisted to the shared state ledger
    And the worker transitions to "PULL_NEXT_TICKET" with mission "#8390"
    And attempting to transition to "IDLE_WAIT_FOR_FOUNDER" fails closed with "ERR_FOUNDER_EVENT_LOOP_FORBIDDEN"

  Scenario: Watcher aborts immediately when lane head is superseded in Greenlane state ref
    Given a watcher is tracking lane "lane/i8387-unlandable" at head "7d8741cc1"
    And GitHub commit status for "7d8741cc1" still answers "pending"
    When Greenlane state ref reports current lane head "7d575dacc"
    Then the watcher aborts immediately with verdict "SUPERSEDED_HEAD" and zero further polls

  Scenario: Founder passkey tap is durable under stable key until committed-file receipt
    Given the Founder completes a WebAuthn passkey registration POST
    When the Worker stores the registration
    Then it writes under stable key "reg:founder" with consumer-ack persistence (never nonce-only 24h TTL)
    And a read using a different nonce still returns the pending registration
    And purge is refused with "ERR_UNCONSUMED_FOUNDER_TAP" until a valid 40-hex git commit SHA receipt is recorded
    And any local Mac poller PID or terminal-only ESCALATE/1 emission is rejected with "ERR_LOCAL_POLLER_OR_TERMINAL_TRAP"

  Scenario: Pre-emit workflow and Legion admission preflight fail closed before cloud dispatch
    Given a workflow YAML file has an empty or unrunnable job map
    When pre-emit preflight inspects the workflow
    Then it rejects the commit with "ERR_ZERO_JOB_WORKFLOW"
    Given a "legion-run" dispatch targets issue "#8302" while an active conflicting claim exists or required contract fields are missing
    When admission preflight evaluates the dispatch
    Then it rejects dispatch locally with "ERR_ADMISSION_PRECONDITION_FAILED" and exact structured reasons
