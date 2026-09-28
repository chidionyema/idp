# Adding a report to the Reports page

A report is a markdown file written on a clock by a workflow, plus a one-line meta fragment. The portal's Reports page (`/reports`) lists whatever the index on the state branch names; the page itself never changes when a report is added.

## Steps

1. Add a subcommand to `bin/idp-reports-render` that writes `<id>.md` and `<id>.meta.json` through the shared `write()` helper. The fragment needs `id`, `title`, `file` (`docs/reports/<id>.md`), `generated_at` (UTC), `schedule_minutes` and a one-sentence `summary`. When the source cannot be read, write that into the report body and set `"blind": true`; never write an empty table.
2. Call it from the workflow that already runs on the report's clock (`estate-state.yml` every 15 minutes, `estate-inventory.yml` once a day). Add the files to that workflow's artifact so its publish job copies them to `docs/reports/` on `state/live-diagram` and folds the fragment into `docs/reports/index.json`. Copy the existing `for frag in ...` loop; do not add a second index.
3. Push the branch and wait for the workflow to run once. Then read the index:

       curl -s https://raw.githubusercontent.com/chidionyema/idp/state/live-diagram/docs/reports/index.json | jq '.reports[].id'

4. Open `/reports` in the portal. The new tile is there, dated. If it is red at once, the schedule in the fragment does not match the clock the workflow actually runs on.

Do not add a new scheduler, a new store or a new branch for a report; the three above are the only writers of `docs/reports/`.
