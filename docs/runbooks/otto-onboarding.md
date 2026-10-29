# Runbook: onboarding Otto into the estate

**Date:** 2026-10-29 · **Claim:** idp#7432 · agent `pi`
**Decision:** `docs/decisions/0047-otto-is-the-estates-front-door-not-a-second-agent-platform.md`
**Spec:** `docs/specs/2026-10-29-otto-is-the-estates-front-door.md`
**Epic:** `docs/epics/2026-10-28-otto-minimum-viable-programme.md`
**Incident:** `docs/incidents/2026-10-29-the-cluster-lost-its-control-plane.md`

Otto is the estate's front door: everything a human says to the estate, and everything the
estate needs a human to say, crosses Otto. Below the seam Otto owns nothing — it borrows the
estate's one router, one memory, one executor, one verifier, one identity and one secret store.

This runbook is the *Otto* half of onboarding. The estate's half — the cluster itself — is
`#7387` (single-node k3s on one A1 VM) and `#7378` (one boot volume, at most two `oci-bv`
PVCs), and it is owned there. Nothing in this document rebuilds infrastructure, hand-applies a
manifest, or waits for the founder.

**The one command that answers the question:**

```bash
bin/otto-readiness-gate          # READY / NOT READY / BLIND, with the row that decided it
```

Exit 0 = onboarded. Exit 1 = not onboarded, and the failing row is named. Exit 2 = blind: a
row's source could not be read, so nothing is proven. `BLIND` is not `FAIL` — a dark estate is
not a broken door.

---

## 1. Where the estate actually is (measured 2026-10-29)

| what | measurement | meaning |
|---|---|---|
| `https://example.com` | `http=200` | this laptop's egress works |
| `https://otto.mumchimp.com/healthz` | `http=000` | the door's edge is down |
| `https://mcp.mumchimp.com/estate/mcp` | TLS: `read 0 bytes, wrote 1561` | the memory gateway is down |
| `https://llm.mumchimp.com` | TLS: `read 0 bytes, wrote 1562` | the estate's router is down |
| `https://141.147.80.229:6443/version` | `dial tcp: i/o timeout` | the cluster's control plane is unreachable |
| `otto`, `mcp`, `llm`, `api` under `mumchimp.com` | all resolve to `193.123.184.22` | **one shared public ingress** — a single point of failure for the door, the memory gateway and the router at once |
| OCI load balancer at `193.123.184.22` | `ACTIVE`, no working backend | the ingress is up; nothing is behind it |
| OKE tenancy limits | `cluster-count=0`, `enhanced-cluster-count=0`, `node-count=0` | Oracle removed the OKE entitlement (root cause, `docs/incidents/2026-10-29-the-cluster-lost-its-control-plane.md`) |

So: **the outage is estate-side, and it is not the laptop's.** Every public estate door shares
one address, so one broken ingress takes the door, the gateway and the router down together.
That is worth a follow-up of its own (§7, ticket filed with this runbook).

The doctor's live verdict at the time of writing — `2026-10-29T08:25:41Z` — was
`3 agents, 0 healthy, 0 broken, 3 blind`, verdict
`BLIND -- a source could not be read; the estate is dark from here`, exit 0 (it answered).

## 2. What can be done right now, with the estate dark

Everything in this section is offline and was run on 2026-10-29.

| step | command | receipt |
|---|---|---|
| Otto's manifests do not name a layer the estate owns | `bin/otto-conformance-gate` | `8 baselined debt row(s), 0 new violation(s)` — the debt is today's known violations, each with the wave that owns it |
| the estate's one-writer rule holds | `bin/otto-readiness-gate --offline` | `one writer (platform/otto-gateway/registration-reconciler.yaml), no long-poll, hermes-agent holds no token` |
| the doctor knows every Telegram surface | same command | `3 agents (jit-broker, otto-gateway, otto-golden), the declared owner is registered` |
| the offline verdict | same command | `READY otto-readiness: Otto is onboarded: every row is proven` |

