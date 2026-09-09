# Onboarding: keeping every repository on the one board

## What this is for

The estate has one board. It is a Linear workspace, team MUM, and the point of it is that a person
can look in one place and see what is outstanding without opening twenty repositories. That only
works if every repository actually reaches it, and until now exactly one did.

`bin/idp-linear-mirror` is the check that keeps the promise honest. It reads the board and the
repositories, compares them, and tells you which repositories the board is not showing you.

## Running it

```
bin/idp-linear-mirror
```

It needs a Linear API token. It takes one from the `LINEAR_API_TOKEN` environment variable if you
have set one, and otherwise reads vault entry `cyrus-linear-api-token` — the same entry the cyrus
deployment already reads, so nothing new was minted for this and there is no second credential to
rotate. The token is never printed, and neither is any part of it.

Exit codes, because this runs in CI as well as by hand:

| exit | meaning |
|---|---|
| 0 | every repository with an open issue is on the board |
| 1 | one or more are not; the run names them and prints the founder's action |
| 2 | it could not measure — no token, no network, or an answer it could not read |

Two is deliberately not a pass. A check that could not see anything must say so.

## When it fails

A failing run ends with a `FOUNDER ACTION` block: the settings URL, four numbered steps, and the
repositories to connect listed largest first. Connecting a repository is a row on
<https://linear.app/crewestate/settings/integrations/github> — pick team MUM, set the direction to
two-way, done. There is no API for it; Linear owns that page.

Before you work down the list, read the headroom line the run prints just above it. Linear's free
plan counts active issues against 250 and counts Done and Canceled until they are archived. If the
run says the gap is larger than the headroom, connecting everything will not give you a fuller
board — the overflow is refused. The fix for that is already in the tree:
`platform/linear/setup.py` turns on auto-archive at one month and auto-close at three, and running
it frees the room the new repositories need.

## Where it fits

It measures a rule the founder set on 2026-09-09 — "all repos should just map the same way" — and
it is the only thing in the estate that can tell whether that rule currently holds. Nothing else
looks at the board from the outside. Before this, the fact that eighteen repositories had never been
connected was discoverable only by someone who happened to count.
