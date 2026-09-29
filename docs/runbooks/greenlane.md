# Runbook: the Greenlane

Founder, 2026-09-29: "I need mathematical guarantees PRs can't fail on this platform", "main
must never go red, never", "a PR that can fail should never be allowed to be raised", "prove it
with minimum 500 concurrent lanes", "radically change our work practices".

## What holds, and why

The lane is a gated trunk: Rust's bors (2013, the "not rocket science rule": automatically
maintain a repository that always passes all tests), Uber's SubmitQueue ([Keeping master green
at scale](https://dl.acm.org/doi/10.1145/3302424.3303970), EuroSys 2019), GitHub's merge queue
(refused on this user-owned repository: `422 Invalid rule 'merge_queue'`). One engine,
`greenlane/engine.py`, is the only thing that moves main:

1. Agents push work to `lane/<name>` (the intent `lane-submit`; `flux/image-updates` is the
   controller's lane). Nobody raises a pull request. Nobody pushes main.
2. The engine stacks pending lanes onto the current main into one candidate commit (squash per
   lane), pushes it to `queue/<batch>`, and waits for the six required checks on that exact sha.
3. Green: one pull request per lane is raised by the App, born with its proof, and main is
   fast-forwarded to the tested commit -- the same bytes. GitHub marks the pull requests merged.
   Red: the batch is bisected until the red lane stands alone; it is re-tested twice (flaky
   checks), then carries the reason on its head's `greenlane` commit status. Its branch stays.
4. A pull request raised by hand is closed with a comment, its branch kept and made a lane.

Two rulesets make it hold on GitHub, not in prose: `idp-main-writer` (only the estate App may
update main; nobody else, admins included) and `required-checks-main` (the sha main moves to
must carry the six checks). GitHub itself refuses a push that violates either.

Proof: `features/gates/greenlane.feature`, bound by `sovereign/tests/bdd/test_greenlane.py`,
runs the real engine through the estate's chaos at 500 lanes (stale worktrees, broken commits,
incompatible pairs, rebase conflicts, re-pushes, deletions, hand-raised pull requests, direct
pushes, a bot lane, one-way flaky checks). Assertions are zero, not thresholds: main never red,
zero direct pushes succeed, every hand-raised pull request refused, no open pull request after the
platform handled the event, no work lost, every green lane lands, the engine survives a restart
between every tick. The one assumption: a check never passes on a broken tree.

## Reading the lane

- /fleet, "The lane (main never red)": main green?, open pull requests, candidate, every lane.
- `bin/idp-greenlane status` prints the same JSON.
- The verdict on your own lane: `gh api repos/chidionyema/idp/commits/<sha>/status` -- the
  `greenlane` context reads `pending` (testing in b<N>), `success` (landed) or `failure` (reason).

## Arming it (once, the founder)

1. `bin/idp-github-app app-id` prints the estate App's numeric id; put it in
   `platform/github/ruleset.idp.main-writer.json` in place of `"${GITHUB_APP_ID}"`.
2. `bin/repo-rulesets --apply` creates `idp-main-writer` and aligns `required-checks-main`.
3. Delete the old lane: `.github/workflows/{merge-when-green,pr-age,pr-cap,pr-consolidate,
   agent-trunk-batch,deploy-when-green,image-update-pr}.yml`, `bin/idp-pr-age`,
   `bin/idp-max-open-prs-gate`, `bin/idp-pr-landable` and their tests. Each of them either
   grades pull requests after they exist or merges with the App's token; both are now refused
   by construction, and a second lane is stitching.

## When something is wrong

- A lane sits `pending` for more than 90 minutes: a required check never reported on the
  candidate. Compare `gh api repos/chidionyema/idp/commits/<candidate>/check-runs` with the six
  contexts in `ruleset.idp.required-checks.json`; a renamed job is the usual cause.
- Main is red: it cannot be, by the rulesets. If /fleet says so, someone bypassed the App's
  ruleset; `bin/repo-rulesets` shows the drift.
- To pause landings: disable the `greenlane` workflow. Lanes queue; nothing is lost.
