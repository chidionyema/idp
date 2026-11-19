# AGENTS.md — Persistent Container & Verification Contract

## Invariants
1. **Do not declare new custom environment variables** in `.env.example` or `process.env.*`. Public ingest addresses belong in `CANONICAL_BUNDLE_INGEST_URLS` inside `src/engine/debugPackBuilder.ts`:
   - `https://otto.mumchimp.com/api/ingest/bundle`
   - `https://genesis-founder-surface.pages.dev/api/ingest/bundle`
2. **Do not depend on `/app/applet/.git/` surviving checkpoints**. Always generate/verify `dist-exports/meridian-hermes-today.bundle` idempotently via `ensureGitRepoAndBundle`.
3. **Automatic Boot & Build Sync**: `vite.config.ts` (`genesisBundleSyncPlugin`) executes non-blocking bundle sync on `npm run dev` container boot, and `package.json` `postbuild` runs `scripts/sync-bundle.ts` on `npm run build`.
4. **Zero Client HTTP Polling (`I-8090`) & `AGENTS.md` No-Growth Ratchet**: Client components must use SSE (`/api/union/stream`, `/api/sync/stream`, `/api/reactivity/stream`) rather than `setInterval` HTTP polling, and `AGENTS.md` must remain strictly `<= 300` lines.
5. **Rego Policy-as-Code & System-First IoC (`R-008..R-010`, `LAW_SYSTEM_FIRST_IOC_RECONCILER`)**: Read `FLEET_3DAY_CANONICAL_MANIFEST.md`, `ROUTER.md` (`pennyd` `127.0.0.1:4200`; LiteLLM `:4000` & OKE `193.123.184.22` tombstoned), and `GENESIS_SPORE.dna` (`<=4096B`) first; enforce `<=150ms` UHNW SLA, turnkey `/setup` + `/phone-boot` DR, and `Plan != Test != Live Yield`.
6. **Verification**: Run sequential `npx --yes tsx --test --test-concurrency=1 src/engine/httpIntegration.test.ts` and `npx --yes tsx --test --test-concurrency=1 src/engine/router.test.ts` (`41/41` suite cases `INT-01..10` + `F1..F31`, `20/20` guarantees, `12/12` proven FSMs, `12/12` DR red-team, and `18/18` 3-day fleet sync seal), `npm run lint`, and `npm run build`.


