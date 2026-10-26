# The founder's five surfaces, reviewed against the packs and the kit

**Date:** 2026-10-24 · **Author:** pi (agent pi) · **Scope:** every page the
founder can reach — `/fleet`, `/face`, the Backstage portal, mumchimp.com, and the Meridian site.

**How this was measured.** Every number below is the output of a command you can re-run, not an
opinion. The kit's own guards are the measuring instrument:

```bash
node packages/estate-ui-kit/guards/purity.mjs <dir>        # colour literals, inline styles, off-scale sizes
node packages/estate-ui-kit/guards/kit-import.mjs          # does the surface import @estate/ui-kit
node packages/estate-ui-kit/guards/contrast.mjs <dir>       # text against its own background
```

The rules applied are the ones in the estate's own skill packs (`~/.estate/skills/packs`, the layer
this branch lands): **taste** `references/tells.md` (the dated registry of what reads as generated),
**hallmark** `references/gates.md` (numbered gates with tiers), **impeccable** `reference/craft-floor.md`,
and **design-md**. Each finding below names the rule it breaks, in the pack's own vocabulary, so a
builder can read the rule and not this document.

**A gate that cannot fail.** `guards/contrast.mjs` reports `96 pairs checked across 2 palette(s)
(kit, mumchimp), 0 fail` on every surface — because it checks the *kit's* palette, and no surface
uses the kit. The surfaces' own literal pairs (`#7fd1b9` on `#0b0e14`, `#0E6E62` on `#FAFAF8`) are
never measured by anything. The contrast result below is therefore the kit's, not the pages'; it
becomes a real measurement when the surfaces import the tokens, and that is the point of fix 1.

**The one finding under all five.** The estate built a design system and did not use it.
`packages/estate-ui-kit` holds a complete token set (two modes, six type steps, a space scale, a
motion scale), three guards, a brand set, a gallery and a scaffold. The kit-import guard says:

```
warn   backstage/packages/app: no kit import yet; legacy until 2026-10-31
warn   ~/Documents/code/prospector/store_platform/src/Store.Web: no kit import yet; legacy until 2026-10-31
REFUSE ~/Documents/code/bytesync-web: src/app/globals.css does not import @estate/ui-kit (deadline 2026-10-15 passed)
```

Not one founder surface imports it. Every colour on every page below is a literal typed into a
component, so the tokens, the contrast guard and the scaffold are all dead code, and the
bytesync-web consumer is already past its deadline and refusing.

---

## 1. `/fleet` — the work surface (backstage/packages/app/src/modules/room)

**Measured:** `purity: 128 violations in 20 files — colour literal: 112, inline style: 16`.

**What it is:** the founder's primary surface — a live 3D topology of the estate's agents, the news
desk, the claims panel, the greenlane HUD. It is the most information-dense page in the estate and
the one the founder watches to know the estate is alive. The redesign must keep the topology, the
24 live agents, the news desk and the voice path exactly as they are; only the *material* changes.

| # | Finding | Evidence | Rule |
|---|---|---|---|
| F1 | A neon cyan on a near-black ground, with a glow shadow on it | `ui/FleetReactorApp.tsx:76` (`thinking: '#00f0ff'`), `:2158` (`boxShadow: '0 0 8px #00f0ff'`) | taste §2: "Near-black ground with one neon accent and a glow" — **banned**. hallmark 2a (Floor): cyan-on-dark gradient/accents; 29: "a coloured zero-offset glow shadow on dark" |
| F2 | Glass panels: translucent black with a 10–14px backdrop blur | `ui/FleetReactorApp.tsx:2152`, `:2167` | taste §1: "Glass panels: backdrop blur, translucent cards — warned (2 or more)"; "Opaque surfaces one tone step from the ground" |
| F3 | A cyan→amber gradient bar used as a heat meter | `ui/FleetReactorApp.tsx:2053` | hallmark 2b (Reflex): gradient where one hue would do; taste: gradients read as generated |
| F4 | The state palette is four raw hexes, not the estate's four state inks | `ui/FleetReactorApp.tsx:76-83` | the kit has `state-running-ink`, `state-needs-ink`, `state-red-ink`, `state-good-ink` — the same semantics, already tokenised, already contrast-checked |
| F5 | Mono as costume: the whole HUD's labels are monospace | `ui/FleetReactorApp.tsx:2142` | hallmark 64 (Reflex): "mono as costume — on labels, captions, meta rows … when the content is not code" |
| F6 | Uppercase tracked micro-labels above content | `ui/NewsDesk.tsx` (3 occurrences), `ui/FleetReactorApp.tsx` (2) | taste §2: "Eyebrow / kicker: tiny tracked uppercase label above every heading — banned"; hallmark 54 (Floor, house rule) |
| F7 | 112 colour literals across 20 files | the purity count above | the kit's rule: "tokens, not literals" |

