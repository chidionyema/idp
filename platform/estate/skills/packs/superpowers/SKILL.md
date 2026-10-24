---
name: superpowers
description: "Staff-level engineering practice as skills: brainstorming, plan writing, plan execution, test-driven development, subagent-driven development and skill authoring. Use when starting any non-trivial change, or when a build has to be driven by a plan rather than by improvisation."
license: MIT
metadata:
  estate-category: engineering
  estate-upstream: obra/superpowers
---

# Superpowers -- plan first, test first, subagent-driven development

The staff engineer's daily loop, as skills: brainstorm the approach, write the plan, execute it in steps, drive it with tests, and review the result before it is called done.

## When to use this

Before any change that is more than a one-liner, and whenever a build is going wrong:
the failure mode this pack removes is an agent that starts editing before it has agreed
what it is building.

## How to use it

1. `upstream/skills/brainstorming/SKILL.md` - agree the approach before any code.
2. `upstream/skills/writing-plans/SKILL.md` - the plan the estate's `delegate-build` consumes.
3. `upstream/skills/executing-plans/SKILL.md` - run the plan in steps with checkpoints.
4. `upstream/skills/test-driven-development/SKILL.md` - the test decides, not the builder.
5. `upstream/skills/subagent-driven-development/SKILL.md` - how a plan is driven by builders.
6. `upstream/skills/writing-skills/SKILL.md` - how a pack like this one is written.

## Estate rules that bind this pack

- **Proof, not assertion.** A claim about this skill's effect is a command and its output.
- **One of each layer.** If the estate already owns the capability, use it; a pack never
  becomes a second copy of a layer.
- **Voice first.** A surface the founder cannot speak to and watch live is not finished.
- **The claim is the contract.** Work lands only against a live claim (AGENTS.md 5).

<!-- provenance:begin -->
## Upstream material

Vendored verbatim from `obra/superpowers` at commit `2ce8aa15d05bd57213e6f746f953aafb7ded7a8b`
(MIT, 304366 stars at 2026-10-24T08:02:01+00:00). See `NOTICE.md`.

- `upstream/LICENSE`
- `upstream/skills/brainstorming/SKILL.md`
- `upstream/skills/executing-plans/SKILL.md`
- `upstream/skills/subagent-driven-development/SKILL.md`
- `upstream/skills/test-driven-development/SKILL.md`
- `upstream/skills/writing-plans/SKILL.md`
- `upstream/skills/writing-skills/SKILL.md`

<!-- provenance:end -->
