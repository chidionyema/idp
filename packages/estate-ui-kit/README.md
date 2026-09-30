# @estate/ui-kit — the one design source (crew#694)

One file, `tokens.json`, is the standard. `node build.mjs` turns it into the three things a front
end imports; nothing else in the estate may carry a colour, size, space, radius or easing literal.

```
tokens.json            ← edit this, nothing else
build.mjs              → dist/tokens.css (CSS variables, light + dark), dist/tailwind.theme.css (Tailwind v4 @theme), dist/tokens.ts
guards/contrast.mjs    every text × surface pair, both themes, WCAG 4.5:1 / 3:1 — exits 1 on failure
guards/purity.mjs DIR  refuses #hex, rgb(), hsl(), px font-size, inline colour styles in .css/.tsx/.astro/… — exits 1 with file:line
ui.review.yaml         the intent that runs all of it; a front end that fails it is refused
```

## Use it

```css
/* Astro / plain */   @import "@estate/ui-kit/tokens.css";
/* Tailwind v4 */     @import "tailwindcss"; @import "@estate/ui-kit/tailwind.theme.css";
/* React island */    import { color, type, space } from "@estate/ui-kit/tokens";
```

Then `color: var(--color-text-2)`, `font-size: var(--type-lg)`, `gap: var(--space-4)`. State is always a
dot + a word + a tint (`--color-state-good-ink` / `-bg`); colour never carries a meaning alone.

## Where the values came from

Seeded 2026-09-30 from `backstage/packages/app/src/modules/theme/tokens.ts` (crew#459 "quiet
instrument") and Store.Web Brand v3. Two values were changed because the contrast guard failed on the
originals: `border-strong` light `#d0d5dd` → `#8791a3` (1.47:1 → 3.18:1 on white) and dark `#3b4048` →
`#5f6774` (1.88:1 → 3.43:1); `text-muted` raised in both themes to clear 4.5:1 on `surface-3`.

## Measured on 2026-09-30

- `guards/contrast.mjs`: 48 pairs, 0 fail (after the two fixes above; 2 failed before them).
- `guards/purity.mjs` on Store.Web `src/`: **215 violations** in 136 files (41 colour literals, 174 off-scale sizes).
- `guards/purity.mjs` on the portal `modules/home`: **23 violations** (17 colour literals, 6 inline styles).
- `guards/purity.mjs` on bytesync-web `src/`: see that project's REPORT.md.

## What is deliberately not here yet

Components (shadcn/ui + Radix, restyled through these variables), the seven page templates, Storybook,
`ui.scaffold`. They come after crew#694 CP1 (the founder's word on the component library). The tokens
and guards come first because they are what every later piece is graded against.

## Landing

Lands in `idp/packages/estate-ui-kit/`; `ui.review.yaml` lands in `~/.estate/intents/` via idp. Under the
crew#987 freeze this directory is handed to the merge queue as a diff, not pushed.
