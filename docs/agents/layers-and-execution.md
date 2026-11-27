<!-- estate:routed-from AGENTS.md -- current law, not history. It is loaded on demand through the AGENTS.md route table instead of at Turn 1 (idp#8636). Moved verbatim. -->

## 6. One of each layer. A second copy is stitching and gets deleted.

The platform is `idp`. Products run on it. Exactly one of each: routing, traces, identity, secrets,
scheduling, catalog, execution boundary, evidence, verification, memory. A product is never deleted
for living outside `idp`; a duplicate layer always is.

**Before building anything, prove it does not already exist** — `growmos query "<what you want to
build>"`, then read the candidate. The estate has built the same capability five to ten times. Do
not make it eleven.

**But raising the bar supersedes do-not-duplicate (founder's ruling, 2026-10-26).** A new layer is
allowed when it RAISES the bar, and then the lesser implementation is merged into it or deleted in
the same change. The bar is raised when the new thing adds something the old one cannot do, and
says so: a store where the old one had none, an invariant where the old one had a convention, a
query contract an agent can use where the old one could only be read by a human, a falsifier where
the old one could not fail. Two implementations of the same layer, one of which is measurably
better, is a stitch - and a stitch is deleted in the same change, not left to rot.

Worked example, 2026-10-26: `bin/estate-discover` (a view that read the estate's maps and answered
on demand) was replaced by `bin/capability-index` (one store, one writer per plane, five
falsifiable invariants, a query contract over CLI and MCP, a committed machine-generated snapshot
CI proves drift-free). The view's census became the registry's writers; the view was deleted in
the same change. The rule is not "never build a second thing" - it is "never leave two".

---

## 7. Execution — intents only

Every action the agent performs goes through an **intent YAML** in `~/.estate/intents/`.

```
~/.estate/              # NOT a git repo — lives outside version control
  bin/estate-execute    # executor binary
  intents/*.yaml        # 24 intents: shell.parse, git.branch, ci.run, etc.
  libexec/*.sh, *.py    # helpers: shell-suggest.py, shell-verify.py, etc.

~/Documents/code/idp/mcp/plugins/estate_mcp.py   # MCP plugin (3 tools only)
  estate_list   — list all available intents
  estate_show   — show args for one intent
  estate_invoke — run an intent
```

**Rule: if an action is not a YAML intent, the agent cannot perform it.**

`estate_executor.py` (13 raw tools) is deleted. `estate_simulate.py` is deleted.
Only `estate_mcp.py` remains — it wraps the intent executor.

To add a new capability: write `~/.estate/intents/<name>.yaml`, commit to idp.
To invoke: `estate_invoke { intent: <name> }` via MCP, or `estate-execute <name>` directly.

Design spec: `docs/specs/2026-09-24-estate-agent-enforcement-platform.md`

**The estate's one skill layer.** The twelve UI/design/research/architecture capabilities
the founder named live once, in `platform/estate/skills/`, and they reach an agent through
four intents: `skill.list` (what exists, where it came from, where it is installed),
`skill.verify` (the checksums and the front doors), `skill.install` (put a pack in a
runtime's skills directory), `skill.vendor` (re-fetch a pack's upstream at its pinned
commit). Do not fetch a skill from the network and do not copy one into a runtime by hand —
that is a second copy of a layer the estate already owns (§6). Run
`estate-execute skill.list` first, then
`estate-execute skill.install pack=<id> runtime=<pi|claude|codex|agents> apply=true`.
Spec: `docs/specs/2026-10-23-estate-skill-layer.md`.

**Lost work: `estate-execute work-audit` (days=28).** Before saying work is done, missing or
"never landed", run it. For every closed-unmerged PR, stash, local-only branch and uncommitted
worktree it measures how many added lines are on origin/main now, or were and got deleted:
LOST / PARTIAL / REMOVED / LANDED, plus unticked checkpoints in open issues. Full result:
`~/.estate/work-audit/latest.json`. Source: `platform/estate/libexec/work-audit.py`.

