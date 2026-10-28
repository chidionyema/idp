# 0039 — The estate keeps its own continuity

- Status: accepted (founder ruling, 2026-10-28: "no automated continuity"; "reliance on founder
  memory is stupid for autonomous estate"; "if macbook dies now, all that work is in the abyss")
- Date: 2026-10-28
- Extends: §5 (claims and heartbeats), §2 (Greenlane), ADR 0037 (the fallback ladder), and LAW 34
  ("the checkpoint lives on the issue, not on the agent"). This ADR answers the question those do
  not: what happens to the work when the agent itself is gone.
- For: the headless agent. The founder's word: "for headless agent". A session started by the
  fleet plane has no human watching it, no memory of what it was doing, and no one to notice it
  died. It must not be able to lose work.

## Context

The estate knows how to keep a promise (Greenlane) and how to fail over (the ladder). It had no
answer for the third thing: an agent dies (out of tokens, a crash, a macOS stall) and its work
stays on one laptop.

Measured on 2026-10-28, on this machine:

- The census (`work-inflight`, the estate's own board) measured **233 work items**: 5 LIVE, 88
  RECOVERABLE, 140 LANDED, 0 DEAD, across **66 claims**.
- Most of the RECOVERABLE items were marked **"local only"**: their content existed on this
  machine and on no remote. Four stashes were local only. Three `preserve-plan` worktrees held
  commits reachable only from their own HEAD.
- Two lanes of mine were in the same state at the moment this was written: the imported-instruments
  lane had a commit and no push, and the capacity-convergence lane had six edited files and no
  commit at all.
- The reason nothing could be committed was the executor's disk floor: **414 MB free against a
  1500 MB floor**, so `estate_execute`, `estate_run_gate` and `estate_run_tests` refused every
  command with `the volume has 414 MB free, under this door's 1500 MB floor`. Every agent on the
  estate was unable to stage, commit, push or test at the same time. That is the void, measured:
  not a missing feature, a machine with no room to write.
- The census's own source (`platform/estate/libexec/work-inflight.py`) was **not in the repository**:
  it existed only in the runtime on this laptop. The estate's answer to "what is in flight" was
  itself only in flight on one machine.
- The census also mis-graded one case, which this ruling fixes: a worktree whose branch equals
  `origin/main` but which holds **uncommitted changes** was reported as LANDED, because "is this
  content on main" was asked of the branch, not of the worktree. Uncommitted work is not landed.

## Decision

**1. The estate knows its own state without a human.** The census runs on a schedule
(`ai.estate.continuity`, every 15 minutes), writes its ledger under
`~/.estate/results/work-inflight/`, and the ledger is the answer to "what is in flight". A human
asking is allowed; the answer exists whether or not anyone asks.

**2. Nothing lives only on a machine.** Every run, the rescue copies work that exists only in this
repository to origin, as a branch named `backup/preserve-<date>-<name>`: local branches that
origin does not hold, worktrees with uncommitted changes (captured through a temporary index, so
the owner's index, files and HEAD are never touched), and stashes. A dead laptop then loses
nothing that was not already on a remote.

**3. The headless agent's work is rescued first.** The census says which claim holds each item and
whether that claim's heartbeat is still fresh. Work held by a **lapsed** claim is the work of a
session that is gone, so it is rescued before unclaimed work, and unclaimed work before the work
of a session that is still alive (that session will land its own work). The rescue names the claim
in its report, so the founder can see whose work was at risk.

**4. The founder's memory is not a dependency.** Continuity is a job, not a habit. A session that
dies leaves a landed branch or a salvage branch, never a void.

**5. A branch is not a result.** The board separates LANDED (on `origin/main`) from RECOVERABLE
(content exists, not landed). A salvage branch is a rescue, not a delivery: the work still has to
be finished and landed through the Greenlane.

**6. BLIND is never clean.** If the census, the origin ref list or a push cannot be read, the
continuity run says BLIND and exits non-zero. A rescue that was not measured is not a rescue.

**7. The rescue never destroys.** It only adds branches under `backup/preserve-*`. It never pushes
to `main`, never force-pushes, never deletes a branch, ref, stash, worktree or file, and never
touches a branch origin already holds. A run that rescues nothing exits 0.

**8. Uncommitted work is not landed.** The census grades a worktree by its own content: dirty
files make it at risk whatever its branch says.

## Consequences

- `bin/idp-estate-continuity` is the job: census, then rescue, then one measured line in
  `~/.estate/continuity.log`, and a notification at most once an hour when work was rescued or the
  board could not be read.
- `platform/estate/libexec/estate-rescue.py` is the rescue: it adds `backup/preserve-*` branches on
  origin and reads each one back before it claims the rescue.
- `launchd/ai.estate.continuity.plist.tmpl` is the schedule. The runtime syncs the launcher and
  the libexec helper from `main`, so the job follows the repository, not this laptop's memory.
- The rescue is budgeted (25 items a run) and says what it deferred. A run that rescues 60 branches
  at once is a burst of network, not a service.
- Named hole, to be closed by the next change: the census source is still only in the runtime. It
  must land in `platform/estate/libexec/work-inflight.py` so the estate's own answer to "what is in
  flight" is on a remote.
- Named hole, to be closed by the same change: the census grades a dirty worktree on its branch
  rather than on its content, so it can call uncommitted work LANDED.

## What this does not do

- It does not land work. It moves it somewhere safe; the Greenlane still lands it.
- It does not decide which work matters. It rescues everything local-only, the dead sessions
  first, and lets the board rank the rest.
- It does not raise the executor's disk floor. A starved machine is slower for every agent on it,
  and a floor that cannot fail is not a floor.
- It does not fix the fleet plane. `sb start` is still refused (Temporal at 127.0.0.1:16223
  refuses connections; the docker daemon is not answering). This ADR is the insurance that the
  headless agent's work survives the plane being down, not a repair of the plane.
