---
name: scroll-world
description: "Turn a brand into a scroll-scrubbed 3D world landing page, with the scrub engine and the prompts that produce it."
license: MIT
metadata:
  estate-category: ui
  estate-upstream: oso95/scroll-world
---

# Scroll World -- a brand as a scrollable 3D world

Turn a brand into a scroll-scrubbed 3D world landing page, with the scrub engine and the prompts that produce it.

## When to use this

When a landing page must feel like a place rather than a page: a scroll-scrubbed 3D
world, with the engine and the prompts that produce it.

## How to use it

1. `upstream/skills/scroll-world/SKILL.md` is the entry point; it is long and is the
   method.
2. `upstream/skills/scroll-world/references/pipeline.md` is the build pipeline and
   `references/prompts.md` the prompts.
3. Weight is the risk here: measure the JS budget with `ui.review` before and after,
   and if the scene does not earn its weight, it does not ship.
4. The scroll engine is a `three.js` dependency: the estate's kit has no canvas layer
   of its own, so this pack introduces one and says so in the change.

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

Vendored verbatim from `oso95/scroll-world` at commit `71cc36d3bb150248ae36a2c552f9cbf88802a79c`
(MIT, 10386 stars at 2026-10-23T15:34:03+00:00). See `NOTICE.md`.

- `upstream/LICENSE`
- `upstream/skills/scroll-world/SKILL.md`
- `upstream/skills/scroll-world/references/pipeline.md`
- `upstream/skills/scroll-world/references/prompts.md`

<!-- provenance:end -->
