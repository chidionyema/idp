# Spec: the fallback ladder, and the drill that measures it

- Date: 2026-10-28
- Deciders: founder ("and lastly recurring drill that verifies these critical lanes"; "so our
  estate can never go down like this again")
- Ruling: [0037](../decisions/0037-the-fallback-ladder-and-the-drill.md)
- Trigger: [the router lost every model](../incidents/2026-10-28-the-router-lost-every-model.md)

## 1. The problem, in one measured paragraph

On 2026-10-28 the cloud route answered 503 ("Starting up") and then 504 at the edge, the front
decided the route **on the connect**, so the failure was relayed to the caller while a healthy
laptop lane sat unused. The estate's router had **two** homes, and one of them was the
founder's laptop: if the founder had closed it, the estate had one. Meanwhile the estate's own
"always available" third home — Otto's Cloudflare edge — was **down and had been**: measured
2026-10-28T10:46Z by `bin/idp-otto-homes`, `2 cloudflare lifeboat-llm.mumchimp.com MEASURED_FAIL
no answer from https://lifeboat-llm.mumchimp.com/health (URLError)`, and
`dig +short lifeboat-llm.mumchimp.com` prints **nothing** — the name does not resolve. The
founder's own words at the time: "we attempted to do something like this for otto, always
available".

So the estate had a fallback design and no fallback estate. The design was in
`platform/otto-gateway/three-homes.yaml` and `docs/explanation/otto-survival-matrix.md`; the
practice was one laptop and one cluster.

## 2. What a home is

A **home** is a failure domain: a place the service runs that can die without taking the others
with it. The estate learned that the hard way (Otto's survival matrix): five model lanes in one
ConfigMap, read by one sidecar, in one pod, on one cluster, are five lanes and **zero** homes.
A lane is a vendor that does the thinking; a home is a place it runs. The two are independent,
and the ladder crosses them.

## 3. The rules

**R1 — Three homes, two providers, for every critical service.** A service is critical when
losing it stops the founder or the estate's agents. Its ladder has at least three homes, and
they span at least two providers, so no single provider failure empties the ladder.

**R2 — No shared first rung.** The estate's own cluster is never the only first rung. A home
that is inside the estate's own failure domain (OKE, its load balancer, its DNS) does not
count as a second home, and the switch between homes needs no human.

**R3 — Fail over on the answer, not on the connect.** A connect that succeeds proves nothing:
the 2026-10-28 cloud accepted the connection and then failed. A home is passed over when it
**answers** badly (5xx, a stall, a refusal that is about the model, not the request), and a 4xx
that is the caller's own fault is relayed, unretried, because retrying it cannot help.

**R4 — The last rung is free.** The floor rung costs nothing, so it cannot run out of credit.
The estate's free lanes (Groq, the local Ollama lane in the cluster, Workers AI) are floors,
not first tries.

**R5 — A rung nobody measures is a hope.** Every home in every critical ladder is graded on a
schedule by `bin/idp-estate-homes`, and a dead home becomes a ticket, not a log line.

**R6 — Unknown is not OK.** The verdict vocabulary is Otto's: `MEASURED_OK`, `MEASURED_FAIL`,
`UNKNOWN`. A home is OK only when a question only a working home can answer came back. A drill
that cannot ask is `UNKNOWN`, and it says so instead of reporting a clean board.

**R7 — The ladder is configuration.** `platform/ladder/critical-lanes.json` holds the homes;
adding one is a line in that file. The drill asks the questions; it does not know which homes
exist. The same rule applies to the router front's own list of cloud legs: a home is a URL and
a credential, not a code path.

**R8 — The capacity of a free tier is a design constraint, not a surprise.** ADR 0034 says the
free tier decides placement. A design that asks for more than the allowance has (two A1 nodes
when the allowance is one; two LiteLLM replicas with a `DoNotSchedule` spread on a one-node
pool) is refused at the worst possible moment, and the refusal is a 400 from a vendor, not a
sentence from the estate.

## 4. The router's ladder, as measured

Measured 2026-10-28T10:53Z by `bin/idp-estate-homes --no-file` (the drill, first run):

| home | provider | verdict | what it is |
|---|---|---|---|
| cloud (OKE LiteLLM) | oracle-oke | **MEASURED_FAIL** | the default route; `https://llm.mumchimp.com/health/liveliness` timed out after 10 s |
| lifeboat (Cloudflare edge) | cloudflare | **MEASURED_FAIL** | the cross-provider home; the name does not resolve |
| groq free tier | groq | **UNKNOWN** | the floor; the key was not in that shell's environment |
| laptop front | laptop | **MEASURED_OK** | the in-house fallback; HTTP 200 |

That table is the whole argument for this spec: on the day the router broke, one lane was
alive, and it was a laptop.

## 5. The drill

`bin/idp-estate-homes` grades every lane of every critical service and **files what is down**:
one issue per service, commented on while it stays down, closed when the lane answers again.
It is a door, not a script, and it is on a schedule
(`.github/workflows/estate-homes-drill.yml`, every 30 minutes) because a drill nobody schedules
is a drill that runs once.

The drill's rules, so it cannot lie:

- every probe carries a `user-agent` (measured 2026-09-10: `api.groq.com` answers **403
  "error code: 1010"** — Cloudflare's browser-fingerprint rejection — to Python's default agent,
  and **200** to the same request one second later with a plain agent string; a probe without
  this line grades a working vendor dead);
- a lane that needs a secret this host does not carry is `UNKNOWN`, never `FAIL` (a runner
  without the key cannot grade a lane it cannot ask);
- a loopback lane that is not here is `NOT_HERE`, never `FAIL` (the laptop is not down from a
  runner that is not the laptop);
- a ladder that cannot be read is `BLIND` and exits 2 — a drill that cannot see is not a drill
  that says all clear.

## 6. Cross-platform homes, and what each one costs

| candidate | provider | what it gives | the constraint, measured |
|---|---|---|---|
| **Cloudflare Workers** (the lifeboat) | Cloudflare | anycast, no node, no OCI, no DNS of ours; Workers AI in-process with **no key and no account id** | the name `lifeboat-llm.mumchimp.com` **does not resolve** (measured 2026-10-28); the worker's own subdomain (`*.workers.dev`) needs no zone, so it is the road when the zone is not in the estate's Cloudflare account (`mumchimp.com is not a zone of this account`, measured while bootstrapping Cloudflare) |
| **Groq free tier** | Groq | a second provider, a card-free floor | 1,000 requests/day (its own `x-ratelimit-limit-requests` header, measured 2026-09-10) — a floor, never the first try; and a probe must carry a user-agent (above) |
| **A second vendor lane (MiniMax, Gemini, OpenRouter)** | each its own | the estate already holds keys for them in the vault | they are *lanes*, not *homes*: they still run from inside the cluster unless a home carries them |
| **The laptop** | the founder's machine | the lane that actually answered on 2026-10-28 | a machine that can be closed, and that measured 16 output tokens in 24–46 s (it was removed as a home for that reason) — a fallback, never the only one |
| **GitHub Actions (schedule)** | GitHub | where the drill itself runs, free | it is the drill's home, not the estate's services' |

## 7. Capacity, seen as a ladder problem

The router died of capacity, and the estate was blind to it. The measured facts:

- the compartment held **14 block volumes / 700 GB** against a **200 GB** Always Free allowance
  (`platform/oci/main.tf`: "Block storage is 200 GB Always Free and the PVCs claim 21 GB");
- **9 of them were dead** (TERMINATED) and still held **450 GB** — a deleted volume becomes
  TERMINATED rather than gone, so reclaiming orphans freed nothing until the dead ones were
  deleted as dead;
- the pool asked for **2 A1 nodes** when the allowance is one, and OKE refused the apply with
  `nodes-per-node-pool limit has been exceeded`;
- LiteLLM asked for **2 replicas** with a `DoNotSchedule` spread on `kubernetes.io/hostname` on a
  pool that can hold one node, so the second replica could never be scheduled — which is exactly
  how a deployment ends with `available=1 desired=2` and an edge that answers 503.

The recommendations, in the order they matter:

1. **Reclaim the dead volumes as dead** (done: the reclaim door's rule, 450 GB released).
2. **Ask the free tier for what it gives.** One A1 node for `a1`, `--nodes=1:1` for the
   autoscaler, one LiteLLM replica (or `ScheduleAnyway`) — an unschedulable replica is a 503
   with a green deployment behind it.
3. **Measure capacity before the apply, not after the refusal.** A capacity guard that reads the
   compartment and compares it with the declared allowance, run before `tofu apply`, turns "the
   cluster is down and nobody knows why" into "the estate is 250 GB over its allowance, here is
   the list". The estate had a `capacity_cap` precondition once and deleted it (ADR 0034); the
   replacement is a drill that runs on a schedule, not a precondition that blocks a merge.
4. **The drill grades capacity as a lane** (R5): a service whose capacity is over the allowance
   is a service with one fewer home, and the board must say so.

## 8. What this spec does not do

It does not reverse the routing law (the cloud is the default, the laptop is the fallback), it
does not make any provider permanent, and it does not replace the free floor with a paid one.
It does not promise that nothing breaks: it promises that when something breaks, the estate has
at least one other home, that the home is measured rather than believed, and that the ladder is
data — so a new home is a line in a file, not a quarter of work.
