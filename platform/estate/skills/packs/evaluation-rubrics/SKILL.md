---
name: evaluation-rubrics
description: "Evaluation methodology for agents and models: how to build a rubric, how to score against it, and how to raise a score that is too low. Use when a change to a prompt, a model route or a policy has to be graded, not asserted."
license: MIT
metadata:
  estate-category: verification
  estate-upstream: wshobson/agents
---

# Evaluation methodology -- rubrics, scoring and improving a score

How to grade an agent or a model against a rubric, how to write that rubric, and what to do when the score is wrong: the methodology, the rubric reference and the score-improvement loop.

## When to use this

Whenever the question is "is this better?" - a new prompt, a new model route, a new
policy. The estate's answer is a rubric and a score, not an opinion.

## How to use it

1. `upstream/plugins/plugin-eval/skills/evaluation-methodology/SKILL.md` - the method.
2. `.../references/rubrics.md` - rubric shapes, read before writing one.
3. `.../references/improving-scores.md` - what to do when the score is low.

## Estate rules that bind this pack

- **Proof, not assertion.** A claim about this skill's effect is a command and its output.
- **One of each layer.** If the estate already owns the capability, use it; a pack never
  becomes a second copy of a layer.
- **Voice first.** A surface the founder cannot speak to and watch live is not finished.
- **The claim is the contract.** Work lands only against a live claim (AGENTS.md 5).

<!-- provenance:begin -->
## Upstream material

Vendored verbatim from `wshobson/agents` at commit `0874a27b17a22e2b7c2e2bcd725768e0803cad06`
(MIT, 41619 stars at 2026-10-24T08:04:32+00:00). See `NOTICE.md`.

- `upstream/LICENSE`
- `upstream/plugins/plugin-eval/skills/evaluation-methodology/SKILL.md`
- `upstream/plugins/plugin-eval/skills/evaluation-methodology/references/improving-scores.md`
- `upstream/plugins/plugin-eval/skills/evaluation-methodology/references/rubrics.md`

<!-- provenance:end -->
