---
name: gsap-skills
description: "GSAP used correctly: core tweens and timelines, ScrollTrigger, plugins, React integration, and the performance rules that keep it smooth."
license: MIT
metadata:
  estate-category: ui
  estate-upstream: greensock/gsap-skills
---

# GSAP skills -- motion that runs at 60fps

GSAP used correctly: core tweens and timelines, ScrollTrigger, plugins, React integration, and the performance rules that keep it smooth.

## When to use this

When a page needs motion that is smooth and controllable: GSAP used the way the
library's authors intend, with the performance rules attached.

## How to use it

1. `upstream/skills/gsap-core/SKILL.md` then `upstream/skills/gsap-timeline/SKILL.md`
   for the model; `upstream/skills/gsap-utils/SKILL.md` for the helpers.
2. `upstream/skills/gsap-scrolltrigger/SKILL.md` for scroll-driven work -- the pack
   that most often collides with the page-weight budget.
3. `upstream/skills/gsap-react/SKILL.md` and `gsap-frameworks/SKILL.md` for the
   framework integration; `gsap-plugins/SKILL.md` for the paid ones.
4. `upstream/skills/gsap-performance/SKILL.md` before shipping: it is the pack that
   keeps the JS budget.

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

Vendored verbatim from `greensock/gsap-skills` at commit `aed9cfd3277740755f6bfc1155c7aa645403b760`
(MIT, 16981 stars at 2026-10-23T15:33:47+00:00). See `NOTICE.md`.

- `upstream/LICENSE`
- `upstream/skills/gsap-core/SKILL.md`
- `upstream/skills/gsap-frameworks/SKILL.md`
- `upstream/skills/gsap-performance/SKILL.md`
- `upstream/skills/gsap-plugins/SKILL.md`
- `upstream/skills/gsap-react/SKILL.md`
- `upstream/skills/gsap-scrolltrigger/SKILL.md`
- `upstream/skills/gsap-timeline/SKILL.md`
- `upstream/skills/gsap-utils/SKILL.md`

<!-- provenance:end -->
