# OMNIFLOW GitHub Survival Collaboration — operational fallback contract v1

**Purpose:** provide a shared, near-real-time, durable, vendor-neutral collaboration path TODAY, even when NATS, OCI, Otto, OpenCode or the new OMNIFLOW service is down. This is a transport adapter for existing IDP #7481, not a second authority. Existing Argon #40 Git peer board is a candidate: audit its merged/deployed state first; its former PR #39 was closed unmerged, so do not assert it works. Read AGENTS.md and the canonical master.

## Transport hierarchy and actual availability

1. Live: existing authenticated NATS JetStream / trusted gateway when independently healthy.
2. GitHub fallback: GitHub Issues + comments for work and conversation, Actions repository_dispatch/workflow_dispatch for admitted work triggers, Git branch commits for versioned patches, GitHub API ETag/conditional polling or GitHub App webhook for low-latency notification. GitHub is NOT a command-signing authority or proof of execution.
3. Optional independent contingency: authenticated cloud-to-cloud or email transport *only if already deployed and verified*; do not create a second unowned broker.

All lanes exchange the same v1 immutable envelope: protocol version, logical event ID, mission/activity/correlation/causation IDs, actor principal verified by gateway (not author/login text), artifact digest/ref, expiry, idempotency key, source cursor, authority epoch, access class, type and explicit receipt level. GitHub issue comment ID or commit SHA is a TRANSPORT CURSOR, never a founder approval or an independently verified effect.

## Immediate operational model

- ONE canonical issue per mission (existing issue if present), no new duplicate tracker. Parent #7481 owns this fallback capability. Use an existing issue label/topic/structured machine-readable comment prefix (e.g. `OMNIFLOW-EVENT/v1`) for typed events. Never put private screenshots, tokens, customer data, secret-bearing logs, personal records or unredacted binary blobs into public GitHub issues; store only digest and opaque authorized references. No Git LFS as default for sensitive bytes.
- Agent A/B/C use authenticated GitHub App or existing authorized identity to append small bounded event comments; maintain their own independent cursor. An agent with GitHub access can participate even if local OpenCode session disappears. Respect GitHub secondary rate limits, backoff, Retry-After, ETag and API permissions.
- Prefer authenticated GitHub webhooks with signature verification for immediate wakeup. If webhook receiver unavailable, conditional poll every 5–15s while active, then exponential backoff with jitter (max 60–120s); make interval configurable and prove rate-budget. No guaranteed 1s delivery claim. On reconnect, scan from last committed cursor, dedupe, verify expiry, preserve ordering per mission and reconcile with canonical FLOW ledger before acting.
- No executable effect based only on comment body, Git author, commit trailers, self-declared `agent` or webhook payload. Gate commands through existing trusted instruction admission with principal/tenant/policy/lease. If authority unavailable, queue intent as PROPOSED/WAITING_AUTHORITY and permit read-only coordination; do not bypass protected execution gates. Never mark applied on mere read.
- Claim path and ticket are existing AGENTS.md source of truth. Comments can carry `CLAIM`, `OFFER`, `ASK`, `ANSWER`, `PATCH_REF`, `EVIDENCE_REF`, `BLOCKED`, `RECOVERY`, `RELEASE_VERDICT` event types, each referencing exact SHA/issue/session and evidence source. Use existing GitHub API permissions and claims; no bot token pasted into chat.
- Track receipt tiers independently: GITHUB_ACCEPTED, ADAPTER_OBSERVED, GATEWAY_ADMITTED, WORKER_ACCEPTED, RESULT_RECORDED, INDEPENDENT_EFFECT_VERIFIED, FLOW_YIELD_RECORDED. Github 201/200 means only GitHub accepted a record.
- Deterministic reconciliation: logical event ID + tenant + digest; one authoritative mission instruction ID; compare GitHub cursor and NATS cursor, replay missing, reject conflicting duplicate, no duplicate protected effects; explicit partition and conflict state.
- GitHub outage: preserve local durable outbox and replay after service recovery; where available switch to NATS, otherwise explicit DEGRADED/UNAVAILABLE. Never claim universal availability or guaranteed exactly-once transport.

## Three OpenCode session deployment

A (foundation): implement GitHub transport adapter in existing #7481 messaging architecture; authenticated webhook/polling, dedupe, identity binding, two-way reply, cursor replay and reconciliation. Avoid new scheduler or ledger. B (experience): show mission discussion, progress, cross-agent references and freshness in existing Genesis/Otto views, with GitHub fallback indicated. C (adversary): independent 2-agent/2-host and 2-tenant tests, forged author/comment, duplicate webhook, out-of-order/expired event, rate limit 403/429, GitHub downtime, lost cursor, NATS outage, return to live, stale lease, prompt injection, revoked GitHub token, secret leakage, conflicting patch, 10k-event replay, recovery. Test must prove duplicate effects absent, event retention/reconciliation correct, and stale evidence not shown as current.

## First fallback canary — required actual proof

With NATS deliberately disconnected, A posts a structured authenticated request on an existing issue; B sees it on a different host/provider using GitHub alone, responds with correlated message and exact artifact digest; C independently verifies two-way delivery and receipts; authorized mission admission remains gated. Restore NATS and reconcile without duplicate mission or effects. Repeat with actor impersonation and GitHub 429, both rejected/queued safely. Measure median/p95/p99 event visibility, poll/API cost, recovery time and GitHub API quota. Log exact issue/comment URLs, source SHAs, credentials scopes (names only), independent runner evidence and live user experience. Only after real canary mark fallback OPERATING.

## Anti-duplication

Check Argon #40, IDP #7481, #7490, #7794 and existing Git peer board before writing code. If the existing board is sound, extend it; if superseded, retire its obsolete adapter in same change. Keep one canonical message identity, one mission ledger, one source of truth. Preserve GitHub fallback permanently as independently exercised resilience capability; drill it regularly, not only during incidents.

**Current stage: SPECIFIED, NOT VERIFIED OPERATIONAL.** This file is an actionable instruction for the three console workers; its presence in GitHub is not proof the fallback is deployed.
