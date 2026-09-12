# Onboarding: FleetView

## What it is for

One screen where you see every AI agent you run — what each is working on, what it costs, which
pull request it opened — and from which you can stop, approve, deny or steer any of them. No
terminal. From a phone if you want.

The board is a product. It sits inside the estate's portal, behind the estate's login, and a
customer can be given only their own fleet.

## Where it lives

| piece | path |
|---|---|
| the record every runtime must emit | `backstage/plugins/fleetview-backend/schema/session.json` |
| the adapters and the record builder | `backstage/plugins/fleetview-backend/src/sessions.py` |
| the routes | `backstage/plugins/fleetview-backend/src/routes.py` |
| the acceptance criteria | `features/fleetview/cp1_contract.feature` … `cp5_offering.feature` |

The routes:

- `GET /api/fleetview/sessions` — every session, one JSON envelope.
- `GET /api/fleetview/stream` — server-sent events; one frame per session change. This replaces
  the old three-second poll.

## What it costs

FleetView is sold inside the Platform plans and standalone. Standalone: the Team plan price,
**$24,000 a year**, for up to ten agent runtimes. Enterprise includes it.

It runs on the estate that already exists — the same portal, the same cluster, the same login.
There is no second server to pay for and no second account to create.

## How to stop it

The board is read-only until you press a button. To take it out of service, remove the
`fleetview-backend` mount from the portal's router and redeploy the portal; the adapters stop
being called and nothing else in the estate is affected. No data is written anywhere except the
audit table, which records who pressed which signal and when.

## Adding your own runtime

Write one adapter that emits the record in `schema/session.json` and it appears on the board with
its trace, spend and pull requests enriched, exactly like the built-in runtimes. The schema is the
whole integration surface; there is no second API to learn.

## What is not here yet

Checkpoints CP2–CP5 are specified in `docs/specs/2026-09-08-fleetview-backstage-offering.md` and
not yet built: the `/fleet` page itself, the four signal buttons, the extra runtime adapters, and
tenant scoping. CP1 is the contract and the routes underneath them.
