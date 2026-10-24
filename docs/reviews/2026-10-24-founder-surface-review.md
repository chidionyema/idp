# Founder surface review — 2026-10-24

The five surfaces the founder named — Fleet, Face, the Backstage portal, Meridian, mumchimp —
reviewed against the estate's own kit (`packages/estate-ui-kit`) and the estate's own laws
(AGENTS.md §6 one of each layer, §9 voice first, §3 proof not assertion).

Every number in this document is the kit's own guard output, measured on 2026-10-24 on this
laptop against `origin/main` @ `664df1924` (`packages/estate-ui-kit/guards/purity.mjs`). Nothing
here is an estimate.

## Method

```
node packages/estate-ui-kit/guards/purity.mjs <dir>
```

refuses three things in `.css/.scss/.tsx/.jsx/.astro/.svelte/.vue`:

1. **colour literals** — `#hex`, `rgb()`, `hsl()`, `oklch()`;
2. **off-scale sizes** — `font-size:` with a `px`/`rem` literal instead of `var(--type-*)`;
3. **inline styles** — a `style=` attribute carrying a colour or a font-size.

and `node packages/estate-ui-kit/guards/kit-import.mjs` refuses a consumer whose stylesheet does
not import the kit's tokens (`packages/estate-ui-kit/consumers.json`).

## The five surfaces, measured

| Surface | Where | Stack | Violations | Files | Colour | Off-scale | Inline | Kit tokens | Voice |
|---|---|---|---|---|---|---|---|---|---|
| Fleet (`/fleet`) | `backstage/packages/app/src/modules/room` | React (Backstage) | **128** | 20 | 112 | 0 | 16 | no | no |
| Face (Backstage home) | `backstage/packages/app/src/modules/home` | React (Backstage) | **67** | 41 | 58 | 0 | 9 | no | **yes** |
| Backstage portal (the rest) | `backstage/packages/app/src` minus room/home | React (Backstage) | **186** | 24 | 158 | 26 | 2 | no | no |
| Meridian | `web/app` | Next.js 15 | **87** | 19 | 52 | 14 | 21 | no | no |
| mumchimp | `prospector/store_platform/src/Store.Web/src` | Next.js 15 | **215** | 136 | 41 | 174 | 0 | no | no |

Totals across the three codebases: **683 violations** (421 colour literals, 214 off-scale sizes,
48 inline styles). The Backstage app alone is 381 of them.

## What the numbers say, surface by surface

### 1. Fleet — the founder's primary work surface

`/fleet` renders `FleetReactorApp` (`modules/room/ui/FleetReactorApp.tsx`); the modules around it
are the claims panel, the delivery board, the greenlane HUD, the efficiency HUD, the news desk,
the harvester panel, the research findings, the radial menu and the spotlight. It is the surface
AGENTS.md §5 promises the founder: *"The founder sees every live claim on /fleet: who, what,
which paths, and heartbeat age."*

128 violations in 20 files, and **every one of them is in the room's own CSS and inline styles**
— 112 colour literals, 16 inline colour styles, zero off-scale sizes. The room paints its panels
with literal hex values, so the same state colour can be four different hexes on one screen: a
state that must be readable at a glance (red / needs you / running / good / stale / can't check)
is the one thing the founder cannot afford to misread, and it is the one thing the room paints
by hand. The kit already carries the six states as `state-red-ink`/`state-red-bg` pairs with a
contrast guard over them.

There is a second, quieter problem: `/fleet` has no voice. AGENTS.md §9 says every surface ships
voice on day one and that the canonical engine is `useEstateVoice`. Fleet is the surface the
founder watches most; it is the one place where "what is happening" is a spoken question.

### 2. Face — the only surface that got it right, and then kept going its own way

`modules/home` is the estate's Face (`EstateFace.tsx`, `FacePage.tsx`). It is the only surface
that mounts the canonical voice hook (`modules/home/useEstateVoice.ts`) — and it is the only one
whose hooks, router, platform tests and retries are covered by real tests
(`useEstateVoice.micPlatform.test.ts`, `FacePage.router.test.tsx`, `useEstateVoice.kokoroSpeaker.test.tsx`).

67 violations in 41 files: 58 colour literals, 9 inline styles, spread thin. `EstateFace.tsx:57`
carries `color: 'rgba(232,237,245,0.72)'` inline — a hand-tuned text colour on the estate's own
quiet-instrument canvas. `EstateMap.tsx` paints its own graph palette (`'#2b6cb0'`, `'#805ad5'`,
`'#38a169'`, `'#f6e05e'`) — a diagram's own colours, which the kit's vocabulary has no room for
until a brand says so.

The Face's problem is not ugliness. It is that its *own* palette (`modules/theme/tokens.ts`,
13 tones × 2 themes) is the seed the kit was grown from, and it still lives: the kit declares
`tokens.json` as the single source, and `consumers.json` says of the portal, *"its tokens.ts
seeded the kit and is replaced by it."* It has not been replaced. The estate is paying for the
kit and still running the seed.

