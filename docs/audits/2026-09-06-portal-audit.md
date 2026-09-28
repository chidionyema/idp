# Portal audit — what's broken, why it stays shocking, and the road to 100/100

**Date:** 2026-09-06 · **Author:** crew session · **Status:** audit + plan, awaiting founder go. Nothing here is built.
**Method:** code read + live probes + CI receipts. Every claim carries its command. Where I could not measure, it says UNKNOWN.

---

## A. What the portal is today (measured)

- Backstage (new frontend system) in `idp/backstage`: 52-line `App.tsx` shell + modules (`home, nav, theme, shell, signin, i18n, metrics, catalog, featureRegister`); one custom backend plugin (`catalog-backend-module-dagster-entity-provider`); kustomize deploy under `platform/backstage/`.
- Catalog: `bin/catalog-refcheck catalog/catalog-info.yaml` → **617 entities, 1,956 references, all resolve**. The spine is strong.
- Front door: `curl https://catalogue.mumchimp.com` → 302 to OCI IDCS SSO. Correct per standards row 29.
- Doors: all **32/32** estate URLs from `backstage/founder/catalog-info.yaml` answer (302 SSO / 200 health / expected 30x). Probe run today; routing, DNS, edge, cert lanes are healthy.
- Pages: Home, Catalogue, Health (/ops), Docs, You, Create, Map, Kubernetes, Tools, Find, plus /investigate, /reports, /screen, /pair, /estate.

## B. What is actually broken (empirical, this morning)

1. **The data plane is red, so the portal shows stale or empty panels as if live.**
   - `estate-state` workflow: FAIL — `git checkout` exit 1 in `publish-reports` (run 34016141869). The hourly state receipt is not publishing. Home, Health, Investigate all read receipts.
   - `science-facts`: FAIL — "sources=0 rows=0 … the science writer never reached the collector" (run 34016135935). LAW 50 breach; the showcase panel has no data.
   - `agent-workforce` drill: FAIL — "crew#850 has waited 1788 min for a plan (grace 60); the crew is not taking its queue". The agent workforce is wedged ~30 hours.
   - `oke-check`: FAIL — `tofu plan rc=2`; cluster check broken, so cluster-health numbers are untrustworthy.
