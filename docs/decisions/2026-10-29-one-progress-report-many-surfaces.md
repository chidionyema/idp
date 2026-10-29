# One progress report, many surfaces

Date: 2026-10-29
Status: accepted (first slice landed under #6687)
Relates to: #6687, #7344 (context substrate), #7311 (AEI), ADR 0034 (placement), ADR 0045 (AEI is
an observation plane)

## Context

The founder asked, repeatedly, for one plan for metric collection across the estate, and asked
how a self-improving estate can be blind to its own data. Measured, the estate was not missing
data: the Greenlane state, the Actions API, the focus register, the decision-door state and the
cluster receipt each hold part of the picture, and nothing joined them.

Three measurements made the gap concrete: the estate's own inventory has never been produced on
the laptop (`~/.estate/inventory/` does not exist), the inventory's Prometheus feed is written by
`bin/idp-inventory` and read by nothing, and the Greenlane's 778 landings, 209 conflicts and 423
timed-out lanes are visible only as a summary the surfaces choose to show.

The tempting shape is a metrics library per surface, each one reading the sources it cares about.
It fails for a reason that is arithmetic, not taste: every surface would have to learn the
Greenlane's state format, the Actions API, the claims register and the receipt schema, and keep
them current. Four integrations per surface, each wrong in a different way, and a number that
disagrees between surfaces - which is worse than no number, because it looks like a fact.

## Decision

**One writer, one canonical signal set, many renderers.**

1. `bin/estate-progress` is the only writer. It reads the chain (the Greenlane state), CI (the
   Actions API), the claims (the focus register), the founder's queue (the decision-door state)
   and the live stage (the cluster receipt), and writes one canonical artefact:
   `estate-progress.json`, with `estate-progress.prom` and `estate-progress.md` beside it.
2. A surface never measures. It renders the signal set. A new number is added to the signal set
   once, and every surface gets it.
3. A source that cannot be read is BLIND, never zero, and carries the reason. The verdict
   degrades to `PARTIAL` when something is blind and `UNKNOWN` when the chain itself cannot be
   read.
4. The verdict is a deterministic function of the signals, with the thresholds written in
   `docs/specs/2026-10-29-the-estate-reports-its-own-progress.md` and pinned by tests. No model
   reads a number in this path.
5. Progress is a delta against the previous report. A report with no predecessor says so instead
   of inventing a baseline.
6. The report is read, not pushed: surfaces serve the cached artefact (the writer runs on a
   schedule), so a founder question never waits on a measurement.
7. The report carries its own canonical spoken sentence (`speak`), and the door that every surface
   calls (`platform/estate/intents/estate.progress.yaml`) resolves the writer in a fixed order
   (`~/.estate/bin`, then the estate's main tree, then the root it was given). A host with no
   writer still speaks the sentence the report already carries; a host with no report says
   `unknown`. Neither invents a number, and neither writes its own wording.

### Why the sentence is inside the report

Measured on 2026-10-29: the intent's root default was `~/Documents/code/idp` and the executor
shell-quotes every argument, so the tilde was never expanded. On a host whose checkout sat on a
work branch the writer was not there at all, and the door had nothing to speak. Two changes
follow from that measurement, and both are architectural rather than local:

* the canonical sentence lives in the report, so a missing writer costs a host its own wording,
  not its truth;
* the writer the door finds first is the copy the runtime sync stages into `~/.estate/bin` from
  `main`, so the door and `main` always carry the same bytes - and a host that has neither still
  answers.

The same lesson applies to the sync itself: a notification failure must never kill a convergence
tick (the `osascript` timeout of 2026-10-29 killed one, and the estate ran a seven-hour-old tree
because nobody noticed). The log is the record; the notification is best-effort.

## Alternatives rejected

* **A metrics library per surface.** Rejected: N integrations per surface, and the numbers
  disagree between surfaces, which reads as a fact and is not one.
* **A new collection service or a new database.** Rejected: the estate has one evidence layer
  (Aevum, ADR 0028) and one Prometheus; a second collector would be a second authority. The
  signals here are derived, joinable, and cheap to recompute; they do not need a store of their
  own. The committed snapshot is the artefact, not a database.
* **Let Prometheus own everything.** Rejected: Prometheus measures the cluster's internals well
  and the estate's own work badly - the Greenlane's timings, the claims and the founder's queue
  are not cluster resources. It would also make the founder's question depend on the cluster, and
  the cluster is currently degraded (#7343), which is exactly the blind spot this closes.
* **Extend `bin/idp-inventory` alone.** Rejected: the inventory grades resources and ownership
  (six planes, four verdicts) and says nothing about work: no landings, no waits, no failures,
  no delta. It is one plane of the same problem, not the whole of it.

## Consequences

* The founder's question ("are we progressing, and is what we are doing making sense?") has one
  answer, from one artefact, in the same numbers on every surface.
* The estate's self-report is measurable in both directions: the report proves the delivery chain
  is moving, and the same report names what it cannot see.
* A blind source is a first-class, visible condition, so the report can fail.
* The report is read-only over existing artefacts: it adds no state, no credentials, and no
  cluster footprint, and it never blocks another agent's work.