The runtime row is the one that cannot be answered while the estate is dark, and it says so
rather than guessing.

## 3. The onboarding order, when the estate answers

Each step has a command, a proof and a falsifier. A step is done when the proof exists.

### Step 1 — the estate answers again

```bash
bin/idp-cluster-state          # or: kubectl version --short
```

* **Proof:** the API server answers with a version, and `kubectl get ns` lists the namespaces.
* **Falsifier:** `dial tcp 141.147.80.229:6443: i/o timeout` → the cluster is still dark; stop here.
* **Owner:** `#7387` / `#7378`.

### Step 2 — the public ingress answers again

```bash
curl -sS -o /dev/null -w '%{http_code}\n' https://otto.mumchimp.com/healthz
```

* **Proof:** `200`.
* **Falsifier:** `http=000` → the ingress has no backend; the cluster may be back while the
  door is not. Fix the ingress before anything below.
* **Note:** `193.123.184.22` serves every `*.mumchimp.com` host, so one broken backend takes all
  four with it.

### Step 3 — the door's chains are healthy

```bash
bin/otto-readiness-gate
```

* **Proof:** `READY`, with `runtime -- N agents healthy`.
* **Falsifier:** `NOT READY` → the row that failed is named, and the doctor's own output names
  the first broken link and the fix that repairs it.
* **Owner:** the doctor, `platform/estate/libexec/telegram-agent-doctor.py`.

### Step 4 — the estate's router is the door's default route (wave 1)

Today the door's default route is a pod-local loopback
(`platform/otto-gateway/deployment.yaml:327`, `LITELLM_BASE_URL=http://127.0.0.1:4010/v1`),
so every turn answered by the in-pod lifeboat is a turn the estate's router never sees and
never accounts for. `platform/otto-gateway/three-homes.yaml:41-47` says the estate keeps one
router and home 1 is it; the manifest does the opposite.

* **Proof:** the deployment's default route is the estate's router, the lifeboat is the last
  rung, and a turn answered by the lifeboat is recorded as `router.outcome` so it is counted.
* **Falsifier:** `bin/otto-conformance-gate` still reports the R2 debt row → wave 1 is not done.
* **Owner:** wave 1 ticket `#7445`.

### Step 5 — `remember` is the door's only memory (wave 2)

ADR 0036 deleted `otto_facts`, hindsight and the `otto-memory-store` Job on 2026-10-02. The
Job is still in the tree (`platform/otto-gateway/memory-store-job.yaml`), the deployment still
points at hindsight (`platform/otto-gateway/deployment.yaml:269`), and a NetworkPolicy still
opens the road to the hindsight namespace
(`platform/otto-gateway/network-policy.yaml:113`).

* **Proof:** `bin/memory-gate --check` is green on the manifests, a live `remember` is readable
  by a later `recall`, and no Otto manifest names a retired plane.
* **Falsifier:** `bin/otto-conformance-gate` still reports R1 debt rows → wave 2 is not done.
* **Owner:** wave 2 tickets (`#6162`, `#6163`, `#6165`, `#6229`).

### Step 6 — the shell runs without secrets (wave 3)

`docs/specs/otto-door-hands-and-senses.md` step 6 says a model-driven shell never runs in the
process that holds the bot token, the database password and the GitHub token, and that
`code_execution` stays out of `OTTO_TOOLSETS` until the sandbox lands. The secret-holding
container has both today (`platform/otto-gateway/deployment.yaml:356`).

* **Proof:** the shell runs as a Job in a sandbox namespace with no secrets mounted; the
  secret-holding container's toolsets carry no shell; estate-affecting actions go through
  estate intents.
* **Falsifier:** `bin/otto-conformance-gate` still reports R3 debt rows → wave 3 is not done.
* **Owner:** wave 3 ticket `#7446`.

### Step 7 — the SLA tick concludes, and the verdict is the doctor's (wave 4)

