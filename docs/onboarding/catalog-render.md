# Onboarding: catalog-render

What it is: the scheduled job that keeps `docs/architecture/live.md` current on main. It is
`com.estate.catalog-render` in `scheduler/schedule.yml`, wired `after: com.estate.inventory`,
so it runs each time the inventory does (four times a day) and never on a stale inventory.

What it does, in order: fetch origin/main, move the detached worktree at `../.idp-state`
(override with `IDP_STATE_WORKTREE`) to it, run `bin/catalog-gen` and `bin/estate-diagram`,
and if the page changed, commit it, push `state/live-diagram`, open the pull request once, and
switch auto-merge on. GitHub merges it when the required checks pass.

How to read it: the scheduler UI shows the run; the open PR on `state/live-diagram` shows a
render waiting on checks; `git log -- docs/architecture/live.md` on main shows every render
that landed, each with the inventory timestamp in its subject.

Exit codes: 0 on its way or unchanged, 1 with the failing step named, 3 BLIND when
`~/.estate/state/inventory.json` is missing.

Spec: `features/gates/estate_gates.feature`, scenario "The live architecture page reaches main
on a schedule, through a pull request".
