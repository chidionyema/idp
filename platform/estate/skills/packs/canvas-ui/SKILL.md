---
name: canvas-ui
description: "Canvas/WebGL UI primitives for interfaces that cannot be DOM: 3D scenes, shaders, and interactive canvases inside a product."
license: NOASSERTION
metadata:
  estate-category: ui
  estate-upstream: DavidHDev/canvas-ui
---

# Canvas UI -- canvas and WebGL interface primitives

Canvas/WebGL UI primitives for interfaces that cannot be DOM: 3D scenes, shaders, and interactive canvases inside a product.

## When to use this

When the interface cannot be a document: a canvas or WebGL surface inside a
product, with the primitives and the model licensing to check.

## How to use it

1. `upstream/README.md` is the index of what the kit provides and how it is used.
2. `upstream/LICENSE.md` is the licence of the kit; `upstream/public/assets/models/LICENSE.md`
   is the licence of the models it ships -- read both before shipping an asset.
3. A canvas surface is not reachable by voice unless the surface exposes its state
   to the voice plane; say how it does that in the change.

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

Vendored verbatim from `DavidHDev/canvas-ui` at commit `a04a99b235299ee79a123a16ccb2e6cf9da74b6b`
(NOASSERTION, 5070 stars at 2026-10-23T15:34:07+00:00). See `NOTICE.md`.

- `upstream/LICENSE.md`
- `upstream/README.md`
- `upstream/public/assets/models/LICENSE.md`

<!-- provenance:end -->
