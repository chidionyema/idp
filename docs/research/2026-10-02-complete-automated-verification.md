# Complete automated verification of /fleet and /face — research and design

Status: DRAFT (research + design, for approval) · Date: 2026-10-02 · Author: epoch-8 router session
Trigger: founder ruling, 2026-10-02 — "complete verification automated, real voice conversations on
fleet and face that is verified, and all other features automated verification... every single
feature on both must be extensively verified before and after deployment. I don't want a hint of
a gap."

---

## 1. Why this exists: what today proved

Three defects reached the founder's screen on 2026-10-02. Each one maps to a missing gate:

| # | Defect (measured) | The gate that was missing |
|---|---|---|
| 1 | /fleet grey squares — right-rail chips had no CSS rule; invisible defect class (22 more utilities unresolved) | No check that the CSS generator resolved every utility the source uses |
| 2 | /face and /voice dead on the cluster — every asset (brunette.glb 4.72MB, talkinghead.mjs 217KB) served 200 by the app but 302→IDCS login through the gate | No probe ever fetched a page asset **through the public gate**; all checks hit the app directly |
| 3 | The fix for #2 (lane A) sat committed on the laptop, never pushed | No check that a "done" lane actually exists on origin |

A fourth meta-defect covers all three: verification was manual, sporadic, and narrated. This spec
ends that. Nothing below is a human procedure.

## 2. What already exists (measured, not assumed)

