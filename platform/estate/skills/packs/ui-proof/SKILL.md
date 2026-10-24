---
name: ui-proof
description: "Playwright's own agent skills: driving a page, the trace system guide, triaging a failing test, reading test results, and the Playwright CLI. Use when a surface changed and the only honest proof is the page itself."
license: Apache-2.0
metadata:
  estate-category: verification
  estate-upstream: microsoft/playwright
---

# Playwright skills -- drive the real page, read the trace, prove the fix

Proving a UI change on the real page: drive it with Playwright, read the trace, triage a failure, and read the test results - so a UI claim is a screenshot or a trace, never a description.

## When to use this

After any change to a surface the founder can see: the proof is the page, not a
description of the page.

## How to use it

1. `upstream/.claude/skills/playwright-dev/SKILL.md` - drive the page.
2. `.../playwright-dev/trace_system_guide.md` - read the trace when it goes wrong.
3. `.../playwright-triage/SKILL.md` and `triage.md` - triage a failing run.
4. `.../playwright-test-results/SKILL.md` - read the results an artefact.
5. `.../playwright-cli/SKILL.md` - the CLI an agent drives.

The estate's `ui.review` grades token purity; this pack produces the artefact the
grade is about.

## Estate rules that bind this pack

- **Proof, not assertion.** A claim about this skill's effect is a command and its output.
- **One of each layer.** If the estate already owns the capability, use it; a pack never
  becomes a second copy of a layer.
- **Voice first.** A surface the founder cannot speak to and watch live is not finished.
- **The claim is the contract.** Work lands only against a live claim (AGENTS.md 5).

<!-- provenance:begin -->
## Upstream material

Vendored verbatim from `microsoft/playwright` at commit `b4695e3eb2e6736d1a7b1fd255c4e94f78553660`
(Apache-2.0, 98399 stars at 2026-10-24T08:04:55+00:00). See `NOTICE.md`.

The upstream ships these under `.claude/`; the estate refuses a harness
folder in the tree, so the bytes live under a plain path. `NOTICE.md`
names the upstream path for every file.

- `upstream/LICENSE`
- `upstream/packages/playwright-core/src/tools/skills/playwright-cli/SKILL.md`
- `upstream/skills/playwright-dev/SKILL.md`
- `upstream/skills/playwright-dev/trace_system_guide.md`
- `upstream/skills/playwright-test-results/SKILL.md`
- `upstream/skills/playwright-triage/SKILL.md`
- `upstream/skills/playwright-triage/triage.md`

<!-- provenance:end -->
