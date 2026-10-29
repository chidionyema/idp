# The estate's progress report

One report, one writer, every surface renders it. The spec is
`docs/specs/2026-10-29-the-estate-reports-its-own-progress.md`; the decision is
`docs/decisions/2026-10-29-one-progress-report-many-surfaces.md`.

## What it answers

"Are we progressing, and is what we are doing making sense?" - measured on the estate's own
delivery chain: claim -> lane -> CI -> greenlane verdict -> landed -> live.

## How to ask

Any agent, any harness:

```bash
estate-execute estate.progress            # the spoken sentence
estate-execute estate.progress --args fresh=true   # recompute now, then speak
```

The door prints ONE line: the spoken sentence, because the voice surface speaks an intent's last
stdout line. It serves the cached report by default and never waits on a measurement.

### Where the writer is found

The door looks for the writer in this order, because the default root is a working checkout that
may be on any branch:

1. `~/.estate/bin/estate-progress` - staged from `main` by the runtime sync.
2. `~/.estate/runtime/idp/bin/estate-progress` - the estate's own main tree.
3. `<root>/bin/estate-progress` - the repo passed as `root`.

With none of them, the door speaks the sentence the report already carries (`speak`), read from
`~/.estate/progress/estate-progress.json` (override with `ESTATE_PROGRESS_REPORT`). With no
report either, it says the estate's progress is `unknown` - never a zero, never a green.

Or directly:

```bash
bin/estate-progress --read --speak        # the cached report, as a sentence
bin/estate-progress --json                # the whole signal set
bin/estate-progress --publish             # compute, then publish to the estate bucket
bin/estate-progress --strict              # exit 1 unless the verdict is PROGRESSING with nothing blind
```

## Who writes it

* `.github/workflows/estate-progress.yml` - the estate's clock: every fifteen minutes, it
  computes the report and publishes it to the estate bucket (`state/progress`). It commits
  nothing to main and gates nothing.
* On demand - `bin/estate-progress --publish`, or the intent with `fresh=true`.

## Who reads it

* `/fleet` - the fleetview backend's `/progress` route
  (`backstage/plugins/fleetview-backend/src/fleetview_backend/progress.py`), and the `/estate`
  strip's `progress` segment.
* voice and any agent - the `estate.progress` intent.
* the one Prometheus - `estate-progress.prom`.

## What it writes

```
~/.estate/progress/estate-progress.json   # the canonical signal set, including its spoken sentence
~/.estate/progress/estate-progress.prom   # the same numbers as Prometheus exposition
~/.estate/progress/estate-progress.md     # the human view
```

and, published:

```
oci://estate-drill-receipts/state/progress
```

## The verdict

| verdict | meaning |
|---|---|
| `PROGRESSING` | something landed in the window, no rate tripped, nothing blind |
| `SLIPPING` | a third or more of the window's batches conflicted, or a third or more of its CI runs failed, or nothing landed while lanes are in flight |
| `STUCK` | nothing landed, lanes in flight, the oldest held 120 minutes or more |
| `PARTIAL` | it would have been PROGRESSING, but a source was blind |
| `UNKNOWN` | the Greenlane state could not be read; there is no chain to grade |

## Reading it honestly

* A source that could not be read is listed under **Blind** with the reason. It is unknown, never
  zero. A flattering zero is the failure this report exists to prevent.
* The **delta** section compares this report with the previous one over the same window. On the
  first run there is no delta, and the report says so.
* The `estate_progress_*` Prometheus gauges use `NaN` for a signal that could not be read, so a
  blind plane cannot pass as a healthy zero.

## Adding a signal

1. Add it to the signal set in `bin/estate-progress` (source, semantics, unit, TTL, failure
   mode), and to the atomic table in the spec.
2. Render it wherever it belongs - one place for the JSON, one for the exposition, one for the
   human view.
3. Pin it: a scenario in `features/estate-progress/estate-progress.feature` if it carries the
   verdict, a unit test otherwise.

Do not measure it in a surface. If a surface needs it, the signal set grows once and every
surface gets it.
