# Onboarding — the estate portal

## What it is for

Somebody who is not you needs to look at this estate and form a view without you
sitting beside them. An investor, a buyer, a new agent session, or you in three
months having forgotten the details. The portal is the thing they open. It lists
every asset the estate owns, what state each one is in, and what is wrong — and
every number on it links to the query that produced it, so nothing has to be
taken on trust.

It exists because LAW 41 says the buyer arrives tomorrow and you are not in the
room, and LAW 39 says the inventory is only finished when something reads it.

## What it costs

Nothing per month. Backstage, Datasette and sqlite-utils are all Apache-2.0 and
free. Tailscale's free tier covers a single machine. Everything runs on this Mac,
so there is no hosting bill and no account to keep alive.

The real cost is not money. Backstage ships a new version every month and only
backports security fixes for about six months, so it will need a version bump two
or three times a year. That is the whole reason the fallback exists: when a
Backstage upgrade goes wrong, nothing goes dark.

Disk: about 900 MB, almost all of it Backstage's `node_modules`.

## What it watches and what it changes

It reads `~/.estate/state/inventory.json` and nothing else. It writes only inside
`~/dev/code/idp/catalog/`. It changes nothing about the estate, runs no jobs,
touches no repositories and holds no credentials.

The one thing outside its own directory it does touch is the Tailscale serve
configuration, where it claims ports 8443 and 10000. Port 443, which serves the
founder board on 8787, is left exactly as it was.

## Where it lives

```
~/dev/code/idp/
  bin/            six commands, all shell or short Python
  catalog/        the generated catalogue: one YAML file, one SQLite file
  backstage/      the Backstage app (generated, ~1700 npm packages)
  .venv/          Datasette and sqlite-utils
  docs/           this file and the demo
```

## Is it public

No. It is on the tailnet only, which means your devices and nothing else. The
catalogue is a map of every asset the estate owns — paths, repository names, job
names, which drills have never run. There are no secrets in it and it is still
not something to publish by accident.

To show it to somebody outside: `bin/idp-publish on`. It prints what becomes
visible before it does anything, and `bin/idp-publish off` reverses it. Making it
public needs HTTPS certificates enabled for the tailnet, which is one switch in
the Tailscale admin console and is the only step here that needs your hands.

## How to turn it off

```
bin/idp-down
```

That stops both renderers and removes both published ports. Nothing is left
running and nothing is deleted.

## How to turn it back on

```
bin/idp-up
```

It regenerates both renderings from the current inventory, starts whichever
renderer is not already up, republishes both ports and then prints the status.
Running it twice is harmless.

## What goes wrong

**Backstage will not start.** Most likely a Node version. It needs Node 20 or 22;
the system Node on this Mac is 26, which is too new, so everything Backstage runs
through nvm's 22.13.1. The fallback is unaffected and is still serving.

**Both portals show the same wrong number.** That is the design working. Both are
renderings of one inventory, so a wrong inventory produces two identical wrong
portals. Fix the inventory; never edit `catalog-info.yaml` or `estate.db`, because
the next run overwrites them.

**A portal shows nothing at all.** It should not be possible: both generators
refuse to write an empty catalogue, because an empty portal looks exactly like a
healthy portal with nothing wrong. If one is genuinely empty, the generator did
not run — check the inventory file exists.

**A portal shows some of the estate and looks fine.** This is the dangerous one
and it has already happened once: Backstage silently rejected 141 of 194
entities and served the other 53 as a complete-looking catalogue. `bin/idp-up`
now ends with `bin/idp-verify`, which compares what the generator wrote against
what each renderer actually serves and names anything missing. If it says FAIL,
the portal is lying and the reason is in `logs/backstage.log` under "Policy
check failed".

**The URL does not resolve on this Mac.** Expected. This machine does not resolve
its own MagicDNS name. It resolves from your phone and from any other device on
the tailnet.

**The published link points at the wrong thing.** `bin/idp-switch primary` or
`bin/idp-switch fallback`. It refuses to point the link at a renderer that is not
answering.

## The catalogue on Kubernetes (Phase 2 of ADR 0004)

`platform/backstage/base` is the same `idp/backstage:local` image that `backstage/compose.yml`
builds, as a Deployment plus a Postgres StatefulSet, in a namespace that enforces the
`restricted` Pod Security Standard. `overlays/local` adds the two things that come from this
machine: the estate ConfigMap from `catalog/catalog-info.yaml` and the `backstage-env` Secret from
the gitignored `backstage/.env`. No Ingress, NodePort or LoadBalancer exists; `bin/idp-ci` renders
the base and fails on any of them.

```
make cluster-up
make catalogue-deploy     # build, k3d image import, kubectl apply, wait for rollout
# then the port-forward line it prints: 127.0.0.1:3100
```
