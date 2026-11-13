# ADR addendum: the Backstage *source* is not the Backstage *download*

> **Correction, same day.** An earlier draft of this addendum claimed the app was "estate code
> wearing Backstage's build tooling", on a measurement of the ROOT `package.json`, which carries
> only 4 `@backstage/*` entries. That measurement was wrong: it read one workspace file and
> generalised. Measured properly, `packages/app/package.json` and `packages/backend/package.json`
> each carry **32** `@backstage/*` dependencies, and the app source imports them **181 times**
> (`frontend-plugin-api` 63, `catalog-model` 23, `frontend-test-utils` 13, `ui` 12,
> `plugin-catalog-react` 11, `core-components` 11, `plugin-kubernetes` 10, ...). This is a real
> Backstage app, not a lookalike. The correction is kept here rather than silently edited away,
> because a record that quietly deletes its own errors teaches nobody.
>
> What survives the correction: the app has a caller (Genesis, `/fleet`) and its tracked source
> costs 2 MB. The download had no caller and cost 2.4 GB. The distinction holds; the reason given
> for it was partially wrong and is now fixed.

**Status:** accepted (frozen)
**Date:** 2026-11-12
**Amends:** `2026-11-12-backstage-is-frozen-history.md`
**Decider:** machine — the measurements below decide it, not a judgement. Issue #8000.

## Why this addendum exists

On 2026-11-12 the decision was taken to delete the 2.4 GB Backstage **install** and refuse it
coming back. The same day the founder asked for the **tracked source** to be purged on the same
reasoning ("not even being used in genesis").

Before deleting 505 tracked files plus their pipeline, the reasoning was measured. It does not
hold. This addendum records the measurements so nobody repeats the mistake of treating one
Backstage (a download nobody imported) as the other (the platform Genesis itself runs on).

## The measurement

| what | claimed | measured | how |
|---|---|---|---|
| Backstage is unused | "not even being used in genesis" | **Genesis lives inside it** | PR #7987 `[LEGION] INS-00011 Genesis mothership` — every file under `backstage/plugins/fleetview-backend/` |
| Genesis is a separate repo | implied | **no `genesis` repo exists**; no `~/genesis`, no `~/.genesis` | `ls -d */`, `ls -d ~/.genesis` → absent |
| it is one directory | implied | **741 files outside `backstage/` reference it** | `git grep -l backstage -- ':!backstage' ':!*.md'` |
| nothing depends on it | implied | **13 CI workflows** build, deploy or verify it | `git grep -l backstage -- .github/workflows` |
| it is a stray download | "using up space" | **`backstage/node_modules` is 0 MB and git-excluded**; the 2.4 GB was `~/.estate/frontend`, already deleted | `du -sm`, `git check-ignore -v` |
| nobody works on it | implied | **PR #7891 merged 2026-11-11** (yesterday) — a dependency bump in `backstage/` | `gh pr list --state merged --search "backstage in:title"` |
| the surface is a side project | implied | `clusters/oke/backstage.yaml` header: *"the founder's /fleet surface"* | read verbatim |

`/fleet` is not currently serving — `fleet.mumchimp.com` answers `http_status=000` and no
`fleetview` process runs locally. That is an outage, not a retirement: the Flux application and
the 23 cluster objects it reconciles are live configuration, and `/fleet` is the primary work
surface AGENTS.md §3 requires operational work to be visible on.

## Decision

1. **The install stays deleted and stays refused.** `bin/backstage-refused` is unchanged by this
   addendum — no 2.4 GB download returns to any machine.
2. **The tracked source stays.** Deleting it would delete the Genesis platform
   (`backstage/plugins/fleetview-backend/`), the `/fleet` surface, and red thirteen CI workflows in
   one move. That is not a purge; it is taking the board offline to save space it does not occupy
   (`node_modules` = 0 MB).
3. **If `/fleet` should be retired, that is a different decision with a different record.** It
   needs its own claim, its own blast-radius list (741 referencing files, 13 workflows, 23 cluster
   objects), a migration of the Genesis workers that live inside it, and a Flux removal that
   leaves no orphaned objects. This addendum explicitly declines to perform it silently.
4. **The lesson is refined, not replaced.** The rule was "do not install a layer until a real
   caller imports it." The refinement from this measurement: **cost and caller are separate
   questions.** The install had no caller *and* cost 2.4 GB — delete it. The source has a caller
   (Genesis, `/fleet`) *and* costs 2 MB tracked — keep it. Measuring only one of the two questions
   gives the wrong answer in both directions.

5. **Derived artifacts are the third thing, and they were the 214 MB.** `packages/app/dist`
   (144 MB) and `packages/app/node_modules` (70 MB) are untracked, git-ignored, and rebuilt by
   `RUN yarn build:all` in `backstage/Dockerfile:84`. They were deleted on 2026-11-12: free space
   4,140 MB -> 4,361 MB, and `git status --porcelain backstage/` printed **0** lines, so nothing
   tracked was touched. This is the class the founder's "separate it from what isn't used" points
   at: not the source, not the framework, but the build output and the downloads.

## Falsifier

`tests/test_backstage_source_is_not_the_download.py` proves the distinction cannot quietly collapse:

- the tracked source is present, and `backstage/plugins/fleetview-backend/` exists — so a future
  agent deleting "Backstage" wholesale fails here instead of in production;
- `backstage/node_modules` is not tracked — so the disk cost cannot creep back through a commit;
- the install is still refused by the door — so the deletion is not undone by the same confusion;
- the `/fleet` Flux application is still declared — so the surface is not silently dropped.

## Consequence

The founder keeps the 2.4 GB. The Genesis platform, the `/fleet` surface and the CI that ships them
all stay. The reason is written down with its numbers, so the next agent does not re-litigate it
from memory — which is exactly what this record was for.
