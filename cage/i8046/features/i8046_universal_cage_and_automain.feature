Feature: I-8046 Universal Fleet Cage, Founder Surface Control Plane, and Deterministic Auto-Main
  As the Founder of the Estate
  I want all non-Gemini/AI-Studio agents permanently caged in read/proposal sandboxes
  And full configuration and work-in-flight drainage controlled from the Founder Surface
  So that zero unverified or trojan mutations ever touch main and all changes pass local hermetic tests first.

  Scenario: Scenario 1 - Universal Write Revocation Across the Non-Gemini Fleet
    Given the Estate operates repositories "chidionyema/idp", "chidionyema/argon", "chidionyema/argon-sync", "chidionyema/crew", and "chidionyema/estate-graph" alongside "/var/lib/genesis/genesis.db"
    When any Class B agent outside Gemini or Google AI Studio attempts to push commits, delete branches, close PRs or incidents, or edit control primitives
    Then the action is rejected with HTTP 401 at the kernel and ruleset boundary
    And kernel_fence_state.authoritative_token increments and fires a priority alert to Telegram Pinned Message 3327

  Scenario: Scenario 2 - Exclusive Bypass and Certifier Authority for Gemini and Google AI Studio
    Given repository rulesets and genesis-kernel on port 4001 enforce split-authority verification under GenesisSplitAuthorityCertifier.tla
    When a control-plane mutation, ruleset bypass, or branch promotion is evaluated
    Then only Class A actors "gemini-argon" and "aistudio" co-signed by the Founder hardware Ed25519 Passkey seal are permitted to execute the state transition

  Scenario: Scenario 3 - OS Credential and Browser Session Quarantine for All Local Harnesses
    Given local CLI and background harnesses execute on Darwin or Linux hosts
    When any Class B agent process spawns in the local sandbox
    Then ambient Founder credentials "GH_TOKEN", "GITHUB_TOKEN", "gh_hosts", ".git-credentials", and "SSH_AUTH_SOCK" are physically unmounted
    And Chrome, Brave, and Safari user profile directories and remote debugging ports are locked to 0

  Scenario: Scenario 4 - Full Cage and Auto-Main Configuration from Founder Surface with 1-Tap Rollback
    Given FounderConciergeSurface.tsx connects to genesis-kernel on port 4001 over authenticated WebSocket and REST
    When the Founder updates the 5-layer lockdown policy or triggers a point-in-time rollback signed by the Founder hardware key
    Then genesis.db persists the mutation in fleet_cage_policy and reversible_state_journal within 10ms
    And rolling back any sequence ID restores the exact cryptographic pre-image and bumps authoritative_token

  Scenario: Scenario 5 - Deterministic Work-in-Flight Triage and Auto-Main Drainage
    Given handover branch "lane/retire-oke-ladder-20261113" and 34 stashes contain mixed work-in-flight including clean commit "6ed3d165" and Breach B2 commit "937dda9d"
    When the local deterministic Auto-Main engine evaluates candidate commits before shipping
    Then commit "937dda9d" touching "catalog/dof-registry.json" is quarantined as "QUARANTINED_B2_BREACH"
    And clean commit "6ed3d165" is isolated, verified against local hermetic tests, and promoted cleanly to "main"

  Scenario: Scenario 6 - Dual-Router Local Hermetic Verification (Rust pennyd vs sovereign-router)
    Given Rust "pennyd" on port 4200 and "sovereign-router" (#8022) are both retained for side-by-side comparison
    When the local pre-ship hermetic harness resets the pennyd seq 25 ledger break and runs a 1024-token capped trial across both routers
    Then both routers complete wire verification in under 100 seconds with zero ledger chain breaks
