# Agent Prison / One History — executable falsification record

**Date:** 2026-11-10. **Scope:** IDP. **Status:** bounded model executed locally; production gates NOT proved. This is not an implementation or deployment claim.

## Research hypotheses under test

The two founder-supplied research papers propose one signed, causally referenced history supplying four projections (sync, audit, activity, observability), while agent tools and emitted factual claims are checked against evidence and protected authority. The protected **Finality Sink** must mediate effects; session failure must preserve evidence and permit bounded recovery rather than destroy context.

These are *hypotheses about a future operating system*, not guarantees that follow from adding SHA-256 to a JSONL file.

### Necessary distinctions

1. **Integrity is not convergence.** Signatures and hash links prove record provenance under a trusted-key assumption. Convergence additionally requires a deterministic, domain-valid reducer for concurrent events. The model supplies an arrival-order counterexample.
2. **Audit is not finality.** An event reporting that a tool executed is not enforcement. A Candidate Act is non-effective until a separate authority validates the exact operation, policy epoch, capability, signer, and freshness immediately before releasing the effect.
3. **A receipt hash is not semantic truth.** Verification distinguishes PROVEN, INSUFFICIENT_EVIDENCE, and FALSE, and requires an independently trusted observation tied to the exact operation and result. A bad oracle can still sign a false statement.
4. **Historical validity is not current authority.** Revocation is appended, never used to erase earlier effects. A protected sink must serialize revocation versus effect finality; offline CRDT convergence does not confer immediate global revocation.
5. **Safety is not liveness.** Finite invariants cannot prove recovery progress, availability, or termination under arbitrary partition. Model fairness/recovery separately; preserve the instruction and evidence after quarantine.

### Model run

Command: node architecture/research/agent-prison/model-check.mjs

The standalone model explores 4,096 possible subsets of 12 abstract events: 172 causally closed subsets, 100 admissible subsets and 1,168 causally valid three-replica partition/reconciliation cases. It asserts counterexamples for arrival-order divergence, no authorization, stale authority, approval substitution, unsupported/false claims, and a completed state without termination. The bounded model contains a *hypothetical* trusted policy sequencer, not an existing production signer. It is an executable specification and test corpus, **not** a cryptographic proof or an end-to-end production conformance test.

### Current IDP source evidence (read from GitHub, 2026-11-10)

| Boundary | Current behavior | Required property | Executable falsifier |
|---|---|---|---|
| platform/llm/action_ledger.py | The signature covers request fields, not result_hash; the append parent is computed without a multiwriter transaction; record failure is caught and the call continues | Signed outcome and predecessor, durable before acknowledgement; independently verifiable without private key | tests/test_agent_prison_falsification.py includes strict xfail for last-record outcome mutation and missing signer |
| platform/executor/daemon.py | Handler._execute accepts a command via the socket and starts it after local guards, without a signed Candidate Act/AuthorizationDecision witness check in this path | No effect before protected verification of the exact candidate and policy epoch | Needs a controlled process-boundary adversarial test, not a unit mock |
| bin/reasoning_gateway_hook.py | Stop-hook checks retrospective transcript evidence and intentionally permits a second response when stop_hook_active=true | No unverified factual claim may reach the founder output channel | Needs a harness-level interception test: Stop hook is not an output Finality Sink |
| platform/estate/governance/ledger.py | Violation rows and mutable session state operate separately from router call records and executor receipts | One authoritative operation identity and chain of causal receipts, with distinct projections | Needs a cross-system trace and process-kill/restart test |

**Important:** A strict xfail is a *recorded missing guarantee*, not a green security verdict. When the production boundary is implemented, change the tests to require the protected outcome. The positive control must still detect request-signature tampering.

## Production admission criteria

A candidate implementation is not delivered until the protected signer and Finality Sink run with process/credential separation, independent verifier challenges real tamper/replay/kill/partition paths, authorized effects are exactly-once or idempotently deduplicated, unverified factual claims are withheld before emission, the same session resumes with its complete evidence, and **Optimus plus Founder Surface** show linked operation_id / permission / attempted effect / verified yield / denial / stagnation metrics. Validate on staging, then exercise the operational path; a passing code test or branch commit is not yield.

**No parallel ledger deployment authorized by this research branch.** Preserve the estate's canonical instruction-to-yield protocol and identify a single authoritative write path before replacing existing projections.
