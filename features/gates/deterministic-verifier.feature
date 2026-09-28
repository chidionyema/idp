Feature: Deterministic Verifier and Zero-Trust Agent Governance
  To eradicate agent hallucinations and probabilistic outages
  As the enterprise governance system
  I want to physically prevent agents from mutating live state without mathematical verification and cryptographic attestation.

  Rule: Direct mutation of the live estate is physically impossible.

    Scenario: The agent attempts to directly write to the active worktree
      Given an agent session is active in the host environment
      When the agent invokes the "write_file" or "bash_exec" tool targeting the live worktree
      Then the executor intercepts the invocation at the system level
      And the operation is forcefully rejected with a fatal error
      And the worktree remains completely unmodified

  Rule: The agent can only propose patches to an ephemeral ledger.

    Scenario: The agent successfully queues a change for verification
      Given the agent is restricted to the "propose_patch" tool
      When the agent submits a code modification via "propose_patch"
      Then the executor isolates the payload into an ephemeral, sterile ledger
      And the live worktree is completely isolated from this payload
      And the agent is suspended pending deterministic verification

  Rule: Proposed patches must pass a three-stage mathematical and deterministic gauntlet.

    Scenario: A proposed patch contains structural, symbolic, or execution flaws
      Given an agent has proposed a patch to the ephemeral ledger
      When the Deterministic Verifier evaluates the patch in a sterile microVM
      And the patch fails either structural compilation, SMT symbolic proof, or execution of supplied tests
      Then the ephemeral ledger is immediately destroyed
      And no cryptographic signature is generated
      And the exact raw stderr of the failure is returned to the agent
      And the agent's claim of completion is mechanically registered as "FAILED"

    Scenario: A proposed patch achieves mathematical and execution correctness
      Given an agent has proposed a patch to the ephemeral ledger
      When the Deterministic Verifier evaluates the patch in a sterile microVM
      And the patch strictly passes structural compilation, SMT symbolic proof, and execution of supplied tests
      Then the Deterministic Verifier generates a cryptographic attestation signature via Sigstore
      And the cryptographically sealed patch is staged for admission
      And the agent is un-suspended with a "VERIFIED" receipt

  Rule: The estate admits no change without the Verifier's cryptographic seal.

    Scenario: An unverified payload attempts to bypass the Verifier and enter the estate
      Given a Kubernetes manifest or Git commit is submitted to the estate
      When the payload lacks the exact cryptographic signature from the Deterministic Verifier
      Then the Kyverno Admission Controller or Git pre-receive hook intercepts the payload
      And the payload is physically rejected with an "UNATTESTED" violation code
      And the estate state remains untouched

    Scenario: A mechanically verified payload enters the estate
      Given a Kubernetes manifest or Git commit is submitted to the estate
      When the payload carries a valid, untampered cryptographic signature from the Deterministic Verifier
      Then the Kyverno Admission Controller or Git pre-receive hook validates the signature
      And the payload is successfully merged and applied to the live estate
