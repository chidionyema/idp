# Front ends in the estate (crew#694 CP0)

Inventory taken 2026-09-30 by reading each repo (no build run). "Served" means a Flux row or an
edge route exists for it; it does not mean it was watched working today.

| Front end | Path | Framework | Design source | Served |
|---|---|---|---|---|
| Backstage portal, incl. FleetView (`modules/home`, `modules/room/ui`) | `idp/backstage/packages/app` | Backstage new frontend system, React 18, MUI v4, @backstage/ui, three 0.158, @xyflow/react | `src/modules/theme/tokens.ts` ("quiet instrument"), `modules/home/DESIGN-RULES.md` (25 rules), `POLISH-SPEC.md`; no Tailwind | Yes: `clusters/oke/backstage.yaml` → `platform/backstage/overlays/oke`, HTTPRoute `catalogue.mumchimp.com` |
| Store.Web (mumchimp.com, www) | `prospector/store_platform/src/Store.Web` | Next 16 pages router, React 19, Tailwind v4, Storybook, Playwright, Lighthouse | `src/styles/tokens.css` (202 tokens, Brand v3) **and** `mumchimp.css` (a second `:root`); 215 purity violations measured | Yes: `prospector/deploy/k8s/base/edge.yaml` (apex, www, api listeners), pulled by `idp/clusters/oke/ingress.yaml` |
| Ops.Console | `prospector/store_platform/src/Ops.Console` | Next 16, Tailwind v4 | none of its own | No route found |
| Status page | `idp/platform/edge/status-page.yaml` | static HTML in a ConfigMap (nginx) | hard-coded `#0f1115`, system-ui | Yes: Traefik 502/503/504 pages |
| Cockpit | `idp/sovereign/cockpit/` | single-file HTML Telegram Mini App + stdlib Python server | none | No (`docs/marketing/capabilities.md`: "not running") |
| Deploy visualisations | `idp/web/templates/deploy-{river,observatory,time-scrub}.html` | static HTML | none | No |
| Docs (idp, crew) | `idp/mkdocs.yml`, `crew/mkdocs.yml` | mkdocs, rendered by TechDocs in the portal (ADR 0002) | mkdocs theme | Via the portal |
| Newsroom | backend `idp/platform/voice-router/internal/newsroom/*.go`; UI is `NewsDesk.tsx` in the portal | Go + portal React | portal tokens | Via the portal |
| portfolio-site | `~/Documents/code/portfolio-site` | Astro 6, React islands, Tailwind 3, framer-motion | own | haworks-platform.pages.dev (`astro.config.mjs:39`) |
| tfp ("tasks-for-perks") | `~/Documents/code/tfp` | Next 15, Tailwind, framer-motion | own | unknown |
| precedent, precedenty | `~/Documents/code/precedent{,y}` | Next + Tailwind + framer-motion templates | template | No |
| mumchimp-medusa storefront | `mumchimp-medusa/apps/storefront` | Medusa Next 15 starter | template | No |
| Home | `~/Documents/code/Home` | CRA "business-consulting-site" (title "React App") | none | No |
| hermes-agent web | `hermes-agent/web` | Vite, React 19, Tailwind 4, three, gsap, motion | own | unknown |
| hermes-agent website | `hermes-agent/website` | Docusaurus | theme | unknown |
| Chrome extension popup | `idp/packages/chrome-extension` | HTML | none | n/a |
| look-engine (crew#232) | `prospector/docs/storefront/look-engine` (prototype only; branch gone) | — | 10 looks, 40 screens; never reached Store.Web | No |

**No company website exists.** `www.mumchimp.com` is the Store.Web shop. crew#690 is the build ticket;
crew#235 holds the earlier decision; crew#691 (company name) is open.

**Design sources today:** two (portal `tokens.ts`, Store.Web `tokens.css`) plus one stray `:root` in
`mumchimp.css`. The kit in `packages/estate-ui-kit/` (crew#694 CP2) replaces all three with one file.

## Addendum 2026-10-01 (second sweep, read-only)

Rows the 2026-09-30 table missed or got wrong, from a full `find` over `~/Documents/code`:

| Front end | Path | Framework | Design source | Served |
|---|---|---|---|---|
| bytesync-web (company site, crew#690) | `~/Documents/code/bytesync-web` (local only; **no GitHub remote**) | Next 16.3 App Router, static export, React 19, Tailwind v4, Vitest, Playwright, Lighthouse | its own `:root` in `src/app/globals.css` (oklch, a **fourth** token system) | `deploy.yml` to Cloudflare Pages exists; real domain unset; not verified live |
| Store.Web, correction | as above | as above | as above | Served by **Fly** (`store_platform/deploy/fly/web.fly.toml`, `fly certs add mumchimp.com`) and a k8s manifest in prospector, not by an idp Flux row |
| hermes-agent desktop | `hermes-agent/apps/desktop` | Electron, Vite, React 19, Tailwind v4 | `DESIGN.md` (rules, no token file) | desktop app |
| ironcage UI | `ironcage/ui/index.html` | one HTML page embedded by `include_str!` in the Rust API | none | with the API image |
| survival-stack lighthouse | `survival-stack/lighthouse/index.html` | one static page + a Worker | none | not yet (`REPLACE_WITH_KV_ID`) |
| hermes-config mini-app | `hermes-config/mini-app/index.html` | one HTML file | none | unknown |
| nextjs-lucia-auth template | `~/Documents/code/nextjs-lucia-auth-email-password-reset-drizzle` | Next 14, Tailwind 3, shadcn | template | No |

Not found anywhere: `pixer-react`, `ecommerce-frontend`, any web UI in hermes-v2 (Python; chat surface adapters only).

**Duplicates:** the Backstage app is checked out three times (`idp`, `idp-memory-bdd`, `agent-workspaces/task-e2etest2`, the last a broken worktree link); precedent and precedenty are one template twice; the mumchimp-medusa storefront duplicates Store.Web's role and is not deployed.

**Design sources today: four** (portal `tokens.ts`, Store.Web `tokens.css` + `mumchimp.css`, bytesync-web `globals.css`, and the kit's `tokens.json`). The kit now holds components, eight templates, a gallery, a scaffold and the kit-import guard (`packages/estate-ui-kit/consumers.json` names the three legacy consumers and their migration dates).
