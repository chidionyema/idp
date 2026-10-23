# The estate skill layer — architecture, contract and adoption

Governed by `docs/decisions/2026-10-23-the-estate-has-one-skill-layer.md`.

One layer, one copy, one door. This spec says where the bytes live, what the registry
guarantees, which intents an agent calls, where a pack may be installed, and what to do when
something drifts.

---

## 1. The shape

```
platform/estate/skills/
  registry.json            the contract: every pack, every file's sha256, every upstream
  sources.json             where each vendored file came from (repo, branch, include globs)
  packs/<id>/
    SKILL.md               the front door: estate-authored, Agent Skills standard
    NOTICE.md              provenance: repo, commit, licence, measured stars, what was taken
    upstream/…             the vendored upstream material, with its LICENSE beside it
```

`platform/estate/libexec/skill-packs.py` is the only tool that touches this tree.
`platform/estate/intents/skill.{list,verify,install,vendor}.yaml` are the only doors.

```
agent ──estate_invoke──▶ skill.list / skill.verify / skill.install / skill.vendor
                              │
                              ▼
                    skill-packs.py ──verify──▶ registry.json (sha256)
                              │
                              ▼
     ~/.pi/agent/skills   ~/.claude/skills   ~/.codex/skills   ~/.agents/skills
     (the only four destinations)
```

## 2. The packs

Fourteen. The founder's twelve, vendored from upstream and pinned; two, estate-native.

| id | category | upstream | licence |
|----|----------|----------|---------|
| `ui-ux-pro-max` | design | nextlevelbuilder/ui-ux-pro-max-skill | MIT |
| `awesome-design-md` | design | VoltAgent/awesome-design-md | MIT |
| `open-design` | design | nexu-io/open-design | Apache-2.0 |
| `taste` | design | Leonxlnx/taste-skill | MIT |
| `impeccable` | design | pbakaus/impeccable | Apache-2.0 |
| `react-bits` | ui | DavidHDev/react-bits | upstream file (NOASSERTION) |
| `emil-design-skills` | design | emilkowalski/skills | MIT |
| `hallmark` | design | Nutlope/hallmark | MIT |
| `design-md` | design | google-labs-code/design.md | Apache-2.0 |
| `gsap-skills` | ui | greensock/gsap-skills | MIT |
| `scroll-world` | ui | oso95/scroll-world | MIT |
| `canvas-ui` | ui | DavidHDev/canvas-ui | upstream file (NOASSERTION) |
| `estate-research` | research | — estate-native | — |
| `estate-architecture` | architecture | — estate-native | — |

The star count and the commit are in the registry, measured on the day of the take. A pack
whose licence GitHub cannot detect says `NOASSERTION` and carries the upstream licence file;
the estate never claims a licence it did not read.

**What is vendored is markdown, not data.** A skill is instructions an agent reads. Font
metrics, site indexes and other data blobs stay upstream: a file over 64KB is refused, and
the `include` globs in `sources.json` name only the markdown.

**The front door is estate-authored.** Each `SKILL.md` is written by the estate, not copied:
it says when to use the pack, how to use it, and which estate rules bind it — tokens not
literals, voice first, proof, performance budgets — and it names `ui.review` and `ui.scaffold`
as the gates that decide. The upstream material is the *method*; the front door is the *law*.

**The front door has to load, and that is measured, not assumed.** A description is written as
a quoted YAML scalar, always. A plain scalar cannot contain `": "` — a YAML parser reads the
colon as a nested mapping and refuses the *whole* frontmatter, so the runtime never offers
the skill to an agent. This was not theoretical: on 2026-10-23, pi's own loader discovered
4 of the estate's 14 packs and refused the other 10 with "Nested mappings are not allowed in
compact mappings", while every checksum said the packs were intact. `skill-packs.py verify`
now parses each front door's frontmatter the way the runtimes do and refuses a pack a
runtime would ignore; the test suite parses YAML rather than matching a regex.

## 3. The registry contract

`registry.json` records, per pack:

- `files` — every file under `packs/<id>/` with its sha256, as a list of
  `{"path": ..., "sha256": ...}` objects. A file on disk that is not listed is drift; a listed
  file that is missing is drift; a listed file whose bytes changed is drift. The digests are
  objects and not a `{path: sha256}` map because gitleaks' `generic-api-key` rule reads
  `"<path>": "<64 hex>"` as a credential whenever the path contains a word like `token` — and the
  design packs' own upstream file names do (`semantic-tokens.md`, `token-architecture.md`). The map
  form made `security-scan` red on every lane that carried the registry. The old map form is
  still read, so a registry written before this change verifies instead of reporting every file
  missing.
- `tree_sha256` — one hash over the sorted (path, sha256) pairs: the pack's identity, copied
  into the install receipt.
- `upstream` — repo, branch, pinned commit, licence, measured stars, and the list of paths
  taken.

`skill-packs.py verify` recomputes all of it and exits non-zero on any drift. A gate that
cannot fail is not a gate; this one fails on a single edited byte.

`verify` does two things, and both can fail:

