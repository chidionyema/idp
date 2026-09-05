# idp — the estate's internal developer platform

Two portals over one catalogue, running at the same time, sharing no runtime.

```
~/.estate/state/inventory.json        the source. LAW 39 produces it hourly.
        |
        +-- bin/catalog-gen  -->  catalog/catalog-info.yaml  -->  Backstage   :3100
        +-- bin/db-gen       -->  catalog/estate.db          -->  Datasette   :8001
```

Neither portal is the source of truth. Both are renderings of the inventory, which
is plain JSON on disk. That is the whole design: a renderer you can replace in one
command is not a dependency.

## Why two

Backstage is the recognised answer and the one an outsider expects to see. It is
also 1,900 npm packages, a Node major-version floor and a monthly release train,
and any one of those can stop it booting on a Tuesday.

Datasette is the fallback. It is Python, it starts in under a second, it has no
build step, and it has never heard of Node. A broken `node_modules` cannot take it
down, which is the only property a fallback actually needs.

Same pattern as Fly and this laptop: the fallback is not a plan, it is already
running.

## The two switches

**0 seconds.** Both are up at their own URLs. If one is wrong, open the other. No
command, no failover, no waiting.

**10 seconds.** `bin/idp-switch fallback` repoints the published URL at Datasette
without the URL changing. That is for when the link has already been handed to
somebody and the thing behind it has to change.

`bin/idp-switch` refuses to point the link at a renderer that is not answering.
A switch to a dead process is a second outage, not a failover.

## Reachability

Tailnet only. The catalogue is a map of every asset the estate owns — paths, repo
names, job names, which drills have never run. There are no secrets in it and it
is still not something to publish by accident, so the default is closed (LAW 21).

`bin/idp-publish` turns on Tailscale Funnel and makes the primary URL public. It
is one command, it prints what becomes visible before it does anything, and it is
the founder's call rather than an agent's.

## Commands

| command | what it does |
|---|---|
| `bin/catalog-gen` | inventory → `catalog/catalog-info.yaml` (Backstage entities) |
| `bin/db-gen` | inventory → `catalog/estate.db` (SQLite, via sqlite-utils) |
| `bin/idp-up` | regenerate both, start both, publish on the tailnet, verify |
| `bin/idp-down` | stop both renderers and unpublish both ports |
| `bin/idp-status` | what is serving, where, and whether it is public |
| `bin/idp-verify` | does what is published match the inventory, entity by entity |
| `bin/idp-switch primary\|fallback` | repoint the published URL |
| `bin/idp-publish on\|off` | make the primary URL public, or stop |

Both generators refuse to write an empty catalogue. An empty portal renders
identically to a healthy one with nothing wrong, which is the failure mode worth
guarding.

## Boundary

- **In:** `~/.estate/state/inventory.json`, one JSON object with a `rows` array.
- **Out:** a Backstage entity file, a SQLite database, and two HTTP services.
- **Needs:** Python 3 (venv, in-repo), Node 22 and yarn for Backstage only,
  Tailscale for publishing. Nothing else, no account, no hosted service.

Swap the inventory for any other JSON with the same shape and this works unchanged.

## Cost

$0 per month. Backstage is Apache-2.0, Datasette is Apache-2.0, sqlite-utils is
Apache-2.0, Tailscale's free tier covers this, and it all runs on the Mac.
