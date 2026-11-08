# Estate Law — Session yield is earned at commit, not asserted

**Authority:** founder directive, 8 November 2026. **Layer:** estate engineering law; must not override independent security, protected recovery, or the founder's own authorization law. **Adoption:** proposed until the hook, existing agents and CI are exercised together. Do not turn on a mandatory rule that has no self-remediation lane.

## The exact distinction

* **Commit yield** is a measurable contribution that survived the current session: an actual source correction, newly verified failure class, quantified friction, reproducible diagnosis, optimization, or durable intelligence that another agent can retrieve. A Git commit is transport, not proof of operational success.
* **Operational yield** is a separately witnessed change in the real caller's ability to achieve its goal. Source receipts, tests, PRs, GitHub job success, documentation and an agent's own claim are *never* operational proof.
* **Friction yield** is an observed failure pattern with stable lookup key and repair route; claim RESOLVED only with numeric before/after or independent operating acceptance. Identified-but-unresolved friction is legitimate intelligence and must remain open.
* **Intelligence yield** is knowledge that reduces a future agent's search/debugging cost: precise symptom, falsifiable cause, discriminator, known correction, exact test and next action. It is reusable only when indexed by stable failure key and accessible across sessions.
* **Unverified vs unknown:** an unverified operational claim remains PENDING. Absent proof is never interpreted as no friction.

## Commit receipt protocol

Before every non-merge source commit, stage the actual changes and run **one command**:

\`\`\`sh
python3 bin/idp-yield-gate record \
  --session <unique-session-run-id> --kind bug-fix \
  --summary "The substantive change and why it matters" \
  --lookup-key <stable-failure-class> \
  --finding "What was learned from concrete evidence" \
  --next-action "The exact test, recovery door or independent acceptance step"
\`\`\`

The command hashes the exact staged Git patch, identifies staged files, records their staged blob hashes, and creates a **new** .yield/session.json. It never guesses a successful runtime effect. Add exactly one \`Yield-Receipt: .yield/<session>.json\` commit trailer. The commit-msg hook checks the staged receipt and refuses absent, replayed, ambiguous, stale, unstaged or fabricated runtime declarations. A commit that has no real staged change has no commit yield.

The receipt's \`intelligence.lookupKey\`, \`finding\` and \`nextAction\` are the session-to-session retrieval seam. The existing memory/graph/agent briefing and friction ledger should ingest this *same* receipt; do not build a second learning store. The source receipt is not itself a memory-server ACK. When memory is down, keep the receipt durable and replay until acknowledged with a readback.

## Mandatory preflight for every critical component

List known failure classes, their symptoms, discriminators, exact probe, affected permissions/dependencies, authorized recovery workflow, idempotency, deadlines, alternative executor and independent effect proof **before** admitting protected effects. Tooling and Legion must pass this standard first, including loss of the recovery worker and capacity 429 from both primary and fallback. Unmodelled symptoms quarantine privileged effects and trigger bounded classification, never indefinite inactivity. A recovery route must exist and work before its corresponding new block is mandatory.

## Observability and incentives

Score separately: source-evidenced changes, independently witnessed runtime effects, verified bugs prevented, friction minutes removed, newly classified faults, future lookup/reuse hits, and false-green/duplicate/rollback rates. Never sum these into a single inflated 'done' count. Feed gaps and high-value known failure classes back into the existing prioritization/agent training loop. Founder sees actual status, exact commit, owner, evidence maturity, next action and expiry.

**Deployment guard:** the existing commit hooks are proposed to become mandatory, but only after compatible agent-sandbox writes receipts, CLI tests and production-like CI tests prove there is an authorized fast repair path. Protected governance remains subject to independent peer and patch-bound founder approval. No emergency lane may synthesize an approval signature.

**Quantified friction claims:** the source receipt accepts finite, nonnegative measured before/after values with a strict reduction only. Non-finite, baseline-zero, worsening or negative claims cannot be marked RESOLVED. A self-reported number is still SOURCE-EVIDENCED; operational friction removal requires a separately witnessed runtime effect and retained measurement methodology.
