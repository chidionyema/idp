# The epistemic firewall has a third leg

Date: 2026-10-29
Status: accepted, implemented in code (`platform/estate/libexec/epistemic_loop.py`, `bin/epistemic-loop`, `platform/estate/intents/epistemic-loop.yaml`), wired into the resident guardian (`bin/idp-disk-watch`)
Issue: chidionyema/idp#7338
Claim: chidionyema/idp#7338
Agent: pi

## The problem, measured

The estate already had two epistemic legs:

- `bin/epistemic_firewall.py` — claim truthfulness: is this statement supported by the trace?
- `bin/trajectory_lock.py` — goal adherence: is the agent still doing what it was asked to do?
- `sovereign/verifier.py` — an independent deterministic three-stage verifier.

What was missing was the leg that answers the question the founder kept asking in the same
shape: **is this loop actually making progress?** The estate had loops that ran for hours,
measured nothing, and reported activity. Measured on 2026-10-29:

- The resident disk guardian ran `rc=4 freed=?M met=? after=?M` on cycle after cycle for
  roughly eight hours. It was alive and ticking. It freed nothing. The `?M` values were its own
  blind measurements rendered as if they were numbers, so the loop could not tell the difference
  between "I did nothing" and "I could not see".
- Free space fell 2361 MB → 2280 MB → 1759 MB → 919 MB → 437 MB → 396 MB while the guardian
  reported the same non-verdict each cycle.
- The NATS JetStream store then failed with `no space left on device`, and the estate's bus,
  memory and focus surfaces went down together. A loop that cannot prove progress is a loop that
  cannot stop.
- The cleaner it was driving never emitted its one `RESULT` line under SIGKILL, so there was no
  artefact to grade and nothing to replay.

The pattern is not disk-specific. It is the failure of a loop to distinguish **progress**,
**no progress**, **regression**, **a repeated action that has stopped working**, and **blindness**.

## What the research says

A 72-source harvest (arXiv, OpenAlex, Springer, Zenodo) over "epistemic firewall", "progress
verification", "bounded loops", "memory correlation bias", "false consensus", "loop detection"
produced mechanisms that converge on five points.

1. **Progress must be measured externally, not self-reported.** The progress-mirage result
   (OpenAlex `W7171902361`) and IAL-Scan (`arXiv:2607.01641`) both show that a system's own
   account of having improved is uncorrelated with external ground truth under optimization
   pressure. A self-reported "done" is the input the firewall exists to distrust. Mingbird
   (`arXiv:2610.02001`) reaches the same conclusion for agent memory: a memory that records
   what the agent believed is not a memory of what happened.
2. **Correlated evidence is not evidence.** Memory-correlation bias (`arXiv:2608.19701`) and
   false-consensus work (`arXiv:2608.23623`, `arXiv:2610.17869`) show that several agents
   converging on the same answer is one source, not several. Fan-out that produces three
   confirmations of one rationale inflates confidence without adding evidence.
3. **Bounded loops need an unwritable exit.** Bounded-loops work (`arXiv:2609.27871`) and
   LoopTrap (`arXiv:2605.05846`) both require the exit decision to be made outside the loop's
   own write scope, and both require a hard budget rather than a timeout that is re-negotiated
   per model.
4. **Oversight has a finite capacity.** "Oversight Has a Capacity"
   (`arXiv:2606.08919`) and the budget-boundary results bound how much human attention a
   supervision loop can consume before it becomes theatre. Escalation must be deduplicated and
   backed off, not fired every cycle.
5. **Escalation must carry remediation data, not a complaint.** ECMR (`arXiv:2610.17869`),
   InfoDelphi (`arXiv:2607.01661`), UndoBench (`arXiv:2610.05622`) and the Epistemic Firewall
   prototype (Zenodo `22671505`) all describe escalation as a structured handover with enough
   context to act without re-deriving the diagnosis.

Two estate-specific findings came out of the harvest and are the reason the third leg was
added here rather than elsewhere:

- **LIMBO (`arXiv:2609.29095`)**: "exactly once" semantics belong outside the model. The
  guardian's progress record must be written by the thing that measures, not by the thing being
  measured.
- **SquidAgent (`arXiv:2610.08647`)**: an agent's own view of its loop state drifts from the
  loop's real state. Hence the guardian owns its own `RESULT` line, synthesised from its own
  `statvfs`, rather than trusting the child's report.

## The design

`platform/estate/libexec/epistemic_loop.py` implements the leg as a small library with four
pieces.

### 1. A world-state fingerprint is the oracle

`ProgressGate(subject, metric, ledger, no_progress_limit, direction)` grades an action by
comparing **externally supplied** before/after state:

```
verdict = PROGRESS | NO_PROGRESS | REGRESSION | LOOP | BLIND
```

- `PROGRESS` — the metric moved in the intended direction by more than the threshold.
- `NO_PROGRESS` — it did not move.
- `REGRESSION` — it moved the wrong way.
- `LOOP` — the same action has produced `NO_PROGRESS` `no_progress_limit` times (default 3).
  The action identity is a fingerprint, so "try the same thing again" is detected even when the
  caller renames it.
- `BLIND` — the metric could not be read. This is **fail-closed**: a blind measurement is never
  scored as zero and never counted as progress.

The gate never reads a verdict from the worker it is judging. The caller supplies before/after
state it measured itself.

### 2. The evidence ledger is append-only and outside the loop's write scope

`LoopLedger` appends one fsynced JSONL record per judgement to
`~/.estate/loops/progress.jsonl` by default. It is append-only: no record is ever rewritten or
removed. A loop cannot erase the evidence of its own failure, and the record is replayable —
the same input stream yields the same verdicts.

