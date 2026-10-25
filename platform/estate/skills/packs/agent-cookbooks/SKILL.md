---
name: agent-cookbooks
description: "Worked agent patterns from Anthropic's cookbook: a code-reviewer agent, research lead and subagent prompts, and a cookbook-audit skill that grades a prompt. Use when writing or reviewing an agent prompt, a reviewer, or a research pipeline."
license: MIT
metadata:
  estate-category: agent-runtime
  estate-upstream: anthropics/claude-cookbooks
---

# Anthropic's agent cookbook -- prompts, review and research patterns

Worked patterns for building agents: a code-reviewer agent, a research lead and subagent pair, and a cookbook audit that grades a prompt against a style guide.

## When to use this

When the thing being built is an agent: a reviewer, a research pipeline, a router, a
voice surface. These are worked examples, not advice.

## How to use it

1. `upstream/agents/code-reviewer.md` - a reviewer agent, written out.
2. `upstream/skills/cookbook-audit/SKILL.md` and `upstream/skills/cookbook-audit/style_guide.md` - grade a prompt against a guide.
3. `upstream/patterns/agents/prompts/research_lead_agent.md` - the lead that plans a research run.
4. `upstream/patterns/agents/prompts/research_subagent.md` - the subagent that does the reading.

The estate's own `research` pack governs what a research claim needs; this pack is how
the agents that do the reading are written.

## Estate rules that bind this pack

- **Proof, not assertion.** A claim about this skill's effect is a command and its output.
- **One of each layer.** If the estate already owns the capability, use it; a pack never
  becomes a second copy of a layer.
- **Voice first.** A surface the founder cannot speak to and watch live is not finished.
- **The claim is the contract.** Work lands only against a live claim (AGENTS.md 5).

<!-- provenance:begin -->
## Upstream material

Vendored verbatim from `anthropics/claude-cookbooks` at commit `a162e0184e71b60290808a43961a6cbc8060123c`
(MIT, 53718 stars at 2026-10-24T08:02:55+00:00). See `NOTICE.md`.

The upstream ships these under `.claude/`; the estate refuses a harness
folder in the tree, so the bytes live under a plain path. `NOTICE.md`
names the upstream path for every file.

- `upstream/LICENSE`
- `upstream/agents/code-reviewer.md`
- `upstream/patterns/agents/prompts/research_lead_agent.md`
- `upstream/patterns/agents/prompts/research_subagent.md`
- `upstream/skills/cookbook-audit/SKILL.md`
- `upstream/skills/cookbook-audit/style_guide.md`

<!-- provenance:end -->
