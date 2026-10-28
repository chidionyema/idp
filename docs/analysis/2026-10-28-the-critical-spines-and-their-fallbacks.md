# Analysis: the estate's critical spines, their homes, and where they are blind

- Date: 2026-10-28
- Question asked by the founder: "analysis and recommendations for other critical services
  spines/backbones that is crucial for the estate to have no fallback", and "how to better
  handle capacity given the options available ... we are blind to the capacity issue and should
  be proactive rather than reactive".
- Ruling: [0037](../decisions/0037-the-fallback-ladder-and-the-drill.md) · design:
  [the spec](../specs/2026-10-28-the-fallback-ladder-and-the-drill.md)
- Method: the estate's own always-on inventory (`clusters/oke/*.yaml`, 45 always-on
  Kustomizations) and the estate's own layer list (`AGENTS.md` §6) were read; every home below
  was then **measured** by the drill (`bin/idp-estate-homes --no-file`, 2026-10-28T10:53Z) or by
  the OCI API. Where a thing could not be measured it says so.

## The measurement this analysis starts from

`bin/idp-estate-homes --no-file`, 2026-10-28T10:53Z: **14 of 22 lanes answered, 6 down,
2 unknown.** The down ones:

| lane | verdict | reading |
|---|---|---|
| llm-router / cloud (OKE LiteLLM) | MEASURED_FAIL | `https://llm.mumchimp.com/health/liveliness` timed out after 10 s |
| llm-router / lifeboat (Cloudflare edge) | MEASURED_FAIL | `nodename nor servname provided` — the name does not resolve |
| otto / cluster (otto-gateway) | MEASURED_FAIL | `/health` is a 404 (the cluster answers 200 on `/healthz` — the path, not the service) |
| otto / lifeboat (Cloudflare edge) | MEASURED_FAIL | the name does not resolve |
| estate-doors / meridian | MEASURED_FAIL | timed out after 10 s |
| estate-doors / acg | MEASURED_FAIL | the name does not resolve — **this host is not published**; the drill's config was wrong, and a wrong lane is a wrong measurement |

And the two unknowns: the Groq floor, whose key was not in that shell (the same key the Otto
grader reached from the vault: `bin/idp-otto-homes` measured Groq **MEASURED_OK HTTP 200** at
10:46Z).

**The estate's doors survived its router.** 14 of 15 published hostnames answered while
LiteLLM was down: `auth`, `catalogue`, `hc`, `langfuse`, `signoz`, `superset` answered 200;
`api`, `mcp`, `cyrus`, `otto` answered 404 (the door is there, the path is not); `www` answered
308; `sandbox` answered **500** (a door that answers and is broken — the only lane class the
first version of the drill could not tell apart from a healthy one).

That is the shape of the estate's risk, and it is not uniform: **the doors are cross-provider
(Cloudflare DNS and an anycast edge survive an OKE outage), and the brains behind them are
not.**

## The spines, one by one

| spine | what breaks without it | homes today | the risk | the recommendation |
|---|---|---|---|---|
| **Routing** (`llm`) — the model router | every agent, the voice loop, every surface that streams | OKE (down), laptop (up), lifeboat (down), Groq (up, from the vault) | two of four homes are down, and one of the two that work is the founder's machine | bring the lifeboat up on a `workers.dev` subdomain (no zone needed); make the front's cloud legs a **list** so a second provider's home is a config line, not a code path |
| **Identity** (`auth`, Keycloak) | every new login; existing sessions survive (JWTs are validated locally) | OKE only | the *door* is cross-provider, the *realm* is not; a realm outage is invisible to a door-level drill | add a realm-level lane to the drill (the realm's own health endpoint, not the door's 200) and record the degradation honestly: new logins fail, old sessions keep working |
| **Secrets** (external-secrets + the vault) | no *new* secrets; the truth is the vault, which is not in the cluster | vault (outside OKE) + the controller in OKE | the store is safe; the controller is single-homed, and a controller outage is invisible until a workload needs a secret | a drill leg that reads one named secret through the controller (can we still fetch?) — the read, not the list |
| **Data** (`estate-db`, CloudNativePG) | the catalogue, the memory store, the ledger, the receipts | OKE only | **the one thing that cannot be a free floor** — and the one eating the storage allowance that broke the router | a scheduled dump to a free external store as the recovery home, plus a drill leg on the **age of the last dump**; and the capacity guard, because the database's volumes are the allowance |
| **Traces** (Langfuse, SigNoz) | the evidence plane's UI; the work continues | OKE only | traces are write-only for the estate's health — losing them loses the record, not the work | the OTLP exporter already has a free hosted receiver in ADR 0034's ladder; make that the configured receiver for the lean tier (it is), and grade the receiver, not the UI |
| **Scheduling** (Flux + cronjobs) | the estate's periodic work (drills, digests, GC) | Flux in OKE + GitHub Actions schedules (free) | already two homes, but the two are not both graded | every critical cron gets a GitHub Actions twin and a drill leg; the drift door runs there |
| **Catalog** (`catalogue`) | the portal's content | OKE (the door) + **the git repository** (the content) | the content is safe in git; the door is not | the lifeboat can serve the catalogue statically from the repo — one Worker, no cluster |
| **Execution boundary** (the executor, the intents) | every agent's action | the laptop executor + the Actions runner | the laptop is the founder's machine; the runner is GitHub's | already two providers; add the drill leg and keep the session plane (Temporal) as the third |
| **Evidence / verification** (the gates, the registry, the graph) | the estate's ability to say "done" honestly | the repo (git) + the graph repo + the fact store | the memory door measured **HTTP 500** on `brief`/`recall`/`remember` during this incident — the estate was blind while it worked | the graph is the working second store; grade the memory door so its outage is a ticket, not a surprise |
| **Memory** (the memory door, growmos) | the estate's shared memory; the work continues but the context is lost | the memory door (500) + the graph repo | same as above | a drill leg for the door's own health, and the graph as the standing fallback |
| **The edge and DNS** (Traefik, external-dns, Cloudflare DNS) | every public door | **Cloudflare DNS + anycast edge** — already a second provider | the DNS survives an OKE outage (measured: 14 of 15 doors answered) | keep it there; add the lifeboat Worker so a door can answer *with something* when the service behind it cannot |
| **Voice** (the voice loop) | the founder's primary interface | the cluster's voice router + the laptop's ASR/TTS lanes | the one surface where "degraded" is felt first | put the voice loop first in the drill's order and give it the laptop's lanes as its floor |

