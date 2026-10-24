# 0041 — The artifact on screen is the real artifact, not a picture of it

Date: 2026-10-23
Status: accepted (founder framing: *"one good demo of this is seeing an agent build something in
a movie and then seeing the same thing, e.g. UI, in real life / realtime"*)
Related: 0034 (placement by the free tier), 0037 (deterministic twin), 0038 (one scene contract),
`docs/specs/2026-10-23-estate-as-movie-director-engine.md` (§5.8, law L11, DS1–DS7),
`docs/reviews/2026-10-23-consultant-review-packet.md` (Q11, Q12)

---

## Context

The founder's flagship demo is one sentence: an agent builds something **in the film**, and then
the **same thing** appears live. That is stricter than "the film is live", and it splits the
product into two planes that look alike and behave very differently:

- the **estate plane** — the cast, the camera, the narration — is rendered, deterministically,
  from the event spine (0037). This is the film's own material.
- the **artifact plane** — the thing the agent actually built — is not the estate's rendering at
  all. It is the agent's output: a surface, a url, a commit, a running process.

The tempting shortcut is to draw the artifact inside the room: a Three.js mock of the UI the
agent is building, or a screenshot of the real page pasted into a frame. Both are cheap, both
demo well, and both are the thing the estate's own laws forbid. A picture of a UI is a mock. The
estate's law is proof, not assertion (AGENTS.md §3); a rendered artifact that was never rendered
by the agent is an assertion with a 3D surface on it.

Measured on 2026-10-23, in this repo:

- the room **has no iframe today** — `rg -n "iframe" backstage/packages/app/src/modules/room/ui/`
  → no hits `[M]`;
- the room **already renders the estate's real state in live panels** —
  `room/ui/Delivery.tsx` (the merged→operating beam), `room/ui/GreenlaneHud.tsx` (the lane's
  brief), `room/ui/ClaimsPanel.tsx` (live claims) `[M]`. "Live truth in the room" is a pattern the
  estate already owns; the artifact plane extends it to the thing an agent built;
- the deploy path is minutes, not seconds: merge to `main` → `build-multiarch` → Trivy/cosign →
  `ghcr` tag → Flux image-automation → deploy-when-green (AGENTS.md §2) `[M]`.

So the fork is real and it is now: **the artifact plane shows the real surface, embedded live**
(the url the agent's work is actually served from, or the dev server while it is being built) —
or the film draws a picture of it.

## Decision

**The artifact on screen is the real artifact. The film never redraws it and never mocks it.**

- The scene frame carries an **artifact reference** — `{kind, url, sha, ref}` — and the room
  resolves it to a live surface. A sha that is on `main`; a url that answers; a process that is
  running. No fixture, no seed, no screenshot in the artifact path (law L11).
- The **estate plane is rendered**; the **artifact plane is embedded**. That split is the whole
  design: one is a film of the estate, the other is the estate's product, on the wall, live.
- The artifact plane is a **view, not a door**. It does not accept input that changes the estate;
  the founder's input goes through the voice path and the governed doors (law L5, law L8).
- **Reachability is part of the design.** A deployed service is reachable from the founder's
  browser (`catalogue.mumchimp.com/face/` `[R]`); a laptop dev server is not, without a route to
  the laptop. So the deployed url is the proof artifact (DS2) and the dev server is the
  build-in-progress artifact (DS4) — and the demo states which plane it is showing. The cost of
  that distinction is a question for the consultant (review packet Q12), not a hidden detail.
- The demo is **one take**: no edits, no cuts, no post-production, and it re-runs live on demand
  (DS1, DS7). A demo that cannot be re-run live is theatre.

### Why the moat survives this

The founder frames the project as a business and moat play. This decision is what keeps the
moat in the right place. A rendered artifact would put the estate's credibility behind a renderer
anybody can imitate — and would make the film's most impressive moment the one moment that is
not true. The real artifact in the room cannot be faked by a competitor: it is the estate's own
governed output, appearing in the estate's own surface, at the moment it was built. The moat is
still causality, provenance and the corpus (0037) — this decision just makes the flagship demo
point at the moat instead of at the commodity.

## Consequences

**Positive.** The flagship demo is the thing the founder actually described. Every frame of the
build carries a row id, so the demo is auditable like everything else in the estate. The room
gains one pattern (a live surface in the world) rather than a new capability.

**Negative, accepted.**

1. **The deploy path is minutes.** The fully real artifact (deployed, merged, Flux-applied) is
   not available in the same second as the first file write. Accepted: the demo proves the real
   artifact (DS2) and the build-in-progress view uses the dev server (DS4), with the difference
   visible in the film rather than hidden by a mock.
2. **The artifact plane needs the founder's browser to reach whatever it embeds.** A laptop dev
   server needs a route; a service behind auth needs a session. This is real work the spec puts
   in S3.5, not a footnote.
3. **An embedded live surface is a new surface with new failure modes** — a dead url in the room
   is a bad frame. Accepted: a frame whose artifact reference no longer resolves is refused by
   the renderer rather than shown stale.

## Enforcement

- The scene frame's `artifact` field is required to carry a **resolvable** reference; a frame
  with an unresolvable artifact reference is dropped by the Director, not rendered (L11, DS2).
- No screenshot, image, canvas snapshot or hand-built mock of an agent's output may appear in
  the artifact plane. A grep of the artifact plane for image/mock/fixture sources fails the
  build.
- The demo's acceptance (DS1–DS7) is written into the consultant's delivery contract
  (review packet §6, slice S3.5), and every narrated step of the build carries the row id of the
  gate that produced it (law L2, DS3).

## What would reverse this

A decision that the founder's browser cannot reach the artifact plane reliably, on the founder's
actual devices, at the actual latency of the deploy path — **and** the founder's explicit
preference for a drawn artifact over a real one. That would be a new record, not a quiet
change: the draw would then be declared a **simulation**, in the same words, and no acceptance
criterion would still call it the real artifact.
