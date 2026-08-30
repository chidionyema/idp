# Documentation policy

Founder question, 2026-08-28: "our policy on documentation across the platform and estate, the
standards and future-proofing we agreed, and how documents are managed across the estate."
This page is that policy. The decision behind it is [ADR 0002](../../decisions/0002-documentation-is-code-and-the-portal-renders-it.md);
this page says what a person does, what a gate refuses, and where each repository stands.
Counts below were measured on 2026-08-28 with the commands shown.

## 1. The policy in one paragraph

Every document lives in the repository of the thing it describes, changes through a pull
request like code, follows one structure (Diátaxis), records decisions in one shape (MADR), and
is read in one place: the Backstage portal, which renders each repository's `docs/` with
TechDocs. There is no wiki, no Notion, no second site, and no document that only a laptop holds.

## 2. The four standards

| Standard | What it fixes | The rule |
|---|---|---|
| Diátaxis structure | Readers cannot tell a tutorial from a reference | Four directories only: `docs/tutorials/`, `docs/how-to/`, `docs/reference/`, `docs/explanation/`. A page that fits none of them does not go in `docs/`. |
| MADR decision records | Decisions live in chat and get re-argued | `docs/decisions/NNNN-title.md`, one decision per file, status PROPOSED until the founder accepts (R16). Every row of `crew/docs/STANDARDS.md` cites its ADR. |
| Docs-as-code through TechDocs | Documents drift from the code they describe | `mkdocs.yml` at the repository root, `backstage.io/techdocs-ref: dir:.` on the catalog entity, the portal builds it. A doc is published when its PR merges, not when someone uploads it. |
| C4 diagrams from one model | Diagrams are drawn once and never again | `architecture/workspace.dsl` is the model; `architecture/render` writes the Mermaid views into `docs/explanation/architecture/`. Hand-drawn diagrams are not committed. |

## 3. How a document is managed

1. **Write it beside the code**, in the repository's `docs/`, in the Diátaxis directory that
   matches its job. Name how-tos `<verb>-<thing>.md`.
2. **Put it in the nav.** `mkdocs.yml` lists every page; a page not in the nav is a page the
   portal never shows.
3. **Open a pull request.** The docs build is a CI rung: `mkdocs build --strict` (idp
   `bin/idp-ci` rung 8c, `.github/workflows/ci.yml:40`). A broken link or a page outside the
   nav fails the build, and the PR does not merge.
4. **A feature ships with its docs** (LAW 32): the PR carries a reference page and a how-to with a
   `Demo:` line; `crew/scripts/pr-evidence.py check` refuses a PR body without them (DoD rows 4
   and 5 in `crew/docs/STANDARDS.md`).
5. **Read it in Backstage.** TechDocs renders the merged `docs/` under
   `/docs/default/component/<repo>/`. Cross-repository links use that path, never a GitHub blob
   URL (see the crew audit link in `idp/mkdocs.yml`).
6. **Retire it by pull request too.** Moving a page into a Diátaxis directory keeps its history
   (`git mv`); deleting a page removes its nav line in the same PR so the strict build stays green.

## 4. Where each repository stands

| Repository | `docs/*.md` | `mkdocs.yml` | In the portal | Diátaxis |
|---|---|---|---|---|
| idp (platform) | 165, 151 of them in the four directories or decisions | yes | yes, `/docs/default/component/idp/` | swept (idp#647) |
| crew (the board and the laws) | 82 | yes | yes, `/docs/default/component/crew/` | swept (crew#605) |
| hermes-v2 (product) | 9 | no — to onboard, crew#194 | no | not yet |
| prospector (product) | 164 | no — to onboard, crew#194 | no | not yet |

Measured with `git ls-files 'docs/*.md' | wc -l` and `ls mkdocs.yml` in each checkout. A
product is onboarded to the portal, never re-homed into it (platform is not product): it gets a
`mkdocs.yml`, a catalog entity with `techdocs-ref`, and its `docs/` swept into the four
directories. crew#194 tracks the two products.

## 5. Future-proofing: what keeps this portable

- **Plain Markdown in git.** Every page renders on GitHub, in MkDocs, in any static generator.
  Nothing is stored in a vendor's database. Leaving Backstage costs a nav file, not a migration.
- **Mermaid, not images.** Diagrams are text, diffable, and rendered by GitHub and TechDocs with
  nothing installed. The C4 model is Structurizr DSL, an open format with several renderers.
- **MADR is a folder of files.** Tooling (`adr-tools`, `log4brains`) is optional; the format
  survives without it.
- **Every standard is the mainstream choice** (Diátaxis: Canonical, Python; TechDocs: Backstage's
  own docs; MADR: the `adr` GitHub organisation). Each was chosen after the alternatives were
  rejected in ADR 0002, so the next person does not re-run the argument.
- **The strict build is the guard.** A document that would rot silently fails a PR instead.

## 6. What is not covered here

Generated pages (`SHOWCASE.md`, `FOUNDER.md`, `NEXT.md`, `CONSCIENCE.md`) are written by
`bin/` scripts from live data and committed; they follow this policy's delivery rule and are
exempt from the Diátaxis directory rule because a script, not a person, places them.
