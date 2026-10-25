# Realtime film vs. a virtual world — which one the founder actually asked for

**Question** (the founder, 2026-10-25, three times in one sitting):

> "investigate ongoing work into film integration into fleet and face and consider if virtual world fits
> more than realtime film as founder's intentions … realtime virtual worlds that mirror the estate
> activities so founder interacts with agents through this virtual world with avatars … so founder can
> see an avatar of an agent coding, steer the movie, the agent ships, shows the app working in virtual
> world and sends the URL to founder who opens a real browser and sees the same app working in real
> world … is this realistic engineering-wise? what tools and open-source tooling is available?"

**Answer in one paragraph.** The founder described *three* things, not two, and they have different
truth properties. A **film** is narration over what already happened — honest only if every sentence is
a template over the ledger. A **world** is spatial presence over what is happening now — honest only if
every avatar state is a projection of a real record. A **real browser opening a real URL** is the only
one of the three that is *evidence*. So the decision is not "film or world": run **one scene contract**
(already specified in the movie spec §5.2) and build the world as a second renderer over it, gated
behind the film's S0–S2 — the world buys presence, the film buys narrative, and neither buys truth: the
URL does. Building the world first would be building the most expensive renderer before the record it
renders exists.

**Tags.** `[M]` measured by this pass (commands in Appendix A); `[R]` reported elsewhere in the repo and
not re-measured here; `[A]` asserted design decision, open to challenge.

---

## 1. What already exists, so this is not a greenfield decision

| Artefact | State | What it already settles |
|---|---|---|
| `docs/specs/2026-10-23-estate-as-movie-director-engine.md` | `[M]` present, 780 lines, "ready for external review" | the loop, the **Scene contract** (§5.2), the director (§5.3), the referent resolver (§5.4), three kinds of interruption (§5.5), the latency budget (§5.6), slices S0–S4, and a kill criterion (RB5). The causality claim — the founder's speech is upstream of agent behaviour — is S0, and S0 needs **no new visuals** |
| `docs/research/2026-10-23-cinematic-agent-interface-research.md` | `[M]` present | five findings that already moved the design: the film is a *plan* not a set of shots; camera control is parameters not prompts; shot grammar must be gradeable; the human's control is the product; the hardest warning is *stories that are not true* |
| `docs/specs/2026-09-08-estate-world-model-simulate-before-execute.md` | `[M]` present | the estate's existing "world" ambition is a **simulator** (simulate before execute), a different product; it must not be conflated with this one |
| `platform/voice-router` | `[M]` running 1/1 (`estate-inventory`, 2026-10-25) | the realtime media path already exists; a world does not need a new media stack |
| `platform/event-bus` | `[M]` running 1/1; JetStream with a file-store PVC (`platform/event-bus/nats.yaml`) | the event spine a world would render already exists, with replay |
| `platform/backstage`, `serve-fleetview`, `hermes-agent` (Face) | `[M]` backstage 1/1, hermes-agent 1/1, fleetview in `bin/` | three founder surfaces exist; finding F-09 is that none of them shares a command contract |

So the candidate is not "adopt a virtual world platform". It is "add a third renderer to a scene
contract that has been specified and not yet built".

## 2. What open source actually offers — measured liveness, 2026-10-25

Pulled with `gh api repos/<r>` in this pass (`[M]`). Stars are attention; `pushed` is the fact that
matters: a repo untouched for a year is a fork you will own.

