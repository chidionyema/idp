# Adaptive executor timeout bounds: a proposal with a decision core, not a number

Status: proposed. The decision core is landed and proven; the door is not wired.
Date: 2026-10-30.
Claim: chidionyema/idp#7544.
Agent: pi-design-cores.

## The problem, measured

The executor's ceiling is the only place wall-clock time is bounded in the estate
(`bin/timeout-budget` proves that there is exactly one). It is 100 seconds, it is a hard
boundary, and it is not going to move.

What the door does when a command wants more than 100 seconds is refuse it. The governed
friction report at `2026-10-30T05:56:35Z` -- the authoritative measurement, 2,375 events:

| kind | count | what it means |
|------|-------|---------------|
| `pace-wait` | 864 | the command was a sleep and was paced |
| `refuse-disk` | 638 | the disk floor stopped the run |
| `steer` | 403 | the executor redirected the command |
| `refuse-wait` | 232 | a long sleep was refused |
| `refuse-ceiling` | 229 | **the command asked for more time than the ceiling allows** |
| `refuse-plan` | 9 | the plan itself was refused |

`refuse-ceiling` is 9.6% of all friction. An agent writes `timeout 180`, the door refuses, and
the agent has to work out on its own that the work has to be decomposed, backgrounded or moved
to another door. The refusal is correct -- the cap must not move -- but it is a dead end with no
signpost.

The other measurement says the cap is right for the overwhelming majority of work. Of 790
retained executor jobs, measured this session:

| p50 | p75 | p90 | p95 | p99 | max |
|-----|-----|-----|-----|-----|-----|
| 0.6s | 4.0s | 14.1s | 25.9s | 58.9s | 100.0s |

Four jobs were killed at the ceiling (exit 124, all at 100.0s). So the shape of the problem is
not "the ceiling is too low". It is "the ceiling is right for 99% of work, and for the tail the
answer is not a bigger number but a different door".

## Why the answer is not a bigger number

`docs/decisions/2026-10-29-timeout-obligations.md` is explicit: *preserve the existing caller
deadlines while measuring their suitability; do not increase a number to hide a failure.* A
learned ceiling that grows because a job was killed is exactly that: a number increased to hide
a failure. A job killed at 100s is evidence that the ceiling was too small **for that job**, and
it is *not* evidence that 300s would have been enough -- the job might have needed an hour, or
might have hung forever.

So the rules of the proposal are:

1. **The hard cap stays at 100 seconds.** No caller, and no learning loop, can raise it.
2. **Learning is from observable outcomes only.** A job that succeeded is evidence about
   duration. A job that was killed is evidence that the ceiling bound, and it is routed to the
   optimisation obligation, never to a larger grant.
3. **A deadline breach is an obligation, not a retry.** The governing decision says a timeout
   must become an optimisation obligation in the existing incident plane: the work is recorded,
   the cause is named, and the deadline is not extended by waiting.
4. **The caller's own deadline is never rewritten.** 30 means 30.

## The grammar: a bound is a string

Today a caller expresses a timeout by writing a timeout into the command, and the executor
scrapes the command for every spelling it knows (`timeout 150`, `timeout 2m`,
`gtimeout -k 5 150`, excluding grace-period values). Scraping a command is a guess: the string
inside quotes is data, and the executor's own rule says so. A bound should be a first-class
value with an explicit grammar, so the door can answer "what does this mean" instead of
"does this string look like a number".

| bound | meaning |
|-------|---------|
| `30` | exactly 30 seconds, honoured verbatim, clamped to the cap |
| `auto` | the door measures this command shape and grants the measured p95 |
| `quick` / `standard` / `deep` | named classes with ceilings of 10s / 30s / 60s; measurement may lower them, never raise them |
| `range:10..45` | an explicit window; the door grants at most 45 |
| `need:600` | "this work needs about 600 seconds"; granted when it fits, routed when it does not |
| `none` | no bound requested; the door applies its own default |

Anything else is `DENY`. A bound that cannot be parsed is a bound that cannot be trusted, and a
typo must not silently become the maximum.

## The four states

The resolver returns one of four states, and the distinction between the last two is the point
of the whole design:

| state | meaning | bound granted |
|-------|---------|---------------|
| `ALLOW` | the door knows what to grant | the measured or caller-bound seconds |
| `ROUTE` | the work does not fit under the cap, but it is not refused | none; a named destination is returned |
| `DENY` | the request cannot be honoured and cannot be routed | none |
| `UNKNOWN` | the door has no measurement for this shape | a conservative default, and it is labelled `UNKNOWN` |

`UNKNOWN` is not a failure and it is not a pass. It is the honest state of "I have never seen
this shape of work". The bound it grants is the conservative one (30 seconds, or the class
ceiling if that is lower), and because it is labelled `UNKNOWN`, the receipt says so, so the
next run has an incentive to measure it.

## Routing, not refusal

`need:600` is not a refused command; it is a request for a different door. The resolver names
the destination instead of saying no:

