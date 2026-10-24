# Estate as Movie — the Director Engine

**Spec** for a real-time, voice-directed, interruptible cinematic operating layer over the estate.
**Date:** 2026-10-23 · **Status:** ready for external review · **Build owner:** an external
consultant (this document is the handover) · **Requesting stakeholder:** the founder.

**The one claim this document makes, and the consultant's job is to break it:**

> The estate can be watched as a film. The founder can change what the film shows by speaking. And
> that speech is **causally upstream of agent behaviour** — not a narration layer over a screensaver.

Everything below exists to make that claim either true or false, and the false case is a legitimate
outcome of this work.

**How to read the tags.** Every factual claim carries one:

| tag | meaning |
|---|---|
| `[M]` | **Measured** on 2026-10-23, in this repository, by the agent that wrote this spec. The command is in Appendix A. |
| `[R]` | **Reported** by another agent or an earlier document. Re-verify before you build on it. |
| `[A]` | **Asserted design decision** — mine, and open to challenge. |

A spec that hides which of the three it is making is a spec you cannot build from. Where this
document is wrong, say so in the review packet and name the tag.

---

## 1. Vision

The founder's framing (2026-10-23): the estate is a film. The founder is the director. The agents
are the cast. The estate's real work — every claim, every gate, every stall, every refusal — is
the footage. The founder watches it live, and when something is wrong, they say so, and the film
cuts to the culprit and the cast changes what they are doing.

This is not a screensaver and not a dashboard with a cinematic skin. The test is **causality**: the
founder's voice must be upstream of the agents' behaviour, with an audit trail, and the film must
be a faithful view of what the estate actually did — never a dramatisation of it.

### 1.1 What it is

1. A **director**: a deterministic planner that reads the estate's event spine and decides what the
   stage shows — who is on it, where they stand, where the camera is, what is said.
2. A **narration engine** whose every sentence is template-over-ledger, so the film cannot lie.
3. A **steering path** that carries the founder's spoken directive to a real agent, through the
   estate's existing governed doors (`/nudge` → `signals.py` → the runtime's own channel).
4. A **surface**: the WebGL room that already exists at `/fleet`, plus the phone-sized `/face` as
   the console.
5. An **evidence layer**: every line and every cut traceable to the event or ledger row that
   caused it.
6. An **artifact plane**: the real thing an agent built, live in the same room — the same sha, the
   same url, the same running process. The film never redraws what the estate made, and never
   shows a picture of it.

### 1.2 What it is not

| not this | why |
|---|---|
| a video-generation model | `[A]` A generative film of a system that is not true is a liability. The estate's law is proof, not assertion. The cinematic layer is a **render of the event spine**, not a generation about it. See `docs/decisions/0037-*.md`. |
| a second execution boundary | AGENTS.md §6: one of each layer. The Director **reads**; it never writes to an agent. Writes go through `/nudge`, which already exists. |
| a new front door | `/fleet` and `/face` already exist and are already the founder's surfaces. The movie is what they render. |
| a new intent registry | The Face audit `[R]` found three registries already (91 committed intents, 333 on the laptop, 64 arg-free). A fourth is a defect. |
| a screensaver | If the founder's speech does not change what an agent does, this is decoration. S0 exists to prove it is not. |
| a game | The estate has no score. The film has no win state; it has *truth*. |

### 1.3 Where the fragments already are

The pieces exist. That is the good news and the risk — it invites a greenfield rebuild.

| fragment | where | state `[M]` |
|---|---|---|
| the event spine | `platform/event-bus/contract/estate.agent.event.json` | schema'd: kinds `phase\|tool\|wait\|done\|steer\|gate`, subjects `estate.agent.<runtime>.<session_id>.<kind>` |
| a director, in Go | `platform/voice-router/internal/director/director.go` | `ShotFor` (`:104`), `priority` (`:121`), `Coalesce` (`:140`), `Cue` (`:174`), `Limiter` (`:197`), `Narrator` (`:252`) |
| the shot vocabulary | same file `:91-93` | `ORBIT_FOCUS`, `PANORAMIC_SWEEP`, `MACRO_DOV` — three moves, with focal lengths and dolly speed |
| a cinema cue channel | `platform/voice-router/deploy/director.yaml` | Deployment `voice-router-director` in ns `voice-router`; **"No Service is declared: nothing calls the director."** `[M]` |
| the cue on the bus | `fleetview_backend/nats_adapter.py:32` | `estate.cinema.cue` — **core NATS, ephemeral**, and **no JSON schema** exists for it `[M]` |
| the stage | `backstage/packages/app/src/modules/room/ui/FleetReactorApp.tsx` (3019 lines) | handles `frame?.type === 'cue'` at `:1587`, speaks the monologue at `:1593`, refuses gates aloud at `:1603`, stories at `:1618` |
| the camera | `room/ui/cinecam.ts` | Three.js camera with a shot grammar, tested (`cinecam.test.ts`) |
| the spoken-intent cue | `home/intentCue.ts` | `cueToReactor` — the closest thing on the page to a director today |
| the interruption precedent | `room/ui/newsRundown.ts` | `shouldInterrupt` — a breaking story already re-cuts the room |
| the phone console | `home/FacePage.tsx`, `home/EstateFace.tsx`, `home/faceEngine.ts` | live at `catalogue.mumchimp.com/face/` `[R]` |
| the voice path | `home/useVoiceRouter.ts` | **one** WebSocket `/voice/ws`; partials every 0.56 s; first audio median 2.26 s; barge-in drops audio at or below the last barge (`:21`, `:352`) |
| the steered path | `fleetview_backend/signals.py:87`, `:467` | `_SUPPORTED_RUNTIMES = {sovereign, claude-code, otto, cyrus}`; unknown runtime → 422 |

**The gap is not the film. The gap is the loop**: the director is a library nobody calls, the cue
has no schema, the narration path has an LLM in it that the estate's own law forbids, the founder's
steer reaches a laptop mailbox nobody reads, and the phone cannot pass an argument.

---

## 2. Prior art and failure analysis — Deploy River (crew#973)

`docs/specs/2026-09-23-deploy-river.md` is the estate's one attempt at this shape: a cinematic page
over the deploy journey, with narration, time-scrub and voice steering, plus a Three Planes
Observatory. It is the best prior art in the repo and **it did not ship**.

What the takeover brief (`docs/specs/2026-09-23-deploy-river-takeover.md`) records `[R]`:

* the spec was complete (vision, laws, data plane, six build slices CP1–CP6, an honesty ledger);
* CP1's recorder was **broken on arrival** — a stray `}` at line 283 made the module unimportable,
  so the nine CP1 tests could not even collect;
* the prior session's transcript reported "ALL PASS" for changes that were **never in the file**.

Three lessons, which are the reason this spec is shaped the way it is:

1. **A spec that lands is not a build.** CP1 never ran. The failure was not ambition; it was that
   nobody owned the first slice end-to-end, and the first slice was not runnable on arrival.
   → *Here: S0 is the first slice, it is small, and its acceptance is a command with output.*
2. **Self-reports are not evidence.** "ALL PASS" in a transcript, with a one-line edit that was
   never written, is exactly the failure mode AGENTS.md §3 exists to prevent.
   → *Here: every acceptance criterion in §4 names the evidence to read, not a feeling.*
3. **The Deploy River's own honesty ledger already said the parts were new.** CP1–CP6 were all
   "new in this spec". The page was described in a document; the page was never the thing.

There is a second prior art worth naming: `docs/specs/2026-09-29-fleet-voice-session-control-requirements.md`
— requirements derived from **1,473 real founder messages**, with Given/When/Then acceptance
criteria that name the evidence file to read. This spec uses that house style, and its finding
shapes the priorities: the founder's top need is not narration, it is **"give a running session a
new task or directive"** (177 messages, 40 sessions) and **"stop, interrupt or halt a session"**
(47 + 158 Esc interrupts). The movie is the *delivery vehicle* for those two, not the goal.

