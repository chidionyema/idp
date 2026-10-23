---
name: taste
description: "Critique a screen the way a designer does, against a reference library of real work, with the tells named."
license: MIT
metadata:
  estate-category: design
  estate-upstream: Leonxlnx/taste-skill
---

# Taste -- critique a design against real references

Critique a screen the way a designer does, against a reference library of real work, with the tells named.

## When to use this

When a screen exists and the question is whether it is good: this pack reads type,
layout, motion, colour and imagery against a reference library, and names the tells
that make a design read as careless.

## How to use it

1. Read `upstream/skills/taste-skill/SKILL.md` for the method.
2. `upstream/skills/taste-skill/references/tells.md` is the checklist of tells.
3. `references/type.md`, `references/layout.md` and `references/critique.md` are the
   long reads for the part under review.
4. Write the critique as findings with a severity and a fix, not as adjectives.

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

Vendored verbatim from `Leonxlnx/taste-skill` at commit `6010f91a9935f1c167dfc500fb1a475681892e6b`
(MIT, 101484 stars at 2026-10-23T15:32:31+00:00). See `NOTICE.md`.

- `upstream/LICENSE`
- `upstream/skills/taste-skill/README.md`
- `upstream/skills/taste-skill/SKILL.md`
- `upstream/skills/taste-skill/references/critique.md`
- `upstream/skills/taste-skill/references/layout.md`
- `upstream/skills/taste-skill/references/tells.md`
- `upstream/skills/taste-skill/references/type.md`

<!-- provenance:end -->
