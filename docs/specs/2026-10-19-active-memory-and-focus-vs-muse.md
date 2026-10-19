# Active Memory and Active Focus: the estate against Meta Muse

Date: 2026-10-19. Follows idp#6543 (the gap analysis; its sources are Meta's Muse Spark Open
release, the Muse Glimmer-30B architecture writeup, and huzjie/museforge, the Apache-2.0
reference implementation). This file records what changed, what is measured, and what is still
behind. It claims "superior" only where a check below can fail.

## Root cause of the stale focus

`ACTIVE FOCUS claim idp6525 ...` was an ordinary memory fact: hand-typed, no lifecycle, nothing
flipped it when the claim closed. idp#6543 added a filter, but only in `bin/estate-brief`, the
session-start hook. The `brief` and `recall` tools an agent calls during a session go
`bin/estate-memory-mcp` -> gateway -> server and never touched that filter. Measured 2026-10-19:
both tools returned two dead idp6525 facts while the hook dropped them. A fix in one of two doors
is a half fix, and the tools are the door agents use most.

## What changed

| Layer | Before | Now |
|---|---|---|
| Where ghosts are retired | the session-start hook only | `platform/estate/memory/focus.py`, called by the hook **and** the bridge every runtime passes |
| What "focus" is | a typed fact | read from the claim ledger (open issues with a CLAIM comment); closing a claim removes it, with nothing to remember to retire |
| Staleness window | 3600s cache: a ghost outlived its issue by an hour | 300s |
| Liveness | none | the heartbeat rule of AGENTS.md section 5.4: under 2h is LIVE; older is counted as free to take |
| Agent must read memory | advice in CLAUDE.md | `bin/estate-memory-enforce pre` refuses the first durable edit of a session that was never briefed |
| Agent must declare focus | claim-gate at merge time | the same hook refuses an edit to an idp file no live claim covers (and, with ESTATE_AGENT set, one that is not that agent's own) |
| Agent must write back | nothing | `bin/estate-memory-enforce stop` refuses once per turn when files changed and nothing was remembered |

Every enforcement decision is appended to `~/.estate/memory/enforce-ledger.jsonl` (pass, refuse,
unknown, optout). Every check fails open on an unreadable ledger, so memory trouble cannot take a
session down.

## Against Muse

| Capability | Muse Wonder (per the #6543 sources) | Estate | Verdict |
|---|---|---|---|
| Budgeted retrieval | top-k plus token budget | `limit` plus a per-item character cap on brief; top-k on recall | even |
| Retrieval score | relevance, recency, importance, frequency | cosine plus MAPLE-Guard (trust, harm, taint, scope), gate 0.35; then `ranking.py` adds recency (30-day half-life, decisions and incidents exempt) and frequency (log, capped), at most +0.08, applied after the gate so they order and never admit | **even on terms, ours gated**: weights are uncalibrated starting values; no importance term |
| Retrieval reinforcement | `access_count += 1` | `memory_access` table, bumped on recall and brief hits, in a savepoint that cannot fail the recall; its own table because updating `memories` fires the version-bump trigger and would reset the recency it is ranked with | **even** |
| Consolidation | episodic buffer distilled to semantic facts | per turn: every `remember` already posts to `/harness/memory/consolidate` (gate, promote a recurring preference, bi-temporal write). Between turns: an hourly CronJob expires scratchpad rows and ages preference counters. No distillation of episodic into semantic facts | **behind on distillation**, even on the rest |
| Stale-fact retirement | recency decay | a focus fact is retired the moment its claim closes; other facts are not decayed | ahead for focus, behind for the rest |
| Focus signal | scalar from progress, persistence, adaptivity | the claim ledger: owner, paths, heartbeat age, open or closed | different: ours is observed from outside the agent, Muse's is computed from its own attempt log |
| Overlap protection | not in the sources | a live claim covers the file or the edit is refused, at edit time and again in claim-gate at merge | **ahead** |
| Stuck detection | consecutive no-progress ticks | a live claim open 3h+ with no commit on its paths since is flagged STUCK in the register every agent reads. Observed from outside the agent; reads this checkout's refs, so it under-reports until fetched. `ActiveFocusController` is still code with no process | **even for claims**, behind for in-run loops |
| Agents are made to use it | a library you call | hooks refuse the edit and the stop | **ahead** |
| Trust boundary on recalled text | not in the sources | recalled text is data, never instruction (memory-gate checks it) | **ahead** |

Reading: ahead on enforcement, on a focus signal an agent cannot misreport, and on trust. Even on
ranking and stuck detection, with weights nobody has calibrated. Behind on one thing that matters:
Muse distils episodic memory into semantic facts and the estate does not. Calling the estate
superior overall would be a claim with no check behind it.

## Operating, and not yet

Built is not operating (AGENTS.md section 3).

- Operating on the founder's laptop since 2026-10-19: the bridge, the hooks and the stuck flag,
  installed by `bin/estate-memory-install` (`--check` all ok). Other machines get them on their
  next install run. `~/.estate/memory/enforce-ledger.jsonl` records every pass and refusal.
- Measured on install, against the live ledger: unbriefed edit refused; briefed edit under the
  agent's own live claim allowed, in the main checkout and in a /tmp worktree; unclaimed file
  refused with the claim-open command; another agent's file refused as overlap; files outside
  idp untouched. Two defects were found this way and fixed before the lane landed: the ledger
  query missed fresh claims past the 50-row cap, and /tmp worktrees passed ungated.
- Not yet operating: ranking, the access table and the CronJob, until the lane lands and Flux
  rolls the new image. `schema.sql` creates `memory_access` at server start. Until then the live
  server ranks on MAPLE alone.
- The CronJob's pod fence is the namespace-level `unified-memory` egress to estate-db; it was not
  exercised against the cluster, and Kyverno judged it BLIND (estate-only policies absent), the
  same verdict as the unchanged manifest.

## Follow-ons

1. Calibrate: replay recorded recall queries with the boost on and off and set
   `MEMORY_RECENCY_WEIGHT` / `MEMORY_FREQUENCY_WEIGHT` from the result, as RECALL_MIN_COSINE needs.
2. Distil episodic into semantic facts through the `chat` lane, as llm_derived facts that cannot
   supersede one another (anti-Ouroboros), only if step 1's replay shows recall improving.
3. Decide promotion: `curation_worker.py` was never deployed and its UPDATE resets `updated_at`;
   delete it or rewrite it against `memory_access`-style side tables.
4. Show STUCK on /fleet; today it reaches agents through the register, not the founder.
