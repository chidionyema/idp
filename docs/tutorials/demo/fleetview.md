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
    python /tmp/serve_fv.py 18790 backstage/plugins/fleetview-backend/src/routes.py
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
