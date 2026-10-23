---
name: ui-ux-pro-max
description: "Turn a request into a token-backed design system: primitive and semantic tokens, a component spec, a brand kit, and a banner that matches the brand."
license: MIT
metadata:
  estate-category: design
  estate-upstream: nextlevelbuilder/ui-ux-pro-max-skill
---

# UI/UX Pro Max -- design system, tokens, brand, banners

Turn a request into a token-backed design system: primitive and semantic tokens, a component spec, a brand kit, and a banner that matches the brand.

## When to use this

When the brief is 'make it look right' and there is no design system yet: this is the
pack that turns taste into tokens, a component spec, states and variants, and a brand
kit that the rest of the estate can point at.

## How to use it

1. Start with `upstream/skills/ui-ux-pro-max/SKILL.md` for the method.
2. Shape the token layers with `upstream/skills/design-system/references/token-architecture.md`,
   `primitive-tokens.md` and `semantic-tokens.md`.
3. Carry the result into `packages/estate-ui-kit/tokens.json` -- the estate's one
   token file -- rather than into a new file beside it.
4. Use `upstream/skills/brand/SKILL.md` when the work carries a brand, and
   `upstream/skills/banner-design/SKILL.md` for a banner or hero image brief.
5. Grade the result with `ui.review`.

## Estate rules that bind this pack

- **Tokens, not literals.** Colours, spacing, type scale and radii come from
  `packages/estate-ui-kit/tokens.json`. `ui.review` grades token purity and can fail
  the work; a pack never overrides it.
- **Voice first.** A surface the founder cannot speak to and watch live is not
  finished, however good it looks.
- **Proof, not assertion.** A claim about how a design looks is a screenshot or a
  graded `ui.review` run, never a description of what it would look like.
- **Budgets are budgets.** The JS and page budgets in `ui.review` are the caps.
  Motion and 3D packs earn their weight or they do not ship.
- **One of each layer.** If the estate already owns a component, a token or a
  pattern, this pack informs it; it does not become a second copy of it.

<!-- provenance:begin -->
## Upstream material

Vendored verbatim from `nextlevelbuilder/ui-ux-pro-max-skill` at commit `d14efff8ed1faa4187f004f79926f428c8074ec7`
(MIT, 139301 stars at 2026-10-23T15:26:31+00:00). See `NOTICE.md`.

The upstream ships these under `.claude/`; the estate refuses a harness
folder in the tree, so the bytes live under a plain path. `NOTICE.md`
names the upstream path for every file.

- `upstream/LICENSE`
- `upstream/skills/banner-design/SKILL.md`
- `upstream/skills/brand/SKILL.md`
- `upstream/skills/design-system/SKILL.md`
- `upstream/skills/design-system/references/primitive-tokens.md`
- `upstream/skills/design-system/references/semantic-tokens.md`
- `upstream/skills/design-system/references/token-architecture.md`
- `upstream/skills/design/SKILL.md`
- `upstream/skills/ui-ux-pro-max/SKILL.md`

<!-- provenance:end -->
