# Founder surface redesign — spec (2026-10-24)

**One house style, five surfaces, one published channel.** Every founder surface (Fleet, Face,
the Backstage portal, Meridian, mumchimp) takes the estate kit's tokens, guards, templates and
voice primitive through the kit's published npm dependency, and each one proves it with the
kit's own guards rather than with a screenshot.

Companion review: `docs/reviews/2026-10-24-founder-surface-review.md`.

---

## 1. The shape

```
packages/estate-ui-kit/          the one design system (tokens.json, brands/, guards/, templates/, src/voice/)
        │  subtree split, force-pushed on every main   (.github/workflows/ui-kit-publish.yml)
        ▼
   the public branch `ui-kit` of chidionyema/idp
        │  "npm install github:chidionyema/idp#ui-kit"     (prepare builds dist/ on install)
        ▼
   node_modules/@estate/ui-kit/dist/tokens.css   (+ dist/brands/<brand>.css, dist/tokens.ts)
        │
        │  @import "@estate/ui-kit/tokens.css";   in the surface's own stylesheet
        ▼
   the surface's CSS uses var(--color-*), var(--type-*), var(--space-*) — never a literal
        │
        │  node node_modules/@estate/ui-kit/guards/purity.mjs <the surface's paths>
        ▼
   0 violations
```

**There is no second distribution channel.** The kit is already published as a public git branch
and installs with no token; this spec uses it. Measured on this laptop, 2026-10-24:

```
npm install github:chidionyema/idp#ui-kit                     → dist/tokens.css present
yarn@4.13.0 add @estate/ui-kit@github:chidionyema/idp#ui-kit  → dist/tokens.css present
```

**No new token layer.** A surface never redefines a colour, a type step, a space step or a
radius. A surface that wants its own colours gets a **brand** in
`packages/estate-ui-kit/brands/<name>.json` — colours only; type, space, radius and motion stay
the kit's — and imports that brand's CSS after the tokens.

## 2. The mechanism (one channel, one ratchet)

### 2.1 Take the dependency

| Consumer | Command | Import |
|---|---|---|
| Backstage app (portal, Fleet, Face) | `yarn workspace app add "@estate/ui-kit@github:chidionyema/idp#ui-kit"` | `@import "@estate/ui-kit/tokens.css";` in `src/styles.css` |
| Meridian (`web/`) | `npm install github:chidionyema/idp#ui-kit` | `@import "@estate/ui-kit/tokens.css";` in `app/globals.css` |
| mumchimp (`Store.Web`) | `npm install github:chidionyema/idp#ui-kit` | `@import "@estate/ui-kit/tokens.css";` in `src/styles/tokens.css` |

A consumer with a brand imports it after the tokens:
`@import "@estate/ui-kit/brands/mumchimp.css";` (and `brands/meridian.css` for Meridian).

### 2.2 The guards the surfaces now answer to

The kit's guards ship inside the published package, so every consumer runs the *same* guard, from
`node_modules`:

```
node node_modules/@estate/ui-kit/guards/purity.mjs <the surface's paths>
```

* `purity.mjs` refuses colour literals (`#hex`, `rgb()`, `hsl()`, `oklch()`), `font-size` with a
  `px/rem/em/pt` literal instead of `var(--type-*)`, and inline `style=` carrying a colour or a
  font-size. Its exit code is the done-check.
* `kit-import.mjs` refuses a consumer whose stylesheet does not import `@estate/ui-kit` once its
  `migrate_by` date has passed — and, from this change, also refuses a consumer whose stylesheet
  imports the kit while its `package.json` does not declare the dependency (an import that cannot
  resolve is worse than no import).

### 2.3 The ratchet — how the surfaces get guarded without going red

`packages/estate-ui-kit/guards/budget.json` holds, per surface path, the number of violations
that path may still have. `purity.mjs --budget guards/budget.json <paths>` fails only when a path
**exceeds** its budget. The budgets are today's measured numbers, so the guard starts green:

```json
{ "backstage/packages/app/src/modules/room": 128,
  "backstage/packages/app/src/modules/home": 67,
  "backstage/packages/app/src": 186,
  "web/app": 87,
  "store_platform/src/Store.Web/src": { "max": 215, "repo": "prospector",
                                        "root": "~/Documents/code/prospector" } }
```

