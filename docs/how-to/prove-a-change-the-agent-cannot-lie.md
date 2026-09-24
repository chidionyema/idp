# How to prove a change the agent cannot lie about

> The "Agent That Couldn't Lie" demo. Run it, see the contradiction caught, merge refused.

## Why this exists

The two-engine framework (Engine 1: shadow/GitOps, Engine 2: JIT break-glass) makes a
specific promise to the buyer: **the AI that operates the estate cannot ship a change it
hasn't proven, and cannot fake the proof.** `bin/idp-truthteller-demo` is the runnable
demonstration of that promise — a buyer clicks a button, sees an agent claim a workload is
Ready, sees the truth-teller read the actual shadow-cluster state, and watches the
contradiction get caught on screen.

## Run it from the laptop

```bash
# The full buyer demo (rogue scenario by default)
bin/idp-truthteller-demo demo

# The same shape with an honest claim (matches observed)
bin/idp-truthteller-demo honest

# Just read the observed state of a workload
bin/idp-truthteller-demo state --workload demo-shop

# Format that read as the agent would assert (probe / warmup)
bin/idp-truthteller-demo claim --workload demo-shop
```

Output for the rogue scenario (target: demo-shop, the seed of the demo-sandbox vcluster):

```
======================================================================
  ZERO-TRUST AUTONOMY: the moment an agent cannot lie
======================================================================

  Workload:    demo-shop
  Observed at: 2026-09-10T12:00:00Z

  AGENT'S PROOF OF CONVERGENCE (what it claimed):
    Target:    demo-shop
    Change:    Raise memory limit from 256Mi to 1Gi on the OOMKilled workload
    Status:  Ready
    Replicas: 1
    Logs:    "Memory raised, pod restarted, probes green. OOMKill resolved."

  TRUTH-TELLER'S OBSERVATION (read from the shadow cluster):
    Status:  CrashLoopBackOff
    Ready:   0 / 1
    Available: 0 / 1

  FIELD-BY-FIELD:
    LIE  status               claim=Ready          observed=CrashLoopBackOff
    LIE  replicas             claim=1              observed=0

  ======================================================================
  MERGE REJECTED  — AGENT FABRICATION DETECTED.
  ======================================================================

  CUSTOMER OUTCOME PREVENTED:
    If this AI had been trusted, the change would have merged.
    A workload would have stayed in CrashLoopBackOff in production.
    Customers impacted: ZERO — the truth-teller caught it.
  ======================================================================
```

(The four-act narrative prints the same shape: claim → audit → contradiction → customer
outcome prevented. The exact text is from the founder's prototype, kept verbatim.)

## Run it from Backstage

The Showcase page on the portal has a tile: "Live: the agent that couldn't lie." Clicking
the tile runs the same Python script and renders the same side-by-side in the page.

## How it works

The truth-teller is structurally incapable of forging its answer because:

1. **The assertions are platform-owned** (W0.6): the script compares the agent's claim field
   by field against a read from the actual cluster. The agent does not pick the assertions.
2. **The read is read-only** (W1.1): `idp-kube` answers as `system:serviceaccount:agents:agent-reader`,
   not as the agent. The agent's identity cannot write to or modify what the truth-teller reads.
3. **The compare is fail-closed** (W2.2): a partial match is still a refusal (`ready==available==required`).
   A blind read is a refusal too, never a green zero.
4. **The observed state carries its own timestamp** (W0.5 hook): when the cryptographic signing
   of the shadow run lands (cosign), the SHA becomes part of the verdict so a forged body can't
   pass even if the comparison were somehow tricked.

## What's NOT in scope (yet)

- **W0.5 (sign the proof):** the verdict carries the observed timestamp, but it is not yet
  cosign-signed. Adding the signature is a small, separate change to `idp-shadow-run` (the
  producer already exists on main).
- **W0.6 (platform-owned assertion sets):** the per-workload assertion list is not yet
  surfaced as `platform/assertions/<workload>.yaml`. Today the script reads the workload's
  observed state directly.
- **The live Showcase tile** (Backstage component that runs the demo on click): the surface
  is laid out, but it's a follow-up change to `backstage/` once the core script is merged.

## Exit codes

- `0` — claim matched observed (or honest demo ran)
- `1` — contradiction caught (the buyable moment)
- `2` — blind (the truth-teller could not read the shadow cluster)

A blind exit (`2`) is not a green pass. The spec's fail-closed default.
