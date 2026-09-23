Feature: The typed multi-domain mutation ledger
  To close the gap where code, a manifest and a SQL migration for one logical change
  are proposed as three unrelated calls with three unrelated verdicts,
  As the enterprise governance system,
  I want one ledger spanning all three domains that rises or falls together, and admits
  only to a new Git branch for the founder's own merge -- never live.

  Rule: A proposal with nothing in it is refused before a ledger opens.

    Scenario: The agent calls propose_mutation with every domain empty
      Given the agent is restricted to the "propose_mutation" tool
      When the agent proposes an empty mutation
      Then the proposal is refused with the error "nothing to propose"
      And no ledger is opened

  Rule: A proposal spans every domain supplied, in one ledger.

    Scenario: The agent proposes code, a manifest and a SQL migration together
      Given the agent is restricted to the "propose_mutation" tool
      When the agent proposes a mutation touching "code, manifest, sql"
      Then the executor isolates the payload into one ledger spanning all three domains
      And the agent is suspended pending deterministic verification

  Rule: Verification is all-or-nothing across the bundle.

    Scenario: Every domain in the bundle passes
      Given an agent has proposed a mutation touching "code, manifest, sql"
      When the Deterministic Verifier evaluates the whole bundle
      Then every domain is reported "VERIFIED"
      And the bundle is admissible

    Scenario: The SQL domain fails while code and the manifest are sound
      Given an agent has proposed a mutation with a broken "sql" domain
      When the Deterministic Verifier evaluates the whole bundle
      Then the bundle is not admissible
      And the "sql" domain carries the real stage error, not a paraphrase
      And the "code" and "manifest" domains are marked not verified for the same reason

  Rule: A bundle cannot be sealed without first passing verify_mutation.

    Scenario: The agent calls seal_mutation before verify_mutation ever passed
      Given an agent has proposed a mutation touching "code, manifest, sql" but has not verified it
      When the agent calls seal_mutation
      Then the seal is refused because no verified bundle exists for that ledger

  Rule: The estate admits no mutation bundle without the Verifier's seal, and never merges.

    Scenario: An unattested bundle attempts to be admitted
      Given a verified and sealed mutation bundle exists
      When admit_mutation is called with no attestation
      Then the admission is intercepted with violation code "UNATTESTED"

    Scenario: A validly attested bundle is admitted to a new branch, never main
      Given a verified and sealed mutation bundle exists
      When admit_mutation is called with the valid attestation
      Then the bundle is admitted to a new branch named after the ledger
      And the branch is never "main"
      And pr_required is true
      And the admission reports its delivery outcome

  Rule: A mutation carries a pre-validated inverse or it is refused (ADR 0024).
    Scenario: A proposal arrives with no reversibility envelope
      Given an agent has proposed a mutation touching "code, manifest, sql" with no envelope
      When the Deterministic Verifier evaluates the whole bundle
      Then the bundle is refused with violation code "NO_INVERSE"
      And the refusal names the missing envelope, not a paraphrase

    Scenario: A proposal carries an inverse that merely echoes the forward action
      Given an agent has proposed a mutation whose envelope answers the forward with itself
      When the Deterministic Verifier evaluates the whole bundle
      Then the bundle is refused with violation code "NO_INVERSE"
      And the refusal names an inverse that reverses nothing

    Scenario: A proposal claims an irreversible exemption with a forged token
      Given an agent has proposed a destructive mutation claiming an exemption it did not sign
      When the Deterministic Verifier evaluates the whole bundle
      Then the bundle is refused with violation code "NO_INVERSE"
      And the refusal is a signature verdict, not a prefix match

    Scenario: A proposal carries a deterministic inverse with a state probe
      Given an agent has proposed a reversible mutation with a deterministic inverse
      When the Deterministic Verifier evaluates the whole bundle
      Then the inverse is accepted and the bundle is graded on its own merits

  Rule: A declared probe is executed against the real machine, not read as a string.

    Scenario: The inverse's probe is run against state the forward created
      Given a forward mutation has created a file on the real filesystem
      When the rollback path performs the inverse
      Then verify_inverse runs the declared probe and reports the machine's exit code
      And the probe holds only after the inverse has run
