---
name: react-bits
description: "Pick and adapt animated React components (text, backgrounds, buttons, containers) instead of writing a bespoke animation from scratch."
license: NOASSERTION
metadata:
  estate-category: ui
  estate-upstream: DavidHDev/react-bits
---

# React Bits -- animated React components you can drop in

Pick and adapt animated React components (text, backgrounds, buttons, containers) instead of writing a bespoke animation from scratch.

## When to use this

When a front end needs motion and hand-rolling the animation would cost more than
adapting one: a library of animated React components and the tools behind them.

## How to use it

1. `upstream/README.md` indexes the components by category.
2. Copy the component, then read it and strip what the estate already has: the
   estate's own kit owns tokens, contrast and page weight.
3. `upstream/src/tools/shape-magic/README.md` covers the shape generator behind the
   blob and text effects.
4. Grade the result with `ui.review`: the JS budget is where a component library
   usually loses.

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

Vendored verbatim from `DavidHDev/react-bits` at commit `e12c22192ac7b4b452c5e2feb9b586d74765d696`
(NOASSERTION, 50059 stars at 2026-10-23T15:32:55+00:00). See `NOTICE.md`.

- `upstream/LICENSE.md`
- `upstream/README.md`
- `upstream/src/tools/shape-magic/README.md`

<!-- provenance:end -->
