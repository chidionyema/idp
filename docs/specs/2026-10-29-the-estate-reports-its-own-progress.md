# The estate reports its own progress

Status: first slice landed; the surfaces read this report, they do not measure anything themselves.
Owner: the delivery chain (`greenlane`, CI, Flux, claims, the decision door).
Ticket: #6687 (the founder's ask, already open; this fills its named gaps).

## The problem, measured

The founder asked, more than once, for one plan for metric collection across the estate, and
asked how a self-improving estate can be blind to its own data. The estate was not blind because
the data was missing. It was blind because the data was **never joined**:

| what exists | where it lives | who reads it |
|---|---|---|
| the Greenlane state: per-lane timings, failure reasons, batch cycles, landings | one JSON blob on `refs/greenlane/state` | `bin/idp-greenlane status`, the Fleet HUD, and nobody else |
| CI: every run, its jobs, its conclusion, its duration | the GitHub Actions API | the merge queue, the founder's patience |
| claims: who is working which files, and whether two agents collide | the focus register | the write gate |
| the founder's queue: asked, answered, expired | `~/.estate/sovereign/decisions.json` | the decision door |
| what became live: Flux, pods, nodes | the cluster receipt in the object store | `bin/idp-cluster-state` |
| what the estate owns and where it drifts | `bin/idp-inventory` (six planes, four verdicts, a BLIND row per unread plane) | a table in `docs/inventory.json` |

Three measurements from this session show the blindness is not a theory:

1. **The estate's own inventory has never been produced on this laptop.**
   `~/.estate/inventory/inventory.json` does not exist. The committed `docs/inventory.json` records
   `kubernetes: UNKNOWN`, `github: UNKNOWN`, `mac: UNKNOWN`, `oci: UNKNOWN`, `tailscale:
   UNKNOWN` - five of six planes blind, because the collectors run from a laptop that cannot
   reach the cluster and does not have the SaaS readers installed.
2. **The inventory's Prometheus feed goes nowhere.** `bin/idp-inventory` writes
   `inventory.prom` ("the third feed into the one Prometheus"), and nothing in the repository
   scrapes it: no textfile collector, no pushgateway, no job that ships it. The one Prometheus in
   `platform/monitoring` therefore never sees the estate's own inventory.
3. **The Greenlane holds the delivery metrics and hides them.** Its own map
   (`platform/estate/intents/map.greenlane-live.yaml`) names the gaps: "status hides landings +
   per-lane arrived/attempts; no stored per-check progress; no push-to-live measure". The state
   blob holds `landed`, `landings`, `arrived`, `attempts`, `reason` and per-batch cycles for 778
   landed lanes, 209 conflicts and 423 timed-out lanes; the surfaces see a summary.

So the estate could not answer "are we progressing?" because progress was never defined as a
measurement, and "is what we are doing making sense?" was answered by reading 778 lane names.

## The plan: one signal set, one writer, many readers

**One writer.** `bin/estate-progress` computes the report. It runs on the estate's own clock -
the scheduled workflow `.github/workflows/estate-progress.yml`, every fifteen minutes, the
free-tier rung - and publishes one artefact to the estate bucket (`state/progress`), beside the
cluster receipt every surface already knows how to read. It writes three forms:
`estate-progress.json` (the canonical signal set), `estate-progress.prom` (the same numbers as
Prometheus exposition, for the one Prometheus) and `estate-progress.md` (the human view).

**One signal set.** Every surface renders the same numbers. A surface that wanted a new number
adds it to the signal set, once; it does not measure it twice.

**The sentence travels inside the report.** The report carries its own canonical spoken sentence
(`speak`), produced by the same function that `--speak` prints. That is what lets a host with no
writer installed still say exactly what the estate says, instead of each surface inventing its
own wording for the same numbers.

**Many readers.** `/fleet` reads it through the fleetview backend's `/progress` route
(`fleetview_backend/progress.py`), the voice surface speaks the intent's last line, any agent
asks the `estate.progress` intent, and the Prometheus scrapes the exposition. Nothing in a
surface computes estate state.

**Why per-surface metrics are not feasible, and what solves it.** Each surface would have to
learn the Greenlane's state format, the CI API, the claims register and the receipt schema, and
keep them current: four integrations times every surface, each one wrong in a different way.
The estate already has the machinery that removes this duplication:

| need | the estate's existing tool | what it already does |
|---|---|---|
| infrastructure metrics | kube-prometheus-stack in `platform/monitoring` (one Prometheus), Coroot for the service map, ServiceMonitor and blackbox probes for the founder's surfaces | already scrapes the cluster; the rules plane already probes the voice service and the founder surfaces |
| traces | the OTLP door (issue #5935, one OTLP door to Grafana Cloud) | the decision is open; this report does not duplicate it |
| LLM calls | Langfuse, and AEI (issue #7311) for the estate's own model-call record | AEI measures one call; it does not measure the estate's progress |
| the estate's own work | this report | the delivery chain, joined |
| the estate's own resources | `bin/idp-inventory` | six planes, four verdicts, BLIND never zero |
| one claim's pace | `fleetview_backend/plan_pace.py` (and `bin/estate-work-status`) | how long THIS claim's remaining sub-goals take, from its own checklist |

So: **the estate does not need a metrics layer per surface; it needs one measurement per
question, and one rendering per surface.** That is the whole architectural answer.

The last row matters: `bin/estate-work-status` and `plan_pace.py` answer "where does this agent
stand, and how long is its remaining work?" - one claim, on demand, read-only. This report
answers "is the estate progressing, and what is stuck?" - the whole chain, on a clock. They are
not two copies of a layer: one is a per-claim reader of the issue and the claim, the other is the
aggregate the surfaces render.

## The signal set (atomic)

Every signal names its semantics, unit, source, transport, store, owner, cadence, freshness TTL
and failure mode. "Unknown" is a value: a source that cannot be read contributes a BLIND row and
no number, and the verdict degrades from `PROGRESSING` to `PARTIAL`. A missing measurement is
never zero.

| signal | semantics | unit | source | transport | store | owner | cadence | TTL | failure mode |
|---|---|---|---|---|---|---|---|---|---|
| `chain.landed_in_window` | lanes that reached `main` inside the window | count | Greenlane state `landings` | git ref read | `estate-progress.json` | greenlane | 15 min | 30 min | no state ref readable -> BLIND, chain unknown, verdict UNKNOWN |
| `chain.landed_total` | lanes that ever reached `main` | count | Greenlane state `landed` | git ref read | same | greenlane | 15 min | 30 min | as above |
| `chain.lanes_inflight` | lanes the Greenlane holds right now | count | Greenlane state `lanes` | git ref read | same | greenlane | 15 min | 30 min | as above |
| `chain.oldest_lane_age_min` | age of the oldest lane still in flight | minutes | `lanes[*].arrived` | git ref read | same | greenlane | 15 min | 30 min | as above |
| `chain.queue_to_land_min.p50/p90` | minutes from a lane's head first seen to its landing | minutes | `landings[*].queued`, `landings[*].landed` | git ref read | same | greenlane | 15 min | 30 min | as above |
| `chain.batch_cycle_min.p50/p90` | minutes from a batch's start to its verdict | minutes | `history[*].started`, `history[*].verdict_at` | git ref read | same | greenlane | 15 min | 30 min | as above |
| `chain.conflict_batches_in_window` | batches in the window that ended in a conflict | count | `history[*].outcome`/`action` | git ref read | same | greenlane | 15 min | 30 min | as above |
| `chain.top_failure_reasons` | the reasons lanes are red, with the URL stripped to `<url>` | count | `lanes[*].reason` | git ref read | same | greenlane | 15 min | 30 min | as above |
| `ci.runs_in_window` | CI runs started inside the window | count | Actions API | gh api | same | ci | 15 min | 30 min | gh missing or API failing -> BLIND `ci_runs` |
| `ci.failed_in_window` / `ci.fail_rate` | runs that concluded `failure` | count / ratio | Actions API | gh api | same | ci | 15 min | 30 min | as above |
| `ci.duration_min.p50/p90` | wall time of a run | minutes | Actions API | gh api | same | ci | 15 min | 30 min | as above |
| `ci.top_failing_workflows` | which gate fails most | count | Actions API | gh api | same | ci | 15 min | 30 min | as above |
| `claims.live_claims` / `claims.stale_claims` | claims alive (heartbeat under 2 h) and lapsed | count | focus register | file read | same | estate | 15 min | 30 min | register missing -> BLIND `claims` |
| `claims.overlapping_paths` | paths two live agents both hold | count | focus register | file read | same | estate | 15 min | 30 min | as above |
| `decisions.asked/answered/expired` | what the founder was asked and what came back | count | decision-door state | file read | same | otto | 15 min | 30 min | state file missing -> BLIND `decisions` |
| `live.flux_not_ready` | Flux Kustomizations not ready | count | cluster receipt | object store | same | flux | 15 min | 60 min | receipt older than 60 min -> BLIND `cluster_receipt`; a stale receipt is not a fact |
| `live.pods_not_ready` | pods not ready | count | cluster receipt | object store | same | flux | 15 min | 60 min | as above |
| `deltas.landed_in_window` | landed this window minus landed last report | count | this report vs the previous | file read | same | estate | 15 min | 30 min | no previous report -> `available: false`, never a fake zero |
| `deltas.queue_to_land_p50_min` | median wait, this report minus last | minutes | same | file read | same | estate | 15 min | 30 min | as above |
| `verdict.state` | PROGRESSING / SLIPPING / STUCK / PARTIAL / UNKNOWN | enum | the signals above | computed | same | estate | 15 min | 30 min | chain unknown -> UNKNOWN |
| `speak` | the canonical spoken sentence for this report | text | the signals above | computed | same | estate | 15 min | 30 min | a surface with no report speaks `unknown`, never a zero |

### The verdict, deterministically

No model reads a number in this report. The thresholds are written down here and pinned by
`tests/test_estate_progress.py`:

* `UNKNOWN` - the Greenlane state could not be read. There is no chain, so there is no verdict.
* `STUCK` - nothing landed in the window, lanes are in flight, and the oldest has been held at
  least 120 minutes.
* `SLIPPING` - a third or more of the window's batches ended in conflict, or a third or more of
  the window's CI runs failed, or nothing landed while lanes are in flight.
* `PROGRESSING` - something landed, no rate tripped.
* `PARTIAL` - it would have been PROGRESSING, but at least one source was BLIND. The estate does
  not get a clean bill of health it did not earn.

### The door, and where the writer lives

`platform/estate/intents/estate.progress.yaml` is the door every surface calls. It prints ONE
line - the spoken sentence - because the voice surface speaks an intent's last stdout line. It
serves the cached report by default (`fresh=true` recomputes it now), so a surface never waits
on a measurement to answer the founder.

The writer is resolved, in order, because the default root is a working checkout that may be on
any branch:

1. `~/.estate/bin/estate-progress` - the copy the runtime sync stages from `main`, so it is the
   same bytes main carries, whatever this laptop's checkout happens to be on.
2. `~/.estate/runtime/idp/bin/estate-progress` - the estate's own main tree.
3. `<root>/bin/estate-progress` - the repo it was given.

With none of them, the door still speaks: the report's own `speak` field is read from
`~/.estate/progress/estate-progress.json` (override with `ESTATE_PROGRESS_REPORT`). With no
report either, it says `Estate progress: unknown. No progress report is available on this host.`
- unknown, never a zero, never a healthy green.

Measured defect this fixes (2026-10-29): the intent's root default was `~/Documents/code/idp`,
and the executor shell-quotes every argument, so the tilde was never expanded and the path was
literal. On a host whose checkout is on a work branch the writer was not there at all
(`ls ~/Documents/code/idp/bin/estate-progress` -> `No such file or directory`). The default is now
empty and the script expands `$HOME` itself.

### How progress is proven

Not by a feeling and not by a green badge: by the **delta** between this report and the last one,
over the same window, on the same signals, with the same sources. A report that cannot compare
itself to its predecessor says so (`deltas.available: false`) instead of inventing a baseline.

## What this does not do

* It does not measure the cluster's internals: Prometheus, Coroot and the rules plane own those.
* It does not replace `bin/idp-inventory` (what the estate owns) or AEI (what a model call cost).
  It joins the delivery chain, which nothing else joined.
* It does not decide anything, gate another agent's work, or call a model.
* It does not restore the estate-wide `./platform/observability` Flux row.

## The surfaces, and what each one does with this

| surface | reads | renders |
|---|---|---|
| `/fleet` (the work surface) | the backend's `/progress` route | the chain: landed, in flight, stuck with reasons, the delta since the last tick |
| `/face` | the same JSON | one line, and it speaks it |
| voice | the `estate.progress` intent | the intent's last stdout line: the verdict in a sentence |
| any agent | the `estate.progress` intent | the same sentence, or the JSON |
| the one Prometheus | `estate-progress.prom` | the same numbers as gauges |
| Telegram (Otto) | the door's state | what the founder was asked and what came back |

Every surface renders the same signal set. That is what makes the estate self-reporting instead
of blind: one measurement, many mouths.
