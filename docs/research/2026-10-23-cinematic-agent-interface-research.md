# Research digest — cinematic, voice-directed, interruptible agent interfaces

**Date:** 2026-10-23 · **For:** the consultant building "Estate as Movie" ·
**Companion to:** `docs/specs/2026-10-23-estate-as-movie-director-engine.md`

**How this was gathered, and what that limits.** A script queried the arXiv API
(`https://export.arxiv.org/api/query`) with 28 query strings across the themes below
(cinematic agent, film agent, mixed-initiative, barge-in, end-of-turn detection, full-duplex,
voice-agent latency, situation awareness, agent telemetry, silent failures, previz, shot grammar,
cognitive ergonomics), kept every record whose title or abstract mentioned an agent, director,
camera, storyboard or interface, and then curated 41 records down from 149.

**The honest limit:** for each record I harvested the **id, title, published date and first
sentence of the abstract**. I did not read the full papers. Every id below resolves at
`https://arxiv.org/abs/<id>` so a reviewer can check the record itself; the *inference* I draw
from it is mine and is marked as such. Where a paper's abstract does not settle a question, this
digest says so rather than guessing.

The raw evidence is committed: `docs/research/2026-10-23-arxiv-cinematic-agent-harvest.json`
(41 records, each with `id`, `title`, `published`, `theme`, `why_it_is_here`, `first_sentence`,
`url`).

---

## 1. The five findings that change the design

### 1.1 The film is a **plan**, not a set of shots — so the Director is the real work

`2503.07314v1` (*Automated Movie Generation via Multi-Agent CoT Planning*, 2025-03-10): "Existing
long-form video generation frameworks lack automated planning, requiring manual input for
storylines, scenes, cinematography, and character interactions, resulting in high costs and
inefficiencies".

`2603.14790v2` (*Mind-of-Director*, 2026-03-16): "We present Mind-of-Director, a multi-modal
agent-driven film previz framework that models the collaborative decision-making process of a film
production team".

`2412.02259v3` (*VideoGen-of-Thought*, 2024-12-03): "Current video generation models excel at
short clips but fail to produce cohesive multi-shot narratives due to disjointed visual dynamics
and fractured storylines".

**What it changes:** the value is in the planning layer, not the pixels — which is exactly the
estate's situation (we have a WebGL stage, not a generator). It also says the planning layer is
where a *team* of roles sits (script / cinematography / actor placement), which maps to the estate's
existing decomposition: the Director plans, the shot table decides, the narrator speaks, the page
renders. **Inference:** our `director.go` is already a (small) planning layer; the gap is that
nothing calls it and it produces no schema.

### 1.2 Controllable camera means **parameters**, not prompts

`2502.08639v1` (*CineMaster*, 2025-02-12): "In this work, we present CineMaster, a novel framework
for 3D-aware and controllable text-to-video generation".

`2604.09195v1` (*Camera Artist*, 2026-04-10): "We propose Camera Artist, a multi-agent framework
that models a real-world filmmaking workflow to generate narrative videos with explicit cinematic
language".

`2609.07720v1` (*Better Call CineCrew*, 2026-09-07): "Long-form narrative-to-film generation
requires shot-level controllability and cross-clip consistency in both visual identity and
character behavior".

`2610.12455v2` (*Hybrid Cinematography*, 2026-10-08): "On a film set, the camera move is committed
during a take".

**What it changes:** the shot must be a **named, parameterised move** that can be reproduced and
argued about — not a prompt. The estate already has this: `ORBIT_FOCUS`, `PANORAMIC_SWEEP`,
`MACRO_DOV` with focal length and dolly speed (`director.go:91-93`). The fourth abstract is the
sharpest line in this digest for us: *a committed camera move cannot be re-shot for free*. In the
estate that means a cut that is already on screen cannot be undone by a later event — the scene
frame's `seq` and the page's out-of-order drop are the mechanism, and the consultant must not
build a renderer that lets the past rewrite the present.

### 1.3 The field that grades technique is a benchmark field — so our shot grammar must be gradeable

`2505.15145v1` (*CineTechBench*, 2025-05-21): "Cinematography is a cornerstone of film production
and appreciation, shaping mood, emotion, and narrative through visual elements such as camera
movement, shot composition, and lighting".

`2506.21356v2` (*ShotBench*, 2025-06-26): "Cinematography, the fundamental visual language of film,
is essential for conveying narrative, emotion, and aesthetic quality".

