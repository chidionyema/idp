# The estate skill catalogue

Every agent in this estate gets the same skills, from the same governed source, in
every runtime. This is the catalogue: what exists, where it came from (measured, not
claimed), and which piece of estate work each pack is for.

The packs live in `platform/estate/skills/`; the front door of each pack is its
`SKILL.md` (the estate-authored page) and its `upstream/` tree (the capability,
vendored verbatim at a pinned commit). `registry.json` is the checksum of record:
`skill-packs.py verify` recomputes every sha256 against the disk and fails if one
does not match.

## How an agent gets a skill

```
skill.list                      # every pack, its category and its one line
skill.list --pack <id>         # one pack: its upstream, licence, where it is installed
skill.install --pack <id> --apply  # install into every runtime's skills dir
skill.verify                    # recompute the checksums
```

The brief is the front door itself: `platform/estate/skills/packs/<id>/SKILL.md` is the
page that says when to use the pack, how to use it, and the estate rules that bind it.
`skill.list --pack <id>` names that pack, its upstream and the runtimes it is already
installed into.

Install target is the Agent Skills standard (`agentskills.io`):
`<runtime>/skills/<pack>/SKILL.md`, in `~/.claude/skills`, `~/.pi/agent/skills`,
`~/.codex/skills` and the shared `~/.agents/skills`.

## The two sets, and how they are charged daily

1. **The UI set** -- the design packs and the surface primitives: the categories
   `design` and `ui`. Used whenever a surface changes: the tokens
   come from `packages/estate-ui-kit`, and `ui.review` grades purity against them.
   A design pack is named in the plan's `skills` field, and the plan's `done_check`
   runs `ui.review` on the changed files.
2. **The principal set** -- the engineering set: plan, spec, test, review, delegate.
   These are charged by the delegate plan itself: a plan that names no senior pack
   is refused by `delegate-build` before a builder is spawned, because the founder
   asked for staff-level judgement to be applied, not simulated.

The daily ritual is one line in every plan:

```json
"skills": ["superpowers", "estate-architecture", "ui-proof"],
"staff_bar": {
  "design_note": "the decision and the alternative rejected",
  "blast_radius": "what else this touches, by path",
  "rollback": "how it is undone",
  "observability": "the log line that proves it live",
  "simplification": "what was left out"
}
```

A plan that is reusable is reusable *as a template*: `platform/estate/templates/
delegate-plan.json` is the filled-in skeleton, and a plan that names a pack has to
name one that exists (`skill.list` is the authority). A plan is resilient because
every step carries `done_check` -- a command that exits 0 -- so a run can be resumed
by running the checks, not by re-reading the conversation.

## The packs

| Pack | Category | Upstream | Licence | Stars | Commit |
|-----|----------|----------|---------|-------|--------|
| `agent-cookbooks` | agent-runtime | anthropics/claude-cookbooks | MIT | 53718 | `a162e0184e71` |
| `awesome-design-md` | architecture | VoltAgent/awesome-design-md | MIT | 123108 | `3b605329240c` |
| `design-md` | architecture | google-labs-code/design.md | Apache-2.0 | 28498 | `6e5da5382f41` |
| `estate-architecture` | architecture | estate-native | n/a | - | `-` |
| `hallmark` | design | Nutlope/hallmark | MIT | 31159 | `7ec868225c6c` |
| `impeccable` | design | pbakaus/impeccable | Apache-2.0 | 85322 | `5cb95eea9c96` |
| `open-design` | design | nexu-io/open-design | Apache-2.0 | 103540 | `e03d5c23f308` |
| `taste` | design | Leonxlnx/taste-skill | MIT | 101484 | `6010f91a9935` |
| `ui-ux-pro-max` | design | nextlevelbuilder/ui-ux-pro-max-skill | MIT | 139301 | `d14efff8ed1f` |
| `spec-driven` | engineering | github/spec-kit | MIT | 142637 | `67e0f7294e6e` |
| `superpowers` | engineering | obra/superpowers | MIT | 304366 | `2ce8aa15d05b` |
| `k8s-hardening` | infrastructure | kubernetes/website | CC-BY-4.0 | 5410 | `bf999f018443` |
| `estate-research` | research | estate-native | n/a | - | `-` |
| `security-engineering` | security | wshobson/agents | MIT | 41619 | `0874a27b17a2` |
| `canvas-ui` | ui | DavidHDev/canvas-ui | NOASSERTION | 5070 | `a04a99b23529` |
| `emil-design-skills` | ui | emilkowalski/skills | MIT | 48955 | `2d228630ba14` |
| `gsap-skills` | ui | greensock/gsap-skills | MIT | 16981 | `aed9cfd32777` |
| `react-bits` | ui | DavidHDev/react-bits | NOASSERTION | 50059 | `e12c22192ac7` |
| `scroll-world` | ui | oso95/scroll-world | MIT | 10386 | `71cc36d3bb15` |
| `evaluation-rubrics` | verification | wshobson/agents | MIT | 41619 | `0874a27b17a2` |
| `ui-proof` | verification | microsoft/playwright | Apache-2.0 | 98399 | `b4695e3eb2e6` |

