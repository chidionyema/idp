# The estate has one skill layer, and every agent reaches it through an intent

Date: 2026-10-23
Status: adopted (in the tree, behind the estate's green gate)

## The request

The founder asked for the twelve UI, design, research and architecture capabilities to reach
**every** estate agent — not as a wiki page, not as a link, but as something an agent can
actually use when it needs the capability.

## Why the obvious answer was refused

The obvious answer is: let each runtime install what it likes. `claude` gets a skills
directory, `codex` gets a skills directory, `pi` gets a skills directory, and each agent pulls
what it needs from wherever it finds it.

That answer is what the estate has done before, and it is why the estate has the same capability
five to ten times. AGENTS.md §6 says it plainly: **one of each layer**. A per-runtime install
is a copy of the layer, and a copy of the layer is stitching, and stitching gets deleted — after
it has already been depended on by three agents.

It also fails the estate's own laws before it fails on taste:

- **§7 (intents only).** An agent that installs a skill by hand has an action no intent
  describes, so no audit trail, no gate, no receipt. The founder cannot see it on /fleet and
  cannot refuse it.
- **§3 (proof, not assertion).** "I installed the skill" is a claim. "The pack's files hash to
  what the registry says, and the pack is installed in pi, claude, codex and agents" is a
  measurement.
- **§4 (secrets by name).** A skill pack fetched from a URL at install time is an unreviewed
  code path with a network fetch in it, on a machine that holds the estate's keys.

## What was decided

**The packs live in idp, once, and the only way to put one in front of an agent is the
installer.**

1. **One copy, in the platform.** `platform/estate/skills/` holds one directory per pack:
   fourteen of them — the founder's twelve vendored upstream capabilities, plus two
   estate-native ones (`estate-research`, `estate-architecture`) because no upstream was named
   for them. Every file is pinned by sha256 in `registry.json`, and every upstream is pinned by
   commit, licence and a star count measured on the day it was taken.

2. **One door, and it is an intent.** Four intents — `skill.list`, `skill.verify`,
   `skill.install`, `skill.vendor` — and one tool, `platform/estate/libexec/skill-packs.py`.
   No new tool was added to `estate_mcp.py`; §7's law that only the intent executor remains
   holds.

3. **One allowlist of destinations.** A pack may only be written into
   `~/.pi/agent/skills`, `~/.claude/skills`, `~/.codex/skills` or `~/.agents/skills`. The
   installer has no `--dest`: there is no way to point it somewhere the estate does not manage.

4. **The packs are governed material, not a download.** The vendored bytes are in the
   repository, with the upstream licence and a NOTICE.md beside them. The front door of each
   pack is estate-authored: it carries the estate's rules (tokens not literals, voice first,
   proof, performance budgets) and points at `ui.review` and `ui.scaffold`, so the capability
   lands on `packages/estate-ui-kit` instead of growing a parallel design system.

5. **The packs answer to the estate's design gates.** A pack can tell an agent what good
   design is; it cannot make a screen good. `ui.review` and `ui.scaffold` still decide, and a
   pack that contradicts them is wrong.

## What this costs, stated honestly

- **The estate now carries 1.4MB of vendored third-party material** in the repository, and a
  licence obligation to keep the NOTICE files beside it. That is the price of not making every
  agent fetch from the network at install time.
- **A pack is a snapshot.** When upstream moves, the estate's copy is stale until someone runs
  `skill.vendor` and reviews the diff. That is the point of pinning; it is also a cost.
- **Updating a pack is now a review, not a pull.** A hand edit in a runtime's skills directory
  is refused by the next install, so a runtime-local tweak has to be made in `idp` and landed
  through the lane. This is a deliberate narrowing of where the estate's design knowledge can
  live.

## The alternative that was rejected

Keep the packs upstream-only and give agents a URL. Rejected: it puts an unreviewed network
fetch in every agent's start path, it makes the estate's capability set depend on a third
party's uptime, and it makes "what can this agent do?" unanswerable from the estate's own
records.

## How to read the layer

- `platform/estate/skills/registry.json` — the contract: every pack, every file's sha256,
  every upstream's commit and licence.
- `platform/estate/skills/sources.json` — where each vendored file came from.
- `docs/specs/2026-10-23-estate-skill-layer.md` — the architecture, the intents, the adoption
  path, and what to do when a pack drifts.