* `background` -- the executor's detached job, which writes a receipt;
* `session` -- the session plane (`sb start`), which is budgeted and approval-gated;
* `lane` -- Greenlane: the work becomes a commit and CI carries it.

This is the estate's own placement ladder (`AGENTS.md` section 8: delete, GitHub Actions
schedule, Grafana Cloud free, Cloudflare Workers free, laptop just in time, KEDA scale-to-zero,
always-on). The timeout proposal does not invent a placement policy; it uses the one that
exists.

`refuse-ceiling` stays. A command that embeds `timeout 180` in its own text is still refused
with the same message: the caller's *command* may not author its own ceiling. The difference is
that the refusal now names the way out, and the door can offer a bound the caller can accept
without rewriting its command.

## What has to be measured before any of this can learn

The resolver's evidence is a list of receipts:

```python
Receipt(shape="pytest", elapsed_sec=8.2, exit_code=0, killed_at_ceiling=False, repo="idp")
```

Two facts are missing today and must be added before the learning loop is wired:

1. **Elapsed time per job.** `platform/executor/run.py` writes `<job>.log`, `<job>.pid` and
   `<job>.exit`. The exit file carries the exit status and no duration. The ceiling probe
   measures elapsed time locally but does not persist it. Without a per-job duration receipt
   there is no shape-level distribution to learn from, and "learn from the past" would be a
   slogan.
2. **A stable command shape.** The shape key has to be a normal form of the command, not the
   command itself: `pytest tests/` and `pytest tests/ -q` are one shape, `docker build` is
   another. The shape key is a fingerprint of the executable plus the first non-flag argument
   class, with flags stripped of their values. It must be recorded in the receipt, so the
   evidence can be audited rather than trusted.

Both are additions to the executor's receipt writer, in the executor's own slice, with the
executor's own claim. They are not in this slice.

## Anti-gaming

A learned bound is only as trustworthy as the evidence behind it, so the rules that keep it
honest are written down before the code exists:

* **No self-raising.** A caller cannot raise its own bound, by any spelling. The cap is applied
  after resolution, not before it.
* **No evidence from failures.** Only successful completions count toward a shape's measured
  duration. A killed job is routed and recorded as an obligation.
* **No evidence from a different repository.** A fast repository must not teach a slow one. The
  repository is part of the evidence key.
* **No evidence from a different shape.** The shape key is part of the evidence key.
* **The percentile is nearest-rank, not interpolated.** The answer has to be explainable in a
  sentence: "9 of 10 runs of this shape finished within 25 seconds".
* **The learned bound is clamped twice**: by the class ceiling, and by the hard cap. Measurement
  can only lower what the caller asked for, never raise it.
* **A measurement is never negative or zero.** A bound below one second is the floor.
* **The gate is the only writer.** Receipts are written by the executor door, not by the
  caller. A caller that could write its own receipt could write its own permission.

## Falsifiable acceptance criteria

| # | criterion | how it is proven |
|---|-----------|-----------------|
| A1 | no resolution grants more than 100 seconds | `test_no_bound_can_exceed_the_hard_cap` |
| A2 | the resolver's cap equals the executor's `CEILING_SEC` | `test_the_mirrored_cap_matches_the_executor` |
| A3 | a numeric bound is honoured exactly | `test_a_numeric_bound_is_honoured_exactly` |
| A4 | an unmeasured shape is `UNKNOWN` with a conservative bound | `test_an_unmeasured_shape_is_unknown_and_conservative` |
| A5 | a killed job is never evidence of feasibility | `test_a_job_killed_at_the_ceiling_is_not_evidence_that_a_bigger_ceiling_would_work` |
| A6 | a failed job is never evidence of feasibility | `test_failed_jobs_are_not_evidence_of_feasibility` |
| A7 | evidence does not cross repositories | `test_evidence_is_not_pooled_across_repositories` |
| A8 | evidence does not cross shapes | `test_evidence_for_another_shape_is_not_used` |
| A9 | an unparseable bound is `DENY`, never a default | `test_an_unparseable_bound_is_denied` |
| A10 | `need:N` beyond the cap routes and never grants | `test_a_need_beyond_the_cap_routes_instead_of_granting` |
| A11 | a named class never exceeds its ceiling | `test_a_named_class_never_exceeds_its_ceiling` |
| A12 | a range never exceeds its high-water mark | `test_the_range_grants_at_most_its_high_water_mark` |

Twelve criteria, twelve falsifiers, all green in
`tests/test_adaptive_bound_resolution.py`.

## What this proposal does not do

* It does not raise the ceiling. It cannot; the cap is applied after resolution.
* It does not change the executor's behaviour. The resolver is not wired to the door.
* It does not replace `refuse-ceiling`. A command that authors its own ceiling is still
  refused; the proposal adds a way to ask for a bound the door can grant.
* It does not learn from the friction ledger. The friction ledger records refusals, not
  durations; durations need the receipt writer this proposal also asks for.
* It does not promise a smaller refusal rate. The measured `refuse-ceiling` count is the
  baseline that a future slice must beat, with the governed friction report as the yardstick.