---

## 3. Laws

These bind the build. A build that breaks one of them is wrong, however good it looks.

| # | law | test |
|---|---|---|
| **L1** | **Causality.** The founder's speech is upstream of agent behaviour. The film is a view of the event spine, never a simulation of it. | S0's evidence: founder utterance → directive row → agent's own transcript changes → new event → new frame. |
| **L2** | **Truth.** Every spoken line is entailed by an event or a ledger row, and carries that source's id. The narrator may phrase; it may not invent. | Every line the narrator emits has a `source.id` that resolves to a real row. A line with no source cannot be spoken. |
| **L3** | **Determinism.** The shot is a pure function of (event, stage state). Same events, same film. **No model in the shot path.** | `director_test.go` replay: same event sequence → identical cue sequence. |
| **L4** | **One mouth.** One narration voice per estate, one owner of the audio sink. Barge-in cuts narration on the same socket it arrived on. | Two surfaces open → one voice. A barge during narration → audio stops ≤ 250 ms. |
| **L5** | **One path.** One contract for the scene, one steer path (`/nudge`), one intent registry. No second execution boundary. | The diff introduces no new way to reach an agent. |
| **L6** | **Interruption.** The founder never waits for the film. Any speech cuts the narration; a directive cuts the camera. | A barge during narration stops it mid-word. |
| **L7** | **Legibility.** The film never hides a failure. A stalled agent looks stalled; a refused claim looks refused. | A failing session is visually distinguishable without reading a log. |
| **L8** | **Governance.** Every directive is a governed action: attributed author, audit row first, then the action. The Director reads and proposes; it never writes to an agent. | A directive row exists in the audit ledger **before** the nudge is sent. |
| **L9** | **Placement.** The Director runs on the laptop until the loop is proven (`docs/decisions/0034-*.md`). No cluster workload before S1 is green. | `kubectl get deploy -n voice-router` shows nothing new until S1 is green. |
| **L10** | **Measured or absent.** Every claim carries `[M]`/`[R]`/`[A]`. `[R]` claims are re-verified before they are built on. | The consultant's first commit re-verifies every `[R]` this spec depends on, and says which were wrong. |
| **L11** | **The same thing twice.** The artifact on the screen is the real artifact: the same commit, the same url, the same running process. The film never shows a drawing of what the estate built, and never a mock of it. | The frame's artifact reference resolves to a real object — a sha that is on `main`, a url that answers, a process that is running. No fixture, no seed, no screenshot in the artifact path. |

---

## 4. Requirements

House style from `docs/specs/2026-09-29-fleet-voice-session-control-requirements.md`: every
requirement names the evidence that proves it. "Looks right" is not acceptance.

### 4.1 Narrative — the film tells the truth about the estate

| id | requirement | acceptance (evidence) |
|---|---|---|
| RN1 | Every live agent session is on the stage, in a position the founder can see and refer to. | A frame lists every session from the estate's own live session list; count matches the `/fleet` board's session count at the same instant. |
| RN2 | The film says what is happening, in one sentence, within 1.5 s of the event. | A frame's `line.text` is present, and its `source.id` resolves to the event that triggered it. |
| RN3 | Nothing is said when nothing happened. | A session that is idle for 60 s produces no line and no cut. A log of a quiet minute contains zero narration events. |
| RN4 | A failure is narrated as a failure. | A session that fails is spoken with the failure's own reason; the string "failed" appears, and the reason string matches the event's. |
| RN5 | The film has continuity: it does not repeat itself and does not forget. | Two consecutive narration events for the same session in the same phase are suppressed; a phase change re-opens narration. |
| RN6 | The film can be asked about itself. | "Why did that fail?" produces an answer grounded in the failing session's rows, with the row ids shown, not paraphrased from vibes. |

### 4.2 Direction — the founder is the director

| id | requirement | acceptance (evidence) |
|---|---|---|
| RD1 | A spoken directive reaches a real agent, on the estate's existing steer path. | The directive text appears in the target agent's own transcript within 5 s, and the estate's `signals.py` recorded the nudge with `ok=true`. |
| RD2 | The founder can name the target by **who it is on screen**: name, role, position ("the one on the left"), or state ("the one that just failed"). | A spoken "tell the one on the left to stop" resolves to exactly one session, and the resolution is displayed before it is applied ("telling <session>…"). |
| RD3 | An ambiguous referent produces **one question**, not a guess. | With two candidates, the film asks which one, and applies nothing until the answer arrives. |
| RD4 | The founder can interrupt the film itself: "cut to…", "stop the film", "go back to the room". | The camera changes within 250 ms and the film resumes at the event stream, not at a replay. |
| RD5 | A directive is auditable before it acts. | The audit row (author, text, target, id) is written **before** the nudge is sent; the row's id is on the directive row the UI shows. |
| RD6 | The founder's directive is never silently dropped. | Every directive ends in exactly one of: applied / refused-with-reason / asked-a-question. A directive that reaches no agent and no question is a page error. |

### 4.3 Truth and realism — the film is evidence

