# The Reports page

The founder asked for every report to be produced by the estate, on a clock, and shown on one page in the portal. This feature adds that page at `/reports`. Two reports ship with it: **Flux: what is applied** (every 15 minutes, from the cluster receipt: every Kustomization and HelmRelease with its state and the revision Flux last applied, suspended rows shown as their own state) and **Delivery: right first time** (once a day, from GitHub: how many merged pull requests were green on the first push and how many runs on main passed at the first attempt).

Each tile shows when the report was produced and how often it is written. A report older than twice its schedule turns red. A report whose source could not be read says so instead of showing an empty table.

## See it work

Open the portal and go to Reports (also linked from the Tools page as "Reports: what the estate wrote for you"). Pick a tile; the report draws below it, with a link to the file itself.

Produce a report by hand and read it without the portal:

    gh workflow run estate-state.yml
    curl -s https://raw.githubusercontent.com/chidionyema/idp/state/live-diagram/docs/reports/index.json | jq .

Produce the Flux report locally from any cluster receipt:

    bin/idp-reports-render flux-state --cluster-receipt receipt.txt --out-dir /tmp/reports

## Where the pieces live

- Writer: `bin/idp-reports-render` (one markdown file plus a meta fragment per report).
- Clocks: `.github/workflows/estate-state.yml` (Flux report, job `publish-reports`) and `.github/workflows/estate-inventory.yml` (delivery report, job `publish-to-state-branch`).
- Store: `docs/reports/` on the `state/live-diagram` branch; `bin/catalog-render` carries it when it re-renders the branch.
- Page: `backstage/packages/app/src/modules/home/Reports.tsx`, registered in `homeModule.tsx`, listed as `founder-reports` in `backstage/founder/catalog-info.yaml`.
