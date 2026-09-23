# Backstage as a product: catalogue.\<zone\> for a buyer, not a link farm

## Why (founder's own words, 2026-09-05)

> "a lot of backstage is rubbish and not useful containing github links instead of actual thing,
> while github links are useful it actually does nothing for what the capability or tool is,
> need to see, visualise and interact. needs spec across the board to turn this into proper
> product, also showcase needs to wow and impress."

The portal already proves it can do better than a link: `/tools`, `/ops`, `/investigate`,
`/reports` and `/pair` (`backstage/packages/app/src/modules/home/*.tsx`) read the cluster live,
draw it, and in two cases (Investigate, Pair my phone) let the founder act and see the result in
place. Most of the catalogue does not do that yet. Of the 52 hand-written founder-surface
entities in `backstage/founder/catalog-info.yaml`, roughly half carry nothing but a link to a
GitHub blob of a Kubernetes manifest — a manifest is not a capability, and a manifest is
certainly not a demo. This spec is the plan to make every surface either prove itself is a
proper product or be told plainly why it cannot be, and to make `/showcase` the page that does
the impressing.

## Definition of a proper surface

Four levels. A surface names its level in this spec's inventory table and the data source that
backs it. Level 1 is refused for any surface built or touched from this spec onward.

| Level | Bar | Example already in the portal |
|---|---|---|
| **1 — link-only (refused)** | The card's only content is a link to a GitHub file or an external console. Nothing on the card is true right now; it is only ever true when the linked page loads, on someone else's site. | `founder-collector`, `founder-policies` — a link to a manifest |
| **2 — live state** | The card or page shows a value read fresh, on load, from a named data source. No link required to know the fact. | Ops page's healthcheck tiles, read every 60s through the `/healthchecks` proxy |
| **3 — visual** | The live value is drawn, not printed: a graph, a donut, a bar, a countdown, a log tail, a diagram — something a person reads in one look, the way `StateDonut`/`SystemBars` (`modules/home/visuals.tsx`) draw layer health today. | EstateHome's per-system health bars |
| **4 — interactive** | A control changes something or asks something, and the answer renders in the same page, without a tab change. | Investigate's ask box (`/holmes` proxy), Pair my phone's PIN submit (`/sunshine` proxy) |

Every surface's row in the inventory below names its **level today** and its **data source**:
one of the Kubernetes proxy (`kubernetesApiRef`, already wired for every entity carrying
`backstage.io/kubernetes-label-selector`), the estate-state branch proxy (`/estate-state`,
`app-config.yaml`), the Holmes proxy (`/holmes`), a Telegram deep link, or a scaffolder button
(`backstage/templates/founder-actions/*`, one per dispatchable GitHub Actions workflow).

## The inventory table

Source: `backstage/founder/catalog-info.yaml` (52 `Component`/`type: founder-surface` entries,
read 2026-09-06). "K8s tab" means the entity carries `backstage.io/kubernetes-label-selector`
and so gets Backstage's own generic pod/deployment tab; that is level 2 on its own merit, but
none of these cards draw anything from it — the tab is a click away, not on the card.