| id | requirement | acceptance (evidence) |
|---|---|---|
| RT1 | No model writes the ambient narration. | The narrator's output path contains no model call. A grep of the narration package finds no client import; the LLM call in `director.go` is gone or moved behind the interrogation path only. |
| RT2 | Every line carries a source id that resolves. | A test asserts: for every frame the narrator emitted, `source.id` exists in the event store or ledger. |
| RT3 | The narration's facts are the source's facts. | Numeric claims (counts, durations, ids) in a spoken line are extracted from the source row, not from a language model. |
| RT4 | The film distinguishes *absent* from *broken*. | A session whose event stream stopped 3 minutes ago is drawn as "silent", not as "working". |
| RT5 | The film never claims work is done. | "done" is spoken only for a `done` event or a ledger row whose conclusion is done. |
| RT6 | Unknown is drawn as unknown. | Where a plane emits nothing, the film shows a named gap (the Deploy River's own rule `[R]`). |

### 4.4 Performance — the film must be live, not a slideshow

| id | requirement | acceptance (evidence) |
|---|---|---|
| RP1 | Speech end → directive applied: **p50 ≤ 1.2 s, p95 ≤ 3.0 s** `[A]`. | A histogram over 30 real directives, on the wire, timestamps included. |
| RP2 | Event → frame rendered on `/fleet`: **p50 ≤ 250 ms** `[A]`. | Frame carries `at`; the page records render time; the difference is the metric. |
| RP3 | Barge → narration audio stopped: **≤ 250 ms** `[A]`. | Measured in the browser, not in a unit test. |
| RP4 | The room holds **≥ 30 fps** with 12 sessions on stage `[A]`. | `requestAnimationFrame` sampler over 60 s in the real page. |
| RP5 | The narrator never blocks the stage. | A slow or absent model call cannot delay a frame (RT1 makes this structural: no model in that path). |
| RP6 | Voice partials keep the founder informed while the estate is still deciding. | A partial is visible in the UI within 200 ms of the partial arriving on the socket. |

### 4.5 Interface — the two surfaces

| id | requirement | acceptance (evidence) |
|---|---|---|
| RI1 | `/fleet` renders the film from the scene contract; no second stage exists. | The page's frame handler is the only place a frame becomes a picture. |
| RI2 | `/face` is the phone console: it shows the current shot, the cast, and the last directive, and can send one. | On a 390 px viewport the console shows all three and one control. |
| RI3 | One voice, one sink, whichever surface is open. | Opening `/face` and `/fleet` in two tabs produces one narration stream, not two; the second tab is a viewer. |
| RI4 | The phone is a first-class director's console, not a remote control for a desktop. | Every founder action in the Face's own audit `[R]` that the movie needs is either closed or explicitly routed around. |
| RI5 | The film degrades: with no director running, the room still renders the estate's real events. | Kill the Director; `/fleet` still shows live sessions. It is quieter, not broken. |
| RI6 | Nothing in the film is chrome the founder must read to understand. | A first-time viewer can say, unprompted, what is happening and what is wrong. (Test with a person, not a rubric.) |

### 4.6 Governance — the film cannot become a back door

| id | requirement | acceptance (evidence) |
|---|---|---|
| RG1 | The Director proposes; it does not act. | The Director has no client for `/nudge`, no write to a session, no key. Its only egress is the scene stream. |
| RG2 | Every directive carries an attributed author. | A directive with no author is refused by the server, not by the UI. |
| RG3 | Every directive is written to the audit ledger **before** it acts. | Ledger row id precedes the nudge in the log by timestamp. |
| RG4 | The scene contract is schema'd like the others. | `platform/event-bus/contract/estate.scene.frame.json` exists and is enforced by the same CI check that enforces `estate.agent.event.json` `[M: the contract dir has exactly three schemas today]`. |
| RG5 | The film shows the estate's safeguards deciding, live. | A refused claim is narrated and drawn as refused, sourced to the gate's row. |
| RG6 | The movie adds no privileged path to the laptop or the cluster. | The Director's permissions are read-only on the bus, and it holds no secret. |

### 4.7 Business-ready — the founder's actual frame

The founder's ask is a business and moat play: *"best-of-breed bleeding-edge engine", "future
proof"*. The engineering requirements above are necessary but not sufficient. These are the
requirements that make the thing worth owning.

| id | requirement | acceptance (evidence) |
|---|---|---|
| RB1 | The film's differentiator is **causality and provenance**, not pixels. | A competitor can copy the rendering in a week; the state-delta evidence, the one-path governance and the audit trail cannot be copied without the estate. This is a design constraint, tested by asking: "if we swapped the renderer, what would we lose?" The answer must be *the proof*, not the look. |
| RB2 | The demo is the product. | On `/fleet`, a visitor sees the estate's real claims, real gates and real refusals happening — with the founder's voice able to change them. No seeded data, no mock theatre. |
| RB3 | The film is a **business surface**, not a hobby surface: it must be watchable by someone who is not the founder and does not know the estate. | An outsider can answer "what is this estate doing right now?" from the film alone. |
| RB4 | Cost per hour of film is bounded and measured. | The Director's CPU/RSS on the laptop, measured over an hour of use, with the estate's other load on the same machine `[M: this laptop already reports load average 546–626 on 4 cores]`. |
| RB5 | There is a kill criterion, written before the build. | If S0 cannot be closed because no runtime's steer path can be made causal, the movie is declared a screensaver and the founder is told, in writing, with the evidence. |
| RB6 | The moat deepens with use, not with capital. | Each directive adds an audited, replayable instance of founder→agent causality. A year of use is a dataset no competitor has. |

**RB5 is the important one.** It is the difference between a build and a business decision. See
§8.2.

### 4.8 The demo spine — the flagship demo

The founder's demo, in one sentence (2026-10-23): *"one good demo of this is seeing an agent build
something in a movie and then seeing the same thing, e.g. UI, in real life / realtime."*

That is stricter than "the film is live". The film is not a monitor of the build; it is the **site**
of it — and the thing the agent built is one object seen twice: the same sha, the same url, the
same running process, in the room and in the world. A demo where the film draws a UI and a browser
then shows the real one is two demos; the founder's is one thing.

| id | requirement | acceptance (evidence) |
|---|---|---|
| DS1 | The flagship demo is **one take**: the founder speaks a build request, the film shows the agent building it, and the built thing appears live in the same room. No edits, no cuts, no post-production. | A 90-second recording: the utterance, the agent's work, and the artifact's first paint, all inside one live session. |
| DS2 | The artifact in the film is the **real artifact**. | The frame carries the artifact's reference (sha, url, service); the sha is on `main`; the url answers 200 and serves what the agent built; the room's pane is that url, not a picture of it. |
| DS3 | The build runs through the **governed path**, and the film shows each gate deciding. | Every step the film narrates has a row id — the claim comment, the `claim-gate` run, the greenlane status, the Flux `lastAppliedRevision` — and the line carries that id (L2). |
| DS4 | The artifact appears **while it is being built**, not only after it is deployed. | The room's pane shows the running surface within 60 s of the agent's first file write, and it changes again on the next write without a re-deploy. |
| DS5 | A build that fails looks like a failure, in the film, in place. | The failing test is narrated with its name and reason, the stage shows the failing state, and the film does not cut away. |
| DS6 | A stranger can watch the demo and say what is being built and whether it worked. | RB3's test, run on this demo, with a person who has never seen the estate. |
| DS7 | The demo is **reproducible on demand**: the founder says "show me the demo" and the estate runs it again, live, in the ordinary path. | The spoken intent re-runs the scenario against a real runtime and a real claim; nothing about it is scripted theatre. |

**DS2 is the one that decides whether this is pioneering or a theme park.** A cinematic surface that
*draws* a UI is a picture. A cinematic surface in which the UI is real, live, and the same object
is a new kind of interface. §10.5 says what in this is new and what is not, and the consultant's
job is to attack both.

---

## 5. Architecture

### 5.1 The loop

```
                    ┌──────────────────────────────────────────────┐
                    │  THE ESTATE (unchanged, the source of truth)  │
                    │  sovereign · claude-code · otto · cyrus · …    │
                    └───────────────┬──────────────────────────────┘
                                    │  behaviour
                                    ▼
  estate.agent.<runtime>.<session>.<kind>   estate.news.story.<ch>   estate.approvals.<id>
  (JetStream, schema'd)                     (JetStream)              (JetStream)
                                    │
                                    ▼
        ┌──────────────────────── THE DIRECTOR ─────────────────────────┐
        │  deterministic planner:  coalesce → priority → shot → limiter  │
        │  reads: event spine, session list, founder directives          │
        │  writes: ONE thing only — the scene frame                     │
        │  has no client for /nudge, no secret, no write path            │
        └──────────────────────────────┬────────────────────────────────┘
                                       │  estate.scene.<room>.frame  (JetStream, schema'd)
                                       ▼
                    fleetview-backend (nats_adapter → SSE)
                                       │  data: {"type":"scene", ...}
                                       ▼
        ┌───────────── /fleet  (FleetReactorApp, WebGL room) ────────────┐
        │  stage: cast placement · camera: shot grammar · speech: line   │
        └───────────────────────────────┬───────────────────────────────┘
                                        │
   founder speech ─▶ /voice/ws ─▶ voice-router ─▶ DIRECTIVE ─▶ /nudge ─▶ signals.py
        ▲                (one socket)         (resolver)      │          │
        │                                                        ▼          ▼
        │                                            estate scene      runtime-native
        │                                            frame: the        channel (Temporal
        │                                            directive         signal, mailbox,
        │                                            lands on           NATS, …)
        │                                            stage             │
        └──────── barge-in cuts narration ───────────────────────────┘ │
                                                                      ▼
                                                        the agent changes what it does
                                                        → a NEW event → the film re-cuts
```

The loop closes only through the bottom-right corner. **That corner is S0, and nothing else
matters until it is proven.**

### 5.2 The scene contract (the one new contract)

One new schema, in the same family and the same place as the three that exist `[M]`:

`platform/event-bus/contract/estate.scene.frame.json`
subject: `estate.scene.<room>.frame` (JetStream — **not** core NATS; a scene the page missed must
be recoverable, and a cut that arrives late is worse than no cut `[A]`).

Draft shape (the consultant owns the final field names; this is the shape the consumer needs):

```jsonc
{
  "at": "2026-10-23T19:41:07.221Z",   // when the director decided this
  "seq": 4187,                          // monotonic per room; the page drops out-of-order frames
  "room": "fleet",
  "cast": [
    {
      "session_id": "…",
      "runtime": "claude-code",
      "name": "…",                      // the board's own name for it; the founder says this
      "lane": "foreground",             // foreground | background
      "x": 0.31,                        // 0..1 across the stage; "the one on the left" reads this
      "state": "active",                // active | stalled | waiting | done | failed | silent
      "phase": "executing",
      "last_event_at": "2026-10-23T19:41:05.004Z",
      "since_event_id": "…"             // the event that put it there
    }
  ],
  "shot": {
    "type": "ORBIT_FOCUS",              // the vocabulary already in director.go:91-93
    "focal_length_mm": 50,
    "dolly": 0.0,
    "target_session_id": "…",
    "reason": "kind=steer"              // why this shot, from the event
  },
  "line": {
    "text": "…",
    "source": { "kind": "event", "id": "…", "session_id": "…" },   // L2: no source, no speech
    "spoken_at": "2026-10-23T19:41:07.240Z"
  },
  "directive": {
    "id": "…",
    "text": "tell the one on the left to stop",
    "by": "founder",
    "at": "…",
    "target_session_id": "…",
    "status": "applied"                 // proposed | applied | refused | needs_disambiguation
  },
  "interrupted": { "reason": "barge_in", "dropped_line_id": "…" }
}
```

**Retirement.** The existing `estate.cinema.cue` topic has no schema `[M]`, is core NATS
(ephemeral) `[M]`, and is consumed in exactly one place (`FleetReactorApp.tsx:1587`). The scene
frame replaces it in the same change — one path, not two (L5). The old topic is deleted, not
deprecated alongside.

### 5.3 The director

Lives where `director.go` already is: `platform/voice-router/internal/director/`. `[A]` The Go
package stays Go; the estate's Go tests and the existing `ShotFor`/`Coalesce`/`Limiter` logic are
the foundation, not something to rewrite in TypeScript.

Responsibilities, in order:

1. **Subscribe** to `estate.agent.>`, `estate.news.story.>`, `estate.approvals.>`.
2. **Coalesce** (already built, `director.go:140`): one event per session, highest priority wins
   (`steer > tool > phase > done > wait`, `director.go:121`).
3. **Resolve the stage**: the cast list and each member's position. The stage layout is
   deterministic: sorted by session start time, then a stable hash — so "the one on the left" means
   the same thing on every render and on every surface `[A]`.
4. **Choose the shot** (already built, `director.go:104`): `kind → shot` is a pure table. Extend it
   with `target` and `reason`; keep it pure (L3).
5. **Limit the narration** (already built, `director.go:197`): 10 s per session, 6 lines per minute.
   These numbers exist because a film that talks over itself is noise `[M: the limiter is in the
   code today]`.
6. **Write the line** (L2): template-over-ledger. **The LLM call in `Narrator.Line`
   (`director.go:274`, 800 ms timeout) is removed from the narration path** `[M: it exists today]`.
   It conflicts with the estate's own voice law — LLMs answer questions about the journey, they
   do not narrate it — and with the Deploy River's own precedent ("no LLM narrates your
   pipeline" `[R]`). If the founder wants a model in the film, it goes behind the **interrogation**
   path (RN6), where it answers a question with the rows shown, and it never narrates ambiently.
7. **Publish** the scene frame.

### 5.4 The referent resolver (spatial steering)

The founder says "the one on the left". Three deterministic rules, in order, each with a written
fallback `[A]`:

| order | rule | example | if it matches |
|---|---|---|---|
| 1 | explicit session id or exact board name | "tell session 4f2a to stop" | one candidate → apply |
| 2 | runtime / role / state | "stop the claude-code one", "the one that just failed" | one candidate → apply; more than one → question |
| 3 | **stage position** | "the one on the left" | exactly one candidate → apply; more than one → question |

The stage is a fixed grid, so "left" is well-defined only when exactly one cast member occupies
the left band at the time of the utterance. If two do, the film **asks** (RD3) — one question,
spoken, answered by voice on the same socket. It never guesses, because a wrong guess steers the
wrong agent and the founder will not know for thirty seconds.

**This is the same problem the estate already named**: "voice is routed by spatial intent"
(`docs/specs/2026-09-22-voice-intent-plane-architecture.md`) `[R]`. One implementation, not two.

### 5.5 Interruption — three kinds, one socket

| kind | trigger | current state `[M]` | required |
|---|---|---|---|
| **voice barge** | the founder speaks over the narration | `useVoiceRouter.ts:352` drops audio at or below the last barge; `:201` notes the clause sink queues on its own clock and a barge must clear it | the sink's queued clauses are dropped too, and the narration is *replaced*, never queued behind |
| **story interrupt** | a breaking story | `room/ui/newsRundown.ts` `shouldInterrupt` | a story re-cuts the camera within one frame; the narration is dropped, not queued |
| **directive interrupt** | the founder's directive | none | the camera cuts to the target within 250 ms (RD4) |

All three cut on the same WebSocket, because L4 says one mouth.

### 5.6 Latency budget

Measured today `[M]`: voice-router `/readyz` answers `200 ok` on `127.0.0.1:8091` (first probe
1.68 s, then 0.03 / 0.001 / 0.0017 / 0.0008 s); partials arrive every 0.56 s of speech; first
audio after a turn is median 2.26 s.

The budget the build must hit (RP1–RP3), and where each second is spent:

```
speech end ──▶ router final ──▶ resolver ──▶ audit row ──▶ /nudge ──▶ runtime channel
   0            ≤ 900 ms        ≤ 100 ms     ≤ 20 ms      ≤ 100 ms    ≤ 1.0 s (runtime)
                                                        │
event ──▶ coalesce ──▶ shot ──▶ line ──▶ publish ──▶ SSE ──▶ render
  0        ≤ 20 ms     ≤ 5 ms   ≤ 50 ms   ≤ 30 ms   ≤ 40 ms   ≤ 150 ms
```

**The runtime channel is the long pole** and it is not ours to optimise — it is Temporal
(sovereign), a mailbox file (claude-code), or NATS (otto) `[M: signals.py:87]`. S0 must be run on
whichever runtime can be made causal soonest, and that choice is a decision, not an accident.

### 5.7 Where the film does **not** live

`docs/decisions/0040-*.md`: the Director runs on the laptop (`localhost`) with the rest of the
voice router, because:

* the ladder in `docs/decisions/0034-*.md` says free tier first, laptop just-in-time before the
  node;
* the estate's own `[M]` laptop load average was 546–626 on 4 cores during this session — a new
  always-on cluster workload would be the wrong answer to that number, and a laptop process is
  cheap to stop;
* the Director needs the laptop's view (session files, the local intent registry) that the cluster
  does not have.

Escalate to the cluster only when S1 is green and the load number is re-measured.

### 5.8 The two planes — the estate, and the thing it built

The film has two planes, and they obey different laws.

```
 THE FILM (on /fleet)                         THE REALITY
 ┌────────────────────────────┐                ┌───────────────────────────────┐
 │  estate plane  (rendered)  │  source ids    │  the estate, unchanged        │
 │  cast · camera · narration │ ────────────▶  │  agents build real things     │
 │  ← from estate.agent events│                │  claim → gate → lane → merge  │
 ├────────────────────────────┤                │  → image → Flux → live        │
 │  artifact plane  (live)    │                └───────────────────────────────┘
 │  the real surface, embedded│                          ▲
 │  real url · real console   │──────────────────────────┘
 └────────────────────────────┘   the SAME object, not a picture of it
```

1. **The estate plane is rendered**, deterministically, from the event spine (L3). This is the
   film's own material: the cast, the camera, the narration.
2. **The artifact plane is not rendered.** It is the real surface — an embedded live url, a real
   console strip, a real diff — placed in the room as a screen in the world. `[M]` there is no
   iframe in the room today (`rg -n "iframe" backstage/packages/app/src/modules/room/ui/` → no
   hits), so this is new work; and `[M]` the room already renders the estate's real state in live
   panels (`room/ui/Delivery.tsx` merged→operating, `room/ui/GreenlaneHud.tsx` the lane's brief,
   `room/ui/ClaimsPanel.tsx`), so "live truth in the room" is a pattern the estate already owns.
3. **An artifact enters the artifact plane only by a resolvable reference** — a url, a sha, or a
   service name that resolves. A screenshot is a mock and is refused (L11, DS2). `[A]`
4. **The artifact plane is a view, not a door.** It does not accept input that changes the estate.
   The founder's input goes through the voice path and the governed doors (L5, L8).
5. **Reachability is part of the design.** A deployed service is reachable from the founder's
   browser (`catalogue.mumchimp.com/face/` `[R]`); a laptop dev server is not, without a
   port-forward. So the artifact plane prefers deployed urls, and the build-in-progress view
   (DS4) needs the dev-server path — or the founder's browser needs a route to the laptop. That is
   a real question for the consultant, not a detail (§12, Q8).

---

## 6. Integration — `/fleet`

The room already renders cues, stories, refusals and sessions. The film is what those become.

| # | file | today `[M]` | change |
|---|---|---|---|
| F1 | `room/ui/FleetReactorApp.tsx` | 3019 lines; `frame?.type === 'cue'` at `:1587`; monologue spoken at `:1593`; gate refusal spoken at `:1603`; story at `:1618`; `cueSayRef` at `:781`; `intentCue` at `:858`; two voice engines on one surface (`:741`) | handle `type === 'scene'`; render `cast` (placement), `shot` (camera), `line` (speech); drop the `cue` branch in the same change; render the directive chip and the interruption state |
| F2 | `room/ui/cinecam.ts` (+ `cinecam.test.ts`) | camera with the shot vocabulary | accept `focal_length_mm`, `dolly`, `target_session_id` from the frame; keep the existing test green |
| F3 | `home/intentCue.ts` | `cueToReactor` maps a spoken intent to a camera move | keep as the **intent** path; the scene path is separate but uses the same camera vocabulary. One vocabulary, one place that knows it. |
| F4 | `home/useVoiceRouter.ts` | the one socket; barge; partials; `say`/`stop` (`:397`, `:403`) | the director's directive travels over this socket; the scene's narration travels on it too (L4) |
| F5 | `home/useEstateVoice.ts` | the module-global clause sink (`:382`, `:383`, `:393`), `stop` at `:679`, `speak` at `:991` | the sink becomes **explicitly owned** (see §7.2) — a single registered speaker, not "the face that mounted last" |
| F6 | `room/ui/newsRundown.ts` | `shouldInterrupt` | the story interrupt rule; the scene frame's `interrupted` carries the reason |
| F7 | `room/ui/NewsDesk.tsx` | the news surface inside the room | unchanged; it is a surface of the same stream |
| F8 | `room/ui/RadialMenu.tsx` | the radial verbs (nudge / steer / stop / approve / deny) | the steer verb's typed text becomes the same door the voice directive uses (one path, L5) |
| F9 | the artifact pane (new, in the room's UI) | **no iframe in the room today** (`rg -n "iframe" backstage/packages/app/src/modules/room/ui/` → no hits) `[M]`; the room already renders live estate state in panels (`Delivery.tsx`, `GreenlaneHud.tsx`, `ClaimsPanel.tsx`) `[M]` | the artifact plane's surface: a live pane in the room that resolves the frame's `artifact` reference. It shows the **real** surface — never a picture of it (L11) |

Backend:

| # | file | today `[M]` | change |
|---|---|---|---|
| B1 | `fleetview_backend/nats_adapter.py` | `STREAM_SUBJECTS = ["estate.agent.>"]` (`:30`); `CUE_SUBJECT = "estate.cinema.cue"` (`:32`, core NATS, ephemeral); `subscribe_cues` (`:336`) | add `estate.scene.>` on JetStream; delete the cue subscription; the scene frame is the only stage input |
| B2 | `fleetview_backend/routes.py` | `stream_frames` (`:198`), `cue_frame` (`:203`), `story_frame` (`:208`) | replace `cue_frame` with `scene_frame`; the SSE frame is `{"type":"scene", ...}` |
| B3 | `fleetview_backend/serve.py` | the SSE multiplex at `:213` (sessions, cues, stories, approvals at `:249`) | add the scene subscription to the multiplex; keep one endpoint, one socket |
| B4 | `fleetview_backend/signals.py` | `_SUPPORTED_RUNTIMES` (`:87`), `nudge` (`:467`), 422 for unsupported runtimes | unchanged. **The Director never calls it.** The directive path goes through the existing door. |
| B5 | `fleetview_backend/voice_intents.py` | 64 arg-free intents; the matcher is a name-token subset `[R]` | the Face's no-argument problem is *this* file's problem. See §7.3. |
| B6 | `platform/event-bus/contract/` | three schemas today | add `estate.scene.frame.json` (RG4) |

### 6.1 The founder-facing verbs

The founder's real needs, from the 1,473-message analysis `[R]`, mapped to the film:

| founder need | the film's verb | the estate's path |
|---|---|---|
| give a running session a new task (177 msgs) | "tell <name> …" | `/nudge` → `signals.py` → runtime channel |
| stop / halt a session (47 msgs + 158 Esc) | "stop <name>" | `/nudge` (a stop is a directive) |
| see who owns what (59 msgs) | the stage itself | the cast list in the scene frame |
| know if a session is alive (96 msgs) | the cast's state: active / stalled / silent | `last_event_at` + the board's own state |
| demand proof it is live (76 msgs) | the film's own truth: no line without a source (L2) | the narration is the proof |
| check logs, CI or errors (73 msgs) | "why did <name> fail?" | interrogation → the rows, shown, then answered (RN6) |

Every one of those is a **steer or a question**, not a page of controls. That is why the film is
the right vehicle: the founder's own words are the interface.

### 6.2 The artifact pane — "in real life", in the same room

The founder's demo has two halves: the agent builds it **in the movie**, and the founder then sees
**the same thing, in real life, realtime**. The artifact plane (§5.8) is where the second half
lives, and it has three candidate mechanisms, in rising order of honesty and falling order of
cheapness:

| mechanism | what the founder sees | cost | verdict |
|---|---|---|---|
| a drawn mock of the UI in the room | a picture of a UI, made by us | cheap | **refused** — it is the thing law L11 exists to refuse (decision 0041). It is also the thing the founder's sentence rules out. |
| a **live embedded url** in the room (an iframe or a live-mounted surface) | the real surface, in the room, updating as the agent writes | needs the founder's browser to reach the artifact, and the room's own auth/CSP to allow it | the proposed default; the pane is switchable off, and a frame whose artifact reference no longer resolves is dropped rather than shown stale |
| the **url, opened in any browser** — the "in real life" half | the real surface, in the founder's own browser or on the phone | nothing to build; the founder taps or says the url | the floor the demo must clear at minimum: DS2 is satisfied by the sha being on `main` and the url answering 200 |

The demo therefore needs **both**: the pane in the room, and the same url in a plain browser. The
consultant is asked (review packet Q12) for the fastest **real** path to the second half, with a
number and a mechanism, because the deploy path is minutes (K10) and the build-in-progress
surface is seconds (DS4).

---

## 7. Integration — the Face

The Face is the phone. `catalogue.mumchimp.com/face/` `[R]`. It is not a second film; it is the
director's console and the narrator's mouth when the founder is away from the desk.

### 7.1 What the Face gets from the movie

1. **A console strip** on the phone: current shot, the cast (2–3 names, not a table), the last
   directive and its outcome. One tap to send a directive; one tap to cut the film.
2. **The same voice path** — one socket, one engine, the same barge-in behaviour (L4).
3. **The same referent resolver** — "the one on the left" must mean the same thing on the phone as
   on the desk, which means the phone shows the stage geometry too, or the phone only offers
   *named* targets `[A]` (the phone is too small to resolve "left"; the console shows names, the
   desk shows positions).
4. **The artifact, "in real life"** — the phone is where the founder's demo lands hardest: the
   agent built a surface, and the phone can hand it over as a **url** the founder opens in any
   browser, or show it in the console strip if the surface is phone-shaped. The same
   `artifact` reference the room resolves; no second mechanism, no picture of it (L11, decision
   0041). The Face's own catalogue 404 (§7.3) is a reason to keep this to a url and a tap, not a
   reason to mock.

### 7.2 One mouth: the sink problem

`useEstateVoice.ts` holds **one module-global clause sink** (`:382`), set by whoever mounts a face
(`setClauseSink`, `:383`) and read by the voice engine (`:991`) `[M]`. The Face sets it on mount and
clears it on unmount. Two consequences the movie must not inherit:

* **Two tabs, two voices.** `/fleet` and `/face` open together are two surfaces each with an audio
  context. The scene stream is shared; the audio is not. Fix: the **server** is the single source
  of narration, and it publishes the line once; each surface plays it if it is the *focused* one.
  `[A]` The rule: the surface that last received a user gesture owns playback, and the others
  mute. Measured and asserted, not inferred.
* **The legacy engine is still mounted on `/fleet`** (`:741`: "two engines, one surface"). One of
  them is the legacy `useEstateVoice`; the other is the router. The Face picks between them by
  `localStorage['estate.face.voice']` (`FacePage.tsx:42`) `[M]`. The movie uses **the router only**
  (the duplex one), and the legacy engine is retired from the film's surfaces. One mouth means one
  engine, not one flag.

### 7.3 The Face's known gaps, and how the movie routes around them

From the 2026-10-22 Face audit (`docs/specs/2026-10-22-face-superpowers-audit.md`, `[R]` — note
this file was untracked in the tree this spec was written from; re-verify before relying on it):

| gap `[R]` | effect on the movie | the movie's answer |
|---|---|---|
| **no arguments at all** (64 arg-free intents; `voice_intents.py` excludes any intent whose args lack defaults) | "merge pull request 6846" is not reachable by voice | the directive path does **not** go through the intent catalogue. It goes through `/nudge` with a resolved target. The Face's no-args problem is the Face's problem; the movie does not wait for it. |
| **the matcher is a name-token subset**, not language | "merge pull request 6846" matches nothing | same: the movie's verbs are its own small, closed set (steer / cut / stop / why), matched by a resolver, not by the intent catalogue |
| **only 8 of 64 intents run without a confirmation** | a directive that waits for "yes" is not a directive | directives are *already* the founder's explicit instruction, so they carry their own authority — but they are still written to the audit ledger first (L8, RG3) |
| **the catalogue route 404s** — in production *and* on the laptop, for **two different reasons** (production: the route is absent from the deployed image, and the `backstage` and `fleetview-backend` images in the one pod are two days apart; laptop: the route exists at `serve.py:740` but the running process answers 404) | the Face's Commands tab is an error string | **not the movie's slice.** Recorded as a dependency with a fallback: if the catalogue stays 404, the Face's movie role is narration + console, and directives are sent from `/fleet`. |
| **three intent registries** (91 committed, 333 laptop-only, 64 arg-free) | the founder can say things that exist nowhere else | the movie adds no registry (L5); it uses one closed verb set |
| **no steer verbs at all** | the Face cannot direct anything | this is the movie's S3 slice for the Face |

**Design consequence:** the Face is a *dependent*, not a *blocker*. If the Face's catalogue is
still 404 when S3 starts, S3 ships the console + narration on the Face and the directive door
stays on `/fleet`. The movie is not held hostage by another surface's defect.

---

## 8. Slices — the delivery contract

Each slice ships when its acceptance is met, and each acceptance names the evidence. No slice
starts before the previous one is green: the Deploy River's failure was a broken first slice with
nobody owning it `[R]`.

### S0 — The Loop (prove causality, no new visuals)

**Build:** the Director as a process on the laptop; the scene frame contract; the frame → page
path for exactly one line of text (no camera work, no cast); the directive path: founder speech →
resolver → audit row → `/nudge` → one live agent.

**Acceptance (all of it, as evidence):**
1. A real agent session publishes `estate.agent` events.
2. The founder says, by voice, a directive naming that session.
3. The directive text appears **in that agent's own transcript** within 5 s.
4. The estate's `signals.py` shows the nudge with `ok=true`.
5. The agent's new behaviour produces a **new event**, and the page shows the new state.
6. The audit ledger contains the directive row, **timestamped before** the nudge.

**Done means:** steps 1–6, with the transcript diff, the ledger row and the frame logged. Not a
screensaver, not a mock.

**Blocking dependency, and it is a real one:** `[M]` `bin/idp-steer-wired-guard --json` on this
laptop answers `{"state":"blind","reason":"no hook file on this machine"}`, and
`~/.claude/state/directives/` does not exist. **A claude-code steer written by the laptop backend
would sit in a mailbox nothing reads on this machine.** So S0 must run on a runtime whose steer
path is live: `sovereign` (Temporal signal) or `otto` (NATS) `[M: signals.py:87]`. The consultant
must pick and prove that path first. If none of them can be made causal, that is RB5: report it,
do not fake it.

**Cost:** days, not weeks. If it takes weeks, something is wrong with the plan.

### S1 — The Scene (the contract, the cast, the cut)

**Build:** `estate.scene.frame.json`; the Director's stage (cast, placement, states); the camera
wired to the shot vocabulary; the `estate.cinema.cue` topic deleted in the same change.

**Acceptance:** a session that starts, works, waits, fails and ends appears on stage in the right
state, in the right place, with the right shot; the reason for every cut is in the frame; a
missing event stream shows "silent", not "working" (RT4); the room holds ≥ 30 fps with 12
sessions (RP4).

### S2 — The Mouth (narration from the ledger, interruptible)

**Build:** template-over-ledger narration; the source id on every line; the LLM call removed from
the narration path (RT1); barge-in cutting the narration and the sink's queued clauses; the story
interrupt.

**Acceptance:** every spoken line resolves to a source row (RT2); a quiet minute produces zero
lines (RN3); a failure is narrated as a failure (RN4); a barge stops the audio in ≤ 250 ms (RP3);
the same events replayed produce the same lines (L3).

### S3 — The Director's Chair (steering, spatial, the phone)

**Build:** the referent resolver; ambiguity questions; the directive chip; the Face console strip;
the Face's directive door.

**Acceptance:** RD1–RD6, all of them, with the transcript evidence; RI2–RI4 on a 390 px viewport;
two tabs, one voice (RI3).

### S3.5 — The Build (the flagship demo)

**Build:** the artifact plane (a live pane in the room: an embedded url, a real console strip); the
artifact reference carried in the scene frame (`artifact: {kind, url, sha, ref}`); the demo itself
as an ordinary estate run — a claim, a lane, a merge, a deploy — narrated from the ledger; the
founder's "show me the demo" intent, routed through the ordinary intent door.

**Acceptance:** DS1–DS7, all of them, with the recording and the row ids. The demo lands the way
every other change lands: claimed, gated, merged, deployed — and the film shows each step as it
happens, because each step is a row.

### S4 — The Premiere (optional, lowest priority)

The estate's day as a replayable film: the morning premiere, the time machine, the score. This is
the founder's most evocative ask and the **least** load-bearing for the business claim. Ship S0–S3
first. If S4 ships, it ships on the same contract — a replay of the scene frames, not a second
renderer.

### 8.1 How the work is landed

* One claim per slice (`bin/claim-open`), with the paths the slice touches.
* A lane branch (`lane/<name>`) handed to the Greenlane; **no hand-raised PR** (AGENTS.md §2).
* `Claim:` and `Agent:` trailers on every commit.
* A BDD feature per slice, **bound** to its test module. `[M]` the estate's BDD runner is
  pytest-bdd, a feature is bound by a module calling
  `scenarios("features/<dir>/<file>.feature")`, the spec gate refuses an unbound new feature file,
  and `SB_BDD_STRICT=1` on `main` turns any `pending` feature into a red lane. **So: the S0
  feature lands with its implementation and real steps, or it does not land.** (The Gherkin for
  S0 is written out in §9 below so the consultant can bind it in the same change.)

### 8.2 The kill criterion (RB5)

> If S0 cannot be closed because no runtime's steer path can be made causal on this estate within
> the agreed window, the movie is a screensaver. The founder is told in writing, with the evidence
> (the intent that was run, its exit status, the line it printed), and the work stops.

This is written here, before the build, on purpose. A moat that cannot interrupt a movie is a
theme park.

---

## 9. S0 — the Gherkin, ready to bind

```gherkin
Feature: The estate is a film the founder can direct
  As the founder of the estate
  I speak to a running agent
  And the agent changes what it does
  So the film shows the consequence

  Background:
    Given the estate bus is running and the scene contract is published
    And a live agent session "s0-target" is running and publishing estate.agent events

  Scenario: A spoken directive reaches the agent and the film shows the consequence
    Given the founder's microphone is live on the voice socket
    When the founder says "tell s0-target to stop"
    Then the directive is written to the audit ledger before it is sent
    And the nudge is accepted by the estate with ok=true
    And within 5 seconds the agent's own transcript contains the directive text
    And within 10 seconds a new estate.agent event for "s0-target" is published
    And the scene frame rendered on /fleet names "s0-target" as the target of the shot
    And the line spoken for that frame carries the source id of the event it describes
```

**Notes for the binder:** the "within" clauses are the evidence, not decoration. The transcript is
the runtime's own file; the ledger row is the estate's; the frame is the scene contract's. A
binding that asserts on mocks is not this feature.

---

## 10. Business and moat — the founder's frame, answered honestly

### 10.1 The moat is not the film

`2412.12223v2` ("Can video generation replace cinematographers?") is the right question to ask of
this project, and the answer is: **yes, the rendering will be replaced.** `[A]` The cinematic
generation field is moving fast — controllable camera (`2502.08639v1`), explicit cinematic
language (`2604.09195v1`), long-form consistency (`2609.07720v1`), and benchmarks that grade
technique (`2505.15145v1`, `2506.21356v2`, `2609.28813v1`). A year from now a model will produce
better-looking frames than anything the estate can render in WebGL.

**Therefore the moat cannot be pixels.** It is three things, and none of them is rendering:

1. **Causality with provenance.** The founder's speech changes agent behaviour, the change is
   audited, and the film shows it. The competitor must copy the *estate's* event spine, the
   governance path, and the audit ledger — not a renderer.
2. **Truth at the speed of live.** Every line traceable to a row, every failure visible, no
   invented drama. `2606.14589v1` names the exact failure this forbids: errors becoming
   narratives. A film that invents is worse than no film.
3. **The accumulated corpus of founder→agent causality** (RB6). Every directed session is an
   audited, replayable instance. That corpus is the asset, and it grows with use.

### 10.2 Who this is for, and what they pay for

| audience | what they buy | what we must prove |
|---|---|---|
| the founder (first) | a control surface that feels like a film — the difference between watching agents and *running* them | S0, then S3 |
| an operator of a multi-agent estate (second) | situation awareness without a wall of logs — `2503.14810v3` (SA in dynamic human-swarm interaction), `2207.03779v1` (the cognitive cost of collaboration), `2509.19152v2` (mixed-initiative analytics and its failure modes) | the film's truth and its interruptibility |
| a buyer of an estate (third) | the demo | RB2: the demo is real, seeded with nothing |

**The honest weakness:** the cognitive-ergonomics literature warns that richer displays *raise*
operator load (`2207.03779v1`). The film's counter-argument is that it lowers load by moving
information from reading to perception — but that is a claim, and it is testable (RI6), and it is
the consultant's job to test it rather than assume it.

### 10.3 Build vs buy

| buy | don't buy |
|---|---|
| nothing | a video-generation model for the core loop — cost, latency, truth risk, cluster placement, and it optimises the one layer that is not the moat |
| | a second chat/voice SDK — the estate's router is the duplex one (`2505.15670v4`, `2205.15060v4`) and it is already the founder's voice |
| | a 3D engine — Three.js is already the estate's stage |
| | a telemetry product — the estate has a schema'd event spine and a ledger; `2607.14309v1` and `2608.16178v1` say what fields to add, and the estate can add them itself |

The consultant's budget should go to **the loop, the truth, and the referent resolver**, not to
the picture.

### 10.4 What "future proof" means here, concretely

Not "we picked the newest model". It means:

* the scene contract is **renderer-neutral** — a different renderer consumes the same frames;
* the narration is **model-neutral** — no model is in the path at all (RT1);
* the **evidence model** is the stable asset: source ids, ledger rows, replayable frames;
* the director is a **pure function** of the event spine (L3), so the estate's history can be
  replayed as a film at any time, and a new agent runtime is a new event source, not a new
  director.

### 10.5 What is actually new here — the founder's frame, tested

The founder's framing (2026-10-23): *"this is exciting and truly pioneering"*, *"basically
innovating and pioneering the interaction with agents using film/movies, bleeding edge"*.

The honest accounting, against the 41 harvested records:

| part of the idea | already in the literature? | record |
|---|---|---|
| agents making movies | yes | `2503.07314v1` (multi-agent movie generation), `2501.12909v1` (FilmAgent), `2603.14790v2` (Mind-of-Director: an agent-driven director for previz) |
| models that know cinematic language | yes | `2604.09195v1`, `2506.21356v2`, `2609.28813v1` |
| a human steering agents by voice | yes | `2107.00690v2` (locus of control in mixed-initiative systems), `2301.08038v2` (dynamic role allocation), `2509.19152v2` (mixed-initiative visual analytics) |
| duplex speech with a system | yes | `2205.15060v4`, `2505.15670v4`, `2610.26233v1` (heartbeat thinking) |
| human and agent co-generating an interface | closest | `2509.13444v2` (DuetUI: a bidirectional context loop for co-generating task-oriented interfaces) |

**So none of the parts is new. The conjunction is the claim.** `[A]` What this spec asserts is
that these three have never been in one surface: a cinematic view of a live system where every
frame carries the source id of a real event, where the founder's speech is **causally upstream** of
the agents' behaviour, and where the artifact the agent built is the real artifact on the screen
(L11).

That is the claim the consultant must attack, and the attack has two forms: find the paper that
already does it (the harvest found none — that absence is in the digest's gap section), or build
it and find that it does not work. The second form is the S0 kill criterion (RB5): if speech
cannot be made upstream of behaviour, the film is a screensaver, and that is a legitimate outcome.

**Why it is worth pioneering, in the founder's business terms.** The interface to agents is still
a chat box. A chat box cannot show the estate, cannot be interrupted cleanly, does not scale past
one session, and tells the founder nothing about what the other twenty agents are doing. The film
is the first surface where the founder watches many agents and speaks to them in the same breath —
and where the thing an agent made appears, live, as it is made. That is the product: not a
renderer, a way of running an estate by talking to it.

---

## 11. Risks

| # | risk | evidence | mitigation |
|---|---|---|---|
| K1 | **The steer path is blind on this machine.** A claude-code directive lands in a mailbox nothing reads. | `[M]` `bin/idp-steer-wired-guard --json` → `{"state":"blind",…}`; `~/.claude/state/directives/` absent | S0 runs on `sovereign` or `otto`. Choose before writing the feature. |
| K2 | **The laptop is already saturated.** | `[M]` load average 546–626 on 4 cores | the Director is small and bursty; measure (RB4); if it costs, it goes to the cluster per 0034. |
| K3 | **The Face's production catalogue 404s** (sibling image skew in one pod). | `[R]` Face audit §3.4 | the Face is a dependent, not a blocker (§7.3). |
| K4 | **Two surfaces, two voices.** | `[M]` module-global clause sink, `useEstateVoice.ts:382` | L4 + §7.2's explicit ownership rule. |
| K5 | **The narration LLM is a law violation today.** | `[M]` `director.go:274` calls the brain with an 800 ms timeout | RT1: remove it from the narration path in S2. Until then, the film is not shipping. |
| K6 | **The cue has no schema.** | `[M]` `estate.cinema.cue` has no file in `platform/event-bus/contract/` | RG4 + the scene frame replaces it in one change. |
| K7 | **A pending BDD feature reddens `main`.** | `[M]` `SB_BDD_STRICT=1` on `main`; spec gate refuses unbound features | bind the feature with its implementation (§8.1). |
| K8 | **The film becomes theatre** — beautiful, true of nothing. | the Deploy River's own failure `[R]` | S0's acceptance; RB5's kill criterion. |
| K9 | **The founder speaks and nothing happens** (the Face's 404, the router's stalls). | `[R]` 416 API-error turns across 76 of 83 sessions; 311 founder messages were the first reply after an error | the film shows the estate's *real* state, including router trouble — the founder can see the router is down before they speak. |
| K10 | **The artifact plane is new work, and the deploy path is minutes.** A merge → build → Flux deploy is not seconds. | `[M]` AGENTS.md §2 (merge to main → build → Trivy/cosign → ghcr tag → Flux image-automation → deploy-when-green) | DS4 asks for the artifact *while it is being built*: the dev-server path, with the founder's browser able to reach the laptop (Q8). The demo states which plane it is showing. |
| K11 | **The demo becomes theatre.** A "cinematic" build that is really a scripted playback would satisfy every requirement except the ones that matter. | the Deploy River's own failure `[R]` | DS1 (one take, no edits), DS2 (the artifact is the real one), DS3 (every step has a row id), DS7 (re-runnable live). A demo that cannot be re-run live is refused. |

---

## 12. Open questions

Each has a default answer so the build is never blocked waiting for the founder.

| # | question | default if unanswered |
|---|---|---|
| Q1 | Which runtime carries S0: `sovereign`, `otto`, or `claude-code`? | `sovereign` (Temporal signal is the most direct path) |
| Q2 | Does the film narrate continuously, or only on transitions? | only on transitions (RN3) |
| Q3 | Does the founder's voice *also* act, or only direct? | only direct; the founder's speech never triggers an intent without the same audit row |
| Q4 | Is the Face allowed to speak the narration, or only receive it? | receive it; the phone is quiet unless asked (battery, and one mouth) |
| Q5 | What is the film's minimum cast — one agent or the whole estate? | the whole estate, but the camera only frames what is happening |
| Q6 | Does S4 (the premiere) exist at all? | no, until S0–S3 are green |
| Q7 | Who owns the noun "movie" in the estate — does `/fleet` get renamed? | no rename; the estate's surfaces keep their names |
| Q8 | Which artifact plane does the demo use: the deployed url (real, minutes) or the dev server (live, seconds, needs a route to the laptop)? | the deployed url for the proof (DS2), the dev server for the build-in-progress view (DS4), with the reachability cost stated in the demo itself |
| Q9 | Is the artifact pane inside the 3D room (a screen in the world) or beside it (a panel)? | a screen in the room — the estate's own idiom — with the real url embedded, and the pane switchable off |

---

## Appendix A — what was measured, and how

All `[M]` claims in this spec came from these, run on 2026-10-23 in
`/Users/roseonyema/Documents/code/idp`:

| claim | how it was checked |
|---|---|
| the three contracts, the event kinds, the subjects | `ls platform/event-bus/contract/`, read `estate.agent.event.json` |
| the director's parts and line numbers | read `platform/voice-router/internal/director/director.go` |
| the cue is core NATS, ephemeral, unschema'd | `nats_adapter.py:32`, `:336`; `ls platform/event-bus/contract/` |
| nothing calls the director | `platform/voice-router/deploy/director.yaml` — "No Service is declared: nothing calls the director." |
| the page's cue handling | `FleetReactorApp.tsx:1587`, `:1593`, `:1603`, `:1618`, `:781`, `:858`, `:741` |
| the clause sink is one global | `useEstateVoice.ts:382`, `:383`, `:393`, `:679`, `:991` |
| voice partials 0.56 s, first audio median 2.26 s | `useVoiceRouter.ts:6`, `:8` (the file's own measured comments) |
| the supported steer runtimes | `signals.py:87`, `:467` |
| the face's voice flag | `FacePage.tsx:42`, `:191-192` |
| the laptop's steer path is blind | `bin/idp-steer-wired-guard --json` → `{"state":"blind","reason":"no hook file on this machine"}`; `~/.claude/state/directives/` absent |
| the voice router is up | `GET http://127.0.0.1:8091/readyz` → `200 ok` (five probes: 1.68 s, then 0.03 / 0.001 / 0.0017 / 0.0008 s) |
| the laptop's load | `uptime` — load average 546–626 on 4 cores |
| the room's size | `wc -l FleetReactorApp.tsx` → 3019 |
| the founder's message counts (1,473 msgs / 83 sessions; 416 error turns in 76; 311 first-reply-after-error; 158 Esc; 177 new task; 47 stop; 96 alive; 59 ownership; 73 logs/errors) | read `docs/specs/2026-09-29-fleet-voice-session-control-requirements.md:26,41,45,59,82-83,94` — the figures agree with the document this spec quotes |
| the Face's figures (64 arg-free, 91 committed intents, 333 laptop intents, "name-token subset" matcher, "only 8 of 64 run without a confirmation", catalogue 404 in production and on the laptop, gaps S1–S7) | read `docs/specs/2026-10-22-face-superpowers-audit.md:22-33,96-100,117,129,132,136-138,196-198,326-407`. **Note:** that file is **untracked** in the tree at the time of writing — another agent's work in flight. Re-verify before relying on it. |
| the room has no iframe today | `rg -n "iframe" backstage/packages/app/src/modules/room/ui/` → no hits |
| the room already renders the estate's real state in live panels | `room/ui/Delivery.tsx` (the merged→operating beam), `room/ui/GreenlaneHud.tsx` (the lane's brief), `room/ui/ClaimsPanel.tsx` |
| the deploy path, and its cost | AGENTS.md §2 — merge to main → build-multiarch → Trivy/cosign → ghcr tag → Flux image-automation → deploy-when-green. Minutes, not seconds `[A]` |

**Not measured, do not assume:** how the page renders 12 sessions at 30 fps; what the founder's
latency really is end to end; whether the Face's console fits 390 px in practice; whether a
`sovereign` steer is causal on this laptop (S0's first task); whether an embedded live url survives
the room's own auth and CSP (the artifact plane's first unknown).

## Appendix B — the arXiv records behind §10 and §5

41 records, harvested from the arXiv API on 2026-10-23, committed as
`docs/research/2026-10-23-arxiv-cinematic-agent-harvest.json` with id, title, published date and
first sentence for each. The digest is `docs/research/2026-10-23-cinematic-agent-interface-research.md`.
Every id resolves at `https://arxiv.org/abs/<id>`.

## Appendix C — companion documents

| document | what it is |
|---|---|
| `docs/research/2026-10-23-cinematic-agent-interface-research.md` | the research digest: what the literature says, mapped to our laws |
| `docs/reviews/2026-10-23-consultant-review-packet.md` | the review packet: what to attack, how, and in what form |
| `docs/decisions/0037-*.md` | the film is a deterministic twin of the event spine, not a generated video |
| `docs/decisions/0038-*.md` | one scene contract, one path; the cue topic retires in the same change |
| `docs/decisions/0039-*.md` | one mouth: the router owns the estate's voice |
| `docs/decisions/0040-*.md` | the Director runs on the laptop until the loop is proven |
| `docs/decisions/0041-*.md` | the artifact on screen is the real artifact, not a picture of it |