## Capacity: the blindness, and what to do about it

**What was blind.** The estate's own apply refused for a week with
`(400, LimitExceeded, false) You cannot create a volume because you have reached your limit.`
and `400-LimitExceeded, LimitExceeded: nodes-per-node-pool limit has been exceeded.` — and
nothing in the estate's gates had asked what the estate *asked for* versus what the free tier
*gives*. The measurements that say it:

| asked for | allowed | measured gap |
|---|---|---|
| 14 block volumes / 700 GB | 200 GB Always Free (`platform/oci/main.tf`) | **+500 GB over**, of which 450 GB was nine dead volumes (a deleted volume becomes TERMINATED, not gone) |
| 2 A1 nodes in pool `a1` | 1 node | OKE refused the update: `nodes-per-node-pool limit has been exceeded` |
| LiteLLM `replicas: 2` with a `DoNotSchedule` spread on `kubernetes.io/hostname` | 1 node to schedule on | the second replica can never be scheduled → `available=1 desired=2` → the edge answers 503 while the deployment looks fine |

**What to do, in order:**

1. **Reclaim the dead as dead** — done: the reclaim door's rule now treats a TERMINATED volume
   as dead (it cannot be mounted, and it still holds the allowance), and 450 GB was released.
2. **Ask the free tier for what it gives** — one A1 node for `a1`; the autoscaler at
   `--nodes=1:1`; LiteLLM at one replica, or a `ScheduleAnyway` spread so the second replica
   lands on the same node instead of never. An unschedulable replica is a 503 with a green
   deployment behind it, which is the most expensive kind of outage: the estate looks healthy.
3. **Measure capacity before the apply, not after the refusal** — a capacity guard that reads
   the compartment and the node pools and compares them with the declared allowance, run
   before `tofu apply`, and reported by the drill. The estate had a `capacity_cap` tofu
   precondition once and deleted it (ADR 0034): a precondition that blocks a merge is the wrong
   shape; a **scheduled drill that says "the estate is 250 GB over its allowance, here is the
   list"** is the right one.
4. **Declare the allowance once** — one file states the free tier's numbers (200 GB of block
   storage, one A1 node, the CPU and memory), and both the guard and the docs read it. Today
   the number lives in a comment in `platform/oci/main.tf`, which is a comment, not a
   constraint.
5. **Cheapest first, always** — ADR 0034's ladder: delete → GitHub Actions schedule → Grafana
   Cloud free → Cloudflare Workers free → the laptop just in time → KEDA scale-to-zero on the
   node → always-on on the node. The capacity problem is usually a placement problem: the
   estate put things on the node that the free tier never agreed to carry.

## The top three moves, by effect

1. **Bring the lifeboat up** (`workers.dev`, no zone, no OCI, anycast) — it is a home for the
   router, for Otto, and for the catalogue, and it is the estate's only cross-provider brain.
   It is currently *down*, and it is the home the founder remembered.
2. **Make the front's cloud legs a list** — a second provider's home must be a line in a
   config file, not a code path, and the front's per-leg state must be per leg so one dead
   provider does not put the whole cloud out of the route.
3. **The capacity guard and the three over-asks** — one node, one replica, one declared
   allowance, measured on a schedule.

## What is not measured here, and would be with the API reachable

The doors were measured; the services behind them were not, because the cluster's public API
endpoint is closed on purpose and the bridge that opens the road is `TERMINATED`. So the
per-service state of Keycloak, external-secrets, CloudNativePG, Langfuse and the voice router
is **not** claimed here — the drill's legs for them are configured, and the next drill run
against a reachable cluster will fill the table.
