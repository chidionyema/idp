# Onboarding: estate-request-router

## What it is

`bin/estate-request-router` routes an inbound request (a message, an issue, a
PR comment) to the estate System that owns it. It is slot 3 of the seven-agent
local ops tier (crew#929, roster in `docs/ops/local-ops-tier-roster.md`).

## Why it exists

Every session someone decides "who handles this" — the recurring routing
question. A router that resolves clear requests to their owning System and
refuses ambiguous ones takes that scan away while staying deterministic and
auditable.

## Where the lanes come from

The owning Systems are read at run time from
`backstage/platform/catalog-info.yaml` (the delivery, edge, identity,
observability, scheduling, agents, resilience, products, data, and commerce
Systems). The router never hardcodes a lane list, so a System added to the
catalog is routable immediately without a code change. Point `ESTATE_CATALOG`
at another catalog file to route against a different inventory.

## How it routes

The request text is matched against each System's name and description after
common stopwords are removed. A System wins when it clearly carries the most
matching signal; a request that ties two Systems, or matches none, is refused
with the nearest candidates named.

## The contract

- A clear request resolves to exactly one owning System (`ROUTE:<system>`).
- An ambiguous or unmatched request is refused with exit code 1 and the nearest
  candidates — a lane is never guessed (the roster's no-op rule).
- Only the request's own text is read and only a route decision is returned; the
  request body is never forwarded or logged to another lane (LAW 21).
- Run it in the ops tier so an inbound issue is pre-routed to its owner before a
  human or frontier call has to read it.
