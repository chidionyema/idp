# 4. The catalogue runs as a container, and the interim is a bridge

Date: 2026-08-24
Status: accepted

## Context

The founder asked, on 2026-08-24: *"who made that decision?"* — about the
catalogue running as a bare `yarn start` process on the laptop.

The honest answer is that nobody recorded making it. `git log -- bin/idp-up`
shows two commits, `9c380d8 feat: two-renderer portal over the estate inventory`
and `f124792 feat: the portal starts itself and stops undoing the switch`, both
authored "Chidi Onyema" because agent sessions commit under his git identity.
There is no ADR, no Dockerfile for the app, and no line anywhere weighing the
alternative. An agent picked the shape that was quickest to get on screen, and
the shape stuck because nothing was written down that could be argued with.

That is the defect this ADR exists to close, and it is a bigger one than the
runtime it is about. The estate has 16 rows in `crew/docs/STANDARDS.md` and, as
of this morning, three ADRs. Decisions taken by whichever session was open are
invisible to the other five, so the next session inherits a choice with no
reasoning attached and either obeys it or silently reverses it.

What `yarn start` actually was, measured on this machine on 2026-08-24:

- `bin/idp-up` sourced nvm and prepended `~/.nvm/versions/node/v22.13.1/bin` to
  `PATH` — a path that exists on exactly one computer.
- The webpack dev server refuses any `Host` header that is not `app.baseUrl`.
  The tailnet link at `:8443` returned **403**; it had never worked from another
  device, and nothing said so.
- The app bound `[::1]:3100` and the backend bound `127.0.0.1:7107`. One product,
  two address families. `curl 127.0.0.1:3100` returned `000` while a browser on
  the same machine got `200`, which is why `bin/idp-up` concluded the portal was
  down on every hourly run and started a second copy on top of the first.
- The database was `better-sqlite3` at `:memory:`, so every restart re-ingested
  the whole estate — 124 seconds, measured — and served a portal that rendered
  correctly with nothing in it.
- Nothing was deployable, so the k3s migration in the other lane would have
  started from zero.

Meanwhile the k3s cluster is being brought up by another session and is expected
green in roughly 48 hours. The founder's constraint was explicit: *"We cannot
wait 48 hours to have a working Backstage, but we also cannot accept the brittle
yarn start laptop hack."*

## Decision

**The catalogue is a container image, built from source by
`backstage/Dockerfile`, and it is the same image in every environment.**

Locally it is run by `backstage/compose.yml`. In the cluster it is run by
Kustomize manifests that ArgoCD reconciles. The compose file is deleted when the
cluster takes over.

**An interim is acceptable only when it is the same artefact as the destination
and its removal is one delete.** This is the generalisable rule, and it is what
separates a bridge from a second platform. `yarn start` fails it on both counts:
it is a different artefact (a dev server, not an image) and removing it means
rewriting the startup path. A container passes it on both.

Three specifics, each of which was a real choice:

1. **Multi-stage, not the scaffolder's `packages/backend/Dockerfile`.** That file
   is a host build — it requires `yarn install && yarn tsc && yarn build:backend`
   on the machine first, with the same Node major as the image. Host node here is
   v26.7.0, the image is `node:24`, and `package.json` declares
   `engines.node: 22 || 24`, so the host build is not runnable on this laptop at
   all. `better-sqlite3` is a native module, so a Node mismatch does not fail
   loudly — it yields an image that crashes at `require()`. Multi-stage puts the
   toolchain inside the build, where its version is a property of a committed
   file rather than of a laptop. Backstage documents this alternative itself.

2. **`yarn build:all`, not `yarn --cwd packages/backend build`.** Backstage's own
   multi-stage example builds the backend only and its documentation states that
   bundle does not contain the frontend. This app runs
   `@backstage/plugin-app-backend` (`packages/backend/src/index.ts:13`), so the
   backend serves the UI. Building the backend alone produces an image that
   starts, answers `/api/catalog`, and serves a blank page — a failure that looks
   like success, which is the category this estate keeps paying for.

3. **Postgres, not in-memory sqlite.** It is what the cluster will use, so Phase 2
   changes where the database runs rather than which database it is, and it ends
   the 124-second window where the portal is up and empty.

## Consequences

**Two ports become one.** The image serves the UI and the API on 3100, published
as `127.0.0.1:3100` and nothing else. Port 7107 is removed from
`catalog/ports.yaml`, and with it the CORS rule the portal needed in order to
talk to its own backend.

**The `0.0.0.0` bind inside the container does not violate R20.** R20 governs
what this machine exposes. A container's network namespace is not the host's: a
process binding `127.0.0.1` inside a container is reachable only from that
container, and the published port cannot forward to it. `compose.yml` publishes
`127.0.0.1:3100:3100`, so `lsof` on the host sees the loopback and the LAN sees
nothing. `bin/port-gate --live` reads host binds and is the check that holds this.

**`bin/idp-up` becomes a reconciler.** `docker compose up -d --wait` is
idempotent, so the hourly launchd run converges instead of stacking copies. The
probe-then-`nohup` shape that caused the duplicate-start bug is gone entirely
rather than repaired.

**There is no default password anywhere.** `bin/idp-up` generates the Postgres
password with `openssl rand` under `umask 077` into `backstage/.env`, which
`idp/.gitignore` already covers via `**/.env`. Postgres has no `ports:` key.

**The tailnet 403 is expected to clear**, because the built app is static assets
served by the backend rather than a dev server enforcing a Host allowlist. That
is a consequence to verify after the first deploy, not a claim.

**This ADR is the record the next session argues with.** If containerising was
wrong, the reasoning is here to be attacked. That is the actual fix for *"who
made that decision?"* — not this particular runtime.

## Alternatives rejected

**Keep `yarn start` for 48 hours and go straight to k8s.** Rejected: the
migration would then have no image to migrate, so the cluster lane would have to
invent the packaging under time pressure, and the 403, the split address family
and the duplicate-start bug would all still be live in the meantime.

**Use a published Backstage image.** There is none that fits. `ghcr.io/backstage/backstage`
exists but is the upstream demo app; a Backstage deployment *is* your own source
— your plugins, your `app-config.yaml`, your catalog. There is no vendor image
that can serve this estate's catalogue, and `docker.io/library/backstage` and
`spotify/backstage` do not exist (checked 2026-08-24).

**Run Postgres on the host instead of in compose.** Rejected: it adds a host
service to install, secure and back up that the cluster will not use, which is
the definition of an interim that does not port.