| Surface (`metadata.name`) | Today | Level | Data source today |
|---|---|---|---|
| `founder-catalogue`, `founder-tools`, `founder-ops`, `founder-investigate`, `founder-reports`, `founder-pair-phone`, `founder-screen` | in-house page, live cluster read, drawn, and (Investigate, Pair) interactive | **3–4** (model to copy) | kubernetes proxy + `/estate-state` + `/holmes` + `/sunshine` |
| `founder-gods-view` | markdown doc served from GitHub via TechDocs, one static link out | 1 | none — static doc |
| `founder-model-router` | two external links (`llm.<zone>`, `llm.<zone>/ui`) — the router UI is real and live, the card is not | 1 | none on the card |
| `founder-traces`, `founder-dashboards`, `founder-telemetry` | external link + one health-endpoint link | 1 | none on the card — vendor has no portal proxy today |
| `founder-jobs` | external link; the same data is already live elsewhere in the portal (Ops page, `/healthchecks` proxy) | 1 on the card, 2 exists elsewhere | `/healthchecks` proxy (Ops page only) |
| `founder-login` | external link to the IdP's own sign-in page | 1 (acceptable — see Non-goals) | none |
| `founder-crew-board` | four GitHub links (issues, P1 filter, `STATE.md`, `STANDARDS.md`) | 1 | none |
| `founder-showcase` | two GitHub links (a markdown file, a shell script) | 1 | none |
| `founder-mcp-gateway` | one endpoint link + one manifest link | 1 | none |
| `founder-platform-repo` | four GitHub links (PRs, security, packages, docs) | 1 | none |
| `founder-drills` | nine GitHub Actions links | 1 | none on the card — verdict data exists (`verdict-backstage`, `verdict-langfuse`, `verdict-signoz` workflows) but nothing reads it into the portal |
| `founder-cloud-console` | external console link + doc link | 1 | none |
| `founder-telegram` | `t.me` deep link | 4, off-portal | Telegram (acceptable — see Non-goals) |
| `founder-kini-finish` | three GitHub links | 1 | none |
| `founder-store` | live storefront link (the product itself is live and real) | 2, off-portal | none on the card |
| `founder-otto`, `founder-cursor` | manifest/dashboard links | 1 | none |
| `founder-otto-door` | one `/healthz` link | 1 (a raw JSON page is not a card) | none on the card |
| `company-mumchimp`, `company-prospector`, `company-hermes` | link to a catalogue Domain page | 1 | none on the card |
| `founder-models-mac`, `founder-dagster` | link to the estate Mac's remote-screen anchor | 1 (the screen itself, once opened, is level 4) | none on the card |
| `estate-scheduler`, `founder-commerce`, `founder-temporal`, `founder-alerts`, `founder-status-page`, `founder-hindsight`, `founder-chaos`, `founder-network-map`, `founder-metrics`, `founder-edge-router` | GitHub manifest link only (`founder-temporal`, `alerts`, `chaos`, `network-map`, `metrics`, `edge-router` also carry `kubernetes` tag but no `kubernetes-label-selector` annotation — no K8s tab either) | 1 | none |
| `founder-gitops`, `founder-policies`, `founder-healing`, `founder-autoscaling`, `founder-secrets-sync`, `founder-certificates`, `founder-dns`, `founder-workload-identity`, `founder-private-network`, `founder-collector`, `founder-cluster-plumbing` | GitHub manifest link only, tagged `kubernetes` / `no-screen`, no `kubernetes-label-selector` | 1 | none |

Same pattern one layer down: `backstage/platform/catalog-info.yaml` (64 `Component`/
`type: platform-layer` entries) every one of which carries a `kubernetes-label-selector`
annotation (real level-2 data, one click into the generic K8s tab) and exactly one link,
`https://signoz.${ESTATE_ZONE}`, titled "Live logs and metrics" — level 1 on the card itself,
because nothing on the card says whether the layer is up.

**The count**: of 52 founder surfaces, 6 are already level 3–4 (the in-house pages), 2 are
level 2/4 off-portal by design (Telegram, the login redirect), 1 is level 2 off-portal (the
store), and **43 are level 1** — a card whose only fact is a URL. Of 64 platform layers, all 64
are level 1 on the card and level 2 one click away.

## The showcase page (`/showcase`)

This is the flagship, because it is the page a buyer's engineer opens first. Today
`docs/SHOWCASE.md` is a generated markdown file read through GitHub or TechDocs — a report, not
a room. It becomes an in-house page (`modules/home`, in the same shell as Tools/Ops/Reports)
built the same way EstateHome is: catalogue query plus one Kubernetes proxy read, `Promise.all`,
refreshed on a clock.

**What it shows live, without a click:**
- The estate bar from `bin/estate-showcase`'s own numbers (entities ELITE/GAP/BLIND, standards
  rows live/not-yet), read from the generated `docs/SHOWCASE.md` front matter through the
  `/estate-state` proxy pattern (the file already regenerates on the `estate-showcase` schedule;
  the page reads the rendered numbers, it does not recompute them) — level 2, on this page.
- A live health donut per system (`system:default/delivery`, `edge`, `identity`, `observability`,
  `scheduling`, `agents`, `resilience`, `products`, `data`, `commerce`), reusing `StateDonut` and
  `SystemBars` from `modules/home/visuals.tsx` — level 3, the same component EstateHome already
  draws with.
- The five Otto capabilities marked LIVE in `docs/specs/otto-capability-inventory.md`, each with
  its one-line proof file reference — level 2, read from that file's own status table, not
  retyped.

