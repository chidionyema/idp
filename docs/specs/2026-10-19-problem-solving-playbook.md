# The observed Claude method — a problem-solving playbook any model can run

Date: 2026-10-19 · Author: estate-agent (pi) · Claim: chidionyema/idp#6607

## Evidence base

Distilled from three real claude-code session transcripts of 2026-10-19 (497 tool calls total,
under `~/.estate/harness/cc/projects/-Users-roseonyema-Documents-code-idp/`):

| Session | Task shape | Tool calls |
|---|---|---|
| `f18d1f67` | Status audit: "what is the status of active memory and active focus" | 228 |
| `5ec0a5ef` | Production bug ("face app erroring with not allowed by csp after clicking tap to talk"), then a large build ask | 176 |
| `0c8d732d` | Ambiguous status ask ("what is the status of our research engines?"), then a consolidation decision | 93 |

The method below is what the transcripts show Claude **doing**, not what it says it does. Each
move cites the observed behaviour that earned it. It is model-agnostic on purpose: nothing in it
depends on Claude. Extractor: `bin/cc-digest.py` (same repo) — run it on new transcripts to
audit drift from this method.

The estate's codified doctrine (AGENTS.md §0 seven gates, §3 proof-not-assertion, §6
one-of-each-layer) already states the *laws*. This playbook is the *operating technique* —
the concrete micro-moves that make those laws come out in behaviour.

## The loop: seven moves

### 1. Orient before judging

Before any answer or change: memory brief/recall, graph, git state, what exists. Never answer
from prior knowledge.

> Observed (`f18d1f67`): first four tool calls are `brief`, `recall`, `growmos context`,
> `git status` — *before* forming a single sentence of the answer.

Prevents: confidently wrong answers, duplicated layers (§6), stale-focus acting on dead facts.

### 2. Separate intent from reality; ground terms in the repo

An ambiguous noun is a search, not an assumption. What a thing is *meant* to do lives in
manifests and docs; what it *is* doing lives in the cluster and the logs. Report both, and the
gap between them.

> Observed (`0c8d732d`): "I'll search the repo and the estate memory for what 'research engines'
> means here." Then `cronjob.yaml` for intent, `kubectl get` + pod logs for reality — answer:
> "There's one research engine, and its latest run **failed**."

Prevents: answering a different question than the one asked; grading intent as if it were state.

### 3. Trace the mechanism end-to-end before touching anything

Follow the actual call path through the real code — including the installed dependency's source
— until the cause is a mechanism you can name. Diagnose from mechanism, never from symptom
correlation.

> Observed (`5ec0a5ef`): task → `useVoiceRouter` → blob:-URL audio worklet → the *installed*
> Backstage `applyCspDirectives` source → "the default `script-src` is `'self' 'unsafe-eval'`,
> which blocks that; `connect-src` had no `ws:`/`wss:`."
> (`f18d1f67`): stale focus facts traced to a filter that ran in the session-start hook but not
> in the `brief`/`recall` bridge — two doors, one rule missing at the second.

Prevents: fixing the next symptom instead of the cause; edits that break at a door nobody traced.

### 4. Measure instead of reading, when a measurement exists

Curl the endpoint. Re-run the failing test on a baseline checkout. Diff outputs. Every number in
a report carries its provenance — measured this turn, or explicitly unverified.

> Observed (`f18d1f67`): failing tests re-run on an untouched main-based checkout to prove they
> pre-date the change; identical Kyverno output on both → "exit 2 is the missing estate-only
> policy set and not a violation."
> (`0c8d732d`): "about 1,125 verified claims… **I haven't checked that figure against the
> database**."

Prevents: narrating instead of proving (§3); regression- blames for pre-existing failures.

### 5. Change in isolation, wired for production

Worktree off `origin/main`, never the shared checkout. Read before write. Prefer pure, testable
modules over imports that drag heavy dependencies. Test the behaviour **and** the
production-only wiring that only fails in production.

> Observed (`f18d1f67`): scoring put in a stdlib module because `main.py` "can't be imported by
> the tests (it uses 3.12 syntax and needs fastapi)"; tests cover "the wiring that would
> otherwise fail only in production, such as the Dockerfile copy list and CronJob labels."

Prevents: clobbering another session's worktree; green tests, red pod.

### 6. Verify every boundary by reading the remote truth

Never trust an exit code across a boundary. tests → local gate → claim-gate → push →
`ls-remote` origin → lane verdict status → **a real production log line**. When a door kills a
push, re-run the same guarded action around the ceiling, then read the remote ref to confirm.

> Observed (`5ec0a5ef`): `lane-submit` "timed out at 60s, which the intent notes can happen even
> when the push lands. I'll check the remote ref." → not there → same push, same pre-push guard,
> in the background → ref on origin → curl the commit status → bounded background watcher.
> Done-criteria stated unprompted: "I'll check for a real production log line from a
> tap-to-talk before calling it done."

Prevents: the silent no-op — a job that reports done while its effect never landed.

### 7. Report the epistemic ledger, not the narrative

Every substantive report has three lists: **proven** (with the measurement), **read but not
reproduced** (with what would reproduce it), **not done** (with what is next). Name the
trade-off and the better alternative. Stop at sanctioned handovers.

> Observed (`5ec0a5ef`): "It is not tested in a browser, deployed or committed. I read the cause
> from the code and the installed Backstage source, but I haven't reproduced the error." Plus
> the trade-off, quantified: "allowing `blob:` loosens the policy a little… the tighter fix is
> to serve the worklet as a static file. I can do that if you'd rather."

Prevents: a green check being reported as done; unsolicited rewrites; silent trade-offs.

## Cross-cutting habits

- **Announce-then-do, one line.** "I'll start by finding the face app and where its CSP is set."
  Every action is narrated *before* it happens, in one sentence.
- **Reuse-first.** §6 inventory before any build: "`/agent-jobs` already exists and `/fleet` uses
  it; the face just never reads it. I'll look at the job shape and the existing board so I can
  reuse them." For N copies of a layer: "pick one engine as the survivor, fix and rewire it, and
  retire or fold in the rest."
- **Fail forward on environment friction.** GNU `sed -i` failing on BSD is one retry with the
  local form, noted — not a blocker report.
- **Quantify trade-offs.** "+0.08 to the MAPLE score, after the 0.35 gate and the cosine floor,
  so it orders results and never admits one" — degrees, not good/bad (§0 gate 2).
- **Subagents for parallel read-only sweeps**, main thread for judgment on their results.

## Adoption for other models

1. **Paste the seven moves into the model's operating context** (system prompt / AGENTS.md
   section) as imperatives. The quotes above are evidence, not required text.
2. **Wire the digest as drift monitor.** `bin/cc-digest.py <transcript.jsonl> <out>` reduces any
   session to its task + narration + tool skeleton. Run it on new sessions and check the loop is
   still visible: orient → ground → trace → measure → isolate → boundary-verify → ledger.
3. **Injection points.** The `claude` runner inherits estate law via AGENTS.md automatically.
   Other runners in the sb registry (`echo | sleep | ask | claude | llm`) compose prompts
   outside the idp tree; appending this playbook's seven moves at their prompt-composition point
   is the follow-up (tracked on #6607).

## Limits of this claim

Derived from n=3 sessions on one day, one model, one repo. The loop matched the codified
doctrine on every observed decision point, which raises confidence that the distillation is the
doctrine's operational form — but the monitoring loop (item 2) is what keeps it honest. A
session that skips a move should be caught by a digest diff, not by vibes.