**What must survive:** the topology metaphor, the live agent count, the interruption model, the
news desk, and the voice path. The redesign is a *re-materialisation*, not a rewrite.

---

## 2. `/face` — the estate's face (backstage/packages/app/src/modules/home)

**Measured:** `purity: 50 violations in 38 files — colour literal: 45, inline style: 5`.

**What it is:** the full-screen voice surface. The founder taps to talk; the face listens, answers
and speaks. Its own rules already exist in this directory (`DESIGN-RULES.md`, 25 sourced rules, and
`POLISH-SPEC.md`, the founder's verbatim asks from 2026-08-29: *"IT NEEDS TO CAPTURE ATTENTION
FIRST"*, *"DON'T ASSUME THE USER KNOWS WHAT YOU KNOW"*). The redesign must not regress any of them.

| # | Finding | Evidence | Rule |
|---|---|---|---|
| F8 | The face's own dark palette is four literals, and a different dark from Fleet's | `FacePage.tsx:237` (`radial-gradient(ellipse at 50% 30%, #1d2533 0%, #0b0e14 70%)`), `:238`, `:324` (`#7fd1b9`) | one surface, one ink: the kit's `canvas`/`surface-1..3` in dark mode |
| F9 | The control pill is glass over the avatar | `FacePage.tsx:289` (`backdropFilter: 'blur(12px)'`) | taste §1: glass panels warned at two or more; the face already has a docstring saying the controls float as a "glass pill" — the pill is the tell, not the framing |
| F10 | Uppercase tracked labels | `FacePage.tsx:266`, `EstateHome.tsx:132`, `ResearchCard.tsx:93` | taste §2 (banned eyebrow), hallmark 54 (Floor) |
| F11 | 45 colour literals across 38 files | the purity count | tokens, not literals |

---

## 3. The Backstage portal (backstage/packages/app/src — everything else)

**Measured:** `purity: 364 violations in 82 files — colour literal: 315, inline style: 23, off-scale size: 26`
(the 82 files include the 20 of `/fleet` and 38 of `/face`; the portal's own remainder is the rest).

**What it is:** the estate's backstage — catalog, ops, metrics, the sign-in door, the nav shell.

| # | Finding | Evidence | Rule |
|---|---|---|---|
| F12 | The portal carries its own token file *and* the kit's, and the kit's is unused | `packages/estate-ui-kit/consumers.json` names `backstage/packages/app` as a consumer with `migrate_by: 2026-10-31`; the kit-import guard prints `no kit import yet` | AGENTS.md §6: one of each layer. The kit replaces `src/theme/tokens`; it does not sit beside it |
| F13 | 315 colour literals and 26 sizes off the six-step scale, across the portal's own modules | the purity count | the kit's `type` scale (`xs`…`xxl`) and `space` scale; `guards/purity.mjs` refuses a size outside the list |

---

## 4. Meridian — the intelligence site (web/)

**Measured:** `purity: 129 violations in 27 files — inline style: 31, colour literal: 84, off-scale size: 14`
(the `web/app` pages alone: `87 violations in 19 files`).

**What it is:** the client-facing site — the pages a client is sent to, and the contact form that
turns a visit into a conversation. It is a *published* surface: every pixel here is a promise.

| # | Finding | Evidence | Rule |
|---|---|---|---|
| F14 | It runs its own token set — 28 custom properties — instead of the kit's | `web/app/globals.css:3-28` (`--bg`, `--ink`, `--accent: #0E6E62`, `--rule`, `--serif`, `--mono`…) | AGENTS.md §6: one of each layer. A second token file is the stitching the law deletes |
| F15 | Mono as costume across the whole chrome: 12 rules set `font-family: var(--mono)` for nav, tags, metrics, buttons, skip-link | `web/app/globals.css:65,68,71,83,101,102,119` | hallmark 64 (Reflex): mono on labels, captions and meta rows when the content is not code |
| F16 | Pure `#fff` and `#000` as colours outside any token block | `web/app/globals.css` (5 lines), `web/app/page.tsx` (4 lines) | hallmark 7a (**Floor**): "`#000`, `#fff` … as a colour outside the token block" |
| F17 | Cream paper with a teal accent and a high-contrast serif display | `web/app/globals.css:3` (`--bg: #FAFAF8`), `:10` (`--accent: #0E6E62`), `:21` (`--serif: 'Playfair Display'`) | hallmark 65 (Reflex): the cream-paper + serif-display + terracotta look, one axis at a time; taste §3: "the remedy published for the first two waves … the most recognisable generated look of all" |
| F18 | A tracked uppercase `.tag` treatment on every tag | `web/app/globals.css:71` | taste §2 (banned eyebrow), hallmark 54 (Floor) |
| F19 | 84 colour literals and 14 off-scale sizes in the pages | the purity count | tokens, not literals |

---

## 5. mumchimp — the public shop (~/Documents/code/prospector/store_platform/src/Store.Web)

**Measured:** `purity: 215 violations in 136 files — colour literal: 41, off-scale size: 174`.

**What it is:** mumchimp.com — packs, ideas, pricing, accounts, the kill log. The store front the
founder's audience buys from. Its own repo is not in this estate; the kit names it as a consumer
with `migrate_by: 2026-10-31` and the note "crew#700 CP1 rebuilds home and pack page on the kit".

| # | Finding | Evidence | Rule |
|---|---|---|---|
| F20 | 174 sizes off the six-step scale — the biggest single violation class in the estate | the purity count | the kit's `type` scale; `guards/purity.mjs` refuses a size outside the list |
| F21 | 41 colour literals, including a `--kicker` literal | `src/styles/globals.css:741` (`--kicker: #6B1D1D`), 41 across the store | tokens, not literals |
| F22 | No kit import; the guard says `legacy until 2026-10-31` | the kit-import guard output above | the deadline is seven days away |

---

## What the redesign has to fix, in one list

1. **Every surface imports `@estate/ui-kit`.** The kit-import guard turns from `warn` to `ok` on
   all five. This is the root cause of the other four.
2. **No colour literal in a component.** The colour-literal count on each surface goes to zero.
3. **No neon, no glow, no glass.** taste §1 and §2's banned rows, and hallmark 2a/29.
4. **No mono as costume, no tracked uppercase eyebrows.** hallmark 64 and 54 (Floor).
5. **No pure `#fff`/`#000` outside a token block.** hallmark 7a (Floor).
6. **Every size comes from the six-step scale.** No 14px, no 22px, no 28px literals.
7. **Nothing the founder already asked for regresses**: the Face's hierarchy and captions
   (`POLISH-SPEC.md`), Fleet's live topology and voice path, Meridian's editorial voice, the
   store's pages.

The companion spec — `docs/specs/2026-10-24-founder-surface-redesign.md` — turns this list into
one scope per surface, with the exact files and a done-check that fails before the change and
passes after it.
