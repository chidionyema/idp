---
name: emil-design-skills
description: "Design-engineering craft: animation vocabulary and performance, native-feeling mobile UI, Apple design language, and the breaking-the-template-look rules."
license: MIT
metadata:
  estate-category: ui
  estate-upstream: emilkowalski/skills
---

# Design engineering skills -- craft, motion and native feel

Design-engineering craft: animation vocabulary and performance, native-feeling mobile UI, Apple design language, and the breaking-the-template-look rules.

## When to use this

When motion, platform feel or the generic-template look is the problem: animation
vocabulary and performance, native mobile UI, Apple's design language, and how to
break the look of a template.

## How to use it

1. `upstream/skills/emil-design-eng/SKILL.md` is the entry point for design
   engineering as a discipline.
2. `skills/animation-vocabulary/SKILL.md` and `skills/animation-performance/SKILL.md`
   for motion that is smooth; `skills/review-animations/SKILL.md` to review it.
3. `skills/apple-design/SKILL.md` for native platform feel, `skills/mobile-native/SKILL.md`
   for mobile, `skills/break-ui/SKILL.md` when the page looks like every other page,
   `skills/prototype/SKILL.md` when the shape is still undecided.
4. Read `upstream/skills/animate/SKILL.md` last: it is the implementation layer.

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

Vendored verbatim from `emilkowalski/skills` at commit `2d228630ba1446365f614a108cb8252f1feda202`
(MIT, 48955 stars at 2026-10-23T15:33:05+00:00). See `NOTICE.md`.

- `upstream/LICENSE`
- `upstream/skills/animate/SKILL.md`
- `upstream/skills/animation-performance/SKILL.md`
- `upstream/skills/animation-vocabulary/SKILL.md`
- `upstream/skills/apple-design/SKILL.md`
- `upstream/skills/break-ui/SKILL.md`
- `upstream/skills/emil-design-eng/SKILL.md`
- `upstream/skills/mobile-native/SKILL.md`
- `upstream/skills/prototype/SKILL.md`
- `upstream/skills/review-animations/SKILL.md`

<!-- provenance:end -->