(A path's count excludes the files under any nested entry, so each scope owns its own number.
Measured at `origin/main` @ `664df1924`.)

When a scope finishes, its budget goes to `0` — that is the closing move of the whole redesign:
the moment the numbers reach zero, the budget stops being a promise and starts being a refusal.

### 2.4 What the kit's CI job does from now on

* the "did this change touch a front end" filter watches `web/`, `backstage/packages/app/src/**`
  and `packages/estate-ui-kit/**` — a change to a surface runs the kit's guards (F6);
* it runs the **budget** check on the surfaces (never above today's number) and the strict
  check on the kit's own code;
* it runs `purity.mjs` on `web/` and on the Backstage app — the surfaces are guarded by the
  guards written for them.

## 3. The five surfaces

Each surface is one claim, one branch, one lane. Each has a **measurable** done-check. A surface
is done when its guard output is zero and its page renders with the kit's tokens.

### Scope A — Fleet (`/fleet`)

* **Where** `backstage/packages/app/src/modules/room` (128 violations, 20 files).
* **What** every colour in the room's CSS and inline styles becomes a kit token; the six state
  colours (`red / needs / running / good / stale / can't check`) become
  `var(--color-state-*-ink)` / `var(--color-state-*-bg)` — the same pairs the kit's contrast
  guard grades; inline styles move to the stylesheet.
* **Do not** change what the room *shows*. This is the founder's work surface; the redesign is
  its material, not its information architecture.
* **Done** `node node_modules/@estate/ui-kit/guards/purity.mjs backstage/packages/app/src/modules/room`
  → `0 violations`; the portal's tests still pass.

### Scope B — Face (Backstage home)

* **Where** `backstage/packages/app/src/modules/home` (67 violations, 41 files) and
  `backstage/packages/app/src/modules/theme/tokens.ts` + `buiVars.ts` (the kit's seed, which
  `consumers.json` says is replaced by the kit).
* **What** the Face's palette comes from the kit's tokens; `tokens.ts` becomes a thin alias over
  the kit's `dist/tokens.ts` (names, not values) or is deleted in favour of the kit's CSS. The
  Face keeps its voice (it already mounts the canonical `useEstateVoice`) and its tests.
* **Done** purity → 0; the Face's voice tests still pass (`useEstateVoice.micPlatform.test.ts`,
  `FacePage.router.test.tsx`, `useEstateVoice.kokoroSpeaker.test.tsx`).

### Scope C — the Backstage portal (the rest)

* **Where** `backstage/packages/app/src` minus `modules/room` and `modules/home`
  (186 violations, 24 files, of which `src/estate-bui.css` is 20).
* **What** `estate-bui.css`'s `--bui-*` values become the kit's tokens; the components that carry
  literals (`components/ErrorBoundary.tsx` and its neighbours) are restyled onto the vocabulary;
  MUI defaults are overridden with kit tokens rather than replaced.
* **Done** purity → 0 for the whole app (room + home included, since one dependency serves all
  three); the portal's test suite passes.

### Scope D — Meridian (`web/`)

* **Where** `web/app` (87 violations, 19 files).
* **What** `web/app/globals.css` stops being a token table: it imports the kit's tokens and keeps
  only Meridian-specific rules. Meridian's identity becomes a **brand**:
  `packages/estate-ui-kit/brands/meridian.json` carries its warm canvas (`#FAFAF8`), its ink and
  its teal accent; the brand must pass `npm run guard:contrast` (the kit grades every brand).
  Inline `style={{ color: "var(--ink-3)" }}` becomes a class or a kit token.
* **Done** purity → 0 for `web/`; `npm run verify` passes (typecheck, voice lint, lint, test,
  build, smoke); the brand is in the kit and graded.

### Scope E — mumchimp (`prospector/store_platform/src/Store.Web`)

* **Where** another repository — a separate claim, a separate branch, a separate lane.
* **What** the 174 off-scale `font-size` literals become `var(--type-*)`; the 41 colour literals
  become kit tokens; the brand is already there (`brands/mumchimp.json`) — the storefront imports
  it. `crew#700 CP1` owns mumchimp's home and pack pages: **this scope is the stylesheet layer
  under that work, not a rewrite of those pages.** Coordinate through the crew issue.
