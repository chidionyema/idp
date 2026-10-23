---
name: design-md
description: "The DESIGN.md specification itself, with worked examples and the linter that checks one, so a brand spec is a checkable artifact rather than prose."
license: Apache-2.0
metadata:
  estate-category: architecture
  estate-upstream: google-labs-code/design.md
---

# Google DESIGN.md -- the specification and its linter

The DESIGN.md specification itself, with worked examples and the linter that checks one, so a brand spec is a checkable artifact rather than prose.

## When to use this

When a design system must be a file an agent, a linter and a human all read: the
DESIGN.md specification, worked examples, and the skills that write one at scale.

## How to use it

1. `upstream/docs/spec.md` is the specification; read it before writing one.
2. `upstream/README.md` explains the format and the linter that checks it.
3. `upstream/examples/totality-festival/DESIGN.md` is a complete worked example.
4. `upstream/.agents/skills/ink/SKILL.md` and `agent-dx-cli-scale/SKILL.md` cover
   writing one and keeping it true at scale.
5. Lint the result with the upstream linter, then with `ui.review` for the estate's
   own rules.

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

Vendored verbatim from `google-labs-code/design.md` at commit `6e5da5382f41edbba9d73b2c62f33f32e9971f15`
(Apache-2.0, 28498 stars at 2026-10-23T15:33:36+00:00). See `NOTICE.md`.

- `upstream/.agents/skills/agent-dx-cli-scale/SKILL.md`
- `upstream/.agents/skills/ink/SKILL.md`
- `upstream/LICENSE`
- `upstream/README.md`
- `upstream/docs/spec.md`
- `upstream/examples/totality-festival/DESIGN.md`

<!-- provenance:end -->