`2609.28813v1` (*CinematicVQA*, 2026-09-23): "Cinematography, the craft of visual storytelling
through framing, lighting, and camera operation, fundamentally shapes how audiences perceive and
emotionally engage with video content".

**What it changes:** a cinematic vocabulary is *testable* — there are benchmarks for whether a
system understands framing, lighting and camera operation. **Inference for us:** our acceptance
for the camera should not be "it looks cinematic"; it should be a checked mapping from event kind
to shot, with the reason in the frame. That is a table, and it is testable today (`director_test.go`
replay, law L3).

### 1.4 The human's control is the product, and it has a shape

`2107.00690v2` (*Trust, Shared Understanding and Locus of Control in Mixed-Initiative Robotic
Systems*, 2021-07-01): "This paper investigates how trust, shared understanding between a human
operator and a robot, and the Locus of Control (LoC) personality trait, evolve and affect
Human-Robot Interaction (HRI) in mixed-initiative robotic systems".

`2211.14095v1` (*Hierarchical Variable Autonomy*, 2022-11-25): "This paper presents a
Mixed-Initiative (MI) framework for addressing the problem of control authority transfer between a
remote human operator and an AI agent when cooperatively controlling a mobile robot".

`2301.08038v2` (*Dynamic Role Allocation*, 2023-01-19): "The growing deployment of human-robot
collaborative processes in several industrial applications, such as handling, welding, and assembly,
unfolds the pursuit of systems which are able to manage large heterogeneous teams while also
monitoring the execution of complex tasks".

`2509.13444v2` (*DuetUI*, 2025-09-16): "Large Language Models are reshaping task automation, yet
remain limited in complex, multi-step real-world tasks that require aligning with vague user
intent and enabling dynamic user override".

**What it changes:** the literature treats **control transfer** as the hard, measurable thing —
not the display. This is the strongest external support for the spec's decision that S0 proves a
*causal* loop before any visual work, and for RD3 ("an ambiguous referent produces one question,
not a guess"): variable autonomy only works if the human can take control and knows they have.
**Inference:** the "one mouth" rule (L4) is also a trust rule — two voices competing for the
founder's attention is exactly the shared-understanding failure these papers describe.

### 1.5 The literature's hardest warning is about *stories that are not true*

`2606.14589v1` (*When Errors Become Narratives*, 2026-06-12): "LLM agent systems increasingly run
as long-lived autonomous runtimes: scheduling jobs, calling tools, maintaining memory, and pushing
results to humans".

`2608.16178v1` (*Agent-Native Telemetry*, 2026-08-17): "Operational telemetry is predominantly
engineered for human reading: systems repeatedly serialize verbose prose, static keys, and
redundant context across billions of log lines".

`2608.24271v1` (*Observability and Fault Injection for LLM-Based Multi-Agent Systems*, 2026-08-25):
"Large Language Model-based multi-agent systems are increasingly explored for software engineering
tasks, but they remain difficult to inspect, debug, and evaluate under controlled failures".

`2606.05872v3` (*Entropy-Based Observability*, 2026-06-04): "AI agents are typically instrumented
through outcome-oriented indicators such as task success, reward, latency, and cost. Although these
indicators are operationally important, they provide limited visibility into the internal structure
of agent behavior".

`2607.14309v1` (*Traccia*, 2026-07-15): "The rapid development of Large Language Models (LLMs) and
Artificial Intelligence (AI) powered autonomous agents has fundamentally changed the existing forms
of software governance".

**What it changes:** the title of the first is the whole risk in one phrase — *when errors become
narratives*. A film is a narrative engine pointed at a system. If the film narrates a failure as
success, it is worse than no film, because the founder's trust in every other surface decays with
it. **Inference:** this is why the spec's law L2 (every line carries a source id; no source, no
speech) is non-negotiable and why the current LLM-narrator (`director.go:274`) must go. The
estate's own rule — "LLMs answer questions about the journey, they never narrate it" — is the
same rule these papers arrive at from the observability side.

The second and third are the positive form of the same law: telemetry designed for machines
(state-delta evidence) rather than for prose is exactly what the scene frame's `source` block is.
The fifth says governance of AI systems is now a platform problem with OpenTelemetry-shaped
answers — the estate already has the shape (`estate.agent.event`), it just does not have the
scene-level evidence yet.

---

## 2. Voice: the latency is a pipeline, and the cut is the hard part

`2508.04721v1` (*Low-Latency End-to-End Voice Agents*, 2025-08-05): "We introduce a low-latency
telecom AI voice agent pipeline for real-time, interactive telecommunications use".