* **Done** purity → 0 for `src`; `npm run verify` passes; the brand CSS is imported after the
  tokens.

### Scope F — voice (named, small, all surfaces)

* AGENTS.md §9: a surface mounts `useEstateVoice`; it does not call the browser APIs.
* The kit ships `src/voice/useEstateVoice.ts` and its `exports` map already publishes
  `./voice` → so a surface installs the same dependency and imports
  `@estate/ui-kit/voice` — **one hook, one copy, one place to fix it**.
* **Face**: keeps the portal's canonical hook — no change.
* **Fleet / Meridian / mumchimp**: mount the kit's hook, if its API (`listen`/`speak`/`status`)
  fits what the surface needs. Scope F is delivered **after** scopes A/B/C/D/E are green; if the
  hook's API does not fit, the gap is recorded on the crew issue rather than papered over with a
  second hook.

## 4. The laws the builders work under

1. **No hex.** Colour comes from a kit token or a kit brand. Not one `#` in a surface's own
   stylesheet.
2. **No literal type sizes.** `font-size: var(--type-sm)`, never `14px`.
3. **No inline colour or font-size styles.** They go in the stylesheet.
4. **One layer.** A surface does not add a token table, a theme provider or a component library
   that duplicates the kit's. If the surface needs a new colour, it is a brand entry, and the
   brand is graded by the kit's contrast guard.
5. **Voice is the hook**, never `SpeechRecognition`/`speechSynthesis` directly.
6. **Claim discipline** (AGENTS.md §5): one claim per scope, paths declared before the files
   change, heartbeat refreshed hourly, `Claim: <owner>/<repo>#<n>` and `Agent: <name>` trailers,
   then `estate-execute lane-submit` — never a hand-raised PR, never a push to main.
7. **Proof, not assertion** (AGENTS.md §3): the done-check is a command and its output. "It
   looks right" is not a done-check.
8. **No dependency the guard cannot see.** A surface's guard runs from `node_modules`, so the
   dependency must be declared and installed — not vendored by hand.

## 5. The build plan — four minimax builders

| # | Scope | Repo | Model | Claim paths |
|---|---|---|---|---|
| 1 | A Fleet + B Face + C portal | `idp` | minimax | `backstage/packages/app/src/modules/room/**`, `.../home/**`, `.../components/**`, `.../theme/**`, `backstage/packages/app/src/estate-bui.css`, `backstage/packages/app/package.json`, `backstage/yarn.lock` |
| 2 | D Meridian + `brands/meridian.json` | `idp` | minimax | `web/app/**`, `web/package.json`, `web/package-lock.json`, `packages/estate-ui-kit/brands/meridian.json` |
| 3 | E mumchimp stylesheet layer | `prospector` | minimax | `store_platform/src/Store.Web/src/**`, `store_platform/src/Store.Web/package.json`, `store_platform/src/Store.Web/package-lock.json` |
| 4 | F voice | `idp` | minimax | `packages/estate-ui-kit/src/voice/**`, `packages/estate-ui-kit/package.json` |

Builder 1 owns the Backstage app's three scopes in one claim because they share one dependency
and one token vocabulary; splitting them would have three agents editing the same stylesheet.

Every builder: read §3 first, then §4, then `docs/reviews/2026-10-24-founder-surface-review.md`
for the numbers their scope starts from.

## 6. What "operational" means here

Not "the tokens are in the file". For each surface:

* the guard prints `0 violations` on the surface's own paths, from the repo root, on a clean
  checkout of the landed commit;
* the surface is **served** with the kit's tokens — the builder proves it by reading the served
  CSS (the bundle), not the source;
* for the two public surfaces, the founder's real path renders: mumchimp.com's home and a pack
  page, meridian's landing — with the kit's type scale and the brand's colours;
* the scope's entry in `guards/budget.json` is `0`, so the guard refuses a regression.

A surface that passes its guard but was never served is *built*, not *operating*. The builder
says which one it achieved.
