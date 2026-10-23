---
name: awesome-design-md
description: "Read and write DESIGN.md: the file that states a brand's colours, type, spacing, motion and components so an agent builds the brand instead of a generic page."
license: MIT
metadata:
  estate-category: architecture
  estate-upstream: VoltAgent/awesome-design-md
---

# Awesome DESIGN.md -- brand design specs as code

Read and write DESIGN.md: the file that states a brand's colours, type, spacing, motion and components so an agent builds the brand instead of a generic page.

## When to use this

When a brand's design has to be written down so that agents and engineers build the
same thing: three real DESIGN.md files, from Vercel, Raycast and Meta, as the
precedent for structure and depth.

## How to use it

1. Read `upstream/design-md/vercel/DESIGN.md` end to end once, to see the shape of a
   complete brand specification.
2. Read `upstream/design-md/raycast/DESIGN.md` and `upstream/design-md/meta/DESIGN.md`
   for the range: a specification can be terse or exhaustive, but it is never vague.
3. Write the estate's own DESIGN.md from `upstream/README.md`'s guidance, in the repo
   that owns the brand -- one copy, not one per product.
4. Check the result against the `design-md` pack's specification and linter.

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

Vendored verbatim from `VoltAgent/awesome-design-md` at commit `3b605329240ce735b510037cca322f1831fdd7f8`
(MIT, 123108 stars at 2026-10-23T15:32:12+00:00). See `NOTICE.md`.

- `upstream/LICENSE`
- `upstream/README.md`
- `upstream/design-md/meta/DESIGN.md`
- `upstream/design-md/raycast/DESIGN.md`
- `upstream/design-md/vercel/DESIGN.md`

<!-- provenance:end -->