The scheduled tick `.github/workflows/otto-parity.yml` has been cancelling itself: measured
2026-10-29, runs `#40715893797` through `#40792186310` all concluded `cancelled`, and run
`#40792186310`'s playbook step was cancelled at the job's own `timeout-minutes: 15` after
every earlier step was green. A tick that cancels itself has measured nothing, so the
estate's Otto SLA has been dark for two days.

* **Proof:** the last tick's conclusion is `success` or `failure` — never `cancelled` — and its
  Telegram rows come from the doctor, so there is one set of rows and one verdict.
* **Falsifier:** the doctor's scheduled-plane row says
  `the last tick of otto-parity.yml was cancelled -- it measured nothing` → wave 4 is not done.
* **Owner:** `#7354`.

### Step 8 — the estate can see Otto

* **Proof:** `/fleet` shows Otto's live verdict and the link that broke.
* **Falsifier:** the verdict is only in a log.
* **Owner:** wave 1 of the epic (door track).

### Step 9 — close the waves with receipts

Each wave ticket is closed with the command and its output on the path the founder uses, per
AGENTS.md §5. Closing a ticket releases the claim.

## 4. What "onboarded" means, as a command

| truth (the epic) | command | receipt |
|---|---|---|
| its state is readable | `bin/otto-readiness-gate` | `runtime -- N agents healthy`, or the first broken link named |
| its health is watched | the doctor's scheduled-plane row | the last tick concluded; not cancelled |
| its delivery is gated | `bin/otto-conformance-gate` | 0 new violations; the debt shrinks as waves land |
| its work is dispatched and receipted | the answer probe's last run | a real completion on every lane the door can route to |
| its surface is the same agent | the same thread on portal and Telegram | wave 4 of the epic |

## 5. What NOT to do

- **Never hand-apply.** A drifted row is repaired by the reconciler that owns it, through
  `flux-reconcile`. No `kubectl apply` by hand, ever.
- **Do not land runtime manifest changes while the estate is dark.** The next cluster will be
  bootstrapped from this tree: prepare the target state in gates, tickets and this runbook,
  and land the manifest change when the estate can prove it.
- **Do not add a second health plane.** The doctor is the one door; the readiness gate reads it
  rather than re-probing.
- **Do not widen the conformance gate's baseline.** A new violation is a fix, not a baseline row.
- **Do not claim a wave done from a green gate alone.** A gate proves a rule holds; a wave is
  done when the behaviour it changes is proven on the real path.

## 6. The gates this runbook depends on

| gate | what it owns | where |
|---|---|---|
| `bin/otto-conformance-gate` | ADR 0047's four manifest rules, with the debt and its owners | `bin/otto-conformance-gate` |
| `bin/otto-readiness-gate` | "is Otto onboarded?", one command, four rows | `bin/otto-readiness-gate` |
| `telegram-agent.doctor` | every Telegram agent's chain, the first broken link, the fix | `platform/estate/libexec/telegram-agent-doctor.py` |
| `bin/memory-gate` | the estate's one memory plane | `bin/memory-gate` |
| `bin/claim-gate` | that a change lands against a live claim | `bin/claim-gate` |

## 7. Follow-ups this runbook found

1. **One shared public ingress.** `otto`, `mcp`, `llm` and `api` under `mumchimp.com` are one
   address (`193.123.184.22`). A single broken backend takes the door, the memory gateway and
   the router down together, and the estate learned it from three separate symptoms. A second
   ingress, or a health check on the load balancer's backends, is the fix. Ticket `#7448`.
2. **`OWNER.yaml` points at a gate that does not exist.** It says
   `Enforcement: bin/idp-rules (rule: telegram-single-writer)`; measured 2026-10-29, there is
   no `bin/idp-rules` in this repository, so the three checks it names were documentation. They
   are checks now, in `bin/otto-readiness-gate`. `OWNER.yaml` should be corrected to name the
   gate that exists. Ticket `#7449`.
3. **A doctor that reports a cancelled tick as BLIND is right, but the tick must stop cancelling
   itself.** Until `#7354` lands, the estate's Otto SLA measures nothing, and the doctor will
   keep saying so — which is the honest answer, not a fix.
