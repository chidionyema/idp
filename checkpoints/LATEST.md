## RESUME HERE

**2026-09-07 20:25Z, idp-1a.** Live pipeline risk, mid-investigation.

**What just landed.** #2357 (kyverno batching: offline-gate 451s -> 152s, and the
`if: github.event_name != 'pull_request'` line deleted so it runs pre-merge) and #2376
(comment-only correction to `platform/jit/rbac.yaml`'s false header). Both merged 20:11.
Then I added `offline-gate` to main's required checks, ruleset 21473806. Backup of the
prior ruleset: `<session scratchpad>/ruleset-21473806.before.json`. STAGED, 60 min,
telegram message_id=40355.

**The risk I am chasing.** Bot image-bump PRs auto-merge with SQUASH and arrive about
every five minutes (20 of the last 40 merged PRs). PR #2381, opened 20:11:30, is red on
`bdd` and `bdd-suites (acceptance)` — the failing step is "acceptance suite (strict on
PRs to main)". Strict mode applies only on PRs, which is why main's own push runs at
20:11 and 20:12 are both green and the breakage is invisible there. The previous bot PR
#2377 passed acceptance at 20:06, so whatever this is started between 20:06 and 20:11 —
the window my two merges landed in.

**Why this is urgent rather than merely red.** `offline-gate` is now a required check.
If bot PRs are also red on bdd, the image-bump pipeline jams: auto-merge blocks and the
PRs pile up.

**Next step, and it is the one I was running when I stopped:** worktree at
`<scratchpad>/wt-red` on origin/main, find the acceptance suite's command in
`.github/workflows/`, run it locally with the PR-strict env (`SB_BDD_STRICT`, set from
the base branch in `.github/workflows/ci.yml`; enforced in
`sovereign/tests/bdd/conftest.py`) and read the actual failure. Do NOT assume it is
mine — #2377 also shows `offline-gate fail 7m31s`, which predates the ruleset change and
may be a separate, older breakage on bot PRs specifically.

**If it is mine and not fixable in minutes:** remove `offline-gate` from ruleset 21473806
first (restore from the backup json), then debug. Unjamming the pipeline outranks keeping
the gate on.