| Repo | Stars | Last push | Licence | Role in a world renderer |
|---|---|---|---|---|
| `mrdoob/three.js` | 116,904 | 2026-10-25 | MIT | the renderer; runs in the founder's browser, nothing to install |
| `BabylonJS/Babylon.js` | 26,224 | 2026-10-23 | Apache-2.0 | alternative renderer; heavier, batteries included (inspector, physics) |
| `colyseus/colyseus` | 7,470 | 2026-10-22 | MIT | room-state sync (authoritative server, delta patches) — the piece a world needs and a film does not |
| `heroiclabs/nakama` | 13,581 | 2026-10-25 | Apache-2.0 | **refused**: brings its own realtime stack *and* its own database — a duplicate layer under AGENTS.md §6 |
| `workadventure/workadventure` | 5,886 | 2026-10-24 | none detected | 2D "office" presence; fastest honest demo of "the founder walks to an agent's desk" |
| `pixiv/three-vrm` | 2,232 | 2026-10-22 | MIT | VRM avatars in three.js — the avatar format, not an avatar vendor |
| `godotengine/godot` | 119,043 | 2026-10-23 | MIT | **refused for v1**: native engine; web export is a second toolchain and a large download for a founder who wants to open a tab |
| `Hubs-Foundation/hubs` | 2,222 | 2026-08-23 | MPL-2.0 | presence-first rooms; a fork surface, not an integration surface |
| `vircadia/vircadia-native-core` | 542 | 2025-07-01 | NOASSERTION | **refused**: dormant 16 months — a maintenance liability |
| `opensim/opensim` | 287 | 2026-10-22 | NOASSERTION | **refused**: the OpenSim lineage; wrong century for a browser-first estate |
| `livekit/livekit` | 21,800 | 2026-10-25 | Apache-2.0 | live A/V; **only if** `voice-router` cannot carry it — otherwise a duplicate layer |
| `versatica/mediasoup` | 7,405 | 2026-10-25 | ISC | SFU alternative to livekit; same rule |
| `remotion-dev/remotion` | 67,323 | 2026-10-25 | NOASSERTION (source-available, not OSI) | **offline** renders of a film cut; not a live path, and the licence must be read before commercial use |
| `microsoft/playwright` | 98,472 | 2026-10-25 | Apache-2.0 | the truth anchor: drives a real browser, captures a real screenshot of a real URL |

Two conclusions from the table alone:

1. **Everything a browser-based world needs is maintained and permissively licensed.** No supply-chain
   reason not to build one, and no vendor to adopt.
2. **Nothing in the list is "an avatar of an agent doing real work".** Each is a renderer, a transport,
   or an avatar format. The mapping from *agent activity* to *what the avatar is doing* is ours, and it
   is the only novel part.

## 3. What the research field says — probed live, not recalled

arXiv API, 2026-10-25, eleven bounded queries across two probes, newest-first (`[M]`), so this is the
field now, not the classics.

| Probe | What came back | What it means for the decision |
|---|---|---|
| `"generative agents" AND simulation` | `2610.22407` simulated urban mobility; `2610.11951` behavioural phenotypes; `2610.09296` the AI evaluation ecosystem | the generative-agent line is alive and has moved to **behavioural fidelity in simulators** — a research instrument, not a UI |
| `"digital twin" AND "software engineering"` | `2610.18635` DTScribe; `2610.10631` ruleless digital twins; `2609.29061` LLM + digital-twin review | "digital twin" means **a model of a physical asset**, not a room where agents have bodies |
| `"world model" AND interactive AND agent` | `2610.30789` Introduction to World Models for Generalist Agents; `2610.31066` Dual Exam; `2610.30657` distributional world models | world models are built to **predict and control** — to replace the environment, not to display it |
| `embodied AND simulation AND benchmark` | `2610.30589`, `2610.29702`, `2610.30197`, `2610.28432` | the sim-to-real ecosystem (NVIDIA Cosmos/COMPASS) is about robots; the estate's embodiment is a browser tab |
| `"multi-agent" AND visualization AND observability` | `2610.30717`, `2610.24498`, `2610.12793`, `2610.07031` | **no paper on visualising real agent work in a world**; hits are video generation, pedagogy, driving world models |
| `avatar AND "virtual reality" AND collaboration` | `2610.26360` avatar gaze control in asymmetric MR–VR; `2603.09294` **latency and QoE in networked VR whiteboards**; `2601.02214` avatar exposure and coordination | presence is studied where it changes **coordination**, and latency is studied because it breaks presence |
| `"GUI agent" AND world` | no GUI-world-model hits | there is no world model of a user interface to lean on; the honest renderer of an app is the app |

**Field-level finding (F-12).** There is a live field for *simulating* agents, one for *presence*, and one
for *predicting environments*. There is **no field for observing real agent work through a virtual
world**. That is not a capability we can import; it is the part we would invent — and an invented
observability surface is exactly the kind that can lie (the cinematic digest's finding 1.5), so it must
be built on a record that already exists and graded by whether it changes a decision.

## 4. The two latency budgets that decide the architecture

- `2603.09294` puts QoE damage on the table at ordinary network latency. A world that lags while an agent
  ships is worse than a film that cuts, because the founder cannot tell lag from a stall. So the world's
  budget is *presentation* latency only: state arrives on the bus, the browser interpolates, nothing
  waits on a round trip to a model.
- The movie spec's §5.6 cut budget (`[R]`) is the film's number. The world reuses it rather than
  inventing a second one — one budget per surface, both traceable to the same event spine.

## 5. Engineering realism — what each option actually costs

Estimates are `[A]`, sized against this estate's own delivery rate (the epic's slices), not a vendor demo.