`2610.26233v1` (*Heartbeat Thinking*, 2026-10-19): "Tool-using voice agents often leave users
waiting after speech ends, even when actionable information arrives earlier in the request".

`2510.16156v1` (*AsyncVoice Agent*, 2025-10-17): "Effective human-AI collaboration on complex
reasoning tasks requires that users understand and interact with the model's process, not just
receive an output".

`2609.11066v1` (*Less can be More: What Aspects of Speech Drive End-of-Turn Detection*, 2026-09-10):
"In conversational AI, detecting when a speaker has finished talking is crucial for natural turn
taking".

`2505.15670v4` (*SALM-Duplex*, 2025-05-21): "Spoken dialogue is an intuitive form of
human-computer interaction, yet current speech language models often remain constrained to
turn-based exchanges, lacking real-time adaptability such as user barge-in".

`2205.15060v4` (*Duplex Conversation*, 2022-05-30): "In this paper, we present Duplex Conversation,
a multi-turn, multimodal spoken dialogue system that enables telephone-based agents to interact
with customers like a human".

`2609.21967v2` (*NemotronLabs VoiceChat*, 2026-09-18): "We introduce NemotronLabs VoiceChat, an
open full-duplex speech-to-speech model with native tool-calling capabilities".

**What it changes:**
* The end-of-turn detector is the latency that the founder feels (the fourth abstract). The
  estate's measured numbers — partials every 0.56 s, first audio median 2.26 s — are the
  pipeline's shape, and RP1's 1.2 s p50 for "speech end → directive applied" is a **pipeline**
  budget, not a model budget (spec §5.6).
* *Heartbeat thinking* argues for acting **during** speech rather than after it: "even when
  actionable information arrives earlier in the request". **Inference:** if the founder says "stop
  the one on the left — no wait, the claude one", the directive should be armed on the partial,
  not the final. Whether the estate's router exposes enough partial fidelity to do this safely is
  an open question the consultant should test early, because it moves the perceived latency more
  than any model change.
* *Duplex* and *SALM-Duplex* say the estate's router is on the right side of this fork: barge-in
  is a capability of the architecture, not a feature to add later. The spec's one-mouth rule
  (L4) is a consequence: a barge that cannot cut the narration is not a barge.
* *NemotronLabs VoiceChat* (tool calling in a full-duplex speech model) is the direction the
  estate's "voice is the execution door" story is heading. **Not** a dependency of this build —
  it is the future-proofing note (spec §10.4).

---

## 3. The human in the loop: what the film is actually for

`2503.14810v3` (*Human-Swarm Interaction: Situation Awareness*, 2025-03-19): "This paper
introduces a framework for human swarm interaction studies that measures situation awareness in
dynamic environments".

`2207.03779v1` (*Pick the Right Co-Worker: Cognitive Ergonomics*, 2022-07-08): "Human-robot
collaborative assembly systems enhance the efficiency and productivity of the workplace but may
increase the workers' cognitive demand".

`2605.16197v1` (*Position: AI as Part of Self*, 2026-05-15): "This position paper argues that
safety and alignment cannot be achieved by constraining an external system: they must emerge from
the co-regulatory design of the human--AI cognitive system as a whole".

`2509.19152v2` (*Scoping Review of Mixed Initiative Visual Analytics*, 2025-09-23): "Artificial
agents are increasingly integrated into data analysis workflows, carrying out tasks that were
primarily done by humans".

**What it changes:**
* The estate's founder is one human in a swarm of agents — that is exactly `2503.14810v3`'s
  subject. The film is a **situation-awareness instrument**, and the metric that matters is
  whether the founder knows what is happening without reading logs.
* `2207.03779v1` is the honest counterweight: richer displays can *raise* cognitive load. The
  film's claim (information moves from reading to perception) is an inference to be tested, not a
  fact. The spec's RI6 turns it into a person-test, and the consultant should run it rather than
  assume it.
* `2605.16197v1` is the philosophical version of the spec's central claim: the founder and the
  estate are one cognitive system, so the interface between them is the safety surface. That is
  the strongest available justification for spending the effort on **interruption and
  attribution** rather than on beauty.
* `2509.19152v2` warns that mixed-initiative analytics has known failure modes — the consultant
  should read its failure catalogue before designing the "what should the founder do next" cue.

---

## 4. Interruption and explanation

`2106.02077v1` (*Eliciting Spoken Interruptions*, 2021-06-03): "Current speech agent interactions
are typically user-initiated, limiting the interactions they can deliver".

