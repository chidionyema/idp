---
name: impeccable
description: "A craft floor for an agent: audit, critique, refine and document a design, with the bar written down before the work starts."
license: Apache-2.0
metadata:
  estate-category: design
  estate-upstream: pbakaus/impeccable
---

# Impeccable -- the design language a harness should speak

A craft floor for an agent: audit, critique, refine and document a design, with the bar written down before the work starts.

## When to use this

When an agent is about to improve an existing interface, or a team needs the bar
written down before the work starts: the craft floor, the audit, the critique and the
new-work playbook.

## How to use it

1. `upstream/.agent/skills/impeccable/SKILL.md` is the entry point.
2. `reference/audit.md` to measure what is there; `reference/critique.md` to judge it;
   `reference/new-work.md` for greenfield; `reference/craft-floor.md` for the minimum
   bar; `reference/component-review.md` for a component in isolation.
3. Grade the result with `ui.review` -- the estate's gate, which can fail.

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

Vendored verbatim from `pbakaus/impeccable` at commit `5cb95eea9c96479f57afe0732a45470d30183326`
(Apache-2.0, 85322 stars at 2026-10-23T15:32:49+00:00). See `NOTICE.md`.

- `upstream/.agent/skills/impeccable/SKILL.md`
- `upstream/.agent/skills/impeccable/reference/audit.md`
- `upstream/.agent/skills/impeccable/reference/component-review.md`
- `upstream/.agent/skills/impeccable/reference/craft-floor.md`
- `upstream/.agent/skills/impeccable/reference/critique.md`
- `upstream/.agent/skills/impeccable/reference/new-work.md`
- `upstream/LICENSE`

<!-- provenance:end -->
