# Fleet Reactor 2100 — the HUD architecture

**Source: the founder's external consultant, 2026-09-20.** Kept verbatim where it states a
decision, so the reasoning survives the context window. This SUPERSEDES the spatial parts of
`2026-09-18-fleet-interface-design.md` where they conflict, and it resolves the tension that
document could not: **no feature is cut, and the text still goes.**

## The resolution in one sentence

Stop building a **dashboard** and build a **HUD**. Do not cut the data — change its **temporal and
spatial manifestation**. Information is ambient until interrogated, and voice is routed by
**spatial intent**, not by typing string names.

## The interaction model

Supervising 43 agents is not a reading task, it is **air-traffic control**. You cannot read 43
labels, but peripheral vision instantly detects an anomaly in a field of 43 moving objects. The
model separates two scales:

- **Macroscopic (the whole fleet):** the 3D scene owns the viewport. State is encoded entirely in
  the particle jets — speed, turbulence, colour. Spend becomes a persistent glowing border — the
  burn bar — shifting cool blue to warm amber as the rate accelerates.
- **Microscopic (one agent):** the 33-line rail and the 24 text chips are banished from the default
  view. They become **on-demand data holograms**, unfolding beside a node when it is focused, and
  collapsing when focus moves.

## 1. Information architecture

| modality | what belongs there | what gets deleted |
|---|---|---|
| **3D space** | topology, activity state via motion/colour, anomaly alerts | the 24 static text chips |
| **fixed scan line** | aggregate health; burn rate as **intensity**, not a number | the static `$0.44` text counter |
| **voice** | intent, commands, high-level routing | "Talk" tabs full of dumb text |
| **on demand** | the 33-line dashboard data; full conversational logs | the permanent 248px left rail |

## 2. The pulse — why it is not a notification feed

A feed demands active reading; a pulse is ambient. It manifests through the existing
`requestAnimationFrame` loop:

- an agent completes → a subtle visual ripple passes through the graph
- an agent is stuck → its node pulses at a discordant frequency
- **it interrupts the person only when a sovereign approval gate (`/approve`) needs human
  sign-off**

## 3. Voice addressing — the footgun fix

Addressing 43 agents by string name (typos included) is a broken paradigm. **Spatial voice
targeting:**

- the person selects a node or cluster in the scene, creating the missing voice-target lock
- when they speak, the voice layer routes the command to the **currently focused `session_id`**
- **log the fix:** pipe Whisper ASR transcripts and latency metrics into `fleetview_signals`, and
  render an **ephemeral subtitle** at the bottom of the viewport showing exactly what was heard,
  fading after 3 seconds

## 4. The whites

**Eliminate the chrome; do not integrate.** Boxing a dark spatial instrument in 224px of bright
Backstage portal shatters the immersion. The WebGL canvas must touch the physical bezels of the
screen.

## 5. The single biggest lie

**The illusion of seamless voice control while hiding the raw transcript.** The person is blindly
firing Whisper transcripts into a black box, producing misheard tasks and broken trust. The one
change that most increases the 2100 feeling is closing that loop: a **live target-lock on the 3D
node being addressed**, plus an **ephemeral on-screen conversational log** that proves the agent
understood before it executes.
