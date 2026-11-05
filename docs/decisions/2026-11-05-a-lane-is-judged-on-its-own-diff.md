# A lane is judged on its own diff -- the scope limiter names its base

**Date:** 2026-11-05 - **Issue:** #7710 - **Claim:** `estate-agent/idp#7710`

## The measurement

Every Greenlane batch was red and nothing landed. The lane brief said it plainly:

```
{"landing": null, "loud": true, "main_red": [], "red": [{"lane": "lane/HEAD", "owner": "agent",
 "why": "ci-success failure https://github.com/chidionyema/idp/actions/runs/41944852174/job/126975799782"}],
 "stuck": [], "summary": "nothing landing. 1 red, first HEAD, owner agent.", "waiting": 0, "work_lost": 0}
```

Run `41944852174`, job `ui-kit` (`126974522682`), push event, `2026-11-05T00:55:05Z`, head
`d24cfeb6d`. Its sibling jobs on the same sha were green: `guarded-paths`, `portal-app`,
`no-harness-folders`, `factory-ci`. One job was red, and it was red on a lane whose diff was
**two documentation files**.

Reproduced locally on a clean `origin/main` worktree (`78242c450`):

```
$ node packages/estate-ui-kit/guards/kit-import.mjs ; echo "EXIT=$?"
REFUSE backstage/packages/app: src/styles.css does not import @estate/ui-kit (deadline 2026-10-31 passed)
REFUSE web: app/globals.css does not import @estate/ui-kit (deadline 2026-10-31 passed)
EXIT=1
```

Two front ends that never migrated to the kit refused a **docs** lane.

## The cause

The ui-kit job asks one question -- *did this change touch a front end?* -- and answered it
with a scope limiter written into the workflow:

```yaml
base="${{ github.event.pull_request.base.sha || github.event.before }}"
case "$base" in ''|0000000000000000000000000000000000000000) echo "yes=true" >> "$GITHUB_OUTPUT"; exit 0;; esac
```

The Greenlane pushes each candidate as a **fresh** `refs/heads/queue/<batch>` branch. That is
a create-push, so `github.event.before` is forty zeros on **every** candidate. The limiter's
answer to *I cannot name the base* was *judge everything*. The kit-import guard then ran
over the whole tree, and the whole tree contains two unmigrated front ends.

So the gate was not wrong about the front ends -- it was wrong about the **diff**. A limiter
that cannot name its base judges everything; that is fail-closed, and it is right for a gate
that must not be skipped. It is only acceptable when the base *can* be named.

## The estate had already decided this

The correct rule was written down three times, and never applied to the job that needed it:

| Where | What it says |
|---|---|
| `greenlane/github.py` `push_candidate` | "Delete the ref first: the create-push then has before=zeros and the verifier grades origin/main...HEAD, the same grade a fresh branch would get." |
| `.github/workflows/verifier.yml` | "Queue pushes always grade against main, like a fresh branch would." |
| `.github/workflows/portal-app.yml` | "A candidate is built on main, so main is its base." |

And the precedent for grading a candidate on its diff was already shipped: `ee3dd3a01` -- *"ci:
grade a Greenlane candidate on its diff -- offline-gate swept all 62 platform dirs every batch
(idp#6604)"* -- with its falsifier `tests/test_queue_candidate_is_graded_on_its_diff.py`.

`f92dd99fb` (*"kit: the ratchet judges a lane against main, not against a snapshot
(#7063)"*) changed the path list of the ui-kit job but left the zero-base degenerate in
place. **The class was not closed; it was moved.**

## The decision

**One script names the base. Every workflow asks it.**

- `bin/idp-ci-base` -- names the ref a change is measured from, per event shape. Exit 0 with
  the base, exit 2 with `BLIND`.
- `bin/idp-ci-touched` -- asks *did this change touch these paths* against that base, and
  answers `yes=true` / `yes=false` to stdout and to `$GITHUB_OUTPUT`.

The rule, in order:

1. a `merge_group` grades against the merge queue's base sha;
2. a `pull_request` grades against its target (the base sha, else `origin/<base_ref>`);
3. a Greenlane candidate (`refs/heads/queue/*`) grades against `origin/main` -- it *is* main
   plus its lanes;
4. a push grades against the range it moved (`github.event.before`);
5. a first push to any other branch grades against `origin/main` -- a fresh branch grades
   like a pull request from the same branch would;
6. otherwise: **BLIND**.

Two properties that are not negotiable:

- **Fail closed.** If no base can be named, the answer is `yes=true` -- the gate runs. A
  gate that cannot judge must not pass (AGENTS.md section 9, R1). This is what the old limiter
  did *by accident*, and it is kept deliberately now, for the cases where it is the only
  honest answer.
- **The base must exist in the checkout.** `git rev-parse --verify <base>^{commit}` before
  the diff. A force-pushed `before` or a shallow clone falls through to the next rule rather
  than producing an empty diff that reads as "nothing changed".

**Not changed:** `.github/workflows/ci.yml`'s `ESTATE_DEPS_BASE`, `build-multiarch.yml`'s
main-push-only discover job, and `estate-dag-gen.yml` (already `bin/estate-dag-changed
--base`) are already correct and are left alone.

## What this does not fix

`web` and `backstage/packages/app` still do not import `@estate/ui-kit`, and
`packages/estate-ui-kit/brands/meridian.json` is still missing. The deadline (`2026-10-31`)
has passed. That is **separate debt**: a lane that really does touch `web/` will still be
refused by the kit guard -- correctly, because that lane touches an unmigrated front end. The
scope limiter stops the *unrelated* lanes from being judged on it. Migrating those front ends
is its own work, with its own claim.

## The falsifier

`tests/test_ci_scope_base.py` is two-sided on purpose:

- **known-bad** -- a candidate that *does* touch `web/` is still judged (`yes=true`). The fix
  points the gate at the right diff; it does not switch it off. A gate that cannot fail is
  not a gate.
- **known-good** -- a candidate that touches nothing under the paths is not judged by that
  gate (`yes=false`).
- **fail-closed** -- no base, or a base that is the head, or a diff that cannot be taken ->
  `yes=true`. Never `yes=false`.
- **the sweep** -- no workflow may keep an inline `000...0 -> yes=true` limiter, and every
  workflow that limits a scope must go through `bin/idp-ci-base` / `bin/idp-ci-touched`.

## Consequence

The fix lands in its own batch. The batch's checkout contains the new `ci.yml`, so the fixed
limiter applies to that very batch: its diff is docs-and-scripts only, the ui-kit job is
skipped, and the batch is green. When main moves, the RED `lane/HEAD` batch is re-evaluated
against the new main (`greenlane/engine.py`: a RED lane returns to PENDING when main moves),
re-tested on a diff that no longer contains the front ends, and lands.
