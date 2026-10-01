# @estate/ui-kit — the one front end (crew#694)

One file, `tokens.json`, is the standard. Everything else in this package is built from it or
graded against it. No product in the estate carries a colour, size, space, radius or easing
literal of its own; a front end that does is refused by the guards below.

```
tokens.json                 edit this, nothing else (W3C design-tokens format)
build.mjs                   → dist/tokens.css (CSS variables, light + dark), dist/tailwind.theme.css (Tailwind v4 @theme), dist/tokens.ts
src/styles/base.css         element defaults on the tokens: body, headings, focus ring, reduced motion
src/components/             Button, Card, Text (Eyebrow/Display/Heading/Lede/Prose/Price), StatePill, Field (Label/Input/Field/Checkbox), Nav (SiteNav/SiteFooter/SiteShell), Feed (LedgerFeed), Dialog, Tabs
src/voice/useEstateVoice.ts the voice primitive: press to talk, Web Speech now, Whisper/Kokoro through `engine` later; VoiceButton
src/templates/              Landing, Catalogue, Detail, Checkout, Account, Docs, ErrorPage, Empty — every page in the estate is one of these
gallery/                    every component in every state, every template with sample data, both themes; `npm run gallery:build` → dist-gallery/index.html (one file)
scaffold/                   the Astro app `ui.scaffold` copies: static output for Cloudflare's free tier, one stylesheet that imports the kit
guards/contrast.mjs         every text × surface pair, both themes, WCAG 4.5:1 / 3:1 — exits 1 on failure
guards/purity.mjs DIR…      refuses #hex, rgb(), hsl(), oklch(), px/rem font-size, inline colour styles in .css/.tsx/.astro/… — exits 1 with file:line
guards/kit-import.mjs       refuses a consumer whose stylesheet does not import @estate/ui-kit (consumers.json; legacy rows carry a migrate_by date)
consumers.json              the front ends the kit-import guard grades
```

Components follow the shadcn/ui pattern on pinned Radix primitives (decision-matrix row
`front-end-kit`): the source lives here, is restyled only through the tokens, and is copied into
nothing. A state is always a dot, a word and a tint; colour never carries a meaning alone.
Every control clears the 44px tap minimum; an arrow never wraps away from its label; small text is
never under 4.5:1. Each of those was a measured flaw on mumchimp.com on 2026-09-30.

## Use it

```css
/* the product's only stylesheet */
@import "tailwindcss";
@import "@estate/ui-kit/tailwind.theme.css";
@import "@estate/ui-kit/base.css";
@source "../../node_modules/@estate/ui-kit/src";
```

```tsx
import { SiteShell, SiteNav, SiteFooter, Landing } from '@estate/ui-kit';
```

A new product: `estate-execute ui.scaffold --name <product>` → `apps/<product>` running on the kit.
Grade any front end: `estate-execute ui.review --target <src> --dist <dist>`.

## Develop

```bash
npm ci                # also builds dist/ (prepare)
npm run guard         # build + contrast + purity + kit-import
npm run typecheck
npm run gallery       # live gallery on Vite
npm run gallery:build # one-file gallery → dist-gallery/index.html
```

CI (`.github/workflows/ci.yml` job `ui-kit`, required by `ci-success`) runs the guards, the
type-check and the gallery build with a 600 KB page budget whenever `packages/estate-ui-kit/`,
`apps/` or the portal stylesheet changes.

## Where the values came from

Seeded 2026-09-30 from `backstage/packages/app/src/modules/theme/tokens.ts` (crew#459 "quiet
instrument") and Store.Web Brand v3. Two values were changed because the contrast guard failed on the
originals: `border-strong` light `#d0d5dd` → `#8791a3` (1.47:1 → 3.18:1 on white) and dark `#3b4048` →
`#5f6774` (1.88:1 → 3.43:1); `text-muted` raised in both themes to clear 4.5:1 on `surface-3`.

## Measured

- 2026-09-30, `guards/contrast.mjs`: 48 pairs, 0 fail.
- 2026-09-30, `guards/purity.mjs` on Store.Web `src/`: 215 violations in 136 files; on the portal `modules/home`: 23.
- 2026-10-01, `guards/purity.mjs` on this package (src, gallery, scaffold): 24 files, 0 violations.
- 2026-10-01, gallery: one HTML file, 336 KB (102 KB gzip), under the 600 KB page budget.

## Not here yet

Storybook proper (the gallery is the equivalent CP2 names, published as one file); the first
consumers (crew#700 CP1 mumchimp home and pack page; crew#690 the company site) — `consumers.json`
carries their migration dates and the guard turns from a warning into a refusal on those days.
