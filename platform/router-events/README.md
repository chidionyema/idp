# Router events — the database announces itself

Founder, 2026-09-12, the decision:

> *"We eliminate the 5-minute polling script entirely. We rely on physics. ... We don't disable the
> database. We weaponize it."*

**The database is the source of truth for routing. Git is the backup.** This directory is the
wiring that makes that safe: every write to a routing lane announces itself the instant it commits,
so nothing has to poll and nothing has a blind spot.

## The four pieces

| # | Piece | What it does |
|---|---|---|
| 1 | `trigger.sql` | Postgres `NOTIFY` fires inside the writing transaction |
| 2 | `publisher.yaml` | a listener catches the notification, publishes `estate.ai.router.changed` to JetStream |
| 3 | the estate twin | subscribes; the graph is millisecond-accurate |
| 4 | `backup.yaml` | a second listener pulls the lane table from the admin API and commits it to git |

## Why the payload carries no secret

`pg_notify` is visible to **every session on the database**. A payload naming a key would be a
key leak to anything that can `LISTEN`. So the event carries only `op`, `table`, `model` and the
timestamp — **where to look, never what is there.** The reader fetches the truth from the source.

## Why git is the backup and not the source

If `estate-db`'s volume is lost, the lanes are gone with it. So a listener writes the routing table
to git on every change. Restoring is then a matter of applying the last commit — and no human has
to remember to run anything.
