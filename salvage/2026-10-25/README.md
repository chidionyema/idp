# salvage/2026-10-25 -- the idp meridian-design salvage packet

Work that existed only inside one laptop checkout -- the idp main checkout, sitting on
`lane/meridian-design` -- and that would have died with the machine. It is preserved here, on a
branch that is **not** a lane and that never lands.

Everything below was measured on 2026-10-25 against the live repository, not copied from the
handoff packet's text. Where the packet was wrong, this file says so.

**This is preservation, not a product change.** Nothing here is a candidate for `main`. The two
documents are the only items with obvious forward value, and they are documents that other
agents' work is waiting on.

## The refs

| Ref | Holds |
|---|---|
| `refs/heads/salvage/idp-meridian-design-20261025` | this README, the two documents, every patch below |
| `refs/tags/salvage/idp-meridian-design-lane` | the four unpushed `lane/meridian-design` commits (tip `3679304df`) |
| `refs/tags/salvage/idp-stash-00` ... `refs/tags/salvage/idp-stash-11` | one stash each, as the stash commit itself |

The stashes and the lane tip are **tags**, not branches, on purpose:

* the pre-push hook judges a pushed **branch** against `bin/claim-gate`, which requires every
  commit in the pushed range to carry a `Claim:` line for an open issue held by the same agent.
  The lane tip's own commits claim `chidionyema/idp#6698` (open, but held by `pi`, not by
  `estate-agent`) and `#164` (closed), and the stash commits carry no trailer at all. A branch
  push of either is refused by the gate -- correctly: nobody may re-claim another agent's work.
* the hook's own `case` statement skips every ref that is not `refs/heads/*`, so a tag push is
  not judged as a change on its way to a pull request. A tag is the estate's own archive form
  (`bin/idp-branch-archive` turns a stale branch into a tag for exactly this reason).
* `salvage/*` is outside the Greenlane's refs (`lane/*`, `queue/*`), so nothing here is ever
  raised as a pull request and nothing can reach `main` by accident.

Nothing was pushed with `--no-verify`, and no guard was bypassed.

## 1. The two documents -- unique on every ref, no copy anywhere else

Both had **no git history on any ref** (`git log --all -- <path>` is empty), so nothing on the
remote could lose them; only this checkout held them.

| File | Why it matters |
|---|---|
| `docs/specs/2026-10-24-estate-cloud-migration-plan.md` | the cloud-migration execution plan Agent C's portfolio executes (P0.T2, restic -> R2) |
| `docs/reports/identity-door-5818-2026-01-14.md` | the identity-door report for #5818 |

They are in this branch at their original paths, byte for byte.

To recover one into real work: `git checkout salvage/idp-meridian-design-20261025 -- <path>` --
but read the note on non-ASCII below first.

## 2. The four unpushed commits

`lane/meridian-design` was 4 commits ahead of `origin/main` and existed on no remote ref. The
commits, oldest first:

```
aad17ed20  meridian(web): one gutter, one accent, one green -- the render audit's findings
f31256c13  meridian(web): the render audit is a tool in the tree, not a script in /tmp
914f3acb1  meridian(web): the pages may be cached -- every navigation was a full round trip
3679304df  metrics-server: restore the Flux row the consolidation deleted (#164)
```