### 3. The Backstage portal — a third token vocabulary

The portal's `src/styles.css` is exemplary: *"Every colour, radius and face below is a
`--bui-*` variable, which `modules/theme/buiVars.ts` fills from `modules/theme/tokens.ts`. No hex
belongs in this file."* And then `src/estate-bui.css` defines 20 `--bui-*` values as hex
literals, because `tokens.ts` is a second palette and the kit is a third.

186 violations in 24 files outside the room and the Face — and 158 of them are colour literals,
concentrated in a few dense files (`components/ErrorBoundary.tsx:77` carries `bgcolor="#f5f5f5"`
in a MUI component, which the kit's vocabulary cannot reach until the component is restyled).
The portal's own catalog, metrics, nav and shell modules are clean (0 violations each) — the
damage is concentrated in `components/` and `estate-bui.css`.

### 4. Meridian — a parallel design system, carefully made

`web/app/globals.css` opens with its own token block: `--bg: #FAFAF8`, `--ink: #0D0D0A`,
`--accent: #0E6E62`, `--serif: 'Playfair Display'`, `--space-1: 4px` … and the comments explain
*why*, in the estate's own voice ("one accent, and not the one every LLM-adjacent brand already
uses"). Somebody thought about this. It is still a second design system: 87 violations in 19
files, 52 colour literals, 21 inline styles (the inline ones are `style={{ color: "var(--ink-3)" }}`
— a token by another name, but an inline style, which the kit's guard refuses because the point of
a token is that it is in the stylesheet), and 14 off-scale sizes.

Meridian's identity is worth keeping. It is the estate's public face and it is not the kit's
house style. The right shape is a **brand** of the kit — the same door `brands/mumchimp.json`
already is — not a second token table in a CSS file.

Meridian is also the only surface with a *written* voice law: `web/VOICE.md` plus
`web/scripts/voice-lint.mjs`, which measures the prose in `content/`, `app/` and `components/`
against four editorial rules and fails the build when one breaks. That is the estate's voice at
its best — it is a gate, not a vibe. It is worth saying plainly: that is a **written** voice.
Spoken voice is a different thing, and it is measured separately below.

### 5. mumchimp — the public shop, mostly wrong in the small ways

215 violations in 136 files: only 41 colour literals, but **174 off-scale sizes** — `font-size: 14px`
written a hundred and seventy-four times instead of `var(--type-sm)`. This is what a surface looks
like when nobody can change the type scale, because there is no scale to change to.

The kit already carries mumchimp's identity: `packages/estate-ui-kit/brands/mumchimp.json` holds
the Brand v3 paper/ink values ("Only colours may be overridden here; type, space, radius and
motion are the kit's"), and `build.mjs` emits `dist/brands/mumchimp.css` and grades every brand
with the contrast guard. crew#700 CP1 owns rebuilding mumchimp's home and pack page on the kit.
The brand exists; the storefront has never imported it.

Mumchimp has no voice either, and it is the one surface a stranger lands on.

## Cross-cutting findings

**F1 — The kit is on none of the five surfaces.** `consumers.json` names three consumers: the
Backstage app (deadline 2026-10-31), mumchimp's `Store.Web` (deadline 2026-10-31) and
`bytesync-web` (deadline **2026-10-15, nine days past**). None of them imports the kit. The
import guard skips a consumer whose checkout is absent from the machine and says so — so on CI,
where `bytesync-web` is never checked out, the passed deadline cannot fail anywhere. A gate that
cannot fail is not a gate.

**F2 — The front door exists; nobody has walked through it.** The kit is published on every push
to `main` as the `ui-kit` branch of this (public) repository, subtree-split and force-pushed by
`.github/workflows/ui-kit-publish.yml`, and installable with **no token** as
`"@estate/ui-kit": "github:chidionyema/idp#ui-kit"`. The workflow proves it: its last step
installs the dependency into a scratch project and asserts `dist/tokens.css` exists — the kit's
`prepare` script builds `dist/` on install, so a consumer gets the tokens without a build step.

Measured on this laptop, 2026-10-24: `npm install github:chidionyema/idp#ui-kit` → 39 packages,
`node_modules/@estate/ui-kit/dist/tokens.css` present; `yarn@4.13.0 add @estate/ui-kit@github:chidionyema/idp#ui-kit`
(the portal's package manager) → 5 packages, `dist/tokens.css` present. The channel works for
both package managers the estate uses.

So the reason no surface has adopted the kit is not a missing mechanism. It is that **nothing
forces it until a deadline, and the deadline only bites when the consumer's checkout is on the
machine that runs the guard** (see F1). Five surfaces, one published kit, zero imports.

**F3 — Three token vocabularies are live at once.** The kit's `tokens.json` (26 colours × 2
themes, 6 type steps, a 9-step space scale), the portal's `tokens.ts` → `--bui-*`, and Meridian's
own `--bg/--ink/--accent`. AGENTS.md §6: one of each layer; a duplicate layer always goes.

**F4 — Colour is the cheapest thing to fix and the most expensive to leave.** 421 colour
literals across the five surfaces, and they are not decorative: they are the state colours the
founder reads to decide whether the estate is healthy.

**F5 — Spoken voice is on one surface of five.** Only the Face mounts `useEstateVoice`. Fleet,
Meridian and mumchimp have no spoken voice: `rg "SpeechRecognition|speechSynthesis"` over
`web/app`, `web/components`, `web/lib` and Store.Web's `src` finds nothing. (Meridian's
`voice-lint.mjs` is a *prose* gate — a different thing, and a good one.) AGENTS.md §9 says a new
surface does not use browser `SpeechRecognition` or `speechSynthesis`; it mounts the hook, and
the hook ships in the kit — so this is a distribution problem again, one level up: the kit is
installable, but nothing mounts the hook.

**F6 — The kit's guards only guard the kit.** `ci.yml`'s `ui-kit` job runs the contrast, purity
and import guards — but the purity guard runs on `src gallery scaffold` (the kit's own code),
and the job's "did this change touch a front end" filter watches `packages/estate-ui-kit/`,
`apps/` and `backstage/packages/app/src/styles.css`. **A change to `web/`, to the Fleet room's
CSS, or to Store.Web never runs the kit's guards at all.** The surfaces are unguarded by the
guards written for them.

**F7 — The kit's own tooling is ready for this and unused.** `build.mjs` emits
`dist/tokens.css`, `dist/tokens.ts`, `dist/tailwind.theme.css` and one CSS per brand;
`guards/contrast.mjs` grades every brand; `guards/purity.mjs` is the measurable bar;
`guards/kit-import.mjs` is the adoption bar; `scaffold/` creates a new surface already wired to
the kit; `src/templates/` holds nine page templates (Landing, Catalogue, Detail, Docs, Empty,
ErrorPage, Account, Checkout) and `src/voice/useEstateVoice.ts` holds the voice primitive.
The kit is a complete house style with no front door.

## Verdict

The surfaces are not badly designed. Meridian's palette is argued for in comments; the portal's
`styles.css` states the rule it wants to live by; the Face has the tests. What is missing is a
**front door**: a way for an existing surface, in any repository, to take the kit's tokens, the
kit's guards and the kit's voice primitive, and to prove it did.

So the redesign is not five beautification projects. It is one distribution mechanism plus five
surfaces that take the house style through it, each measured by the kit's own guards.

The spec that follows: `docs/specs/2026-10-24-founder-surface-redesign.md`.
