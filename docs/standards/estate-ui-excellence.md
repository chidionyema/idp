# Estate UI Excellence — a product contract, not a design memo

Every new or changed human-facing surface uses this contract, including customer
websites, Mumchimp, Genesis/Argon, Telegram, and founder operational instruments.
The existing `packages/estate-ui-kit` remains the shared component/token foundation,
not a requirement to make every product look identical.

## The four things the user must never experience again

- **Silent public visual regression:** production aliases cannot be automatically
  overwritten by unrelated commits. A release is an immutable candidate, browser
  proof, explicit promotion and independently verified visitor readback.
- **Beautiful but fake controls:** every interactive action is either navigational,
  a clearly labelled simulation, or a real authenticated operation with server
  acknowledgement and observable effect. A green badge without evidence is a defect.
- **Crowded command surfaces:** founder interfaces have one primary task per view,
  a clear voice/text entry, status of actual evidence, and a small number of reachable
  expert perspectives. Preserve the complete intelligence estate rather than
  replacing it with a decorative mockup.
- **Unreadable mobile UI:** 320/390/768/1440px screenshot checks, keyboard and
  microphone-denied fallback, 44px targets, normal-text 4.5:1 contrast,
  16px mobile form inputs, visible focus and reduced-motion support.

## Distinct products, shared quality

**Company marketing:** articulate value, credentials and commercial routes. Merdian
must consistently present consultancy, laboratory and ventures. Claims and legal
identity must be evidenced; do not invent customer logos, revenue, incorporation
details, a domain or a mailbox. Enquiry success means an actual message accepted by
the configured provider and independently observed at the destination.

**Founder command surfaces:** instrument the estate, not a prototype. Primary
home answers: what is alive, what changed, what needs a decision, where is an
instruction in the durable lifecycle and what operational yield was verified.
One Eye and specialist perspectives use the same underlying event/evidence
data. Event stream connected != all systems healthy. Data includes source,
event/receipt provenance, freshness and disagreement; unsupported is unknown.
A voice transcript does not bypass instruction authority or become an approval.

**Customer products:** complete task flows, honest errors, recoverable progress,
keyboard/touch parity, mobile ergonomics, no secret leakage, success proven at
the actual receiving system.

Brand art direction may be materially different across products. Shared tokens
are mechanical defaults for readability, motion, focus and state. Product
identity is never replaced by a one-size-fits-all template.

## Release acceptance — measured, not narrated

Each change proves: source SHA, business identity contract, negative mutation test,
typecheck and build, actual screenshot grid, real navigation and essential
interactions, no clipped controls or body overflow, inaccessible/empty/loading/error
cases, runtime user-facing domain check and safe rollback. The reviewer must
compare before/after images. A screenshot artifact is evidence, not automatic
pixel similarity approval. Defects found in QA are corrected on the same candidate.

A founder surface also proves: real event freshness, source ownership,
permission and signature checks, backend action response, reconnect/offline
behaviour, voice-denied fallback, and no fixture projected as live.

A public alias stays pinned to the last **approved** deployment while candidate
CI runs. No force promotion from unrelated `main` updates. A monitored drift
incident opens once, supplies the actual URL and observation, and closes only
after an independent live recheck. When provider credentials or incorporation
are incomplete, mark that one capability unavailable and release other safe work.

## Current executable implementation

- Merdian source/negative fixtures: `web/scripts/merdian-public-release-gate.mjs`
  and `web/tests/merdian-release-gate.test.mjs`
- Merdian real Chromium acceptance: `web/scripts/visual-regression.mjs`
- Merdian release/canary CI: `.github/workflows/merdian-public-release.yml`
- Shared component and token guards: `packages/estate-ui-kit/guards/`
- Genesis founder-source and browser contracts live in `chidionyema/argon`,
  with independent review and protected promotion.

The presence of these scripts does not prove they were run, that the design
was visually approved, or that a deployment is live. Exact CI receipts and
post-deployment readback are required for that claim.