### 3. Evidence gathering is bounded, and parallelism is conditional

`fan_out(probes, budget_s=..., runner=...)` runs probes under a hard deadline
(`deadline = started + max(0, budget_s)`), deduplicates correlated probes by `source`, and
reports the **effective independent source count** rather than the raw probe count. Two
guards:

- A probe that gets less than `MIN_PROBE_WINDOW_S = 0.5` reports `status: "budget"` — it did
  not time out, it was starved. A starved probe must not masquerade as a timeout.
- Fan-out falls back to serial when the independent-source count would not justify the
  coordination cost. Parallel evidence that is correlated is not evidence, and it costs more
  than it returns.

### 4. A verdict that says "stop" escalates

`escalation_for(verdict)` maps `LOOP` and `REGRESSION` to a structured escalation carrying the
action, the measured before/after, the number of prior no-progress attempts, and the
recommended next action. `summarise()` produces the estate-readable digest.

## How it is wired into the resident guardian

`bin/idp-disk-watch` is the first adopter, because it is the estate's first loop that runs
unattended for hours.

- **The guardian owns the delta.** `synth_result()` computes `free_before_mb`,
  `free_after_mb`, `freed_mb` and `met` from the guardian's own `os.statvfs`. If the volume
  cannot be read, the result is `blind` — not `0`, not `?`.
- **The action is the phase set.** The guardian escalates along
  `PHASE_LADDER = ("caches,critical,temp" → "+worktrees" → "+docker,clones")`. Escalating
  changes the action, so it earns a fresh no-progress budget. The escalation state lives in
  `~/.estate/disk-watch.escalation.json`.
- **A blind verdict raises an incident instead of stepping blind.** `BLIND` is not `NO_PROGRESS`
  and is not swallowed.
- **Escalation respects human capacity.** `ESCALATION_ALERT_EVERY_S` (default 1800) bounds how
  often the alert path fires, so a stuck loop cannot storm the founder with alerts or agent
  invocations.
- **The child is terminated, not orphaned.** `proc.terminate()` → 10 s grace → `proc.kill()`
  → 5 s drain. A backgrounded child never holds the caller's stdout pipe, so the executor's
  100 s ceiling is not held open by a leak.

The escalation path produces a structured incident in `~/.estate/incidents/`, an alert row in
`~/.estate/alerts/inbox.jsonl`, a macOS notification, and one bounded agent invocation through
`~/.estate/libexec/agent-invoke.sh --json`.

## The surfaces

| Surface | What it is |
|---|---|
| `platform/estate/libexec/epistemic_loop.py` | the leg: gate, ledger, fan-out, escalation |
| `bin/epistemic-loop` | bash door; prints `BLIND …` and exits 2 when the leg is absent |
| `platform/estate/intents/epistemic-loop.yaml` | the governed door: `judge` / `summary` / `fan-out` |
| `tests/estate/test_epistemic_loop.py` | 23 tests |
| `bin/idp-disk-watch` | first adopter; owns its own delta and escalates its own loop |

## Requirements this decision makes testable

1. A judgement whose before/after state was not supplied externally is `BLIND`, never `PROGRESS`.
2. `BLIND` is never counted as progress and never converted to zero.
3. The same action reaching the no-progress limit produces `LOOP`.
4. The ledger is append-only; a prior record is never rewritten.
5. The ledger and the gate live outside the write scope of the loop being judged.
6. A probe with less than `MIN_PROBE_WINDOW_S` reports `status: "budget"`.
7. Correlated probes are counted once in the independent-source count.
8. Fan-out never exceeds `budget_s` from its start.
9. `LOOP` and `REGRESSION` produce a structured escalation carrying remediation data.
10. The guardian's `RESULT` line is synthesised from the guardian's own measurement, and reads
    `blind` when the volume cannot be read.
11. The guardian escalates its phase set on zero yield rather than repeating the same action.
12. The guardian terminates the cleaner with TERM before KILL.
13. The brake refuses to fire unless pressure was measured.
14. `vm_stat` is executed, not read: the file is a Mach-O binary on this machine, and reading
    it produced no `Pages free` line at all, so the RAM reading was permanently `?M`.

## What this does not claim

This leg does not make a loop intelligent, and it does not make progress measurement
trustworthy where the underlying metric is itself untrustworthy. It makes three things true
that were not true before: a loop that cannot prove progress says so, a loop that repeats a
failing action is caught by an oracle it cannot write to, and a loop that has exhausted its
options escalates with structured data instead of running again.

## Sources

- `arXiv:2607.01641` — IAL-Scan: identity-aware scanning for agent progress
- `arXiv:2610.02001` — Mingbird: memory grounded in observation rather than belief
- `arXiv:2609.27871` — bounded loops with an unwritable gate
- `arXiv:2610.17869` — ECMR: escalation with structured remediation
- `arXiv:2608.19701` — memory correlation bias
- `arXiv:2607.01661` — InfoDelphi: information-theoretic loop boundaries
- `arXiv:2610.08647` — SquidAgent: the agent's own view of its loop state drifts
- `arXiv:2608.23623` — ECT: false consensus in multi-agent evaluation
- `10.1007/s10846-026-02413-w` — managed autonomy and the capacity of supervision
- `arXiv:2606.08919` — Oversight Has a Capacity
- `arXiv:2605.05846` — LoopTrap: detecting repeated non-progress actions
- `arXiv:2610.05622` — UndoBench: reversible changes and rollback accounting
- `arXiv:2609.29095` — LIMBO: exactly-once semantics outside the model
- Zenodo `22671505` — Epistemic Firewall prototype
- OpenAlex `W7171902361` — the progress mirage: externally grounded verification
