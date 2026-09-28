# Fleet 2100: The Deploy River and the Three Planes Observatory

**Founder, 2026-09-23:** "a 2100 jaw-dropping spectacular view of the end-to-end CI/CD
deploy process on the fleetview page, with voice narration and full interaction, every
step from CI to cluster" — and a second page showcasing the Three Planes harness,
"spectacularly." Board row: **crew#973**.

This spec extends — never replaces — `2026-09-20-fleet-2100-hud-architecture.md`. Its
laws bind both pages: information is ambient until interrogated, voice is routed by
spatial intent, chrome is eliminated, and the transcript is never hidden.

## The two pages

| page | route | answers |
|---|---|---|
| **Deploy River** | `/fleetview/river` | "What happened to my code, from push to live?" |
| **The Observatory** | `/fleetview/planes` | "What is the agent OS doing, on all three planes, right now?" |

Both live inside the existing Backstage fleetview module
(`backstage/packages/app/src/modules/`), rendered into the same WebGL lineage as
`FleetReactorApp.tsx`, full-bleed to the bezel.

## Page 1 — The Deploy River

The pipeline rendered as a **river of light running left to right across the viewport**.
Each stage the estate's Definition of Done already names is a **gate ring** over the
water: `push → auto-PR → fast-gate → crucible (bdd, security-scan) → merge →
build-multiarch → trivy → cosign → flux reflector → image-automation →
deploy-when-green → reconcile → pod ready → first production log line`.

- **A commit is a comet.** Push ignites it at the source; it travels the gates in real
  time. Green gate: the ring flashes and the comet accelerates. Red gate: the ring
  **cracks**, sheds debris, pulses at the discordant frequency the HUD spec reserves
  for stuck things, and the comet falls into a glowing **rejection basin** below the
  river — every failure visible from across the room, never a red line in a log.
- **Docking.** At the final gate the ring closes around the comet; the pod
  constellation brightens; the burn bar exhales. The journey is only *done* at the
  production log line — the estate's own definition, rendered.
- **The Andon mood.** While `main` is red the whole scene's ambient light shifts amber.
  Health is felt in peripheral vision, not read.

### Narration (Page 1)

Three modes over the sovereign voice service and `useEstateVoice`:

1. **Live commentary (ambient).** Speaks only at transitions — "Commit `e3cf9e5`
   opened its pull request. Fast gate green in twenty seconds." Unprompted interrupts
   exactly twice: a gate failure, and an approval gate awaiting the founder's word.
2. **Story mode.** Focus any comet or wreck: "This deploy. Pushed 08:12; two gates
   failed first; merged 08:47; signed; rolled in ninety seconds; serving now." Every
   sentence generated **deterministically from the ledger** — templates over real
   timestamps, never an LLM narrating your pipeline from vibes.
3. **Interrogation.** Target-lock a cracked gate, ask "why did this fail?" → routed to
   `ask_holmes` on the estate MCP; the answer is spoken **and** shown as an ephemeral
   subtitle (the heard-transcript proof the HUD spec demands), fading after 3s.

### Interaction (Page 1)

- **Focus a gate** → its data hologram unfolds: real check-run output, real Flux

---

## Page 2 — The Observatory (the Three Planes, alive)

A separate page from the River, one roof: fleetview. Where the River follows *code to
the cluster*, the Observatory follows *intelligence through the machine*. The
consultant's ruling is the geometry: the three planes do not run sequentially, they run
as **concentric filters** — so the Observatory is three concentric rings, and work is
seen passing *outward* through them.

- **Ring 1 — the Generative Swarm (innermost, warm, turbulent).** Every live agent is a
  star. CRDT shadow-memory edits fire as synapses between stars; tuple-space exchanges
  are comets passed hand to hand. A hundred experiments burn here at once and none of
  them touch git — the ring has no outer edge until the Crucible accepts something.
  Spend is the burn bar on the horizon. Data: LiteLLM router stats, the ttcs CRDT
  state, the tuple space, `jev_decisions` latency/confidence.
- **Ring 2 — the Adversarial Crucible (the storm ring).** AI evaluating AI, made
  visible as weather. Red-team mutations strike code as **lightning**; a test suite
  that survives a mutant is exposed as theatre and the strike leaves a scorch mark.
  JudgeWorker's four dimensions turn as scales; JudgeDriftSentinel's JS-divergence is
  the ring's balance — when judges drift, the ring visibly wobbles. Failures don't
  disappear: they fall back inward as embers (`failing_test` tuples) into the Swarm.
  Data: the red-team catalog and promoter, ParEval bootstrap CIs, circuit-breaker
  trips, `bin/idp-reversibility-gate` verdicts.
