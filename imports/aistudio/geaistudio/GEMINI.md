# Workspace Rules & Persistent Architecture Invariants

## 1. Zero-Custom-Env-Var Rule (Mandatory)
- NEVER add new custom variables to `.env.example` or introduce new `process.env.*` references in application code (Google AI Studio Build scans `.env.example` and `process.env.*` and halts the preview container with a prompt modal if an unbound variable appears).
- Public routing endpoints (such as the Genesis bundle ingest URLs) are not secrets; hard-bind them in `src/engine/debugPackBuilder.ts` (`CANONICAL_BUNDLE_INGEST_URLS`) and authenticate transfers by bundle `X-Bundle-Sha256` digest.
- Allowed runtime variables are strictly AI Studio platform variables already declared in `.env.example` (`GEMINI_API_KEY`, `APP_URL`) plus `NODE_ENV`, `PORT`, and `DISABLE_HMR`.

## 2. Reset-Proof Git & Bundle Transport
- Container checkpoints wipe `/app/applet/.git/` and `/root/` while preserving tracked files inside `/app/applet/`.
- Never rely on `.git/hooks/` or stored GitHub PATs inside `.git/config`.
- Instead, rely on:
  - `src/engine/debugPackBuilder.ts` (`ensureGitRepoAndBundle` + `pushBundleToIngest`)
  - `vite.config.ts` (`genesisBundleSyncPlugin` running on `configureServer` container boot)
  - `package.json` (`sync:bundle` and `postbuild` running `scripts/sync-bundle.ts`)
- Canonical ingest targets:
  - Primary: `https://otto.mumchimp.com/api/ingest/bundle`
  - Fallback: `https://genesis-founder-surface.pages.dev/api/ingest/bundle`

## 3. Verification Gate Before Finishing Any Turn
- Enforce `I-8090` zero client HTTP polling across `src/components/*.tsx` (all live updates flow over SSE `/api/union/stream`, `/api/sync/stream`, and `/api/reactivity/stream`) and keep `AGENTS.md <= 300` lines.
- Run `npx --yes tsx --test src/engine/router.test.ts` (`33/33` integration & falsifier cases `INT-01..06` + `F1..F27`, `17/17` production guarantees, `21/21` First-Use Governance Audit tests, `29/29` test blocks, and Git bundle verification must pass).
- Run `npm run lint` (`tsc --noEmit`) and `npm run build` (`vite build` + `postbuild` bundle verification & outbound sync) with 0 errors.