**What a visitor can press, and see happen in the same page:**
- **Launch the buyer sandbox.** This is the centrepiece (CP1/CP2 below). One button, one
  scaffolder action (`backstage/templates/founder-actions/`, following the generated pattern
  `bin/idp-portal-buttons` already stamps from a workflow), dispatching a new
  `demo-sandbox-launch.yml` workflow that runs the exact `flux create kustomization
  demo-sandbox ...` command `docs/runbooks/demo-sandbox.md` already documents by hand. A person
  still presses the button — this spec does not let an agent launch it (`docs/runbooks/
  demo-sandbox.md`: "agents never deploy") — but it stops being a command a person has to type.
- **The countdown**, once launched: the Kustomization's own `cleanup.kyverno.io/ttl` label and
  creation timestamp, read through the same kubernetes proxy `useEstate.ts` already uses,
  rendered as a shrinking bar with a plain-English "N minutes left, then it is gone" line —
  level 3, and the proof the buyer's platform team came to see (bounded, catalogued, mortal).
- Ask Investigate a question about the sandbox itself ("what is running inside demo-sandbox
  right now?") through the existing `/holmes` proxy — no new door, the same one `/investigate`
  already opens.

## Per-surface requirements

One row per group from the inventory, the minimum change to reach at least level 3 (visual).
Every row keeps LAW 46: the proxy or annotation holds the target, never a literal host.

| Group | To reach level 3+ |
|---|---|
| The 20 "GitHub manifest link only" platform-tool surfaces (`founder-gitops` … `founder-cluster-plumbing`, `founder-alerts`, `founder-temporal`, `founder-commerce`, `founder-hindsight`, `founder-status-page`, `founder-chaos`, `founder-network-map`, `founder-metrics`, `founder-edge-router`, `founder-mcp-gateway`, `founder-otto`, `founder-cursor`, `estate-scheduler`) | Add `backstage.io/kubernetes-label-selector` (the manifest already names the workload's labels — no new probe, just the annotation `bin/catalog-gen` already knows how to stamp for platform layers) and add the shared "layer card" component (CP4) so the entity page draws Flux Ready state, pod count and last-deploy time the moment it opens, matching what platform layers already get one click away. |
| `founder-model-router`, `founder-traces`, `founder-dashboards`, `founder-telemetry`, `founder-jobs` | A one-line proxy per vendor (`/langfuse`, `/signoz`, `/superset` — none exist yet, see Data sources) returning one counted fact (trace count last hour, error rate, healthcheck pass count) drawn as a single stat tile on the card, the same shape `useHealthchecks.ts` already reads for the Ops page. |
| `founder-drills` | Read the three `verdict-*` workflows' own signed verdicts (they already write a check-run and a row) through a small proxy, and show last-verdict-per-drill as a status list, not nine links. |
| `founder-crew-board` | One proxy call to the GitHub issues API (already how `crew status` reads it) for open-count and P1-count, shown as two live numbers above the links. |
| `founder-otto-door` | Render the `/healthz` JSON as a status pill (up/degraded/down) rather than linking to raw JSON — same shape as `doorState()` in `modules/home/estate.ts`. |
| `founder-showcase` | Superseded by `/showcase` (this spec); the entity becomes a pointer to the in-house page, not to a markdown file. |
| `founder-gods-view`, `founder-platform-repo`, `founder-cloud-console`, `founder-kini-finish` | Founder-only operational docs and third-party consoles genuinely outside the estate's own render surface — see Non-goals. |
| 64 platform layers | Batch: `bin/catalog-platform` (the generator) gains one card component (CP4) reused across all 64, so a single change lifts every layer at once — never edited one at a time. |

## Data sources we already have, and the ones missing

**Have:** the Kubernetes proxy (`kubernetesApiRef`, live pods/deployments/Flux Kustomizations,
used by `useEstate.ts` and `useClusterHealth.ts`); the `/estate-state` proxy (raw GitHub
content, read-only, GET); the `/holmes` proxy (POST, in-cluster Service, no credential); the
`/healthchecks` proxy already declared in `app-config.container.yaml`; the `/sunshine` proxy for
Pair my phone; 29 scaffolder buttons (`backstage/templates/founder-actions/`) each dispatching
one named GitHub Actions workflow, generated by `bin/idp-portal-buttons` so a workflow with no
button fails CI.

**Missing:** a Langfuse proxy, a SigNoz proxy, and a Superset proxy — the three vendor dashboards
in the inventory that are level 1 on the card today have no in-portal door at all; every read
goes straight to the vendor's own login. Also missing: a signed-verdict reader for the
`verdict-*` workflow outputs, and a countdown-capable read of a Kustomization's TTL label
(a one-field addition to the same Kubernetes proxy call `useEstate.ts` already makes).

## Non-goals

- No surface embeds a third-party product's full UI in an iframe — CSP, auth-cookie scoping and
  the vendor's own clickjacking headers make that a security regression, not a feature (LAW 21).
  A proxy returns one counted fact, drawn by our own component; it does not frame the vendor.
- `founder-login`, `founder-telegram`, `founder-cloud-console`, `founder-store` stay as they
  are: a login redirect, a phone deep link, a third-party console, and a live product outside
  the platform's own catalogue, respectively. None of the four is a platform tool the founder
  self-serves through the portal, and framing any of them inside the portal buys nothing.
- No agent gains a new capability to launch or delete the buyer sandbox. The button in CP1/CP2
  is a person's button; `docs/runbooks/demo-sandbox.md`'s "agents never deploy" line is
  unchanged.
- No new second copy of a dashboard, a metrics store or a scheduler. Every proxy this spec adds
  reads a system that already runs; none stands one up.

## Definition of done, in commands

```sh
yarn --cwd backstage backstage-cli repo test        # portal unit suite, green
yarn --cwd backstage backstage-cli repo lint --since origin/main
gh workflow run login-drill.yml -f evidence_paths="/showcase,/tools,/ops"   # screenshot evidence, green run
gh run list --workflow=login-drill.yml --limit 1 --json conclusion -q '.[0].conclusion'   # "success"
```

The screenshot-evidence gate is not a new workflow: `login-drill.yml` already accepts
`evidence_paths` and `bin/idp-login-drill` already screenshots every path it is given
(`page.screenshot(...)`, `shot_dir`). CP8 changes the default `evidence_paths` so every login
drill run — hourly, not only on demand — captures `/showcase`, `/tools` and `/ops`, and wires
that run's artifact into `docs/reference/policy/definition-of-done.md` Gate 2's "Demo" row as
the standing evidence for this spec, rather than a bespoke script.

## Checkpoints, ordered by buyer impact

- **CP1**: `/showcase` exists as an in-house page (catalogue query + Kubernetes proxy, no
  markdown render), showing the live estate bar, the per-system health donuts, and the five
  Otto LIVE capabilities — nothing pressable yet.
- **CP2**: The buyer sandbox gets a launch button on `/showcase` (a new scaffolder template
  dispatching a new `demo-sandbox-launch.yml`, running the exact command
  `docs/runbooks/demo-sandbox.md` already documents) and a live countdown to its
  `cleanup.kyverno.io/ttl` expiry, read through the Kubernetes proxy.
- **CP3**: A Langfuse proxy, a SigNoz proxy and a Superset proxy exist (`app-config.yaml`
  `proxy.endpoints`), and `founder-traces`, `founder-telemetry`, `founder-dashboards` each show
  one live counted fact on the card instead of only a link.
- **CP4**: A shared "layer card" component (Flux Ready state, pod count, last-deploy time) is
  built once and rendered on every `type: platform-layer` entity page (64 layers, one change).
- **CP5**: The 20 "GitHub manifest link only" founder-surface entities gain
  `backstage.io/kubernetes-label-selector` and the CP4 layer card, so no founder-surface entity
  in the catalogue ships with zero live content.
- **CP6**: `founder-otto-door`, `founder-mcp-gateway`, `founder-otto`, `founder-cursor` each show
  a live status pill from their own health endpoint through a proxy, replacing a manifest link.
- **CP7**: `founder-drills` and `founder-crew-board` read their own live counts (last verdict per
  drill; open/P1 issue counts) instead of listing bare links.
- **CP8**: `login-drill.yml`'s default `evidence_paths` covers `/showcase`, `/tools`, `/ops`
  on every hourly run, and that run's screenshot is the standing Demo-gate evidence in
  `docs/reference/policy/definition-of-done.md`.