2. **Freshness is not a first-class UI concept.** Panels render receipts without a measured-at contract; when a pipeline dies, the panel keeps showing its last load with no degraded state. This is the single biggest "everything is broken" driver: the founder reads dead data as live.
3. **The UX complaint history is on file and recurring.** `POLISH-SPEC.md` quotes: "IT NEEDS TO CAPTURE ATTENTION FIRST… ITS A BLACK BOX", "6 RED 6 WHAT? ITS TOO CRYPTIC", "polish it to perfection, nothing less will do"; `toolGroups.ts` quotes "not intuitive… it's not a maze". Three redesigns (crew#459, #612, #684) have landed and it still reads shocking — the repaints are not the system.
4. **A tile cannot tell a dead tool from a live one.** `catalog-links-check` proves a Component *has* a URL, never that it *answers*. My probe fixed that for one morning; nothing in the estate proves it continuously, and tiles carry no live state.
5. **`EstateHome.tsx` is 1,170 lines.** A god-component: every polish round is slower and more regression-prone than the last.
6. **Two design languages.** Custom estate pages (Home/Tools/Ops) sit beside stock Backstage pages (Docs, Create, Search, settings) with stock look and interaction. It reads as two products stitched — the exact half-stitched signal the headline rule bans.
7. **UNKNOWN (honest gap):** I cannot log in through SSO, so rendered-page judgement is from code, specs and tests, not eyeballs. First build action in Lane 1 includes a local boot with screenshots.

## C. Root cause — why it stays shocking

1. **Firefighting the surface, not the plane.** Each UX round repaints components while the receipt pipelines feeding them fail silently. A beautiful panel showing 30-hour-old data is worse than an ugly one — it lies with confidence.
2. **No enforceable component contract.** Tokens and DESIGN-RULES exist as prose; nothing forces a panel to have title + one-line meaning + state + measured-at + action. Drift is inevitable; polish is manual and ungraded.
3. **Drills grade infrastructure, not experience.** login-drill proves SSO answers; oke-check proves tofu plans. No drill proves "the founder opens /tools and every tile opens a working page with fresh data" (R53: drills grade features — sign in, pages answer, links work).
4. **Curation layer missing between catalog and founder.** The catalog is the list (right), but 617 entities is not a product. The founder's daily five must be a hard, tiny surface; everything else is behind Find/Tools. "Daily" tier exists as an annotation; it is not enforced as a *small* set.

## D. The plan — eight lanes, each with a graded 100

**Lane 1 — Data plane first (P0, week 1).** Fix the four red pipelines (estate-state checkout, science-facts emitter, agent-workforce queue, oke-check tofu). Then the **freshness contract**: every receipt carries `measured_at`; every panel renders it; stale beyond 2× interval ⇒ visibly degraded panel with a "this is stale, pipeline X is red" line; empty ⇒ says why and what runs next. *100 = four greens in CI + a drill that fails when any panel renders stale-as-live.*

**Lane 2 — The founder's five (P0, week 1).** One sitting with him: name the five daily jobs. Home becomes those five doors + the one-sentence estate verdict + the state donut (already specced in POLISH-SPEC — finish it). Everything else behind Find/Tools. *100 = founder UAT: "my five things, one click each."*

**Lane 3 — Tiles that prove they work (P1, week 2).** Today's curl probe becomes `bin/door-probe`, hourly, emitting per-door state to the collector (LAW 50). Tiles show a state dot + probe age; a dead door says why on the tile. `catalog-links-check` extended: a door must have a URL *and* a green last probe. *100 = a broken door shows broken on its tile within the hour; CI refuses a door with no probe.*

**Lane 4 — Design system, not polish (P1, weeks 2–4).** Split `EstateHome.tsx` into composed panels under one contract (title, meaning line, state, measured-at, action). Tokens + panels in one module; Playwright visual-regression wired to CI over the six founder pages; axe pass on each. *100 = a new page is panel composition with zero bespoke CSS; visual suite green in CI.*

**Lane 5 — One design language (P2, weeks 3–4).** Restyle or park the stock pages (Docs, Create, Search, settings) into the estate shell. One search box over entities + docs + reports. *100 = visual suite shows one language; no stock chrome reachable from founder nav.*

**Lane 6 — Speed with budgets (P2).** Lighthouse CI already exists (`test:lighthouse`); set per-page budgets (LCP < 2.5 s behind SSO), catalog query pagination/cache. *100 = budgets enforced in CI, not narrated.*

**Lane 7 — Portal copy through Voice Gate (P2).** Door copy, group blurbs, empty states (`doorCopy.ts`, `toolGroups.ts`) become Voice Gate's second tenant after mumchimp — dogfooding the platform capability. *100 = `lint:copy` green on the portal repo.*

**Lane 8 — Mobile (P3).** PairPhone exists; define the two mobile jobs with him; grade by mobile-viewport Playwright. *100 = those two jobs pass on a phone.*

## E. Sequencing (one answer)

Week 1: Lane 1 + Lane 2 (put the fire out, then the founder's five). Week 2: Lane 3, start Lane 4. Weeks 3–4: finish Lane 4, Lane 5. Lanes 6–8 land continuously after. Voice Gate (prospector repo) is unaffected and independent.

## F. What 100/100 means

Eight lanes, eight numbers, each provable by a command or a drill — no vibe scores. The scorecard is this document's lanes; each "100" clause is the acceptance test. Overall portal score = lanes at 100 / 8, re-measured weekly by the same commands, published to the collector.

## G. Risks (one line each)

- Lane 1's agent-workforce fix may be a people/process wedge (the queue is ignored, not just red) — root-caused before anything is rebuilt.
- Visual-regression on Backstage is flaky if done on animations; the suite runs with animations disabled (R53: structure, never look-and-feel selectors).
- Restyling stock Backstage pages fights upstream; parking them off-nav is the smaller road when both arrive (LAW 23).
