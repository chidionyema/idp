# Moving the board to the production cluster

The laptop is the backup environment. It is where we prove a thing works before the cluster
runs it. Founder, 2026-08-24: "this laptop is just to prove things work", "its a backup env,
not prod, we are still buildig prod cluster".

## What ports and what stays

The seamless login is not a laptop trick that gets thrown away on the way to the cluster.
Kanboard reads the signed-in user from a request header. Something upstream sets that header.
Only that something changes:

| | who sets the header | what the founder sees |
|---|---|---|
| backup env (laptop) | nginx, to a fixed value, on a loopback-only port | no login screen |
| production cluster | an identity proxy, after real authentication | signs in once, at the estate's front door |

Same `REVERSE_PROXY_AUTH` mechanism, same three environment variables. The migration is a
swap of who sets the header, not a rewrite. `kanboard.laptop.yml` is the only file that does
not travel, and it is separated from the base for exactly that reason.

## What has to be decided before it moves, and by whom

Two of these are platform-layer choices. Under the one-platform rule they are chosen once for
the whole estate and recorded as a row in `crew/docs/STANDARDS.md`, not chosen here for the
board alone.

1. **The identity proxy.** One for the estate. Whatever fronts Backstage, Langfuse and
   Datasette fronts the board too. Not yet chosen, and this file does not pick it.
2. **The database.** Kanboard runs on Postgres, and the estate already runs Postgres, so the
   board does not bring a new database with it. `DB_DRIVER=postgres` and four environment
   variables; the password comes from the estate secret vault by name and is never in a file
   in this repo.
3. **The data.** One SQLite file today, `data/db.sqlite`. It is a migration, not a copy, and
   it has never been rehearsed. Until it has been, moving the board means re-importing from
   `crew/ESTATE_STATE.md` and the open pull requests, which is how the cards got here in the
   first place.

## What is not true yet

Nothing above has been booted. There is no `kanboard.server.yml` in this directory, because a
config that has never started is not a plan and would read as one. This file records the shape
of the move and what blocks it. The blocker is item 1, and it is bigger than the board.
