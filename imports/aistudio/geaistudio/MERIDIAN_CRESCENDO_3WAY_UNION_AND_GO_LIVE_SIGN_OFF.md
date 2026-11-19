# MERIDIAN CRESCENDO — 3-WAY UNION & GO-LIVE SIGN-OFF

- **Current Go-Live Status:** **`NO-GO`** — *Local source, 3-stream union & `/crescendo` route verified in container; awaiting external fleet push (`GL-04`), deployed production revision HTTP 200 (`GL-05`), and independent `Key-C Malkuth` external browser verification (`GL-06`).*
- **Canonical Repository Path:** `/MERIDIAN_CRESCENDO_3WAY_UNION_AND_GO_LIVE_SIGN_OFF.md`
- **HTTP Verification Endpoints:**
  - Markdown Sign-Off Ledger: `/MERIDIAN_CRESCENDO_3WAY_UNION_AND_GO_LIVE_SIGN_OFF.md` & `/api/export/crescendo-signoff`
  - Machine-Readable JSON Gate State: `/api/crescendo/signoff`
- **Declared End-User Route:** `/crescendo` (aliases: `/codex-crescendo`, `/hermes/crescendo`, `/?tab=crescendo`) -> deterministically opens **`Hermes · The Living Tree -> Codex Crescendo`**
- **Converged Fleet Custody Obligation:** `OBL-CRESCENDO-3WAY-UNION` (registered on existing fleet recovery lane inside `src/engine/autonomousReactivity.ts` — **0 disconnected tickets created**)

---

## 1. Reconciliation of the External Verifier's Three Findings

### Finding 1 — Source (`MERIDIAN_CRESCENDO_3WAY_UNION_AND_GO_LIVE_SIGN_OFF.md` Missing in Accessible Trees)
- **Diagnosis:** While `src/engine/codexCrescendo.ts` and `src/components/CodexCrescendoPanel.tsx` existed inside the AI Studio workspace, the authoritative root sign-off specification `MERIDIAN_CRESCENDO_3WAY_UNION_AND_GO_LIVE_SIGN_OFF.md` had not been materialized at the repository root or pushed to `chidionyema/argon-sync` / `chidionyema/gemini-sync`.
- **Resolution (`GL-01` — Verified Locally):** Committed `/MERIDIAN_CRESCENDO_3WAY_UNION_AND_GO_LIVE_SIGN_OFF.md` at the Git repository root, bound it to pure engine `src/engine/crescendoThreeWayUnion.ts`, included both in `dist-exports/meridian-hermes-today.bundle` and `meridian-complete-today-2026-11-16.tar.gz`, and exposed live SHA-stamped HTTP routes.

### Finding 2 — Routing (Authenticated Runner Got HTTP `404` on `/api/export/bundle` & `/crescendo` Route Fell Back to Default Tab)
- **Diagnosis A (Why Authenticated Runner Hit HTTP `404` on `/api/export/bundle`):**
  - Unauthenticated requests to `ais-dev-*.run.app` / `ais-pre-*.run.app` hit Google AI Studio's cookie interstitial (`HTML`), whereas an **authenticated** runner reaching a static `dist/` deployment (or pre-export revision) hit **HTTP `404`** because `vite build` + `scripts/sync-bundle.ts` previously wrote `dist-exports/meridian-hermes-today.bundle` *outside* `dist/` (`dist/api/export/bundle` did not exist).
- **Diagnosis B (Declared `/crescendo` End-User Route):**
  - `resolveInitialTab()` in `src/App.tsx` previously read only `?tab=<NavTabId>` (where the tab key was `hermes`, not `crescendo`) and ignored `window.location.pathname`. Navigating to `/crescendo` or `/?tab=crescendo` landed on `union` rather than `Codex Crescendo`.
- **Resolution (`GL-03` — Verified Locally):**
  1. Wired `resolveDeclaredAppRoute(window.location.pathname, window.location.search)` in `src/App.tsx` so `/crescendo`, `/codex-crescendo`, `/hermes/crescendo`, and `/?tab=crescendo` open `hermes` (`HermesLivingTree.tsx`, which defaults `treeMode='codex'` and `atlasTab='codex'`).
  2. Added `materializeStaticDistExports(repoRoot)` in `src/engine/debugPackBuilder.ts` (invoked automatically by `scripts/sync-bundle.ts` during `npm run build` `postbuild`) to populate static `dist/api/export/bundle`, `dist/api/export/git-bundle`, `dist/api/export/all-today`, `dist/api/export/workspace.tar.gz`, `dist/api/export/manifest`, `dist/api/export/crescendo-signoff`, `dist/MERIDIAN_CRESCENDO_3WAY_UNION_AND_GO_LIVE_SIGN_OFF.md`, `dist/crescendo/index.html`, and `dist/codex-crescendo/index.html`.
  3. Once **Share -> Update** is clicked in AI Studio (or `dist/` is deployed to Cloudflare Pages / Cloud Run), static hosts serve `/api/export/bundle` and `/crescendo` with **HTTP `200`** instead of `404`.

