# Consultant review packet — "Estate as Movie"

**Date:** 2026-10-23 · **For:** the external consultant who will design and build this ·
**From:** the estate's technical product manager · **Status:** open for review

You are being asked to do two things, in this order:

1. **Attack the spec** (`docs/specs/2026-10-23-estate-as-movie-director-engine.md`) before you
   write a line of it. The spec makes one load-bearing claim — that the founder's speech is
   causally upstream of agent behaviour, and that the film is a faithful view of the estate, not a
   dramatisation of it. **Your review is the test of that claim.**
2. **Then build it**, slice by slice, with the acceptance criteria as written.

This packet is the handover. Everything you need to judge the work is here or in the three
documents it points to.

---

## 1. What you are reviewing

| document | what it is | how long it is |
|---|---|---|
| `docs/specs/2026-10-23-estate-as-movie-director-engine.md` | the master spec: vision, laws, 40 requirements, architecture, the two surface integrations, five slices, the delivery contract, the kill criterion | the main read |
| `docs/research/2026-10-23-cinematic-agent-interface-research.md` | the research digest: 41 arXiv records, what each one changes, and where the literature has nothing to say | supporting |
| `docs/reviews/2026-10-23-consultant-review-packet.md` | this file | now |
| `docs/decisions/0037-…0040-*.md` | four decision records: the four forks that were taken, and what would reverse each | supporting |
| `docs/research/2026-10-23-arxiv-cinematic-agent-harvest.json` | the raw harvest: id, title, published date, first sentence for each cited record | evidence |

**Read the honesty ledger first.** Every factual claim in the spec is tagged `[M]` (measured on
2026-10-23 in this repo), `[R]` (reported by another agent — re-verify) or `[A]` (my design
decision — challenge it). Appendix A of the spec lists the command behind each `[M]`.

**Your first commit re-verifies the `[R]` claims the spec depends on** and says which were wrong.
That is not optional: the spec's Face integration (§7) and its prior-art analysis (§2) both rest
on `[R]`.

---

## 2. The estate, in one page

* A **fleet** of AI agents (harnesses: `sovereign`, `claude-code`, `otto`, `cyrus`, …) doing real
  work in real repos, under real gates, with real claims.
* Every agent publishes its live mind as **schema'd events** on a JetStream bus:
  `estate.agent.<runtime>.<session_id>.<kind>` (`phase|tool|wait|done|steer|gate`).
* The founder's surfaces: **`/fleet`** — a WebGL room where the estate is rendered live, and
  **`/face`** — a phone-sized talking head that can run estate intents and give an agent a job.
  The founder's voice is the interface on both; the estate's own law is voice-first, and the
  work surface is `/fleet`.
* Work reaches `main` through a **Greenlane** that proves a branch and merges it. Agents never
  raise pull requests by hand.
* Every action goes through an **intent YAML**; the executor refuses anything else. Secrets are
  referenced by name, never pasted.
* The founder's measured working style (from 1,473 real messages `[R]`): terse, interruptive,
  constantly switching between agents. The two things they ask for most are *"give a running
  session a new task"* (177 messages) and *"stop a session"* (47 messages + 158 Esc interrupts).

**So: the film is the delivery vehicle for the founder's two most frequent requests.** If your
build does not make those two things faster, the film is decoration.

---

## 3. What already exists (do not rebuild it)

| exists | where | note |
|---|---|---|
| the event spine | `platform/event-bus/contract/estate.agent.event.json` | three schemas in that directory today; yours is the fourth |
| a director | `platform/voice-router/internal/director/director.go` | shot table, coalescer, limiter, narrator. **A library nobody calls.** |
| a camera | `backstage/packages/app/src/modules/room/ui/cinecam.ts` | Three.js, with tests |
| the stage | `backstage/packages/app/src/modules/room/ui/FleetReactorApp.tsx` | 3019 lines; already renders cues, stories, refusals |
| the voice | `backstage/packages/app/src/modules/home/useVoiceRouter.ts` | **one** WebSocket, duplex, barge-in, partials |
| the steered path | `backstage/plugins/fleetview-backend/src/fleetview_backend/signals.py` | `/nudge` → runtime-native channel |
| the phone | `backstage/packages/app/src/modules/home/FacePage.tsx` | live at `catalogue.mumchimp.com/face/` |
| the news interrupt | `room/ui/newsRundown.ts` | `shouldInterrupt` — a story already re-cuts the room |
| the SSE multiplex | `fleetview_backend/{routes,serve}.py` | one endpoint, four frame types |

---

## 4. The ten questions the review must answer

