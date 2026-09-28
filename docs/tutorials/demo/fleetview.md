# FleetView CP1 — the session contract, seen running

This is what the board's data layer does when you run it, with the real output.

## What it is

Every agent runtime in the estate — Claude Code sessions, sovereign engine sessions, and the
runtimes CP4 adds — becomes **one session record** with the same shape. The board, the drawer, the
signal buttons and the customer's own adapter all speak that one shape.

The shape is a versioned file: `backstage/plugins/fleetview-backend/schema/session.json`.

## See it

Against the estate's real prompt ledger:

```console
$ curl -s http://127.0.0.1:18790/api/fleetview/sessions | jq length
5
```

The spec's own done-command for this checkpoint is that number being 1 or more.

The envelope it returns:

```console
$ curl -s http://127.0.0.1:18790/api/fleetview/sessions | jq '{available, count: (.sessions|length), unreachable}'
{
  "available": true,
  "count": 5,
  "unreachable": []
}
```

One record out of the five:

```console
$ curl -s http://127.0.0.1:18790/api/fleetview/sessions | jq '.sessions[0]'
{
  "session_id": "-Users-chidionyema-Documents-code-prospector",
  "runtime": "claude-code",
  "task": "-Users-chidionyema-Documents-code-prospector",
  "state": "unknown",
  "repo": null,
  "step": null,
  "updated_at": null,
  "trace_url": null,
  "spend_usd": null,
  "pull_requests": [],
  "ticket": null
}
```

`state` is `"unknown"`, not `"running"`. The catalogue says which ledgers exist; it does not say a
session is live. A board that guessed `"running"` here would show a green row for a session that
ended last week.

## Against the cluster

With the port-forward to the estate's Temporal:

```console
$ kubectl -n temporal port-forward svc/temporal-frontend 17233:7233
$ TEMPORAL_HOST=127.0.0.1 TEMPORAL_PORT=17233 TEMPORAL_NAMESPACE=estate \
    python backstage/plugins/fleetview-backend/src/serve.py 18790 backstage/plugins/fleetview-backend/src/routes.py
$ curl -s http://127.0.0.1:18790/api/fleetview/sessions | jq '{count: (.sessions|length), unreachable}'
{
  "count": 5,
  "unreachable": []
}
```

`unreachable` is empty: the sovereign adapter reached the engine and answered. It contributed zero
rows because the engine is running zero sessions — an empty engine is not an error, and the
adapter says so rather than inventing a row.

## When something breaks, it says so

Point it at a catalogue that is not there and you get a 503 with the reason, not an empty board:

```console
$ curl -s -o /tmp/out -w '%{http_code}\n' http://127.0.0.1:18790/api/fleetview/sessions
503
$ jq . /tmp/out
{
  "available": false,
  "error": "FileNotFoundError: catalogue not readable: /data/catalog-info.yaml",
  "sessions": [],
  "unreachable": [],
  "generated_at": "..."
}
```

"no sessions" and "I could not read the sessions" are different facts, and the page renders them
differently. An unavailable board must never look like a quiet one.

## The tests behind it

```console
$ pytest sovereign/tests/bdd/test_fleetview_cp1.py -q
4 passed
```

Four scenarios, bound from `features/fleetview/cp1_contract.feature`, including two that drive the
HTTP route the spec's done-command calls. They fail with the plugin removed and pass with it in the
same session.

## CP2 — the board itself

The page lives at `/fleet` on the portal. It shows every agent session the estate knows about:
which runtime, what it is working on, whether it is still running, what it has cost, and which pull
request it opened. It updates itself; there is nothing to refresh and nothing to poll.

```console
$ yarn workspace app test Fleet
Test Suites: 2 passed, 2 total
Tests:       15 passed, 15 total
```

The board distinguishes three facts that a lesser dashboard collapses into one:

| what is true | what the page shows |
|---|---|
| the source could not be read | **Unavailable**, with the cause in the sentence above |
| the estate really has nothing running | "No sessions are running." |
| one runtime did not answer | a live board whose sentence names the gap |

A session whose runtime did not say whether it is running reads **Unknown**, never **Running**. And
a session nobody measured the cost of shows a dash, not `$0.00` — zero is a measurement, a dash is
the absence of one.

The whole portal suite, proving the page did not disturb anything else:

```console
$ yarn workspace app test --watchAll=false
Test Suites: 27 passed, 27 total
Tests:       221 passed, 221 total
```

## Placement: why the cluster can be full and idle at once

The Ops page (`/ops`) now carries a **Placement** section. It answers the question that had no
page: *could the workloads that run be placed on the nodes that exist, and how much of the CPU we
reserve is actually used?*

Real output from the cluster on 2026-09-12, when the second catalogue replica would not schedule:

```
$ kubectl describe pod catalogue-... | grep FailedScheduling
  0/2 nodes are available: 1 Insufficient cpu, 1 node(s) didn't match pod anti-affinity rules.

$ kubectl top nodes
NAME           CPU(cores)   CPU(%)
10.0.148.221   2283m        39%
10.0.159.197   4974m        85%

$ kubectl describe node 10.0.148.221 | grep -A3 "Allocated resources"
  Resource           Requests      Limits
  cpu                5680m (97%)   19885m (342%)
```

Read those three together and the message `Insufficient cpu` is misleading. The cluster is at
**97% of CPU requests** and **39% of actual usage**. Requests are reservations. A reservation
nobody uses is a place no pod can have, so the scheduler refuses a 250m pod on a node that is
running at 2283m out of 5808m.

The page says exactly that. Its sentence is:

```
2 pods the scheduler refused · 26 pinned (running, but no other node would take them)
  · 5089m reserved but idle (49% of all requests)
```

And the three facts it refuses to collapse into one:

| what is true | what the section shows |
|---|---|
| the scheduler refused it | **not running at all** — listed first, because it is an outage, not a risk |
| it runs but fits no other node | **pinned** — looks fine, and gone after one drain |
| it could be placed again | healthy |

*Pinned* is the one nobody sees coming. It is the state SigNoz's ClickHouse sat in for eleven days:
running, apparently healthy, and it would not come back after a node drain.

## Where the numbers come from

Nothing here is a new measurement. The cluster already runs `platform/state/cluster-state.yaml`
every 15 minutes, computing a `placement` section and the CPU requested/used totals.
`bin/idp-fits-a-node` already grades it in CI. What was missing was publishing it where a person
could read it: a job's stdout reaches nobody who is trying to decide whether to buy a node.

So `.github/workflows/oke-check.yml` publishes the placement document to the state branch the
portal already reads, `bin/catalog-render` carries it forward past each force-push, and `/ops`
renders it. One measurement, one door.
