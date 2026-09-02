# 2026-09-01. The Demo Standard: Machine-rendered demos, one surface, a live sandbox

Founder, 2026-09-01: "we need demo infrastructure not claude code — our own standardised demo
needs to be elite. research the web, we have a lot to demo to investors and buyers" (verbatim:
claude-estate docs/founder/, branch founder-docs-visual-demos). Build word: his "ok" on
[the demo standard plan](https://github.com/chidionyema/crew/issues/805), 2026-09-01. Research record with all sources:
crew docs/research-engine/2026-09-01-demo-infrastructure.md (branch research/demo-infrastructure).

## The standard, three tiers, zero recurring cost

1. **A demo is code.** A CLI feature carries a VHS `.tape` file in `demos/`; a UI feature carries
   a Playwright demo spec. CI renders the tape to `docs/demos/*.gif` on every relevant push
   (`.github/workflows/demo-render.yml`) and commits the result — a demo can never show what the
   software no longer does, because the machines re-record it from the real binary.
2. **One surface.** The feature's `docs/demo/<name>.md` page embeds the rendered file and states
   the command a buyer can run himself; Backstage TechDocs serves it; the picture-evidence rule
   pins the release.
3. **The buyer clicks the real thing.** A 60-minute expiring vCluster sandbox (the next wave of [the demo standard plan](https://github.com/chidionyema/crew/issues/805)) —
   the HashiCorp Terraform Sandbox shape, never a simulated click-through.

Rejected, from the research: the entire demo-simulation SaaS category (Arcade, Navattic,
Storylane, Supademo, Walnut, Reprise, Demostack, Saleo, Guideflow, Floik) — a facsimile an
adversarial buyer engineer unpicks in one sitting, at prices that break the estate ceiling;
asciinema (a recording, not a script — drifts silently); Okteto (per-environment pricing).

## Optimised

Naive: five build-test cycles (record, workflow, docs, gate, backfill), ~10 round trips.
Applied: batch-write decision + tape + workflow + docs in one pass, one commit, one push; the
first render happens in CI on that same push, so the proof needs no local toolchain and the
founder Mac is never touched. Gate extension and backfill are wave 2, after the first green render.
