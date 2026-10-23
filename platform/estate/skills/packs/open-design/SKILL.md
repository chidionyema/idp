---
name: open-design
description: "The working skills of a design workspace: brand kit, design brief, creative direction, review, colour, copy."
license: Apache-2.0
metadata:
  estate-category: design
  estate-upstream: nexu-io/open-design
---

# Open Design -- the design workspace skill set

The working skills of a design workspace: brand kit, design brief, creative direction, review, colour, copy.

## When to use this

When a piece of work needs a brief, a brand kit or a creative direction before any
code is written -- the working skills of a design workspace, taken one at a time.

## How to use it

1. `upstream/skills/design-brief/SKILL.md` to write the brief.
2. `upstream/skills/brandkit/SKILL.md` to hold the brand's assets and rules.
3. `upstream/skills/creative-director/SKILL.md` for direction, `upstream/skills/design-review/SKILL.md`
   for the review pass, `upstream/skills/color-expert/SKILL.md` and
   `upstream/skills/copywriting/SKILL.md` for the parts agents usually skip.
4. `upstream/README.md` is the workspace's own documentation -- read it before
   assuming what the workspace does.

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

Vendored verbatim from `nexu-io/open-design` at commit `e03d5c23f308c39f4de7c057568df66c29a84385`
(Apache-2.0, 103540 stars at 2026-10-23T15:32:22+00:00). See `NOTICE.md`.

- `upstream/LICENSE`
- `upstream/README.md`
- `upstream/skills/brandkit/SKILL.md`
- `upstream/skills/color-expert/SKILL.md`
- `upstream/skills/copywriting/SKILL.md`
- `upstream/skills/creative-director/SKILL.md`
- `upstream/skills/design-brief/SKILL.md`
- `upstream/skills/design-md/SKILL.md`
- `upstream/skills/design-review/SKILL.md`

<!-- provenance:end -->