Measured at vendor time (`stars_measured_at` in `registry.json`). A pack whose
upstream licence is not a recognised open licence is not vendored: the front door
distils the method instead. That is why BMAD's method and Anthropic's per-skill
licences are absent from the table and their capability is covered by
`superpowers`, `spec-driven` and `estate-architecture`.

## Which pack for which piece of work

### design -- UI and brand: tokens, components, banners, motion, canvas

- **`hallmark`** -- The anatomy of a good page: macrostructures, layout, type, flow, interaction states, and the gates a design must pass before it ships.
- **`impeccable`** -- A craft floor for an agent: audit, critique, refine and document a design, with the bar written down before the work starts.
- **`open-design`** -- The working skills of a design workspace: brand kit, design brief, creative direction, review, colour, copy.
- **`taste`** -- Critique a screen the way a designer does, against a reference library of real work, with the tells named.
- **`ui-ux-pro-max`** -- Turn a request into a token-backed design system: primitive and semantic tokens, a component spec, a brand kit, and a banner that matches the brand.

### ui -- The surface primitives: canvas, motion, components, worlds

- **`canvas-ui`** -- Canvas/WebGL UI primitives for interfaces that cannot be DOM: 3D scenes, shaders, and interactive canvases inside a product.
- **`emil-design-skills`** -- Design-engineering craft: animation vocabulary and performance, native-feeling mobile UI, Apple design language, and the breaking-the-template-look rules.
- **`gsap-skills`** -- GSAP used correctly: core tweens and timelines, ScrollTrigger, plugins, React integration, and the performance rules that keep it smooth.
- **`react-bits`** -- Pick and adapt animated React components (text, backgrounds, buttons, containers) instead of writing a bespoke animation from scratch.
- **`scroll-world`** -- Turn a brand into a scroll-scrubbed 3D world landing page, with the scrub engine and the prompts that produce it.

### engineering -- How the estate builds: plan first, test first, spec first, subagent-driven

- **`spec-driven`** -- GitHub's spec-driven method: a specification template, a plan template, a task breakdown, a checklist generator and the commands that drive them, so an agent works from an agreed spec instead of an impression.
- **`superpowers`** -- The staff engineer's daily loop, as skills: brainstorm the approach, write the plan, execute it in steps, drive it with tests, and review the result before it is called done.

### agent-runtime -- How agents are written: prompts, reviewers, research pipelines, skills

- **`agent-cookbooks`** -- Worked patterns for building agents: a code-reviewer agent, a research lead and subagent pair, and a cookbook audit that grades a prompt against a style guide.

### research -- Finding out: what exists, what the world thinks, what is true

- **`estate-research`** -- Research inside the estate: the harvest intent for capability, search-text and explore for the corpus, the knowledge graph for what is already known, and the rule that a claim needs a source.

### architecture -- What it should be: layers, boundaries, one-of-each

- **`awesome-design-md`** -- Read and write DESIGN.md: the file that states a brand's colours, type, spacing, motion and components so an agent builds the brand instead of a generic page.
- **`design-md`** -- The DESIGN.md specification itself, with worked examples and the linter that checks one, so a brand spec is a checkable artifact rather than prose.
- **`estate-architecture`** -- Architecture inside the estate: one of each layer, a spec before the build, a decision record for every fork, and the gates that prove the shape is right.

### verification -- Whether it works: rubrics, traces, the real page

- **`evaluation-rubrics`** -- How to grade an agent or a model against a rubric, how to write that rubric, and what to do when the score is wrong: the methodology, the rubric reference and the score-improvement loop.
- **`ui-proof`** -- Proving a UI change on the real page: drive it with Playwright, read the trace, triage a failure, and read the test results - so a UI claim is a screenshot or a trace, never a description.

### security -- The trust boundary: threats, requirements, controls

- **`security-engineering`** -- Threat modelling as a repeatable craft: attack trees, STRIDE analysis, security requirements extracted from the design, SAST configuration, and a mitigation map that ties each threat to its control.

### infrastructure -- Where it runs: the cluster, the node, the workload

- **`k8s-hardening`** -- The upstream Kubernetes security checklist and pod security standards: the baseline the estate's cluster is held to, so an agent reviews a manifest against the standard rather than against memory.

## The estate's own two packs

`estate-research` and `estate-architecture` are estate-native: they carry no upstream
text, only the estate's own rules (what a research claim needs, what an architecture
decision must state). They are the two packs an agent must read before it goes
looking for anything, because they are the two that stop it reinventing.

## Governance

- One source of truth: `platform/estate/skills/`. A pack is added by vendoring an
  upstream at a pinned commit, never by copying text into a runtime.
- The checksum is the record: `skill-packs.py verify` fails when the disk and the
  registry disagree, and `skill.install` refuses to install a pack that fails it.
- The licence travels with the bytes: each pack carries `NOTICE.md` with the
  upstream repo, commit, licence and measured stars, and the upstream `LICENSE`.
- The estate rules travel with the front door: every pack's `SKILL.md` ends with the
  rules that bind it (proof not assertion, one of each layer, voice first, the claim
  is the contract).