Answer each **numbered**, with a verdict and an argument. A verdict is one of: **AGREE**,
**AGREE WITH CHANGES** (list them), **DISAGREE** (say what you would do instead), or
**CANNOT ANSWER YET** (say what you need to measure first). "I like it" is not a verdict.

**Q1 — The causal claim.** The spec's S0 requires: founder speech → audit row → `/nudge` → the
agent's own transcript changes → a new event → the film shows the new state. Is that the right
definition of causality for this estate, and is it measurable? If your reading of "the agent's own
transcript changes" is too weak, say what a stronger test is. *This is the question that decides
whether the project is real.*

**Q2 — The runtime.** The spec leaves the S0 runtime open (`sovereign`, `otto`, `claude-code`) and
records that the claude-code steer path is **blind on this machine** `[M]`: a directive lands in a
mailbox nothing reads. Which runtime do you pick, and what exactly do you do to make it causal?
If none can be made causal, say so plainly — the spec's kill criterion (RB5) then applies and that
is a legitimate outcome of this review.

**Q3 — The contract.** One new schema, `estate.scene.frame`, carrying cast, shot, line, directive
and interruption. Attack the shape: what is missing, what is redundant, what will you regret in
six months? Is a whole-scene snapshot per frame the right unit, or should the wire carry deltas?
(Note: the estate's own telemetry paper argues for state-delta evidence over prose — but the
estate's *rendering* needs the whole scene. Both can be true; say how.)

**Q4 — The truth rule.** Law L2: every spoken line carries a source id; no source, no speech; no
model in the ambient narration path. Is that the right call, and does it survive contact with a
founder who wants the film to be *good*, not merely true? Where, precisely, is the line between
ambient narration (deterministic) and interrogation (may answer with a model)?

**Q5 — The referent resolver.** "The one on the left" resolves through a fixed stage grid; an
ambiguous referent produces **one question** instead of a guess. Is a fixed grid the right model
of the screen? What happens when the founder says "stop him" about someone not on stage?

**Q6 — The one-mouth rule.** The estate has a module-global clause sink and two voice engines
mounted on `/fleet`. The spec's rule is one voice, one owner, barge-in cuts narration on the same
socket. Is that implementable across two tabs and two devices, or is it a fiction that will fail
the first time the founder opens the phone and the desk at once?

**Q7 — The surface integration.** `/fleet` is the film; `/face` is the console. The spec keeps the
Face a *dependent*, not a blocker, and routes around its known defects (no arguments, a
name-token matcher, a 404 catalogue in production). Is that the right call, or is the Face the
thing that should be designed first? Justify against the founder's actual behaviour, not against
elegance.

**Q8 — The latency budget.** RP1–RP3 set speech-end → applied p50 ≤ 1.2 s, event → render p50 ≤
250 ms, barge → silence ≤ 250 ms. Are these numbers honest given the measured pipeline (partials
every 0.56 s, first audio median 2.26 s, a runtime channel outside our control)? If they are not
honest, give the numbers you would defend, and say what you would cut to reach them.

**Q9 — The kill criterion and the business claim.** The founder frames this as a moat play
("best-of-breed bleeding-edge engine", "future proof"). The spec argues the moat is **not** the
pixels but causality, provenance and the accumulated corpus of directed sessions. Do you agree
that the rendering is commodity? If yes, what would you actually spend money on, and what would you
refuse to spend it on? If no, argue the opposite — the founder's framing should be tested, not
flattered.

**Q10 — The gaps.** What did the spec miss? Specifically: what breaks in production that this
document does not mention? Name at least three things the spec is confidently wrong about, if you
can find them. A review that finds nothing is not a review.

---

## 5. Scope of the work

**In scope**

* the Director (deterministic planner) and its process shape;
* the `estate.scene.frame` contract and the backend path that carries it to the page;
* the cast/stage model, the shot selection, the cut;
* narration that is template-over-ledger, interruptible, and traceable to a source;
* the referent resolver and the directive path (founder speech → audit → `/nudge`);
* the `/fleet` integration and the `/face` console strip;
* the slice-by-slice delivery, with each acceptance met as written.

**Out of scope**

* generating video, or any model in the render or narration path (decision 0037);
* a new intent registry, a new execution boundary, a second stage (law L5);
* changing how work reaches `main` (the Greenlane is not yours to touch);
* redesigning the Face's command catalogue, or fixing the production 404 (another agent's work —
  see the spec's §7.3 for the fallback);
* anything that requires the founder to run a procedure manually (AGENTS.md §2).

**The rules you build under** (they are not negotiable, and they are enforced by gates, not by
good intentions)

* work reaches `main` through a **lane branch** (`lane/<name>`) handed to the Greenlane; agents
  do not raise pull requests and do not push `main`;
* every change carries a **claim** (a GitHub issue) with two commit trailers, `Claim:` and `Agent:`;
* **one claim per slice**, no overlapping paths with other agents — there are several agents live;
* the estate's verification gate (`bin/idp-ci`) and the claim gate must be green;
* a BDD feature must be **bound** to its test module; `SB_BDD_STRICT=1` on `main` means a
  `pending` feature is a red lane. Land the feature with its implementation, with real steps.
* placement follows `docs/decisions/0034-*.md`: free tier first, laptop before the node; the
  Director stays on the laptop until the loop is proven (decision 0040).

---

## 6. The delivery contract

Deliver **slices**, in this order, and do not start a slice before the previous one is green. The
Deploy River (crew#973) is the precedent for failure: a complete spec, a broken first slice, and
a transcript that reported "ALL PASS" for changes that were never in the file.

| slice | what it delivers | done means (evidence) |
|---|---|---|
| **S0** | the loop: voice → directive → agent → new event → the page shows it | the agent's own transcript contains the directive within 5 s; the ledger row precedes the nudge; a new event exists; the page shows the new state. **No new visuals.** |
| **S1** | the scene: contract, cast, placement, states, the cut | sessions appear in the right state and place; every cut carries its reason; a silent stream reads as silent; ≥ 30 fps with 12 sessions |
| **S2** | the mouth: template-over-ledger narration, interruptible | every line resolves to a source row; a quiet minute is silent; a failure is narrated as a failure; a barge stops the audio ≤ 250 ms |
| **S3** | the chair: referents, ambiguity questions, the phone console | RD1–RD6 with transcript evidence; the console works at 390 px; two tabs, one voice |
| **S4** | optional: the premiere (replay of the frames) | only after S0–S3 are green. **Do not start S4 first.** |

**Report format per slice:** what was built, the command and its output that proves each
acceptance, what was not done, and what you would do differently. "Built" and "operating" are
different facts; say which one you mean, and prove the one you claim.

---

## 7. How to file the review

Create one issue in `chidionyema/idp`, claim it with `bin/claim-open --title "…"`, and answer
**Q1–Q10** in it, in order, with a verdict on each and the evidence you used. Attach: the
measured numbers you re-checked and the ones that turned out different from `[M]`, and the `[R]`
claims that did not survive re-verification.

Then, in the same issue, write the **build plan**: the slices as you would run them, the files you
would touch, the first three commits, and the **first thing you will measure** — because the
honest answer to Q1 and Q8 may both be "measure this before designing that".

---

## 8. What the founder cares about, in the founder's words

* *"I want to be the director of the movie; the agents are the cast."*
* *"best-of-breed bleeding-edge engine"*, *"future proof"* — this is a **business and moat play**,
  not a demo. Say what it is worth, and what it is not worth, plainly.
* The work surface is `/fleet`, and it must be watchable live. A capability the founder cannot
  reach by voice or see live there is not finished.
* **The mouth is in the cluster and the hands are on the Mac** `[R]` — the Face's page lives in
  the cluster while the code that executes the intents lives on the laptop. Any design that
  assumes the phone can act on its own is wrong today.
* *"I don't want to be asked to do a procedure."* If your plan needs a manual step from the
  founder, it is not a plan.

---

## 9. Known open risks, so you do not rediscover them

| risk | state |
|---|---|
| the claude-code steer path is blind on this laptop | `[M]` measured; it decides Q2 |
| the laptop's load average was 546–626 on 4 cores | `[M]`; the Director must be small, and placement is decision 0040 |
| the Face's production catalogue route 404s (sibling image skew in one pod) | `[R]`; the movie routes around it |
| the narration LLM in `director.go:274` violates the estate's voice law | `[M]`; it must leave the narration path in S2 |
| `estate.cinema.cue` has **no schema** and is **ephemeral core NATS** | `[M]`; the scene frame replaces it in one change |
| the module-global clause sink makes two tabs two voices | `[M]`; decision 0039 |
| a pending BDD feature reddens `main` | `[M]`; bind with the implementation |

---

## 10. The one sentence to argue with

> *The estate can be watched as a film; the founder can change what the film shows by speaking;
> and that speech is causally upstream of agent behaviour.*

If you believe that sentence, say **what you would build first** and **what you would refuse to
build**. If you do not, say **what the honest version of this project is** — a screensaver with a
nice camera, a control surface without the film, or something else — and what it is worth.
