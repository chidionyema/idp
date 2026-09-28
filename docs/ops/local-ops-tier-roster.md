# The Local Ops Tier — Seven Worker Agents (crew#929)

Client-zero proof of a commercial offering: always-on FREE local model agents (qwen2.5-coder:7b,
llama3.2, gemma3:4b + the forge fine-tunes them) that take the recurring admin and easy work OFF the
founder's hands — work that today burns a frontier call or the founder's own session time. Compiled
from the estate's real operational patterns: the founder's recurrent asks shown across sessions
("update / what changed / what's shipped / is X on main / what's next"), the daily estate snapshot,
PR/issue administration, and the branch/ticket reconciliation that recurs every session.

Each agent has: (1) the concrete work it owns, (2) the output shape, (3) its no-op/liveness contract
(what it does when idle so it never cold-starts and never reports a falsity), (4) measured limit.

Throughput ceiling (measured 2026-09): ~1–2 tok/s CPU on the Intel i7. The tier is BATCH/scheduled,
run by the driver against the local models, NOT interactive for a human-scale reply.

---

## slot 1 — the answer agent ("update"): what changed / red / shipped / next
Owns the single most repeated founder ask from the transcripts — "update", "what changed",
"is X shipped", "what's red". It reads live flux readiness + the estate snapshot + recent merged PRs
and answers concisely.
- **Output:** deterministic `STATUS:` line (RED/ALL GREEN, worker-computed, not model-trusted) + a
  short WHAT CHANGED / WHAT'S NEXT narrative under 60 words.
- **No-op:** holds idle on a durable queue; never emits an unsolicited digest. When polled it answers
  from measured facts only — a "green" with no probe is a refusal, never a pass (LAW 2).
- **V1 proof: `bin/estate-digest-worker`** (PR #2729). Measured honestly: the base model twice
  fabricated "All Green" over real RED rows; status is now deterministic, worker-owned.
- **Limit:** answers only what the snapshot/flux/git inputs measured. No digressions.

## slot 2 — the grader: grade every estate-state row GREEN/RED/NOT RUN + why
Turns the daily snapshot's raw rows into a clean graded ledger with a one-line cause per row.
- **Output:** one line per row, e.g. `delivery | RED | 457 commits no remote, oldest 3.2d`.
- **No-op:** refused to grade a row it cannot measure — returns NOT RUN, never a guessed PASS.
- **Good forge fine-tune target** (deterministic rubric, small output).

## slot 3 — the router: classify + route inbound requests
For each inbound founder message / new issue / PR comment: type (bug, feature, ops, admin, security,
info) + owning subsystem. The "who handles this" decision that recurs every session.
- **Output:** `ROUTE: <subsystem> (<type>)` or `CLASSIFY: <type> (summary)`.
- **No-op:** an out-of-whitelist or security request is refused loudly, never guessed to a lane.
- **Boundary (LAW 21):** never passes customer/user content or a secret body onward; routes on
  metadata+summary only.

## slot 4 — the reconciler: branches, tickets, stranded work
Scans git/issue/PR state for the drifting work that recurs in every session: stale unmerged branches,
closed-but-unmerged, orphaned commits, unowned pending marks, "merged but branch never deleted".
- **Output:** action lines — `archive branch X`, `notify owner of Y`, `merge-status Z`.
- **No-op:** reports clean OR lists drift; both are real and measured, never invented.
- **Note:** these are exactly the "crew#267 image update", branch-leak and stranded-git items in the
  estate snapshot. Mostly deterministic to detect; the model only phrases the action.

## slot 5 — the recorder: turn a session's tail into the durable capsule
Given a block of work, emit the INVENTORY capsule (built / use / expect / not-done / evidence) every
session is now expected to close with — the knowledge-base backstop (R30).
- **No-op:** refuses to record a session whose claims carry no command-run evidence. A green with no
  probe is a refusal.

## slot 6 — the cleaner: propose cleanup, never execute
Flags orphaned kubectl resources, dead references, stale targets, and suggests one action each.
- **No-op / boundary:** a cleanup proposal carries an owning-review line or it is a refusal.
  It SUGGESTS, never runs a destructive command — destructive needs the human driver.

## slot 7 — the keeper: the no-op/heartbeat that holds the tier warm
Responds `ALIVE:<ts>` to a liveness ping, reloads a cold model, reports load. Without a live keeper
every other slot is a cold-start bet (a 7B reload cost the consensus vote its deadline before;
measured 30.8 s cold vs 16.9 s warm, crew#284).
- **Keep-alive:** a periodic tiny `generate` ("reply ALIVE and nothing else") keeps the weights
  resident and proves the tier is alive — the always-warm contract the commercial offer sells.

---

## The common contract (what makes this a product, not a script pile)
- **Status that matters is computed, never trusted to the model** — a drifting 7B cannot greenwash a
  red (proved on slot 1).
- **No agent fabricates a fact.** "Done/green/clean" without a measurement is a refusal, never a pass.
- **No agent posts customer content or secrets.** Boundary of slot 3 is the whole tier's (LAW 21).
- **Destructive = suggest only, execute = human driver.**
- **Batch/scheduled, never interactive** (the ~1–2 tok/s CPU truth).