| | Film (S0–S2) | World v1 (one room, 6 avatars) |
|---|---|---|
| New build | director planner, scene contract, narration templates, TTS, `/fleet` stage | the same scene contract, plus a 3D room, avatar rigs, an activity→pose mapping, a room-state server |
| New dependencies | none beyond what is deployed (bus, voice-router) | three.js + three-vrm + Colyseus (MIT, pushed this week) |
| New ops surface | a renderer process | a room server with state, plus asset hosting |
| Truth property | **strong** — every line is a template over the ledger | **weak by default** — an avatar can be made to look busy; only the side panel and the URL are evidence |
| Founder value | "what happened, and what do I say about it" | "who is here, and can I walk to them" |
| Size | 4–6 agent-weeks to S2 (`[A]`) | 6–9 agent-weeks to a pilot with one 3D generalist, plus ongoing asset cost (`[A]`) |
| Failure mode | a slideshow (kill: RB5) | a screensaver never opened twice |

**Verdict (R-59).** Build the film first on the scene contract, then the world as a *renderer* of the
same contract — never as a second source of truth. The founder's four-part wish decomposes exactly:

| The founder's words | Which renderer answers it |
|---|---|
| "see an avatar of an agent coding" | world (presence), backed by the agent's real tool-call stream — **never** synthesised keystrokes |
| "steer the movie" | film (S3 director's chair, `/nudge` → the runtime's channel) |
| "the agent ships and shows the app working in the virtual world" | film cut + a world "screen" object that is a **live iframe** of the deployed URL |
| "sends the URL to founder who opens a real browser and sees the same app" | neither — Playwright capture plus the URL is the evidence, and it is already the estate's proof pattern |

## 6. The one thing that must never be built

A world in which an avatar types code the agent is not typing, or walks to a desk the agent is not at.
That is a fabricated evidence surface — the same defect as narrating instead of proving (AGENTS.md §3).
So the law is structural: **the world renderer may only read the scene contract, and the scene contract
may only be filled from the event spine and the work-item record.** A state not on the spine shows as
*idle*, and says so.

## 7. Kill criteria for the world pilot (before it starts)

1. **Decision test.** In a 30-minute founder session the world must change at least one decision (a
   summon, an assignment, a halt). Zero changed decisions ⇒ kill, keep the film.
2. **Latency test.** Presentation lag p95 above the film's §5.6 budget for a state update ⇒ kill.
3. **Truth test.** Every visual state in the session resolves to a spine event id. Any visual with no
   referent is a ship-blocker, not a bug.
4. **Second-visit test.** The founder opens it unprompted within two weeks. If not, it is a demo.

## 8. Recommendation, one sentence each

- **Yes to realtime visuals** — that is the film, it is specified, and S0 proves causality with no new
  visuals at all.
- **Yes to a virtual world, later, as a renderer** — one room, six avatars, fed by the bus, the real URL
  on a screen in the room, gated on S0–S2 and the four kill criteria.
- **No to any synthetic depiction of work** — the URL and the ledger are the only evidence, and a world
  that invents them is worse than no world.

---

## Appendix A — the commands behind every `[M]`

```bash
# tooling liveness (2026-10-25, two batches)
for r in mrdoob/three.js BabylonJS/Babylon.js colyseus/colyseus heroiclabs/nakama \
         workadventure/workadventure pixiv/three-vrm godotengine/godot \
         Hubs-Foundation/hubs vircadia/vircadia-native-core opensim/opensim \
         livekit/livekit versatica/mediasoup remotion-dev/remotion microsoft/playwright; do
  gh api repos/$r --jq '"\(.full_name)|stars=\(.stargazers_count)|pushed=\(.pushed_at)|lic=\(.license.spdx_id // "none")|archived=\(.archived)"'
done

# literature (2026-10-25, eleven bounded queries, newest-first)
python3 /tmp/estate_arxiv_probe.py    # six queries
python3 /tmp/estate_arxiv_probe2.py   # five queries

# what is already deployed
# estate-inventory (intent) -> operating=38, degraded=5, frozen=20; voice-router 1/1; event-bus 1/1
rg -n 'jetstream|store_dir' platform/event-bus/nats.yaml
rg -n '^#{2,3} ' docs/specs/2026-10-23-estate-as-movie-director-engine.md
```
