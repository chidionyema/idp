# Instruction-linked execution evidence

Claim: chidionyema/idp#7480. This extends the existing executor, focus reader and SQLite ledger.
It does not create a second memory service or certify semantic completion.

Authority: a versioned host policy anchors the shared founder directive. Each action supplies
instruction_id, instruction_sha256, claim, agent and session_id through ESTATE_CONTEXT_JSON,
MCP context, or the reserved legacy MCP args._context JSON string. The shared focus reader verifies
the current open issue, latest holder and heartbeat, and records the issue body digest.
Agent/session labels are attribution, not cryptographic authentication of the calling model.

`estate-execute --required-context` discovers the current instruction without re-entry by the founder.
`estate-execute --verify-report <receipt.json>` verifies linkage/integrity against the executor's
issued record; exit 0 means the record matches, exit 1 means it does not. Check outcome separately:
a genuine failure receipt is valid evidence of failure. A changed status, claim, session, digest,
or operational flag fails. The executor writes receipt files in ~/.estate/state/response-receipts/.
CLI command stdout is preserved; the structured receipt is emitted on stderr. The MCP adapter
wraps a verified issued receipt and command output in JSON; that is not certification of output prose.

Activation uses the emergency.enforce intent. Stage requires exact installed source/module hashes,
nonempty passing tests, and a verified live claim. Activate requires the staged manifest digest,
then writes policy state and checks actual unanchored refusal, anchored execution, issued-record
verification, tamper refusal and HOME spoof refusal. Runtime code is delivered by the existing
converger. Activation never edits its managed tree or creates a competing release manager.

Enforcement coverage is the shared executor on this host. Native tools, direct-provider final
messages, remote hosts and adapters that bypass it remain explicit coverage gaps. A process with
permission to rewrite policy/SQLite/code can subvert this boundary; it is not a hostile-host sandbox.
Real service acceptance requires existing trusted operational evidence bound to the proposition,
deployment/config revision, caller, observation and freshness window. These receipts cannot supply it.

Trade-off: each admitted action now depends on a fresh shared-focus read; unknown ownership refuses.
No caller-controlled opt-out is introduced. Policy removal stays refused after first activation.
Durable directive supersession, emergency recovery under a memory outage, and every-harness uptake
must be integrated with the existing governance and Fleet owners before universal coverage is claimed.

Recovery: after activation, a missing/corrupt policy is restored only from the last digest-checked
policy in the existing executor ledger. Unanchored actions still refuse. A missing/unverifiable
recorded anchor refuses; no caller-supplied replacement policy is accepted by recovery.
Existing CLI line-output behavior, including its trailing newline, is retained.
