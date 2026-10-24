---
name: spec-driven
description: "Spec-driven development templates and commands from GitHub's spec-kit: spec, plan, tasks, checklist, constitution, and the analyze/converge commands that keep a spec honest. Use when a piece of work needs an agreed specification before implementation."
license: MIT
metadata:
  estate-category: engineering
  estate-upstream: github/spec-kit
---

# Spec-Driven Development -- specify, plan, task, implement, verify

GitHub's spec-driven method: a specification template, a plan template, a task breakdown, a checklist generator and the commands that drive them, so an agent works from an agreed spec instead of an impression.

## When to use this

When the work is bigger than a bug fix: the spec, the plan and the checklist are what
the founder and the agent agree on before the first line of code.

## How to use it

1. `upstream/templates/spec-template.md` - the spec, written before the plan.
2. `upstream/templates/plan-template.md` and `templates/tasks-template.md` - the plan and the task breakdown.
3. `upstream/templates/commands/checklist.md` - the checklist that grades "ready".
4. `upstream/templates/commands/analyze.md` - consistency check across spec, plan and tasks.
5. `upstream/templates/commands/converge.md` - bring the three back into line.
6. `upstream/.github/skills/code-review/SKILL.md` - the review that closes the loop.

## Estate rules that bind this pack

- **Proof, not assertion.** A claim about this skill's effect is a command and its output.
- **One of each layer.** If the estate already owns the capability, use it; a pack never
  becomes a second copy of a layer.
- **Voice first.** A surface the founder cannot speak to and watch live is not finished.
- **The claim is the contract.** Work lands only against a live claim (AGENTS.md 5).

<!-- provenance:begin -->
## Upstream material

Vendored verbatim from `github/spec-kit` at commit `67e0f7294e6e728ab60bf7b4590deb470448bc2d`
(MIT, 142637 stars at 2026-10-24T08:03:29+00:00). See `NOTICE.md`.

- `upstream/.github/skills/code-review/SKILL.md`
- `upstream/LICENSE`
- `upstream/templates/checklist-template.md`
- `upstream/templates/commands/analyze.md`
- `upstream/templates/commands/checklist.md`
- `upstream/templates/commands/converge.md`
- `upstream/templates/constitution-template.md`
- `upstream/templates/plan-template.md`
- `upstream/templates/spec-template.md`
- `upstream/templates/tasks-template.md`

<!-- provenance:end -->
