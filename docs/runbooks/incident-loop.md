# The incident loop

**One error becomes one prioritised ticket, one dispatched agent, one merged fix, one lesson,
and one measured MTTR.** This is the R-14 path of the estate master epic
(`docs/epics/2026-10-25-estate-master-epic.md`):

> an error results in a ticket being raised, prioritised, assigned and depending on capacity an
> agent is automatically launched

The epic's own coverage table recorded R-14 as **missing**, with the reason measured: *"no path
from a red CI job to an owned ticket to a dispatched agent (C-03)"*. Every part of that path
existed separately — `flux-events.yml` opened issues, `bin/claim-open` claimed them,
`lane-submit` raised the PR, `platform/queue/dispatcher.py` held a task table, and
`sovereign/engine/workflow.py` ran one session per agent. The join did not, and two things
inside it did not exist at all: a **priority function** (the queue's `tasks` table has no
priority column) and **one incident record** (there were four ledgers — the intent-run ledger,
claim issues, work-audit findings and Greenlane lanes; epic F-05).

## The shape

```
   sense ──▶ fingerprint ──▶ one ledger row ──▶ score ──▶ one ticket, one label
     ▲                                                            │
     │                                                            ▼
   verify ◀── lesson ◀── verdict + MTTR ◀── dispatch (session | worker queue)
```

| stage | what actually happens | where |
|-------|----------------------|-------|
| sense | red GitHub Actions runs on the watched repos; the executor's own refusal ledger (`~/.estate/friction/events.jsonl`) | `sense_ci`, `sense_doors` |
| fingerprint | sha256 of `source|repo|key` — the same error sensed twice is one incident | `fingerprint` |
| ledger | one sqlite table, `incidents`, in `~/.estate/state/incidents.db` | `open_ledger` |
| score | severity + blast radius + age + capacity cost, each capped | `score_incident` |
| ticket | exactly one GitHub issue per incident, labelled by the score | `raise_ticket` |
| dispatch | a session on the sovereign bus when the bus answers and a session is free, otherwise the estate's own task queue | `dispatch_incident` |
| verify | a later green run for the same branch, a quiet door, or a closed ticket | `verify_incident` |
| lesson | one line into the estate knowledge graph | `write_lesson` |
| MTTR | seconds from `first_seen` to `verified` | `mttr_seconds` |

## The doors

```bash
bin/estate-incident-loop tick       # one pass of the whole loop
bin/estate-incident-loop sense      # what the sensors see right now
bin/estate-incident-loop list       # the ledger
bin/estate-incident-loop show <id>  # one incident
bin/estate-incident-loop report --title "..." --severity major --url "..."
bin/estate-incident-loop drill status
```

The same code is the governed intent `incident-loop` (`platform/estate/intents/incident-loop.yaml`),
so an agent reaches the loop through the executor rather than by shelling out.

## Where it runs

The loop runs **on this Mac**, on a launchd timer, because the estate's placement ladder
(`docs/decisions/0034-workloads-are-placed-by-the-free-tier-not-by-the-cluster.md`) puts work on
the laptop just in time, and because the cluster cannot serve it today. The plist template is
`launchd/ai.estate.incident-watch.plist.tmpl`; the installed job is
`~/Library/LaunchAgents/ai.estate.incident-watch.plist` and it runs `bin/estate-incident-loop tick`
every five minutes. Its log is `~/.estate/state/incident-watch.log`.

The sensors read GitHub and the estate's own state, so the loop keeps working while the cluster
is down — which is exactly when it is needed.

## The policy is data, and it is the only one

`catalog/incident-policy.json` decides severity points, blast-radius weights, the age and
capacity-cost caps, the label thresholds, the SLAs and the dispatch rules. Nothing else may
decide priority: a second priority function is a second convention, which is what AGENTS.md §6
calls stitching.

The dispatch leg is chosen by **measured** capacity, not by hope:

- the bus answers and fewer than `dispatch.max_sessions` sessions are running and the score is
  at or above `dispatch.session_min_score` → a **session** (`bin/sb start`, cloud route first,
  the founder's local Claude Code lane second);
- otherwise → the **worker queue** (`platform/queue/dispatcher.py`, the estate's one queue).

## The sealed-failure drill

The epic's Phase 1 exit is a failure injected on purpose that closes itself. The drill does
exactly that:

```bash
bin/estate-incident-loop drill seed --worktree <worktree> --lane lane/incident-drill-<stamp>
#   -> writes tests/test_<today>_incident_drill_canary.py into the worktree with a
#      deliberately wrong assertion. It writes; it does not commit. The commit is the
#      estate's business: the claim gate wants the trailers, the Greenlane wants the lane.
git commit -am "..." # Claim: #<issue>  /  Agent: <name>
lane-submit <drill-lane>
#   -> the Greenlane builds a candidate, CI goes red for a real reason
bin/estate-incident-loop tick
#   -> the loop senses the red run, raises one ticket with its priority, dispatches it
bin/estate-incident-loop drill fix --worktree <worktree>
#   -> the canary is rewritten to the true assertion; commit and lane-submit it again
#   -> the lane goes green, the Greenlane merges it, and the loop verifies the incident,
#      writes the lesson and measures the MTTR
```

Nothing in the loop is special-cased for the drill: the same sensors, the same ticket, the same
dispatch, the same verdict.

Two things the drill taught the runbook, both measured:

- **The canary must live where CI collects it.** `bin/idp-tests-for`'s blanket runs every cheap
  `tests/test_*.py`; nothing collects `platform/estate/tests/`. A canary in a directory no CI job
  collects is a drill that cannot fail.
- **The canary must carry the day it was injected.** The estate's own rule (`bin/test-executes-gate`)
  refuses a test file named for a rule rather than for the day something broke: `test_incident_*`
  is a note about one instance, and the next session reads the name and writes the next one.

## What it is not

- It is not a second claim system. `bin/claim-open` still claims the work; the loop's ticket
  carries the incident, and the worker that fixes it claims the files it touches.
- It is not a second queue. The worker leg pushes onto `platform/queue/dispatcher.py`'s table.
- It does not merge anything. The Greenlane merges the fix, as it merges everything else.
- It is not a monitoring dashboard. It is a loop: it opens, dispatches, verifies and learns.
