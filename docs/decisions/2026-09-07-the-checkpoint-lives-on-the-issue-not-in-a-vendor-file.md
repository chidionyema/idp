# The checkpoint lives on the issue, not in a vendor's file

**Date:** 2026-09-07
**Status:** accepted
**Founder:** "but not only claude / we have nultiagents now"

## What was wrong

The estate's session-continuity layer was three files, and all three were keyed to one vendor's
private on-disk format:

| Layer | Keyed to |
|---|---|
| `session-recorder.py` | `<claude home>/projects/<slug>/<session-id>.jsonl` and Claude Code's `Stop` hook |
| `ticket-gate.py` | a per-session JSON file under Claude's state directory |
| `dupe-work-fence.py` | that same session identity |

An agent that is not Claude Code has no `Stop` hook, no JSONL transcript and no `session_id`. It
therefore gets no checkpoint, no ticket binding, and is **invisible to `dupe-work-fence`** — free
to duplicate another agent's work, which is precisely the failure the founder named on 2026-08-19
("too many agents fixing the same issues"). LAW 34 (provider agnostic from day 0) was broken at
the foundation of the sync layer.

This is not hypothetical. `git log --grep="cline checkpoint"` returns **55 commits** in this
repository from an agent none of those three files can see.

A second defect sat on top of it. `rule-guard.py` refused any command that opens a new thread of
work — `git worktree add`, `checkout -b`, `gh issue edit --add-assignee` — whenever a
`checkpoints/LATEST.md` was over 30 minutes old. **117 refusals, the single most frequent block in
the estate**, over 13,048 model messages on 2026-09-07.

It never measured what it claimed. `checkpoint_age_s` does `os.path.dirname(transcript_path)`, so
it stats `<claude projects>/<slug>/checkpoints/LATEST.md` — the **transcript directory, not the repo
checkout**. Measured across all 34 project directories holding sessions: **23 of them, holding
11,639 sessions, have no `LATEST.md` at all**, so the rule was BLIND and could never fire. Of the 11
that have one (564 sessions), **10 were already past the threshold**, median age **316 hours**. The
single fresh exception was `idp` — the one repo whose sessions had been trained to hand-write the
file because the rule nagged them.

Silent for 95% of sessions, permanently tripped everywhere it could see, except where it had
trained someone to feed it. It measured who feeds the gate, not who checkpoints.

## The class of mistake

Any continuity mechanism that reads a vendor's transcript format reaches exactly one vendor. Every
fix aimed at one instance — a better recorder, a second hook, re-pointing the guard — fails the
same way for the next runtime that arrives.

## The decision

The record of what a unit of work is doing belongs on **its GitHub issue**, derived from the two
things every agent leaves behind whatever its provider: **git state** and **the issue it is bound
to**. `bin/estate-checkpoint` writes it.

The issue is already mandatory (`ticket-gate` binds one to every session), already the sync layer
(LAW 26), already readable by every agent of every vendor, and already on the founder's phone.

- One comment per `(agent, session)`, located by an HTML marker and **updated in place**, so it
  never spams a thread and needs no local state to know what it wrote.
- **Fails open, always.** No git, no `gh`, no network, no bound issue, unreadable payload: exit 0
  and say why on stderr. A recorder that blocks work is worse than no recorder.
- Per-runtime adapters are thin and optional, supplying only the prose an agent alone knows.
  Claude Code's is one flag, `--from-claude-hook`. Any other agent calls the plain CLI.

## Consequences

- The `rule-guard` staleness gate is deleted, not re-pointed (claude-guards PR #252). `reply.rego`'s
  LAW 16 stale-checkpoint rule goes with it: it reads the same input, and deleting only the LAW 25
  rule would have silently *armed* it, since nothing writes `LATEST.md` any more. Over 43,913
  assistant text blocks its regex alone matches 30 times with roughly half false positives, and a
  guard that refuses correct work is an outage (LAW 38).
- A non-Claude agent gets continuity and becomes visible to its peers for the first time.
- The record survives the death of the session, the machine and the vendor.
