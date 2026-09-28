# Demo: grade Otto's three homes

This walks through what `bin/idp-otto-homes` does and what its answer means. It changes
nothing — `status` only asks questions, and it is the default subcommand for that reason.

## Door (from the UI)

Backstage → the `otto-gateway` component → **Otto homes**. The card shows the same three
verdicts this page produces, refreshed on the estate's schedule. Nothing below needs a terminal
to read; the commands are here so the card can be checked against the thing it reports on.

## Run it

```
bin/idp-otto-homes
```

## What comes back

```
  1 cluster        otto.<zone>                MEASURED_OK    HTTP 200
  2 cloudflare     lifeboat-llm.<zone>        MEASURED_FAIL  no answer
  3 macbook        100.x.y.z (tailnet)        MEASURED_OK    HTTP 200
```

Three rows, one per home, in the estate's three-state vocabulary: `MEASURED_OK`,
`MEASURED_FAIL` or `UNKNOWN`. Never "up", never "healthy". A home is graded by asking it a
question only a working home can answer, and by grading the captured answer rather than piping
a probe into a test — a failing left-hand stage in a pipe inverts a verdict silently, which is
what LAW 55 and `bin/idp-pipeverdict` exist to prevent.

The command exits zero even when a home is red. It is a status board, not a gate: a red home is
a report. Otto still answers while any one of the three is green, which is the entire point of
there being three.

## Why each row is asked the way it is

**Home 1, the cluster.** Probed at `/healthz`, not `/health`. Otto's gateway answers 404 on
`/health`, `/ready` and `/`, so a probe written against the obvious path grades a working
cluster as dead.

**Home 2, the Cloudflare edge.** Probed at `/health` on the Worker, which touches no vendor and
reads no key — so a red row here means the Worker is gone, never that a model lane is out of
quota.

**Home 3, the MacBook.** Probed at its *tailnet address*, read live from
`tailscale status --json`, never at its MagicDNS name. Ollama refuses a `Host` header it does
not recognise: the same machine answers `HTTP 200` by address and `HTTP 403` by name. This one
detail is the difference between a working home and a home reported dead.

## The other two subcommands

`bin/idp-otto-homes deploy` publishes home 2 to Cloudflare and pipes its secrets in on stdin,
so no key is ever an argument, an environment variable or a line of scrollback.

`bin/idp-otto-homes cutover` prints what repointing Telegram's webhook to the edge would
require and then does nothing. Repointing the founder's live assistant is a production change,
and a production change waits for his own plain words.

## The design behind it

[Otto's survival matrix](../../explanation/otto-survival-matrix.md) explains what a *home* is,
why five model lanes in one pod were never three homes, and the arithmetic that makes the
bottom of the ladder inexhaustible.
