---
name: hallmark
description: "The anatomy of a good page: macrostructures, layout, type, flow, interaction states, and the gates a design must pass before it ships."
license: MIT
metadata:
  estate-category: design
  estate-upstream: Nutlope/hallmark
---

# Hallmark -- web design craft, macrostructures and gates

The anatomy of a good page: macrostructures, layout, type, flow, interaction states, and the gates a design must pass before it ships.

## When to use this

When a whole page is being designed or judged: the anatomy of a page, its
macrostructures, layout, type, flow, interaction states, and the gates a design must
pass before it ships.

## How to use it

1. `upstream/skills/hallmark/SKILL.md` is the entry point.
2. `references/macrostructures.md` for the page shapes (hero, bento, long document,
   stat-led, workbench, conversational, and the rest).
3. `references/layout.md`, `references/craft.md` and `references/flow.md` for the
   craft; `references/anatomy.md` for the parts a page must have.
4. `references/gates.md` is the checklist to run before calling a page done;
   `references/design-md.md` is how the design is written down.
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

Vendored verbatim from `Nutlope/hallmark` at commit `7ec868225c6caa040558c321ee0fefa0e73f83a8`
(MIT, 31159 stars at 2026-10-23T15:33:28+00:00). See `NOTICE.md`.

- `upstream/LICENSE`
- `upstream/skills/hallmark/SKILL.md`
- `upstream/skills/hallmark/references/anatomy.md`
- `upstream/skills/hallmark/references/craft.md`
- `upstream/skills/hallmark/references/design-md.md`
- `upstream/skills/hallmark/references/flow.md`
- `upstream/skills/hallmark/references/gates.md`
- `upstream/skills/hallmark/references/layout.md`
- `upstream/skills/hallmark/references/macrostructures.md`

<!-- provenance:end -->