1. **Checksums.** Every file under `packs/<id>/` is hashed and compared with the registry.
2. **The front door.** The frontmatter is parsed as YAML and must yield `name` equal to the
   pack id and a non-empty `description` string of at most 1024 characters. A pack that a
   runtime would ignore is refused.

**Re-pinning is a narrow door.** `skill-packs.py manifest` rewrites the registry's checksums
from what is on disk, and it may only re-pin the estate-authored front door and `NOTICE.md`.
Upstream bytes are re-pinned by `skill.vendor`, which fetched them from the pinned commit: a
hand edit to vendored upstream is not a new version of the upstream, it is a fork, and the
registry refuses to bless it.

## 4. The intents

| intent | what it does | when an agent calls it |
|--------|--------------|------------------------|
| `skill.list` | names every pack, its category, its upstream, and where it is installed | "what design capability do I have?" |
| `skill.verify` | recomputes every checksum; non-zero on drift | before trusting a pack, and in the gate |
| `skill.install` | verifies, then writes the pack into one of the four runtime roots | "give me this capability" |
| `skill.vendor` | re-fetches a pack's upstream at its pinned commit and rewrites the provenance | a pack is behind upstream |

Arguments are strings; an empty value means "no filter", so an intent can always pass its
flags. `install` is a dry run unless `apply=true`. `install` refuses a pack that does not
match the registry, a runtime outside the allowlist, and an existing install without
`force=true`.

```bash
estate-execute skill.list category=design
estate-execute skill.verify
estate-execute skill.install pack=taste runtime=pi          # dry run
estate-execute skill.install pack=taste runtime=pi apply=true
```

## 5. Adoption — how a runtime gets the packs

The packs are staged onto the laptop by the estate's own convergence, not by hand:

- `bin/estate-runtime-sync` copies `platform/estate/skills` into `~/.estate/skills` (and
  `platform/estate/libexec/skill-packs.py` into `~/.estate/libexec`) whenever main moves.
- `platform/estate/bin/estate-converge` links `~/.estate/skills` into the current release
  alongside `intents` and `libexec`, so a root-owned release carries the packs with it.

Then, once per runtime:

```bash
estate-execute skill.install pack=all runtime=pi apply=true
estate-execute skill.install pack=all runtime=claude apply=true
estate-execute skill.install pack=all runtime=codex apply=true
estate-execute skill.install pack=all runtime=agents apply=true
```

Each install writes a receipt at `~/.estate/skills-state/<runtime>/<pack>.json` naming the
pack, the tree hash and the upstream commit it came from. `skill.list` reads those receipts,
so "what can this agent see?" is answerable from the estate's own records.

**The proof that a runtime can see them.** An install is not an adoption until the runtime
itself lists the packs. pi's own loader is callable without a model:

```bash
PI=$(npm root -g)/@earendil-works/pi-coding-agent/dist/index.js
node -e "import('$PI').then(m => { const r = m.loadSkills({cwd: process.cwd(),
  agentDir: process.env.HOME + '/.pi/agent', skillPaths: [], includeDefaults: true});
  console.log('discovered', r.skills.length, 'diagnostics', r.diagnostics.length);
  console.log(r.skills.map(s => s.name).join(' ')); })"
```

On 2026-10-23 that printed 14 of 14 with no diagnostics, from `~/.pi/agent/skills`. The
same frontmatter is what Claude Code reads from `~/.claude/skills`.

The four roots are the Agent Skills standard: `<skills-dir>/<name>/SKILL.md` with YAML
frontmatter (`name`, `description`).

**One pack, one root.** pi reads two of them — `~/.pi/agent/skills` and `~/.agents/skills` — so
installing the same pack in both makes pi warn about a name collision (the bytes are identical
and the first found wins, so nothing breaks, but the signal is noise). Install a pack into the
root of the tool that will use it, and use `~/.agents/skills` only for a tool that has no root
of its own. The estate's own adoption installs into `pi`, `claude` and `codex`, and leaves
`~/.agents/skills` for the shared case.

## 6. When something drifts

1. `estate-execute skill.verify` — it names the pack and the file.
2. If the drift is an upstream move: `estate-execute skill.vendor pack=<id> apply=true`, then
   review the diff and land it like any other change. The registry's new checksums are part
   of that diff.
3. If the drift is a hand edit in a runtime's skills directory: the runtime copy is not the
   source of truth. Re-install with `force=true`, and if the edit was worth keeping, make it
   in `platform/estate/skills/packs/<id>/` and land it.
4. If a pack is broken and must not be in front of an agent: remove it from the runtime root
   and note it. The layer is a convenience; the estate's gates (`ui.review`, `ui.scaffold`)
   are what decide quality.

## 7. What this layer is not

- It is not a design system. `packages/estate-ui-kit` is; the packs teach agents to use it.
- It is not a place to put secrets, keys or a client's private material.
- It is not a second copy of a capability the estate already owns: if a pack's subject is
  already in `idp`, the pack is deleted, not merged.
- It is not a bypass of the claim gate: every change here still needs a claim and lands
  through the lane.
