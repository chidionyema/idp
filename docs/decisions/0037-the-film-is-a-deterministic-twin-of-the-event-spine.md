# 0037 — The film is a deterministic twin of the event spine, not a generated video

Date: 2026-10-23
Status: accepted (founder framing: *"Estate as Movie — the estate as a live film, me the director,
agents the cast"*)
Related: 0034 (placement by the free tier), 0038 (one scene contract), 0039 (one mouth),
`docs/specs/2026-10-23-estate-as-movie-director-engine.md`,
`docs/research/2026-10-23-cinematic-agent-interface-research.md`

---

## Context

The founder asks for the estate as a film: the founder is the director, the agents are the cast,
the work is the footage. The cinematic-generation field is moving fast, and the natural reading
of "best-of-breed bleeding-edge engine" is: put a video model in the loop.

Measured on 2026-10-23, in this repo:

- the estate already has a **director**: `platform/voice-router/internal/director/director.go` —
  a shot table (`ShotFor`, `:104`), a coalescer (`:140`), a limiter (`:197`) and a narrator
  (`:252`), with three named camera moves (`:91-93`);
- the estate already has a **stage**: `room/ui/FleetReactorApp.tsx` (3019 lines) renders the
  estate live in WebGL, already handling cues (`:1587`), stories (`:1618`) and gate refusals
  (`:1603`);
- the estate already has a **spine**: `estate.agent.<runtime>.<session_id>.<kind>`, schema'd, on
  JetStream.

So the film does not need a generator. It needs the existing event stream to become frames.

The case *for* a generator is real and was read: controllable camera (`2502.08639v1`), explicit
cinematic language (`2604.09195v1`), long-form consistency (`2609.07720v1`), and benchmarks that
grade technique (`2505.15145v1`, `2506.21356v2`). The case *against* is sharper:

- **Truth.** The estate's law is proof, not assertion; the voice law says LLMs answer questions
  about the journey, they never narrate it. A generated frame of a system that is not true is a
  liability, and the telemetry literature names the failure exactly — *when errors become
  narratives* (`2606.14589v1`).
- **Cost and placement.** A video model is a paid, cluster-placed dependency for a layer that is
  not the moat (`0034`).
- **Latency.** The loop the founder needs is speech → agent → visible consequence. A generator
  adds seconds to the one path that must be fast.
- **A committed camera move cannot be reshot for free** (`2610.12455v2`) — the estate's frames are
  commitments about the past, and generative rendering blurs exactly that.

## Decision

**The film is a deterministic twin of the event spine. No generative video in the loop, now or
later, for the core product.**

- The Director is a **pure function** of the event stream: same events, same frames, on every
  surface, forever. It is replayable, diffable and arguable.
- The renderer is whatever consumes the frames — Three.js today, something else later. The
  contract does not change when the renderer does.
- **No model in the ambient narration path** (spec law L2, requirement RT1). A model may answer
  a question the founder asks about the estate — with the rows shown — but it never narrates.
- A generative renderer may be added later as an **optional illustration layer** that is never
  allowed to contradict the frames. It is not part of this product and no acceptance criterion
  may depend on it.

### Why this is the moat, not the sacrifice

The founder frames this as a business play. The moat is not pixels: it is **causality with
provenance** (the founder's speech changes agent behaviour, audited), **truth at the speed of
live** (every line traceable to a row), and the **accumulated corpus** of directed sessions. A
competitor can copy a renderer in a week; they cannot copy the estate's spine, governance and
ledger. The rendering was always the commodity — this decision stops pretending otherwise.

## Consequences

**Positive.** Every frame is evidence. The film is replayable (a day of frames is a film of the
day). The build has no model dependency, so no cost, no cluster workload and no truth risk. The
acceptance criteria are testable rather than taste-based.

**Negative, accepted.**

1. **The picture is our own, not a frontier model's.** It will not look like a generated film.
   Accepted: the founder is watching *his estate*, and the alternative is a beautiful picture of
   something that did not happen.
2. **Cinematic craft is on us.** The shot grammar is ours to write and to grade
   (`2505.15145v1` is a reminder that technique can be benchmarked; ours is a table plus a test).
3. **A future "make it look like a movie" request will be refused by this record.** Reversing it
   is a new decision, not a quiet change.

## Enforcement

- The narration path contains **no model client**. A grep of the narrator for an LLM client fails
  the build (RT1).
- The Director's shot selection is a pure table; the replay test in
  `platform/voice-router/internal/director/director_test.go` asserts identical frames for an
  identical event sequence (law L3).
- No acceptance criterion in the spec or the review packet may name a generative model.
