# Commercial public UI release standard — agent-executable
Status: REQUIRED for public/customer-facing surfaces. Established 2026-11-11 from an independently observed Merdian credibility incident.
Scope: every estate agent that builds, reviews, tests, or releases commercial web UI. Internal research surfaces continue their rapid experiment loop; this standard applies when work is actually visitor-facing.

## The failure pattern
A release can be technically READY while publicly self-discrediting. In the 2026-11-11 Merdian readback, an unsubstantiated portfolio placeholder, ambiguous arrow semantics, overlapping mobile orbit labels, low-contrast eyebrows, crushed display word spacing, generic copy, and inconsistent hierarchy were compatible with the existing technical release contract. The previous release canary checked the approved hero/design signature, not the experience, content, and semantics. Existing browser regression code was not run by the release workflow.

## Truth and provenance before cosmetic correction
- Canonical corporate identity must come from the founder-approved brand authority, not domain spelling, spellcheck, or an external critique. As of the 2026-11-09 approved recovery, the brand was **Merdian Intelligence**; `meridian-intelligence-uk.vercel.app` was an alias, not naming authority. Any later rebrand requires an explicit authoritative update to the single identity record, visible UI, metadata, and tests together.
- Categorise external QA claims as VERIFIED (reproduced on live/rendered UI), DISPUTED (conflicts with brand or product authority), or UNVERIFIED (requires measured contrast/layout/reputation). Never silently transform a disputed assertion into a production change.
- Do not invent product maturity, benchmark values, customer adoption, partner names, compliance certifications, deployed systems, contact channels, or commercial claims. Prefer omission over "coming soon" theatre.

## Release acceptance contract (falsifiable)
1. **Institutional credibility:** No placeholder venture cards, lorem ipsum, "details to follow", fictitious case studies, unsupported performance statistics, or promises presented as proof. Each public capability claim must have an identifiable deliverable, dated evidence/source, or explicit research/experimental qualification. Public research != production certification.
2. **Semantic hierarchy:** Top-level public sections use a continuous sequence; child cards use parent indices (e.g. 02.1, 02.2). Decorative system IDs must not masquerade as hierarchy.
3. **Navigation honesty:** `→` for same-site route navigation, `↓` for section scroll, `↗` only for genuine external navigation. Noninteractive rows must not imply clickability. Links, buttons, keyboard focus, and touch targets have visible states.
4. **Typography:** Test whole-word boundaries in uppercase display type. Do not use extremely negative tracking without visible word spacing. Outlined text must be visually separated from filled text at 320/360/390px, tablet, and wide desktop.
5. **Geometry:** No body horizontal overflow, clipped captions, graphic-label collisions, overlapping buttons, or nonresponsive grid imbalance. Labels inside responsive diagrams must be tested against geometry at narrow sizes, not only bounding-box clipping.
6. **Accessibility:** WCAG 2.2 AA for relevant text contrast (4.5:1 normal, 3:1 large), non-text controls, focus, reduced motion, semantics and keyboard operation. Compute resolved foreground and background colours in the rendered browser. A nice palette does not waive contrast obligations.
7. **Conversion:** Primary CTA must lead to an operational commercial journey. Read-only probe contact readiness; do not send personal information in a canary. Claims about service capabilities should lead to specific engineering outputs rather than only abstract verbs.
8. **Evidence:** Candidate checks include typecheck, deterministic source contract and negative tests, production build, Chrome render at 320/390/768/1440px, route interaction, screenshot artifacts, and live readback on all public aliases. The final production origin must be inspected independently after promotion.

## Corrective **and compensating** action
For each public escape, the responsible agent must **contain** the exposure, fix the direct defect, **sweep sibling pages and aliases**, encode a negative/falsification regression test, apply the equivalent rule to estate-wide surface guidance, re-run rendered QA, independently verify the live customer view, record exact Git SHA/deployment identifier, and notify the incident owner with open/closed criteria. A fix without a prevention mechanism and observed live outcome is not complete. A passing test against the wrong source tree is not evidence of customer recovery.

Prioritisation: P0 for public brand/identity confusion, false claims, inert conversion routes, and institutional placeholders; P1 for WCAG, mobile collision, misleading affordances, and editorial hierarchy; P2 for optional polish. Essential security and authorisation controls remain in force, but there is no blanket ceremony for internal lab experiments.

## Required evidence envelope
```text
surface + origin | candidate SHA | public deployment ID | source/brand authority
defect class | customer impact | reproduction viewport/route | verified screenshot or readback
direct fix | sibling sweep | negative regression test | CI run | contrast/geometry result
release/promotion state | independent live evidence | remaining caveats | incident owner
```

Do not claim VERIFIED_YIELD from a PR, READY build, screenshot existence, or source-only assertion. The visitor-facing origin and relevant customer journey must be demonstrably correct.
