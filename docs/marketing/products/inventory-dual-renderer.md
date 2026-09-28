# Inventory + Dual-Renderer

> One source of truth, two renderers, runtime-separated fallback — for
> platform teams that have outgrown a wiki and don't want to be Backstage
> admins.

## The problem

You have an inventory of what is running. You need a portal where people
find it. The wiki is wrong. The spreadsheet is stale. The Backstage
instance the platform team stood up a year ago is hitting the wall: the
catalog has drifted from the manifests, the auth integration needs a
maintainer, and the ticket backlog is measured in months.

You do not want to be a Backstage admin. You want the portal to render
the inventory, and you want the fallback to be a different runtime so
the buyer is not stuck on a single point of failure.

The Inventory + Dual-Renderer is that pattern, packaged.

## What you get

- **One inventory format.** A YAML or JSON file, owned by you, in your
  repo. The renderer reads it; you write it. *Benefit: the inventory is
  not a separate silo; it is in git.*

- **Two renderers, runtime-separated.** Backstage (node) is the primary
  portal; Datasette (python) is the fallback. They share no runtime —
  one bad node install does not take both down. *Benefit: a buyer is not
  stuck on a single point of failure.*

- **A switch, not a choice.** The published URL routes to whichever
  renderer is up. The fallback exists for the case where a link has
  already been handed to somebody. *Benefit: the buyer does not have to
  pick.*

- **A failover contract.** The fallback was the bug that was in
  Datasette — a `mv` over an open handle left the renderer serving stale
  data. The fix is in: SQLite's online backup API writes into the
  existing file under a writer's lock, so the open reader keeps its
  handle and reloads. *Benefit: the failover is not a slide; it is a
  fix that ships.*

- **A upgrade contract.** The renderers are upgraded through Git. The
  inventory is the contract; the renderers can be replaced. *Benefit:
  lock-in is on the surface, not in the data.*

- **A generator.** `bin/catalog-gen` produces the YAML from your repo;
  `bin/db-gen` produces the SQLite. Both are adapters over the inventory
  LAW 39 already produces. *Benefit: nothing about the estate is stored
  in the renderer's repo.*

## How it works

You point the renderers at one inventory file. Backstage reads it on a
poll; Datasette reads it through the SQLite backup API. The published URL
is one — the gateway switches between renderers with no operator
intervention.

The renderers are swappable: a buyer can replace Backstage with another
Backstage install, with a wiki, or with nothing — the inventory is what
holds. The renderers are a renderer.

## Why us

- **The catalogue is the asset, the portal is a renderer.** That is the
  architecture rule on record. *Benefit: lock-in is on the surface, not
  in the data.*
- **Runtime-separated fallback.** Most portals' fallback shares the
  primary's runtime. Ours does not. *Benefit: one bad node install
  cannot take both renderers down.*
- **The fix is shipped.** The `mv` bug was real; the SQLite backup API
  fix is in. The failover is not a slide; it is a fix that ships.

## Pricing

| Tier | Price | What you get |
|---|---|---|
| Solo | $50/month | Single inventory, both renderers, the failover contract |
| Team | $500/month, up to 25 entities | Up to 25 entities, both renderers, the upgrade contract, GitHub Action |
| Enterprise | Contact us | Unlimited entities, custom renderer, dedicated support, on-prem |

A 30-day trial of the Team tier is available with the install wedge.

## Get started

- **Run the install wedge.** `idp/quickstart` spins up both renderers on
  k3d in 30 minutes. The failover is automatic.
- **Read the architecture.** `docs/explanation/architecture-overview.md`
  has the 10-second switch and why the fallback is real.
- **Read the fix.** `b06d05c` is the SQLite backup API commit. The fix
  is on the record.
- **Call us.** For the Enterprise tier, for a custom renderer, or for a
  procurement-grade security one-pager.

The inventory is the asset. The portal is a renderer. Replace the
renderer when it is wrong; the estate does not move.
