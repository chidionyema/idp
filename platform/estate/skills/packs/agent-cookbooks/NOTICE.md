# agent-cookbooks -- provenance

Upstream: anthropics/claude-cookbooks (branch main, commit `a162e0184e71b60290808a43961a6cbc8060123c`)
Licence: MIT
Stars at measurement: 53718 (measured 2026-10-24T08:02:55+00:00)

The files under `upstream/` are vendored verbatim from the upstream repository
at the commit named above, under that repository's licence. They are the
capability itself; the estate-authored `SKILL.md` next to them is the front door
that says when to use it and which estate rules bind it.

Vendored files:

- `upstream/LICENSE`
- `upstream/agents/code-reviewer.md`
- `upstream/patterns/agents/prompts/research_lead_agent.md`
- `upstream/patterns/agents/prompts/research_subagent.md`
- `upstream/skills/cookbook-audit/SKILL.md`
- `upstream/skills/cookbook-audit/style_guide.md`

Moved on the way in: the upstream path is kept here because the estate
refuses a harness folder in the tree, so `.claude/` was dropped from the
vendored path. The bytes are the upstream bytes.

- `.claude/agents/code-reviewer.md` -> `upstream/agents/code-reviewer.md`
- `.claude/skills/cookbook-audit/SKILL.md` -> `upstream/skills/cookbook-audit/SKILL.md`
- `.claude/skills/cookbook-audit/style_guide.md` -> `upstream/skills/cookbook-audit/style_guide.md`