- **The prover framework** (crew#631): `bin/idp-prove <target>` runs probes, binds the result to
  the artifact that was running, signs a verdict. No vault/machine identity ⇒ verdict is BLOCKED
  and unsigned, never silently green. Targets today: `langfuse`, `backstage`, `signoz`.
  Hourly workflows `verdict-*.yml` write check-runs and verdict-table rows.
- **Playwright** `@playwright/test` is a devDependency in `backstage/package.json` and
  `packages/app/package.json`, `test:e2e` script exists, `playwright.config.ts` exists —
  and there are **zero spec files**. A harness with no tests: the exact shape of the problem.
- **Greenlane**: every lane is proven on top of current main before landing — the right place for
  a pre-deploy suite to run.
- **Flux + deploy-when-green**: image tags land on merge; the right place for a post-deploy
  verdict to run immediately after.
- **ambient-os research** (Autonomous Verification Chamber, Automated Canary Analysis, Firecracker
  microVMs): graph-checked — those are *research documents from another estate*, never built here.
  No duplication; the idp-native pattern is the prover, and this design extends it.

## 3. The law that makes "no gap" possible

**Coverage is generated, not narrated.** The feature inventory is not a hand-maintained list that
drifts; it is enumerated from the code at gate time, and **the gate fails when any enumerated
feature lacks a covering probe**:

```
inventory = routes(App) ∪ panels(room/ui) ∪ assets(public/face) ∪ states(useEstateVoice)
             ∪ routes(fleetview-backend)
gate      = for f in inventory: assert f has ≥1 probe result
            fail on: uncovered feature, failed probe, or inventory-source parse error
```

A new panel, asset, voice state or backend route that ships without a probe turns the gate red —
the same philosophy as `gen-reactor-css` (name what you cannot resolve; never pass silently).

## 4. Levels (each feature is verified at every level that applies)

| Level | What | How (real, never synthetic-only) | Catches |
|---|---|---|---|
| **L1 reach** | page/asset reachable **through the public gate**, signed-out AND prover-token | HTTP fetch via catalogue.mumchimp.com; assert status, content-type, byte-size floor | defect #2 (login-wall on assets), CDN/proxy misconfig |
| **L2 auth** | negative controls: wrong token refused, right token accepted | same URLs, bad bearer | an open surface or a broken gate |
| **L3 behavior** | the UI itself in a real browser | Playwright, system Chrome channel (no browser download): panels mounted, chips rail geometry, labels present, no console errors, no dead React | defect #1 (invisible CSS gaps), any render regression |
| **L4 voice** | a **real voice conversation**: utterance → STT → intent (voice.py through the estate router) → TTS audio → spoken back; on /face also the avatar's lipsync | fixture WAV (committed, checksummed) fed to the *same STT endpoint the browser uses*; assert transcript ≥ threshold (normalized Levenshtein); assert TTS response is real audio (RIFF/duration/RMS, not silence); on /face assert the avatar entered `speaking` and lipsync visemes advanced (page-side hook state via Playwright) | voice plane breakage of any kind — key, router, model, TTS, avatar |
| **L5 realtime** | the stream the board shows is live | subscribe to the estate bus feed the board subscribes to; assert a frame arrives within N s and its session set matches `/sessions` | a frozen board showing stale state — "operational" means live |
| **NEG** | failure must be visible | every probe class has a deliberate negative control (bad token, missing asset, muted audio) proving the probe CAN fail — a probe that cannot fail is deleted | fake tests |

Voice states enumerated from `useEstateVoice.ts`: `off · listening · thinking · speaking · error`
— each state transition asserted during L4.

## 5. Today's inventory (generated by the enumerator; this table is a snapshot, the code is truth)

**Pages:** `/fleet` (FleetReactorApp), `/face` (FacePage), `/voice` shell.
**Fleet panels** (`room/ui`): AgentJobs, ConciergeTasks, Cost, EfficiencyHud, FleetCanvas,
FleetReactorApp, HarvPanel, KeySync, MindPanel, NewsDesk, RadialMenu, Room, SpatialCanvas,
Spotlight, Waveform (+ cinecam, reactor, newsRundown logic modules).
**Voice:** EstateVoiceState ×5, mic device acquisition, model picker, push-to-talk.
**Face assets** (`public/face`): VERSIONS, brunette.glb, dynamicbones.mjs, lipsync-en.mjs,
playback-worklet.js, talkinghead.mjs, three/*.
**Backend routes** (`fleetview-backend`): sessions, voice, signals, metrics, history, notes,
approvals (adapter), each with an auth negative control.
**Cross-cutting:** CSS-utility resolution (defect #1 class), right-rail geometry, no-console-errors,
app-config feature flags the pages depend on.

## 6. Wiring — before AND after deployment, fully automated

**Pre-deploy (in the lane, before merge):** the greenlane proof job gains one step:
`bin/idp-verify-surfaces --pre` — boots the built app (the CI container already builds it),
runs L1–L4 against localhost, plus the coverage gate (§3). Red lane = no landing. No human.

**Post-deploy (after Flux converges):**
1. `deploy-when-green`, after merging an image-update PR, dispatches `verdict-surfaces` immediately.
2. `verdict-surfaces.yml` runs hourly regardless (verdict TTL 1h, matching the existing pattern).
3. Verdict is signed, bound to the running image digest, written as check-run `verify/surfaces`
   and a row in the verdict table — visible on /fleet (verification is itself a surface).

**Rollback (the part that makes it a gate, not a report):** L1/L2/L3 failure on a fresh deploy ⇒
the verdict workflow opens an automatic revert PR of the image tag (through the Greenlane, never
hand-applied). L4/L5 failure on 2 consecutive runs ⇒ same. The founder reads the fleet page, not
a log.

## 7. Phases

- **CP1 — the enumerator + L1/L2 battery** (`probes/surfaces.py`, `bin/idp-prove surfaces`):
  gate-through fetches with negative controls + the coverage gate. Runnable from a laptop for
  dev (against localhost or prod); signed verdicts only in CI. *Proof it works: run against
  production today it must FAIL on the /face and /voice asset 302s — the live defect.*
- **CP2 — L3 Playwright suite**: system-Chrome, per-panel mount/geometry/label/no-error checks,
  wired into the greenlane pre-deploy step and the verdict workflow.
- **CP3 — L4 real voice conversations**: fixture WAV → STT → voice.py → TTS → STT-back +
  avatar-viseme assertions on /face; conversation scripts (3 utterances: status query, action
  query, refusal-path) exercising all five voice states.
- **CP4 — L5 realtime + rollback**: bus-subscription liveness probe + automatic revert PR on red.

## 8. Non-goals / honesty

- Signed verdicts require CI machine identity; a laptop run is dev-grade (BLOCKED verdicts are
  correct behavior, not a bug).
- Voice L4 depends on external STT/TTS vendors through the estate router; flakiness is handled by
  the two-consecutive-failure rule, not by loosening assertions.
- This covers /fleet, /face, /voice and fleetview-backend. Other Backstage plugin pages join by
  adding their features to the enumerator's sources — one place, no per-page test stacks.