### Finding 3 — Deployment (No Verified Production Revision or External Browser Receipt Established Yet)
- **Governance Rule (`Rego R-010` + Veil of Qesheth Three-Key Non-Collusion Theorem):**
  - A container build or green unit test inside AI Studio **never** equals production sign-off (`PLAN != TEST != LIVE_OPERATIONAL_YIELD`).
  - `evaluateCrescendoGoLiveSignOff()` holds `overallDecision = 'NO-GO'` until `GL-04` (remote Git sync), `GL-05` (external runner HTTP `200` against deployed production revision), and `GL-06` (independent `Key-C Malkuth` external browser verification of `/crescendo`) are recorded.

---

## 2. Three-Stream Convergence Contract

| Stream ID | Source Stream | Governing Authority | Cryptographic Binding | Local Status | External Production Status |
|---|---|---|---|---|---|
| **`STREAM_1_GEMINI_HERMES`** | Codex Crescendo 231-Gate Matrix, Four Worlds, Three Veils, 10 Qliphoth, Web Audio & `/crescendo` UI | `src/engine/codexCrescendo.ts`, `src/engine/crescendoThreeWayUnion.ts`, `src/components/CodexCrescendoPanel.tsx`, `src/App.tsx` | Synthesis & Local Chromium Proof | `VERIFIED_LOCAL` | Pending `GL-04..GL-06` |
| **`STREAM_2_ARGON_GREENLANE`** | Reset-Proof Git Bundle, Static `dist/api/export/bundle`, Outbound HTTPS Push & `OBL-CRESCENDO-3WAY-UNION` | `chidionyema/argon-sync` & `chidionyema/gemini-sync` (`refs/heads/aistudio/meridian-hermes-live`) | `Key B · Chesed` Executor (`YIELD/1` SHA-256) | `ADAPTER_READY` | `NO-GO` until remote push receipt |
| **`STREAM_3_IDP_PRODUCTION`** | Production Revision Promotion, Rego `R-010` Gate & Out-of-Band Physical Witness | `chidionyema/idp` + Production Host | `Key A · Binah` Oracle + `Key C · Malkuth` Witness | `CONVERGED_OBLIGATION` | `NO-GO` until deployed SHA + external browser test |

---

## 3. Six-Gate Go-Live Verification Ledger (`GL-01` .. `GL-06`)

- **[x] `GL-01` (Local Verified):** `/MERIDIAN_CRESCENDO_3WAY_UNION_AND_GO_LIVE_SIGN_OFF.md` tracked in Git `HEAD`, bundled in `.bundle` + `.tar.gz`, and served HTTP `200`.
- **[x] `GL-02` (Local Verified):** `C(22,2) = 231` Sefer Yetzirah gates evaluated, Qesheth cross-gate `(14, 32)` blocked, `3/3` independent Ed25519 keys (`Key_Binah != Key_Chesed != Key_Malkuth`) verified, `0` active Qliphothic fractures.
- **[x] `GL-03` (Local Verified):** `/crescendo`, `/codex-crescendo`, `/hermes/crescendo`, and `/?tab=crescendo` resolve to `hermes` (`Codex Crescendo`), and `postbuild` populates static `dist/api/export/bundle` + `dist/crescendo/index.html`.
- **[ ] `GL-04` (`NO-GO` — Pending External Fleet Sync):** Push `meridian-hermes-today.bundle` to `chidionyema/argon-sync` and `chidionyema/gemini-sync` (`refs/heads/aistudio/meridian-hermes-live`).
- **[ ] `GL-05` (`NO-GO` — Pending Deployed Revision & External HTTP `200`):** Refresh Shared App (**Share -> Update**) or deploy production revision, then confirm `HTTP 200` + matching `X-Bundle-Sha256` from external runner.
- **[ ] `GL-06` (`NO-GO` — Pending Independent External Browser Witness):** Execute external Playwright/browser check against live production `/crescendo` route and countersign with `Key C · Malkuth`.

---

## 4. Fleet Handoff & Verification Commands

```bash
# Step 1: Verify bundle integrity after Lane 1 (Outbound HTTPS Push) or Lane 2 (1-click Browser Download)
git bundle verify meridian-hermes-today.bundle
git clone meridian-hermes-today.bundle meridian-crescendo && cd meridian-crescendo

# Step 2: Independently replay 31/31 test blocks, TypeScript lint, and static dist/ export materialization
test -f MERIDIAN_CRESCENDO_3WAY_UNION_AND_GO_LIVE_SIGN_OFF.md
npm ci
npx --yes tsx --test src/engine/router.test.ts
npm run lint
npm run build
test -f dist/api/export/bundle && test -f dist/crescendo/index.html

# Step 3: Push to canonical fleet sync remotes to clear GL-04
git remote add argon git@github.com:chidionyema/argon-sync.git
git remote add gemini git@github.com:chidionyema/gemini-sync.git
git push argon HEAD:refs/heads/aistudio/meridian-hermes-live --force-with-lease
git push gemini HEAD:refs/heads/aistudio/meridian-hermes-live --force-with-lease
```
