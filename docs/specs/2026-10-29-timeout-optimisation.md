# Timeout optimisation obligations

Authority: founder instructions in the recovery session, 2026-10-29. Claim: chidionyema/idp#7457.
The founder operates Fleet, Face and the founder surfaces, not the MacBook.

## Context and measured baseline

The real discovery intent INTENT-20261029-154450-da57b173 returned executor status ok
(exit 0), while printing: "GRAPH unavailable -- growmos query failed:
... timed out after 30s". This is a false success for a required source.
The standalone installed graph caller completed in 24.567 seconds in
INTENT-20261029-154302-01ea642a, but the real concurrent discovery caller still timed out.
A successful retry therefore cannot be treated as optimisation proof.

The graph query previously saved its entire loaded store after reading. The query repair
removes that write, with a regression asserting unchanged graph bytes and mtimes.
Bulk JSONL parsing preserves blank-line, malformed-line and Unicode behavior. It adds
temporary allocation for the input text and joined array; peak memory under concurrent
load still requires verification. Wall time varies with host contention: a profiled run
spent 35.221 wall seconds and 1.450 CPU seconds. Do not infer a controlled speedup from
separate runs on this host.

## One incident and one authority

Extend the existing incident ledger, priority policy and executor. Do not create another
incident database, scheduler, router, memory store or approval system. The incident-loop
files are currently held by pi-incident-loop on #7379; coordinate there before changing them.

Any exceeded deadline, including an inner subprocess deadline, must:
1. Retain partial diagnostics, return a non-success/UNKNOWN result to the caller, and
   preserve partial search hits without asserting that the missing source is empty.
2. Upsert an optimisation-required incident keyed by the capability and operation.
   Record the deadline, observed duration, intent ticket and attempt sequence; no secrets
   or raw credential-bearing commands in the identity or event.
3. Stream its state through the existing outbox and JetStream path to Fleet and Face.
4. Keep the obligation across retries, process restarts, issue closure and quiet windows.
   Neither generic incident auto-closure nor a later green run discharges it.

Scope the completion/landing refusal to the affected capability. Diagnostic and repair
intents must remain usable. A global refusal of all tools would prevent the repair itself.
Hook recursion protection must not certify an unresolved capability as complete.

## Exactly two discharge mechanisms

Optimisation proof: a changed deployed artifact, the measured baseline, deterministic
regression coverage and repeat real-caller measurements within the caller's deadline.
Evidence must identify the artifact and the actual caller. A test, an HTTP 200, an unrelated
green CI run, or an agent's prose does not establish operation.

Founder waiver: an explicitly authenticated founder decision on Fleet, Face or another
founder surface. Reuse the estate's existing approval verification and replay protection.
Bind it to this incident and its latest failure sequence, stated reason and scope.
Agents cannot manufacture the approval by calling the local decision answer command,
setting a founder name, closing an issue, or editing a result. Expiry or silence is not yes.
A Mac Touch ID prompt or desktop login dialog is not a usable founder decision route.

## Refusal tests and operating proof

Negative checks must cover swallowed inner timeouts, lost partial diagnostics, quiet-time
closure, issue closure, a successful retry without a changed artifact, cross-incident and
replayed waivers, unsigned answers, and session-stop recursion bypass.

Operating proof requires a real timed-out operation creating one incident and its live
Fleet/Face event, a subsequent completion attempt being refused, and either verified
optimisation or a valid founder-surface waiver clearing precisely that obligation.
Until this chain is observed, the estate-wide requirement remains incomplete.

## Recovery status

Four targeted discovery/executor regression checks passed in
INTENT-20261029-155033-1f1edfa2. Those changes are in the isolated repair checkout and
are not yet operating. The installed graph read repair is not sufficient under the real
discovery load. Desktop's vault command was changed to avoid login-shell startup; the
reconnecting session also has certificate/network failures, so Desktop recovery is not
certified. The previous memory/identity/congruence objective has not yet been certified
complete. No ticket should be closed from this document.

## Exact recovered objective

The prior founder history identifies agent DNA (not a separate dual-congruence component),
unified and active memory, active focus, routing and Quad evidence as one operational
foundation. Original history session: 01a17a10-80d6-7061-882a-7c5ef61b6d11. The handoff
left automatic Codex memory injection, active-focus supervision, DNA delivery and end-to-end
routing unproven. Treat that history as a recovery pointer, not current operational evidence.

The runtime synchroniser previously wrote the existing alert inbox and then made an
osascript notification call whose ten-second timeout escaped and crashed convergence.
The repair retains that inbox write and removes the desktop dependency. Inbox persistence
alone does not prove delivery to Fleet or Face. That delivery remains an acceptance gate.