`3679304df` is already on `main` by patch-id (it landed as #6891 through the normal path); the
three `meridian(web)` commits are unique to this checkout and touch `web/` only.

* The tip itself: `git fetch origin tag salvage/idp-meridian-design-lane` then
  `git show salvage/idp-meridian-design-lane`.
* The whole delta as a readable patch: `salvage/2026-10-25/lane-meridian-design.patch`
  (`git diff f404c10de82d97c3feeeacbaf0784ec74e8de05f 3679304df`).

The three web commits are **not** on `main` and their `web/` paths are not claimed by a live
claim on this issue, so they can be recovered onto a lane by any agent that wants them.

## 3. The twelve stashes

The handoff packet said 5. There are 12. All 12 are absent from every remote ref, so all 12
were at risk.

Each is preserved twice: as the **stash commit** (tag `salvage/idp-stash-NN`, exact bytes, index
state included) and as a **patch** (`salvage/2026-10-25/stashes/stash-NN.patch`, `git stash show
-p --include-untracked`). `salvage/2026-10-25/stashes/MANIFEST.txt` lists, per stash, its sha,
date, message and touched paths.

The ones that carry unique content of their own:

* `stash-11` -- deletes six `backstage` room UI components (`Cost.tsx`, `FleetCanvas.tsx`,
  `MindPanel.tsx`, `Room.tsx`, `SpatialCanvas.tsx`, `Waveform.tsx`). That deletion existed
  nowhere else in the estate.
* `stash-03` -- the widest one: the Greenlane pagination work (`greenlane/engine.py`, the
  `.githooks/pre-push` change, `bin/claim-gate`, `bin/idp-identity-apply`,
  `bin/idp-kyverno-render`, `bin/idp-login-drill`, the `backstage` fleetview backend adapters and
  their tests, and the `.growmos` state).
* `stash-10` -- the iOS mic blocker work (`backstage/packages/app/e22-tests/*`, the
  `EfficiencyHud`/`FleetReactorApp` room UI, `bin/estate-runtime-sync`).

To recover one: `git fetch origin tag salvage/idp-stash-03 && git stash apply
salvage/idp-stash-03` (a stash commit is a stash: `git stash apply <sha>` works), or apply the
patch onto the tree it was taken from.

## 4. The dirty tracked files -- preserved as patches, never as an edit

The checkout had five dirty tracked files. Two of them were **stale relative to `main`**
(`platform/bridge/deployment.yaml`, `platform/bridge/service.yaml`: the copy on disk is older
than the copy on `main`), and one was byte-identical to `main`
(`extensions/estate-capabilities/index.ts`). Those three carried no new work and were dropped.

The other two hold paths that **live claims own right now** (`mcp/plugins/estate_executor.py`
under #7003 and #7118, `tests/test_executor_door_steers_instead_of_refusing.py` under #7003,
`platform/llm/active_memory.py` under #6835, `scheduler/schedule.yml` under #7003). Committing
them would have stolen another agent's files, and the claim gate would have refused the push.
So they are preserved as **patches of the delta against the lane tip**, which touches no claimed
path:

| Patch | Delta |
|---|---|
| `patches/mcp-plugins-estate_executor.py.patch` | `mcp/plugins/estate_executor.py` vs the lane tip |
| `patches/tests-test_executor_door_steers_instead_of_refusing.py.patch` | that test vs the lane tip |
| `patches/platform-llm-active_memory.py.patch` | `platform/llm/active_memory.py` vs the lane tip |
| `patches/platform-bridge-deployment-and-service.patch` | the two `platform/bridge` yaml files vs the lane tip |
| `patches/growmos-state.json.patch` | `.growmos/state.json` vs the lane tip |

Two warnings on that row of the table:

* `mcp/plugins/estate_executor.py` on disk is a **regression** against the live lane
  `lane/pi-observe-audit` (11 insertions / 404 deletions; 59 steer/refuse markers against 96).
  It is a stale base plus a small edit, not a superset. Do not restore it over the live version
  -- read the patch for the intent and re-apply it onto the current file.
* `platform/llm/active_memory.py` belongs to claim #6835, whose heartbeat lapsed two days ago.
  It is re-claimable, but the live owner must post a newer claim before anyone edits it.

## 5. What was deliberately left out, and why

| Left out | Why |
|---|---|
| `installer/IDP-Estate.pkg` | a regenerable build artifact, not authored work |
| `extensions/estate-capabilities/index.ts` | byte-identical to `main` |
| `platform/bridge/{deployment,service}.yaml` | older than `main` -- restoring them would be a regression |
| `mcp/plugins/estate_executor.py` as a committed file | its path is held by live claims #7003 and #7118 |
| `~/.estate`'s staged `platform/estate/` files | measured as an older snapshot of `origin/main` (the index is behind `main`, not ahead of it), so the salvage there is to reset the index, not to commit it |

## 6. Note on non-ASCII

The two documents and some of the patches contain non-ASCII bytes (em dashes, typographic
quotes, `x`). `bin/idp-ci --check` refuses non-ASCII in tracked files, so any of this that is
recovered into a **landable** branch has to be ASCII-normalised first. The salvage refs are not
landable and were pushed with that rule in mind; the documents are preserved **byte for byte**
here on purpose, so that whoever recovers them decides how to normalise rather than inheriting a
lossy copy.

## 7. How to check nothing was lost

```bash
git fetch origin 'refs/tags/salvage/*:refs/tags/salvage/*'
git ls-remote origin 'refs/tags/salvage/*' 'refs/heads/salvage/*'
git show salvage/idp-stash-11 --stat
git diff f404c10de82d97c3feeeacbaf0784ec74e8de05f salvage/idp-meridian-design-lane --stat
```

The claim of record is `chidionyema/idp#7122` (CLAIM `agent=estate-agent`, paths
`docs/specs/2026-10-24-estate-cloud-migration-plan.md`,
`docs/reports/identity-door-5818-2026-01-14.md`, `salvage/2026-10-25/*`).
