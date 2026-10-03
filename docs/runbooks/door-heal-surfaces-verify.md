# Door-heal runbook — surfaces-verify lane (written 2026-10-03 while the executor was down)

The executor daemon's job runner SIGTERMs every job instantly ("exceeded the 0s ceiling")
while `estate_executor_status` reports alive/60s. Evidence: jobs exec-1790983353-973
(`echo`), exec-1790983387-974 (pytest), exec-1790983666-976. The daemon is not ours to
restart (AGENTS §5); everything below runs the moment the door answers `echo`.

## What is already built in this worktree (files on disk, uncommitted)

- `probes/realtime.py` — L5 bus-liveness probe (frame ≤ 20s, ghost-session desync check).
- `bin/idp-verify-surfaces` — the battery: `--pre` (L1/L2+coverage, L3 generated spec,
  L5) and `--post` (through the public gate, + L4 voice). Prints `PASS|FAIL|SKIP
  surfaces.<x>` lines and a verdict JSON bound to git sha + running digest.
- `.github/workflows/verdict-surfaces.yml` — hourly + dispatch battery through
  catalogue.mumchimp.com, check-run `verify/surfaces`, standing red pages crew#1019,
  dispatched red opens an automatic REVERT PR on the flux image-updates branch (raised by
  the workflow, landed by the lane; never hand-applied).
- `probes/gen_panels_spec.py` — now also generates the `/fleet-original` presence test
  (FleetReactorOriginal must be reachable at its own route or generation fails).

## Ordered steps once `estate_execute 'echo alive'` answers

1. **Commit and push what is here.** The uncommitted set: the four files above. Commit,
   push `lane/surfaces-verify` (already exists on origin), stop. The lane grades it.

2. **Room wiring (the 6 unreachable components).**
   ```
   git sparse-checkout add backstage/packages/app/src .github/workflows/ci.yml \
     platform/github/ruleset.idp.required-checks.json
   ```
   Then read `room/ui/Room.tsx` imports. If Room composes FleetCanvas (which composes
   SpatialCanvas) and Waveform — and MindPanel/Cost hang under it or nowhere — add to
   homeModule.tsx, after fleetOriginalPage:
   ```ts
   // /room: the room-rewrite stack (Room -> FleetCanvas -> SpatialCanvas + Waveform),
   // mounted so every room/ui component is reachable and graded. No route could render
   // it before; that was the wiring gap the panels generator went red naming.
   const roomPage = PageBlueprint.make({
     name: 'room',
     params: { path: '/room', noHeader: true, loader: () => import('../room/ui/Room').then(m => <m.default />) },
   });
   ```
   (add `roomPage` to the extensions list; adjust to Room's actual export). If MindPanel
   or Cost are still unreachable after that, mount them inside Room where they belong —
   they are the rewrite's HUD panels. Regenerate: `python3 -m probes.gen_panels_spec` —
   wiring list must be `[]` and coverage 16/16 (minus TRIGGERED/SKIP classes).

3. **Guest auth 501 (blocks every browser test, including existing fleet.test.ts).**
   Find the dev stack's backend log (the serve process; do not restart it) and read the
   guest provider init error. Suspicion to check: `user:default/guest` not ingested by the
   catalog (app-config.yaml:374 says the guest identity resolves through it). If the fix
   is config-only, fix in app-config.local.yaml; if the stack needs a restart, hand the
   evidence to its owner — never restart another agent's process.

4. **nats 400 invalid JSON (steer publish after /voice/hear).** Call sites pinned:
   `voice_media.publish()` (wrapper, never raises) -> `nats_adapter.publish()` ->
   `_ensure_stream()` + `js.publish()`. Payload is `json.dumps` output — always valid.
   Reproduce one-shot with the same kwargs against the live NATS_URL; the server's own
   text names the real cause (suspect: `_ensure_stream_by_name` add_stream config vs the
   existing ESTATE_AGENT stream — only "already in use" is swallowed).

5. **ci.yml: the pre-deploy leg** (insert after the offline-gate job; same placement —
   candidate and main, not per-PR):
   ```yaml
   surfaces:
     if: github.event_name != 'pull_request'
     needs: [fast-gate, verifier]
     runs-on: ubuntu-latest
     timeout-minutes: 25
     steps:
       - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
       - uses: actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97 # v7.0.0
         with: { python-version: "3.12" }
       - uses: actions/setup-node@<pinned>
         with: { node-version: "22", cache: yarn, cache-dependency-path: backstage/yarn.lock }
       - name: browser + backend
         run: |
           npx playwright install --with-deps chromium
           pip install -q -r backstage/plugins/fleetview-backend/requirements.txt
       - name: serve app + backend
         run: |
           (cd backstage && yarn install --frozen-lockfile && yarn workspace app build:gh-pages || yarn workspace app build)
           (cd backstage/packages/app && nohup npx serve bundles -l 3000 &)
           (cd backstage/plugins/fleetview-backend/src && nohup python3 -m fleetview_backend.serve 18790 &)
           # wait-for both doors, then:
       - name: the surfaces battery (pre)
         env:
           APP_URL: http://127.0.0.1:3000
           BACKEND_URL: http://127.0.0.1:18790
           SURFACES_SKIP_L5: "CI runner cannot reach the estate bus; post-deploy verdict grades L5 through the gate"
         run: bin/idp-verify-surfaces --pre
   ```
   (Adjust the serve commands to what the repo's playwright.config.ts already knows; the
   battery is the gate, the serving is plumbing. L3 needs a working auth path — guest in
   dev; if guest 501 persists in CI the job is correctly red.)
   Then add to `platform/github/ruleset.idp.required-checks.json`:
   `{ "context": "surfaces", "integration_id": 15368 }` — so a candidate that breaks any
   surface cannot land. Apply via `bin/idp-github` (rulesets are active enforcement).

6. **Post-deploy dispatch.** `verdict-surfaces.yml` runs hourly; the immediate-after-deploy
   dispatch (`repository_dispatch: surfaces-deployed` with the digest) fires from the
   greenlane tick the moment it lands a `flux/image-updates` lane — one dispatch call in
   `bin/idp-greenlane` after a successful fast-forward, until then the hourly run covers it.

7. **Prove CP4 operating, not built:** merge of an image-update -> dispatched verdict ->
   check-run green on main + verdict row visible; deliberate NEGATIVE: point the battery
   at a broken URL once (workflow_dispatch) and watch the revert PR open and the crew
   comment land. Record the production log line / PR URL in crew#1019.
