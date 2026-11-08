# 0040 — The Director runs on the laptop until the causal loop is proven

Date: 2026-10-23
Status: accepted
Related: 0034 (placement by the free tier), 0037, 0038, 0039,
`docs/specs/2026-10-23-estate-as-movie-director-engine.md` §5.7

---

## Context

`0034` decides placement: free tiers first, and among them the ladder is delete → GitHub Actions
schedule → Grafana/Cloudflare free → **laptop just in time** → KEDA scale-to-zero on the node →
always-on. A PR that adds to the node states its CPU and memory requests, and the node's
requests stay under 1.8 CPU.

The Director is a new long-lived process. The obvious question is whether it belongs on the
cluster (it is a "voice-router" component; there is already a `voice-router` namespace with a
`voice-router-director` Deployment and no Service) or on the laptop.

Measured on 2026-10-23:

- **the laptop is already loaded**: load average 546–626 on 4 cores during this session;
- **the laptop holds what the Director needs**: the local session files, the local intent
  registry (333 intents live only there `[R]`), the runtime channels the founder's agents run on,
  and the `voice-router` process itself, already answering `/readyz` on `127.0.0.1:8091`;
- **the cluster is where the Face's page lives but not its hands**: the Face's intents egress to
  the laptop over Tailscale (`FLEETVIEW_INTENTS_URL` → `fleetview-mac`) `[R]`, so the cluster
  already depends on the laptop for anything an agent does;
- the existing `voice-router-director` Deployment is explicitly a **P1 placeholder**: *"No UI,
  no LLM anchor, no voice in P1 (crew#974). No Service is declared: nothing calls the director."*

So the cluster copy of the director is a placeholder nobody calls, and the laptop already runs
the voice stack the film depends on.

## Decision

**The Director runs on the laptop, beside the voice router, until the causal loop (S0) and the
scene (S1) are green. It is not deployed to the cluster as part of this work.**

- No new cluster workload, no new Deployment, no new Service, no node requests — the ladder in
  `0034` is not reached.
- The `voice-router-director` Deployment in the cluster stays as it is (a placeholder that nothing
  calls) **until** a later decision moves the Director there, with the measured CPU/memory it
  actually uses.
- **The laptop copy is the one that counts.** A Director running in the cluster could not read
  the laptop's sessions, and the founder's agents live on the laptop.
- The process is **small and bursty**: it coalesces events (one frame per session per tick) and
  does nothing when the estate is idle. Its cost is measured (requirement RB4) over an hour of
  use, with the estate's own load on the same machine — the number that decides the escalation.

### Why this is not "it is on my laptop so it is not real"

Because the proof is the point, not the location. S0's acceptance is the agent's own transcript
changing because the founder spoke. That proof runs wherever the agent runs. Putting the Director
on the laptop is a **placement** decision, not a maturity one.

The opposite mistake — putting it on the cluster because it "should" be a service — would make it
a Deployment with no Service that nothing calls, which is exactly what the cluster copy already
is.

## Consequences

**Positive.** No cluster workload, no node requests, no image, no Flux row, nothing to place. The
Director sits next to the voice router it consumes. Iteration is a process restart. The
escalation question is answered by measurement (RB4) rather than by taste.

**Negative, accepted.**

1. **The film dies when the laptop sleeps.** Accepted at this stage: the founder's agents live on
   the laptop too, so the estate's own work stops as well. The Face's page is in the cluster and
   already has this shape ("the mouth is in the cluster and the hands are on the Mac" `[R]`).
   The honest fix — running the Director in the cluster — is a later decision with a measured
   CPU/memory figure, not a guess made now.
2. **The laptop's load average was 546–626 on 4 cores.** Accepted: the Director coalesces and
   idles; its cost is measured over an hour and compared with the estate's other load. If it is
   material, the answer is a schedule or an edge deployment, in ladder order.
3. **Two copies of the code will exist** (laptop and the unused cluster Deployment). Accepted
   only while the cluster copy calls nothing; it is deleted, not kept in parallel, if the
   Director stays on the laptop past S3.

## Enforcement

- `kubectl get deploy -n voice-router` shows **no new workload** as part of this work (law L9).
- The Director runs as a laptop process beside the voice router, started the way the estate
  starts its laptop services, and is visible in the estate's own process inventory.
- Requirement RB4 exists and is filled in with a measured number: the Director's CPU and RSS
  over an hour of use, with the estate's load alongside it.
