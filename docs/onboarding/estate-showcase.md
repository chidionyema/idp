# Estate showcase — onboarding

**What it is for.** One page, `docs/SHOWCASE.md`, that grades every catalogue entity the way a
buyer's engineer would: ELITE, GAP or BLIND, gaps first. It is the continuous elite-grade review
(crew#474): nothing is graded once by hand; the grade is recomputed from the inventory every time
the catalogue is rendered.

**Where it lives.**

- Generator: `bin/estate-showcase` (idp). Reads `catalog/catalog-info.yaml`,
  `crew/docs/STANDARDS.md` and `crew/docs/science/SHOWCASE.md`.
- Schedule: Dagster job `com.estate.catalog-render`, after `com.estate.inventory`
  (cron `13 1,7,13,19 * * *`), via `bin/catalog-render`, which commits the page.
- Gate: `bin/idp-ci` runs `bin/estate-showcase --check`; a PR that changes the catalogue and
  leaves the page stale fails CI.
- Reading guide: `docs/how-to/read-the-estate-showcase.md`. Demo: `docs/demo/estate-showcase.md`.

**What it costs.** One Python process, under two seconds, four times a day, on the render host.
No model calls, no network.

**How to stop it.** Remove the `estate-showcase` step from `bin/catalog-render` and the
`--check` line from `bin/idp-ci` in one PR. The page then stops updating and CI stops
refusing drift; nothing else depends on it.

**Where the gaps go.** Every GAP row is a tracked item: red scheduled jobs are crew#478, dirty
checkouts are crew#479. A new GAP row without an issue is the defect.