`2501.09355v1` (*YETI: Proactive Interventions*, 2025-01-16): "Multimodal AI Agents are AI models
that have the capability of interactively and cooperatively assisting human users to solve
day-to-day tasks".

`2603.02070v3` (*Exploring Plan Space through Conversation*, 2026-03-02): "When automating plan
generation for a real-world sequential decision problem, the goal is often not to replace the human
planner, but to facilitate an iterative reasoning and elicitation process, where the human's role
is to guide the AI planner according to their preferences and expertise".

`2106.01503v1` (*Towards an Explanation Space*, 2021-06-02): "Providing meaningful and actionable
explanations to end-users is a fundamental prerequisite for implementing explainable intelligent
systems in the real world".

**What it changes:**
* The first abstract is the estate's situation in one line — "typically user-initiated". The
  founder's measured sessions (311 messages were the first reply after an API error `[R]`) say
  the founder is *already* trying to interrupt a system that does not listen. A film that cannot
  be interrupted reproduces the estate's core complaint.
* `2501.09355v1` adds the other half: **when the agent should speak up**. The estate's film has a
  narration budget (10 s per session, 6 lines per minute, in `director.go` today) and that budget
  is the governor this literature asks for.
* The last two argue that an explanation should be *navigable* (a space of explanations) and that
  the human's job is to *steer the planner*, not to approve a finished plan. **Inference for the
  estate:** "why did that fail?" (RN6) should return the **space** — the failed gate, the event
  before it, the row that decided it — not one sentence. That is the difference between narration
  and interrogation, and it is where the model is allowed to speak (spec §5.3 step 6).

---

## 5. What the literature did **not** give us

Honesty about the gaps, because a consultant will otherwise assume we checked:

1. **Nothing was found on a live, interruptible cinematic view of a real agent estate.** The
   cinematic papers are about *generating* film; the mixed-initiative papers are about
   *dialogue and control*; the observability papers are about *evidence*. Nobody in this harvest
   joins them. That is the estate's actual contribution, and it also means there is no prior art to
   copy for the seam — it has to be designed, and it has to be tested on a person.
2. **No paper found on a deterministic, non-generative "director" over a live event stream.**
   `2608.12314v1` (*StateFlow*, 2026-08-12: "Previsualization is an intermediate layer between
   ideas and production in film, games, architecture, and urban design") is the closest — a 3D
   world state that is built, evolved and accessed — and `2511.17906v1` (*AnimAgents*, 2025-11-22:
   "Animation pre-production lays the foundation for an animated film by transforming initial
   concepts into a coherent blueprint across interdependent stages") is the second. Both point the
   same way: the layer that matters is the **state**, and the film is a view of it. That is our
   thesis (decision 0037) arriving independently from the previs literature.
3. **No benchmark for "did the founder's speech change behaviour".** The closest is the
   evaluation-gate literature (`2603.27355v2`: "We present a readiness harness for LLM and RAG
   applications that turns evaluation into a deployment decision workflow"; `2601.18827v2`:
   "LLM-based agents are rapidly being adopted across diverse domains"; `2406.01364v1`:
   "Input-output safeguards are used to detect anomalies in the traces produced by Large Language
   Models (LLMs) systems"). S0's acceptance is our own harness, and the consultant should treat it
   as a *harness for a future product*: if it is hard to measure causality for ourselves, it will
   be hard to sell.

---

## 6. How the digest maps into the build

| finding | law it justifies | requirement it lands in |
|---|---|---|
| planning is the value (§1.1) | L1, L3 | RN1–RN6, S1 |
| camera as parameters (§1.2) | L3 | RD4, F2 (cinecam), `shot` in the scene frame |
| gradeable vocabulary (§1.3) | L3, L10 | the replay test in `director_test.go` |
| control transfer is the product (§1.4) | L1, L6 | RD1–RD3, S0 |
| errors become narratives (§1.5) | L2, L7 | RT1–RT6, S2 |
| latency is a pipeline (§2) | — | RP1–RP3, RP6 |
| SA is the point (§3) | — | RI6, RB3, RB5 |
| explanation is a space (§4) | L2 | RN6, RT3 |

**A note on the film's own honesty.** This digest cites papers that are *about generating video*.
The estate's decision is to **not** generate video (decision 0037), and the strongest support for
that decision comes from `2610.12455v2` — a committed camera move cannot be reshot for free — and
from §1.5: a generated film of a system that is not true is a liability. The literature describes
what film *is*; the estate already has what the film is *about*, and that is the event spine.
