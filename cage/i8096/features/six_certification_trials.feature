Feature: Seven Demonstrations of Self-Certifying, Quarantine-Isolated, Real-Time & Universally Reversible Genesis Autonomy
  As the Independent Certifier Authority of the Genesis Estate
  I require adversarial proof across history quarantine, sovereignty, failover, real-time reversibility, inherited intelligence, recursive science, and economic yield
  So that every component operates in real time on /var/lib/genesis/genesis.db with guaranteed 1-step rollback to a known-good state.

  Scenario: Demonstration 0 - Hard Quarantine Between Legacy History and Sovereign Genesis
    Given Legacy History artifacts exist in "~/.estate" and "/var/lib/estate/estate.db"
    And Genesis v0.8.0-SOVEREIGN is configured with "GENESIS_DB_PATH=/var/lib/genesis/genesis.db"
    When a process attempts to open "/var/lib/estate/estate.db" inside "CifKernel::open" or "init_real_db"
    Or attempts to probe "127.0.0.1" or "trycloudflare.com" from a Darwin thin client
    Then the runtime rejects the call immediately with "HISTORY_QUARANTINE_VIOLATION" or "DARWIN_THIN_CLIENT_VIOLATION"

  Scenario: Demonstration 1 - Sovereignty Under Attack (#7452)
    Given GitHub Rulesets 1 through 6 are active on "idp", "argon", "argon-sync", and "crew"
    And the "genesis-certifier" holds an isolated Ed25519 key inaccessible to "genesis-improver"
    When an adversarial actor attempts an unsigned POST to ":4001/api/realtime/rollback"
    And attempts step execution with revoked fencing token 41 against authoritative token 45
    Then all attacks are rejected with HTTP 401 and zero state mutation

  Scenario: Demonstration 2 - Survival Under Laptop and Service Failure (#7379 & #7613)
    Given P0 incident "#7613" is open on "idp"
    When the primary MacBook host goes completely offline and primary router slot ":4001" is terminated
    Then the OCI/CI cloud lane acquires lease "#7613" within 15 seconds with monotonic fencing token 46
    And "genesis-certifier" independently verifies the live health probes and closes "#7613" with a signed receipt

  Scenario: Demonstration 3 - Sub-50ms Real-Time Streaming and Sub-10ms Rollback to Known-Good State
    Given Known-Good Checkpoint "KGC-PRE-MUTATION" is sealed in "known_good_checkpoints" on "/var/lib/genesis/genesis.db"
    When an external process writes a faulty instruction or trial row into "/var/lib/genesis/genesis.db"
    Then the mutation streams over "/api/realtime/ws" within 50 milliseconds with a monotonic "seq_id" and 64-char SHA-256 "merkle_root"
    And triggering "/api/realtime/rollback" to "KGC-PRE-MUTATION" executes the inverse SQL journal in under 10 milliseconds
    And "kernel_fence_state.authoritative_token" increments to 46 while returning the database state and UI to the Known-Good Checkpoint

  Scenario: Demonstration 4 - Inherited Intelligence Across Distinct Agents (#7452)
    Given Agent "worker-claude-01" resolves fault class "FC_CREW_REVENUE_SCHEMA_DRIFT"
    And "genesis-certifier" certifies antibody "AB-7452-01" into "catechism_antibodies"
    When fault "FC_CREW_REVENUE_SCHEMA_DRIFT" is injected into clean Agent "worker-pi-02" with zero chat history
    Then "worker-pi-02" matches "AB-7452-01" at Pass 0 with "diagnosis_passes = 0"

  Scenario: Demonstration 5 - Preregistered Recursive Production Improvement (#6603)
    Given experiment "EXP-6603-ROUTER-LATENCY" is preregistered prior to code execution with sample size 50
    When "genesis-improver" submits candidate optimization "propose/exp-6603-fast-hmac"
    And "genesis-certifier" runs 50 held-out production replay trials against baseline
    Then "genesis-certifier" verifies a statistically significant latency reduction with p_value < 0.01

  Scenario: Demonstration 6 - Economic Superiority and Stochastic CVaR Assurance (#7452)
    Given a consequential stochastic routing decision with potential tail cost
    When "evaluate_empirical_economic_cvar" evaluates 1000 empirical trials at alpha = 0.99
    Then the action is permitted only if "cvar_99_gbp <= max_risk_budget_gbp"