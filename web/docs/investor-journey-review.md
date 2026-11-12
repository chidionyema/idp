# Meridian Investor Journey and Secure Genesis / OTTO View — review contract

Status: implementation candidate for independent Argon security, product and visual review.
Do not infer that the broker, live evidence projections or identity integration are deployed.

## Positioning: Meridian remains a research-led company

Meridian's core is **research, experimentation and commercialisation**.
The workplace of the future is one opportunity emerging from that purpose, not a
replacement for it. Homepage retains consultancy, research and ventures.
Chronos is clearly IN DEVELOPMENT. Never invent adoption, revenue, customer
results, performance gains or live workforce metrics.

## Audience, moment, message and action

| Stage | Visitor | Their question | Experience | Action |
|---|---|---|---|---|
| First visit | Stranger | Who are these people? | Research, experiments, commercial ventures | Browse |
| Customer/partner | Exploring fit | Can they help us? | Services, concepts, contact | Enquire |
| Investor discovery | Evaluating | Why does this matter? | Future-of-work story, Chronos and honest status | Request conversation |
| Invited investor | Named, verified | What has actually been built? | Approved live read-only Genesis and OTTO projections | Inspect and switch views |
| Diligence | Separately approved | Can we verify the claims? | Narrowly disclosed, audited documents | Read permitted evidence |
| Expired/revoked | Unauthorized | What do I do? | Humane access message, no private data | Reverify or contact |

Public marketing must speak to humans: clear priorities, time, trust, decisions,
accountability, and what changes in a working day. Internal reviewers may use jargon.

## Zero-trust access contract

- Founder, staff and workforce credentials (including SPIFFE internal principal)
  are NEVER handed to investors. No direct founder Genesis/OTTO URLs or iframes.
- Existing customer identity ADR 0013 selects Keycloak but is PROPOSED,
  not verified deployed. The dedicated investor broker must independently
  implement named-person OIDC with MFA, broker-side durable grant lookup,
  expiry, revocation and read-only disclosure scope. No second password store.
- The site implements a broker consumer and fail-closed contract, not that
  broker service. Missing broker configuration must deny access.
- Login: same-origin start uses 256-bit state and PKCE S256. Broker verifies
  named investor, MFA, invitation, subject, state, one-time handoff code, code
  verifier and registered redirect. Auth callback introspects the returned
  short-lived opaque session again before setting any cookie.
- Session cookie is __Host-meridian-investor, HttpOnly, Secure, SameSite Lax,
  no Domain, lifetime at most 15 minutes. Identity freshness limit is 30
  minutes. Grant max accepted window is 14 days, shorter by invitation.
- Every API read posts the opaque session and audience to the separately
  authenticated broker endpoint /v1/investor/introspect. It MUST check current
  durable revocation/expiry, named identity, active grant and resource scopes.
  A valid browser cookie does not replace those checks.
- Explicit permissions are investor:genesis:view and investor:otto:view ONLY.
  No model, agent or approval execution permission exists in this consumer.
- Every authorized view is fetched through fixed broker endpoint
  /v1/investor/projection. Broker must revalidate the exact session, grant and
  requested surface at request time. Data must be preapproved, field-redacted,
  free of secrets, PII, confidential customer information and raw telemetry.
- The projection schema requires schema meridian.investor.projection.v1,
  classification INVESTOR_APPROVED, state observed, readOnly true, source SHA,
  a fresh source timestamp, no more than four curated facts or six selected
  observations. Unknown fields are discarded; malformed or stale -> unavailable.
- Broker origin comes only from server configuration; HTTPS and fixed endpoints
  are required. Never forward user-supplied URLs, browser API keys or raw system
  responses. Secrets from mounted estate vault, not public JavaScript.
- Investor routes are noindex and private no-store; CDN/browser must not retain
  session or private data. Revoked/expired response clears the client view.
- The broker/service trust requirements cannot be replaced by Vercel preview
  protection or a countdown timer. Tokens and rights are enforced on the server.

## Required independent Argon falsification

1. No/malformed cookie -> 401, zero private bytes, no network call.
2. Disabled/revoked/expired grant -> denied on NEXT request despite a cookie.
3. Shared invitation, stolen handoff, invalid state, PKCE or redirect -> denied.
4. Unverified identity, absent MFA, wrong issuer/subject/audience/scope -> denied.
5. No broker, network outage, timeout, malformed/stale/fixture data -> explicit
   refusal or unavailable state. No synthetic metrics.
6. Probe HTTP methods, CORS, caching, reflected Host, header spoof, SSRF,
   user-controlled URLs, logging, tokens, secrets, PII and replay.
7. Real staging source readback on both surfaces: approved data, exact source
   revision, observation timestamp, independent verification, no raw access.
8. Revoke access mid-session; confirm next request fails and UI clears.
   Expire a grant mid-view. Verify 15-minute session refresh behavior.
9. Prove the visitor cannot execute OTTO voice/chat commands, approve
   founder decisions, operate agents, or navigate to internal founder pages.
10. Verify first impression on actual mobile/desktop browsers, keyboard,
    WCAG AA contrast and accessible focus. A stranger should understand
    Meridian within ten seconds; a guest should know exactly when access ends.

## Promotion and Argon review

Argon reviews isolation, identity, privacy, security, craftsmanship,
copy, provenance, falsifying tests, operator controls and the end-to-end journey.
No silent merge or claim of private investor readiness before the broker is
implemented and production access/expiry/revocation is genuinely exercised.
Public Meridian, Chronos and investor introduction may be reviewed on their
own merits, but NEVER accidentally expose private sources.
Commercial securities-related messaging must receive legal/compliance review
before investment materials are circulated.
