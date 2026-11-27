# Context governance: SHADOW integration

Authenticated inference schedules non-blocking observations through the existing BudgetLedgerDO transaction boundary. SHADOW never gates inference, mutates requests, replaces financial controls, changes credentials or overwrites estate instructions.

GET /admin/v1/context uses existing administrator authentication. It exposes bounded aggregate token estimates, violations and last observed source SHA. No raw prompts, credentials or client-provided session/mission tags are persisted. Session keys are hashed with the authenticated key identity and bounded to 128 records. Oversized observations are skipped.

Provider usage coverage and cache hit ratio remain UNKNOWN (null); estimates do not establish provider usage, cache performance or enforcement readiness. The adapter forces SHADOW independently of the reference policy. Identity validation and longitudinal promotion evidence remain required before enforcement.

The context-governance directory preserves the reviewed package. Its standalone compiler is reference source, not a replacement for bin/estate-context-compile. It is not installed as an auto-run hook. See the existing context compiler for source retrieval.

Run npm test for the actual Worker/ledger integration falsifiers, Python reference suite and TypeScript SHADOW regression. Release remains exact-main through the existing workflow; tests and source landing are not runtime receipts.

Original archive sha256: cb13e9f77e046b25eda874c2bbe7cf98a35db5962e11fbc11a43fae4754f58c8
Claim: chidionyema/idp#8492
