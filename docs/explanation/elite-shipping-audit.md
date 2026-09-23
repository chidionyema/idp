# Where the estate ships like the elite teams, and where it is still backward

Date: 2026-09-02. Ordered by the founder the same morning the dagster upgrade wedged;
his record is the file `2026-09-02T1114Z-fixing-the-vale-error-from-the-bare-run-0f48afb1.md`
in the founder-docs archive. The pattern he named: the burden of proof moves off the
agent's laptop and onto the platform — write the declarative change, push at once,
and let the pipeline prove it in an environment that behaves like production.

Every verdict below carries its receipt. Nothing here is built yet: the moves at the
end are proposals and wait for his word.

## The scorecard

| # | Practice | Verdict | Receipt |
|---|----------|---------|---------|
| 1 | Push first: no heavy local suites | PARTLY | the pre-push hook already dropped the test rung (a 13-file diff once ran 1,628 tests for 33 minutes; removed 2026-08-31), but it still runs the offline policy judge, which can run past a minute on platform changes |
| 2 | Ephemeral per-change environments | MISSING | no throwaway cluster anywhere in `.github/workflows/`; policies are judged offline, blind to namespace labels — the gate printed a clean pass on the exact Deployment the live cluster refused ([the run that caught it](https://github.com/chidionyema/idp/actions/runs/33618879684)) |
| 3 | Merge queue with auto-rebase | HALF | `ci.yml` answers the `merge_group` trigger and `platform/github/ruleset.idp.merge-queue.json` sits in git, but the live repository rules do not include it — written, never armed |
| 4 | Auto-land on green | MOSTLY | auto-merge and branch-delete-on-merge are on; the founder-only release gate stays by his own standing order, so the human step there is policy, not backwardness |
| 5 | Event-driven readiness over a dependency graph | BACKWARD | 51 `dependsOn` rows under `clusters/oke/`; one unready secret store held about thirty Kustomizations red this morning; ten workloads already use wait-and-retry init containers, so the better pattern exists here and simply is not the rule |
| 6 | Fast pipeline | OK | a green `ci.yml` run takes about five minutes; the fast gate answers in under thirty seconds |
| 7 | Trunk-based, short-lived branches | OK | trunk-only is a standing ruling and merged branches are deleted by the repository itself |
| 8 | Progressive delivery | MISSING | no canary or staged-rollout controller anywhere in `platform/` or `clusters/`; every change lands everywhere at once and the only rollback is a revert |
| 9 | Deploys graded by live measurement | PARTLY | the verification plane measures surfaces (`docs/explanation/verification-plane.md`), but nothing automatically halts or reverses a rollout when the measurements turn bad |
| 10 | No silent verdicts | BACKWARD | two incidents this week where absent checks read like passing ones: a bot commit carrying a skip directive silenced every check on a pull request, and bot-pushed workflow runs sat unstarted awaiting approval while the pull request looked merely slow |

## The three findings that cost the most this week

**The offline judge is a green that cannot fail.** The admission policies select
namespaces by label; the offline judge knows no labels, so those rules silently skip.
Re-run with the labels supplied, nineteen platform directories fail the availability
standard today — merged, live, and unproven. An ephemeral throwaway cluster per
change (practice 2) makes this class impossible: the real admission controller says
no before merge, exactly as production would.

**The dependency graph amplifies every failure.** One stalled secret store turned
into thirty red rows because readiness is expressed as a build order instead of as
each workload waiting for what it actually needs. The init-container pattern already
used by ten workloads lets the pipeline finish instantly and the pods wake when
their dependencies arrive. One edge added this week (secrets waiting on
certificates, `docs/explanation/sdk-server-certificate-deadlock.md`) is
load-bearing and survives any diet; most of the other fifty rows are candidates.

**A missing verdict must be a red verdict.** The skip-directive wedge and the
held-for-approval runs are one class: the pull request shows no failure because
nothing ran. The required-checks rule already names the checks; the gap is that
"expected, never reported" ages into a quiet forever instead of a loud refusal.

## The smallest moves, in order of return

1. Arm the merge-queue rule that already exists in git (one apply of the recorded
   ruleset; the pipeline already answers the trigger).
2. A throwaway cluster job for platform changes: boot a small disposable cluster in
   the pipeline, install the estate's policies, apply the rendered change, and let
   real admission judge it. Retires the offline judge's blind spot for good; the
   namespace-labels patch to the offline judge (proven locally, held on a branch)
   is the stopgap until then.
3. The dependency diet: convert `dependsOn` rows to init-container readiness
   workload by workload, keeping only the load-bearing edges.
4. A "no silent verdict" rung: a scheduled check that turns any pull request whose
   required checks have reported nothing for ten minutes into a loud failure.
5. Progressive delivery stays on the list but last: it needs a controller choice
   (a build-or-buy decision) and his word first.
