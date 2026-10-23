---
name: estate-research
description: "Research inside the estate: the harvest intent for capability, search-text and explore for the corpus, the knowledge graph for what is already known, and the rule that a claim needs a source."
license: see NOTICE.md
metadata:
  estate-category: research
  estate-upstream: estate-native
---

# Estate research -- how an agent finds out

Research inside the estate: the harvest intent for capability, search-text and explore for the corpus, the knowledge graph for what is already known, and the rule that a claim needs a source.

## When to use this

When a task needs facts the agent does not hold. The estate's own research
capability, and the rule that a claim carries its source.

## How to use it

1. **Does it already exist?** `growmos query "<what you want to build>"` and read the
   candidate before building anything. The estate has built this five to ten times.
2. **Capability:** `estate_invoke` the `harv` intent to harvest a verified capability
   with signed evidence, or `search-text` to search the corpus.
3. **Corpus and the estate's own record:** `explore` for the code, `ci.status` and
   `work-audit` for what actually happened, and the knowledge graph for what is
   already known about the subject.
4. **State on the record:** a GitHub issue is the claim of record; a ticket with no
   evidence is an opinion.
5. **A claim without a source is not a finding.** Name the command, its output and
   where it ran. A blocker is reported with the intent that was run and the line it
   printed.

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