- **Ring 3 — the Physics Engine (outermost, cold, crystalline).** No LLM decides
  anything here, so nothing here flickers: Z3 proofs grow as **crystal lattices**, the
  four-stage gauntlet is a vault with four doors, and every Aevum attestation is a
  **seal stamped in light** — Ed25519 + ML-DSA-65, hash-chained, timestamped. What
  passes the third ring is *true*, and the River carries it to the cluster.
- **The event horizon.** The Universal Write Boundary — the unsealed gap where
  `engine.py` still writes straight to disk — is rendered as a **crack in the ring
  wall**, glowing until the day it is sealed. The page does not hide the estate's
  debts; it makes them unmissable. Every known gap is a visible fracture with a name.

## The Ultimate Experience — the layer that makes it 2200

1. **Genesis rewind.** Touch any pod in the cluster and rewind its entire biography:
   the commit, the agent session that wrote it, the debate the judges had about it,
   the mutants it survived, the proof that sealed it, the deploy that carried it.
   Every artifact in the estate has a full ancestry, and the ancestry *plays*.
2. **The estate dreams.** Overnight work is re-rendered as a timelapse at sunrise — the
   morning briefing is a short film of your empire building itself while you slept,
   narrated. Not a digest email. A premiere.
3. **Presence.** The scene idles in ambient mode — slow, beautiful, silent. The moment
   you speak or touch, it swings to command mode. It knows the difference between being
   watched and being used.
4. **The soundtrack.** Each plane is an instrument family; real events are the notes.
   Green gates are consonance; a cracking gate is a dissonance you feel in your chest.
   You can hear main go red from the next room.
5. **Time machine.** Every ledger row is a coordinate. "Take me to last Thursday,
   4pm" — the camera flies you into the estate *as it was*, replayable, interrogable.
6. **Zero chrome, forever.** No sidebar, no breadcrumbs, no material-design card
   floating in space. The room is the interface; the whites stay dead.

  events. Focus moves, it collapses.
- **Time-scrub.** Drag the river's edge back: a week of deploys replays at 60×,
  comets in formation. "Show me Tuesday" — and you watch Tuesday.
- **The receipt.** Hold on a docked comet → the hash-chained proof: sha → PR →
  check-runs → image digest → cosign signature → reconcile revision → first log line.
  Proof, not assertion, as the UI itself.

## The data plane (why none of this is theatre)

One store, per THE HEADLINE: `catalog/estate.db`. New tables only:

- `deploy_journeys` / `deploy_journey_events` — written by `bin/estate-deploy-recorder`
  from facts that already exist (GitHub PRs and check-runs, Flux events via
  `FLUX_EVENTS_PATH`). Read over the one estate MCP server by
  `get_deploy_journey(sha)` / `list_deploy_journeys` (`mcp/plugins/deploy_journeys.py`,
  ADR 0006). The River replays these rows; live mode tails them.
- The Observatory reads what the planes already emit: `jev_decisions`, the red-team
  catalog, JudgeDriftSentinel's divergence scores, the verifier gauntlet's verdicts,
  Aevum receipts. Where a plane emits nothing today, the ring shows a **named gap** —
  UNKNOWN is the default, not a failure, and a dark ring segment is an honest answer.

Narration is template-over-ledger: deterministic text from real timestamps, spoken by
the sovereign voice service. No LLM narrates the pipeline; LLMs answer questions
*about* it (Holmes), and the subtitle proves what was heard.

## Build slices

| CP | lands | done means |
|---|---|---|
| CP1 | `deploy_journeys` ledger: recorder + MCP tools | `get_deploy_journey(<sha>)` returns a real push→merge chain on this repo |
| CP2 | `/fleetview/river` scene: gates, comets, basin, Andon ambient | a live push visibly flies; a forced failure visibly cracks its gate |
| CP3 | narration engine: templates over the ledger → :8899 | story mode speaks a real deploy, timestamps correct |
| CP4 | time-scrub + gate holograms + Holmes interrogation | "why did this fail" answers from a real red run, by voice |
| CP5 | `/fleetview/planes`: the three rings from live plane data | jev decisions, judge drift and Aevum seals all animate in one view |
| CP6 | voice steering both pages: spatial target-lock | "tell the one on the left to stop" reaches the right session |

## The honesty ledger (estate law: built and operating are different facts)

Real today: the Three.js scene lineage (`FleetReactorApp.tsx`), the voice loop and its
2100 spec, `estate-session-recorder`'s pattern, the HUD architecture, every data source
named above, the auto-PR and failure-notification pipeline (this branch). **New in this
spec:** the recorder + MCP tools (CP1, code in this PR), both scenes, the narration
engine, the dream timelapse, the soundtrack. The Universal Write Boundary is drawn as a
crack because it *is* one — the page ships with its debts visible or it does not ship.

