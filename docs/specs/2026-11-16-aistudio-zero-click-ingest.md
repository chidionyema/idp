# AI Studio zero-click ingest (I-8096-REV2)

Status: implemented and unit-proven; edge deployment is the only step that needs the
`AI_STUDIO_INGEST_SECRET`, `OMNIFLOW_GH_TOKEN` and optional `GENESIS_REALTIME_URL` secrets.

## The problem this closes

AI Studio keeps the work in the browser. Until this change the estate could only see a turn
after a human exported it — "Save to GitHub", a zip download, or a Drive desktop mount — and
then triggered a lane by hand. The turn itself was never an event the fleet could observe.

`CLASS-MANUAL-EXPORT-FRICTION` (catalog/issue-classes.json) is the class. It is closed here,
not worked around.

## Two capture channels, one commit

1. **In-browser stream tee** — `ops/aistudio/genesis-mycelium.user.js`. Wraps `window.fetch`
   on `aistudio.google.com`, tees the response stream, extracts fenced code blocks whose info
   string (or leading comment) names a file, hashes each block with SHA-256 in the page and
   POSTs `{source:"stream", files:[...]}` to `/api/ingest/stream`. A `MutationObserver` over
   chat turns is the fallback when the page does not use `fetch` for a turn.
2. **Google Drive push** — the same edge route family accepts `changes.watch` pushes at
   `/api/ingest/drive-webhook`. A `x-goog-resource-state: sync` handshake is acknowledged and
   never ingested.

Both channels call the same engine, `platform/lifeboat/src/aistudio.js`, which:

- re-decodes every `content_b64` and hashes the landed bytes (`59effb8f4`):
  a declared `sha256` or `bytes` that disagrees is a **partial flush**, refused with 409
  before any Git write;
- strips AI Studio mock fixtures (`generalPurposePersonaData.ts`, `physicalEstateData.ts`,
  `INITIAL_SPECIALIST_FLEET`) so Argon's fixture gate is never tripped;
- dedupes within the payload and against the lane head by `(path, sha256)` — the two channels
  therefore produce one commit, not two;
- writes blobs/tree/commit/ref to `chidionyema/idp` on `lane/aistudio-auto-intake` through the
  GitHub Git Data API (no Mac filesystem, DARWIN_THIN_CLIENT preserved);
- comments an `OMNIFLOW-EVENT/v1` `ASSIGN` packet on idp#8133 with the commit and manifest;
- posts `chronicle.aistudio_ready` when `GENESIS_REALTIME_URL` is configured (recorded as
  `skipped` when it is not, never silently asserted);
- dispatches `greenlane.yml` (or the OMNIFLOW relay when `OMNIFLOW_RELAY_URL` is set).

## Fail-closed doors

- Missing `AI_STUDIO_INGEST_SECRET` → 503 (`INGEST_SECRET_ABSENT`).
- Wrong token → 401. The userscript and Drive share this one secret; the Drive webhook also
  presents `x-goog-channel-token`.
- Non-POST → 405. Bad JSON → 400. GitHub failure → 502 with the failing path, never a
  partial receipt.

## Falsifiers

- `tests/test_aistudio_zero_click_ingest.py` — CA2: a simulated stream turn is committed
  sanitized, assigned on #8133 and dispatched to Greenlane; a simulated Drive push dedupes into
  the same commit; a partial flush never reaches a commit.
- `platform/lifeboat/test/aistudio.test.mjs` — engine gates and the Drive sync handshake.
- `ops/aistudio/genesis-mycelium.test.mjs` — the userscript's extractor and SHA-256.

## Broadcast boundaries (CA4), stated honestly

The instruction names `telegram_spooler`, `mcp_doors`, `cloud_apis` and `dsh_web`. Those
named surfaces do not exist in `chidionyema/idp`; a census of the repository finds no such
paths. What exists and is wired today:

- the commit on `lane/aistudio-auto-intake` (the change itself);
- the OMNIFLOW assignment on idp#8133 (the room the reconciler already reads);
- the realtime hook `chronicle.aistudio_ready` (`GENESIS_REALTIME_URL`);
- the Greenlane dispatch that lands the lane;
- the Telegram completion path (`bin/estate-fleet-telegram`) can carry the same receipt when
  the founder's channel is configured.

Creating four new broadcast surfaces to satisfy the names would be four new layers with no
reader. The spec records the gap instead of pretending it is closed.

## Retired route

`.github/workflows/genesis-aistudio-source-intake.yml` stays for the pinned private archive
(its contract test is unchanged). It is no longer the route for AI Studio app turns: the
zero-click path above is. The manual export step is what I-8096-REV2 removes.

## Operating status (measured 2026-11-16)

- `https://genesis-founder-surface.pages.dev/health` answers **200**, so the edge host exists.
- The ingest routes in this lane are **not serving**: they are not on main, and the zero-click
  capability is therefore `declared`, not `operating` (capability-index shows only the manual
  `gha-genesis-aistudio-source-intake` workflow for AI Studio).
- Greenlane could not mint its App token on the runs that judged this lane:
  `TokenExchangeError: Request failed with status code 401` at the OCI OIDC step (runs
  43788408501, 43800409549, 43801061008), and #8181 then failed closed. The fix is
  PR #8182 (SEED App key, no OCI).
- A partial-flush rule, a dedup rule and a sanitizer that never ran in production are still
  `declared`; the falsifier proves the code, not the operation.

## Operating status (measured 2026-11-18)

- `https://genesis-founder-surface.pages.dev/` answers 200; `/api/ingest/bundle` answers 404,
  so the Pages receiver in `gemini-sync` is not deployed.
- `https://lifeboat-llm.mumchimp.com/` does not resolve, so the edge ingest routes above are
  not serving. `bin/idp-otto-homes` already wires `AI_STUDIO_INGEST_SECRET`; the missing step is
  the deploy, not the wiring.
- The zero-click capability is therefore `declared`, not `operating`: an AI Studio turn has no
  live door today, and a human export remains the only route.
