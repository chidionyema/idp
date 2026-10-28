# Incident: the estate's router lost every model while a healthy local router sat unused (2026-10-28)

## Timeline (UTC)

| when | what |
|---|---|
| 2026-10-27 ~12:00 | The estate's cloud route stops answering. `https://llm.mumchimp.com/v1/chat/completions` answers **HTTP 503** with the edge's own "Starting up" page (nginx/1.27.5). `/health/liveliness` still answers **200**, so health checks said the cloud was fine. |
| 2026-10-27 12:00 → 2026-10-28 04:00 | The laptop's front (`:4000`) relays that 503, and then **504 after ~62 s**. The laptop's own LiteLLM slot (`:4001`) answers a real `POST /v1/chat/completions` with **HTTP 200 in 5.5 s** the whole time. Every model call from the estate's agents and surfaces dies while a working router sits on the same machine. |
| 2026-10-28 01:20 | Hypothesis race (`hypotheses.race`, artifacts `/tmp/hypotheses.json`, `~/.estate/logs/hypotheses-race.jsonl`): **H2 wins** — the cloud has no ready endpoint. Posterior **0.997030** (`docs/diagnoses/2026-10-28-the-laptop-lost-every-model.yaml`). |
| 2026-10-28 02:00 | The Greenlane's own tick dies: `UnicodeDecodeError: 'utf-8' codec can't decode byte 0xb0 in position 6` in `greenlane/github.py:_git_text` — the image lane's diff carries a GIF. **One binary file killed every lane in the estate**, and the fix could not land, because the tick that judges a candidate runs main's engine, and main's engine was the crashing one. |
| 2026-10-28 02:30 | Independently: pytest **9.2.0** (published 2026-10-27) removed `FixtureManager._arg2fixturedefs`, which pytest-bdd reads. With an open upper bound in `sovereign/requirements-dev.txt`, every CI run resolved to 9.2.0 and **every scenario in `sovereign/tests/bdd` died** — "85 failed, 104 passed, 1 xfailed" on a candidate that changed nothing but an image tag. The `bdd` gate was red for **every** candidate in the estate. |
| 2026-10-28 04:41 | The landing path comes back: batch `b4408` (the pytest pin and the binary-safe tick) **landed** on main (`7152f30e0e`), so the estate can land again. |
| 2026-10-28 04:44 | The cluster's own recovery path is dead too: `tofu apply` answers `(400, LimitExceeded, false) You cannot create a volume because you have reached your limit` for the break-glass bridge, and `LimitExceeded: nodes-per-node-pool limit has been exceeded` on the worker pool's **UpdateNodePool**. |
| 2026-10-28 05:00 | The second cause of that refusal is found and is not a quota at all: the pool has held **two** nodes since 2026-08-27, when a surge grew it to replace a node that was evicted for low disk. The surge never finished — one node kept serving, the other never came up and its instance has been **STOPPED** ever since. OKE will not shrink a pool with an update, so the pool stayed at two, the free tier's one-node allowance was spent, and every apply was refused. |
| 2026-10-28 05:00 | The fix lands on the laptop and answers: `POST http://127.0.0.1:4000/v1/chat/completions` → **HTTP 200 in 8.50 s, 4.66 s, 4.51 s**, while the log records `front: the cloud failed to answer; the laptop answers for 60s` and the cloud pass-over doubling 60 → 120 → 240 s. |

## First failure, stated exactly

The first failure was **not** the cloud. The first failure was the estate's own router front:

`platform/llm/front.py` decided where a request went **on connect**. It opened a socket to the cloud, wrote the request, and relayed whatever came back. A cloud that accepts the connection and then answers 503 (or hangs, and is cut off at 62 s) was, to the front, "the cloud" — so the front relayed the failure and never asked the laptop's own slot, which was healthy and 5.5 s away from a 200.

So the estate had a working model route on the machine and lost every model anyway. The cloud outage was real; the front's blindness to it was the first failure, and it is the one that is fixed.

## What the cluster's own last receipt says

The estate writes its cluster state to object storage every 15 minutes. The last receipt is **`state/cluster`, written 2026-10-27T11:00:45Z** — the minute the cloud route stopped answering, and 18 hours before this was written. It is read the way every session reads it (the store, not a console):

```
ok cluster-state at 2026-10-27T11:00:45Z nodes=2 ready=2 pods=320 pods_not_ready=18
flux=364 flux_not_ready=21 deploy_short=8 secret_stale_consumers=8
cpu_used_pct=51 mem_used_pct=72 unschedulable=3
```

It says three things that matter:

- **The cluster was alive.** Two nodes, both Ready, 320 pods running, 51% of the CPU and 72% of the memory in use. It was not out of disk, not out of memory, not a node storm. Any story that says "the cluster ran out of room" is wrong, and the receipt says so.
- **The `llm` namespace was short one replica**: `{"available": 1, "desired": 2, "name": "litellm", "ns": "llm"}` — one LiteLLM pod was running on each node, and one of the two was wanted.
- **The volume limit was already storming the cluster**: 2156 `ProvisioningFailed` events on PersistentVolumeClaims, each reading `New volume creation failed … Http Status Code: 400. Error Code: LimitExceeded` (`agent-workforce-data`, `coroot-data`, and more). The free tier's block-volume allowance was spent, so the CSI could not provision a volume for a claim, so pods that need one stayed `Pending`, so deployments stayed short.

And then the receipt stopped: its writer is a CronJob in the cluster, and it has written nothing since. The cloud's 503 is the same minute. What the router's 503 carries is the edge's own "Starting up" page, which is what the edge answers when it has no ready backend to hand the request to.

## Root causes (four, each measured)

1. **The front had no answer-level failover.** It routed on connect and relayed the failure. It could not answer "the cloud is up but cannot serve" — the exact shape of this outage.
2. **The cloud had no healthy endpoint.** OKE's LiteLLM answers 503 "Starting up" behind the edge — the edge's own page, which means the edge had no ready backend to hand the request to. The cluster's last receipt (above) is from the same minute the route died, and it shows the `llm` namespace one replica short and the volume limit failing 2156 claim provisions. What the edge and the LiteLLM pods were doing in the minutes after that receipt is still unmeasured: the cluster could not be reached to look.
3. **The estate's landing path was dead in two independent ways.** A binary file (a GIF in the image lane's diff) killed the Greenlane's tick, and the tick that judges a candidate runs main's engine — so the fix for the tick could not land through the lane that carried it. On top of that, pytest 9.2.0 made the `bdd` gate red for every candidate in the estate, so nothing could land at all.
4. **The cluster could not repair itself.** OCI refused every volume create with `LimitExceeded` while the compartment held orphaned CSI volumes, and refused a node-pool create with `nodes-per-node-pool limit has been exceeded`.

## Fixes (all on the lane `lane/router-front-answer-failover`)

### 1. The front fails over on the answer (`platform/llm/front.py`)

- The request body is buffered (bounded: `MAX_BODY` 8 MiB) and the **cloud's status line is read before anything is written to the caller**. Over-cap requests still stream; they are just not replayable.
- A cloud **5xx**, a cloud that does not answer within `ANSWER_TIMEOUT` (120 s), or a **403 containing `key_model_access_denied`** is replayed to the next target. Every other **4xx is relayed unchanged** — a bad key is the caller's problem, not a reason to try another lane.
- The cloud is then **passed over** for `CLOUD_DOWN_S` (60 s), doubling on each consecutive failure up to `CLOUD_DOWN_MAX_S` (600 s), and reset by any cloud answer. Route order stays cloud-first: while the cloud is marked down, a healthy laptop slot answers first, then the cloud, then the down slots.
- **Replay framing fidelity**: the raw bytes are replayed, chunked framing included; only `Host` is rewritten for the slot; `Expect: 100-continue` is stripped and answered by the front.
- **A failover must not kill the front**: the cleanup closes the *writer*, never a `StreamReader` (the first version raised `AttributeError: 'StreamReader' object has no attribute 'close'` inside `client_connected_cb`, which killed the front on the first failover). The harness now asserts zero unhandled exceptions in the loop's exception handler; the fix is mutation-verified.
- Cost, accepted and documented in the file's header: replaying a POST after a cloud 5xx can double-charge.

### 2. The Greenlane tick survives any byte (`greenlane/github.py`)

- `_git_text` reads **bytes** and returns `None` for output that is not text; a blob that carries a NUL byte in its first 8000 bytes is binary even when it decodes.
- `_image_candidate` drops a file whose copy (the lane's or main's) is binary: **a binary file is content, not a tag bump**. The image-only gate is not weakened — a candidate that is not image-only is still refused.
- `_run` decodes with `errors="replace"`, because every *other* git command the tick runs printed bytes too, and a tick that dies takes the estate with it.

### 3. The pytest pin (`sovereign/requirements-dev.txt`)

`pytest>=8.0,<9.2` — 9.0.x and 9.1.x kept the attribute pytest-bdd reads, so 9.1.x stays eligible. `sovereign/tests/bdd/test_pytest_bdd_compat.py` guards both halves: the pytest running the suite still hands pytest-bdd its fixture map, and the pin is still in the file.

### 4. A governed door for OCI capacity (`platform/estate/{intents/oci-reclaim.yaml,libexec/oci-reclaim.*}`)

The quota had no door: the estate could list volumes and delete them, but nothing could decide *which* were safe and nothing could do it without a human guessing. The new intent lists every volume with the reason it was kept or chosen, and only deletes a volume that is **AVAILABLE, unattached, `csi-`named, tagged `role=persistent_volume`, older than `--older-than-hours` (24) and not among the `--keep-oldest` (3) oldest** — the oldest are kept because a long-lived PersistentVolume may point at them and that data is not reproducible from the API.

### 5. A door that gives back the node that is not running (`bin/lib/node_prune.py`, `bin/idp-oke-surge-node`)

The pool's refusal was not a quota at all: it held two nodes because a surge from 2026-08-27 never finished, and OKE will not shrink a pool with an update. The rule is deliberately narrow — **exactly one node is running and at least one other node's instance is STOPPED → the stopped ones are deleted, with the size decremented**. A running node is never a candidate; two running nodes (a surge in flight) is the surge door's own case and is refused here. The rule lives in `bin/lib/node_prune.py` as a pure function with eight tests, and the estate's own surge door (`bin/idp-oke-surge-node --finish`) reads the instances, asks that rule, and deletes only what it names — printing the volumes it detaches on the way.

## Live proofs (measured, not asserted)

| claim | measurement |
|---|---|
| The front answers when the cloud cannot | `POST http://127.0.0.1:4000/v1/chat/completions` (model `fast`) → **HTTP 200 in 8.50 s / 4.66 s / 4.51 s**; `GET /v1/models` → **200 in 1.43 s** |
| The front knows the cloud is down | log: `front: the cloud failed to answer; the laptop answers for 60s`; the pass-over counter climbs 1 → 60 s, 2 → 120 s, 3 → 240 s |
| The front survives a failover | **0** `Unhandled exception in client_connected_cb` lines since the restart |
| The reclaim door works | plan: `ok oci-reclaim 11 volume(s) reclaimable, 550GB; 3 kept, 150GB`; apply: **6 volumes deleted, 300 GB freed**; the compartment went from 14 volumes / 700 GB to 10 / 600 GB |
| The list is not the truth about attachment | `oci bv volume list` reports `volume-attachments: null` for volumes the delete API refuses with `Volume ... may not be deleted while attached to an Instance.` — the door treats that refusal as a **keep**, so data in use is never deleted |
| The tick survives the binary | greenlane run `40621641312`: `batch b4388: flux/image-updates red`, `batch b4389: ... candidate 76b9fc7d83f9`, `landed_total=718` — no `UnicodeDecodeError` |

## Policy: the free floor was not reversed

The laptop's Ollama lane stays off. `origin/main:llm/config.base.yaml` removed the local ollama rows on purpose (PR #7238) and the zero-cost lane lives in the cluster (`platform/llm/ollama.yaml`), where the cloud's budget, not the laptop's, decides. The estate's own router is the fallback when OKE is unavailable, and the cloud stays the default route (PR #7247). This incident did not change that; it made the fallback real by making the front able to *use* it.

## Also true, and worth recording

- **The memory door is down.** `brief` / `recall` / `remember` answer **HTTP 500**. Durable facts were written to the estate's graph instead (`growmos remember`, node `system/router-free-floor`).
- **A key was printed.** An early verbose `curl` printed the bearer key into executor job `exec-1793145375-4694`. It is printed nowhere else and no verbose curl has run since; the key is to be rotated through the vault.
- **The estate's fact store was broken and is fixed.** The tree-relative intent-count fact was retired and re-added tree-independent (`d401e112f551`); the store now reports `12/12 active facts re-executed (34 retired). verdict: PASS`.

## What is still open, with the exact refusal

The cloud route (OKE) is **not** back yet, and the reason is capacity, not code:

```
(400, LimitExceeded, false) You cannot create a volume because you have reached your limit.
Upgrade to a paid account.
Error: 400-LimitExceeded, LimitExceeded: nodes-per-node-pool limit has been exceeded.
```

Measured facts behind those two lines:

- The compartment holds **10 block volumes / 600 GB** (8 CSI volumes of 50 GB + 2 boot volumes of 100 GB) against the estate's own note that block storage is **200 GB Always Free** (`platform/oci/main.tf`, crew#516 CP4). The 6 volumes the reclaim door deleted (300 GB) were the only provably orphaned ones; the 7 that remain are attached to live nodes and carry PersistentVolume data.
- The **limits API answers `NotAuthorizedOrNotFound`** for every limit name under both `blockstorage` and `compute` with the tenancy OCID, so the numeric allowance could not be read; the shape above is inferred from the estate's own documentation and the refusals, not measured.
- The worker pool's live pool carries **two** nodes — one serving since 2026-08-27, one stopped since the same day — while the free tier's allowance is one, and OKE refuses to shrink a pool with an update: `Error: 400-LimitExceeded, LimitExceeded: nodes-per-node-pool limit has been exceeded.` (Operation Name: `UpdateNodePool`). The stopped node is the surge that never came up; it serves nothing, and the door in fix 5 gives it back.
- The cluster's public API endpoint is closed on purpose: the endpoint NSG `cp-tiafzl` has **no ingress rules** and the control-plane subnet's security list admits only `10.0.128.0/27` on `30562/30537/30198`. The Mac's road is `control_plane_allowed_cidrs` (the Actions variable holds `"81.102.90.209/32","0.0.0.0/0"`), and the break-glass bridge — the runner's road — is `TERMINATED`, three times, because its boot volume is one of the volumes the free tier refuses.

The next moves are now the estate's own, in this order: the surge door gives back the stopped node (fix 5), which frees the node the free tier counts and the 100 GB boot volume the bridge's create needs; the next `oke-check mode=apply` then creates the bridge, and the runner gets its road to the control plane at last. What the LiteLLM deployment is doing behind that 503 is still unmeasured — no kube path existed while this was written, and a measurement is not a guess. If the bridge's create is still refused after the prune, the shape of the limit is count, not storage (10 volumes now), and shedding the eight CSI volumes that carry PersistentVolume data is the founder's call, not an agent's.

## The ladder this should have had — and the drill that keeps it honest

The founder, on the day of this incident: *"we attempted to do something like this for otto, always
available so we need to formalist this for all critical services multi cross platform fallback so
our estate can never go down like this again"*, and *"and lastly recurring drill that verifies these
critical lanes"*. Both are now law and code: [0037](../../docs/decisions/0037-the-fallback-ladder-and-the-drill.md)
and [the spec](../../docs/specs/2026-10-28-the-fallback-ladder-and-the-drill.md).

**What the router had on 2026-10-28: two homes, and one of them was a laptop.** The cloud (OKE
LiteLLM) was down. The laptop's slot was up and answering. The front relayed the cloud's failure
anyway (the defect fix 1 repaired). The estate's third home — Otto's Cloudflare edge, the "always
available" one — was **down as well and had been**: `bin/idp-otto-homes` at 10:46Z measured
`2 cloudflare lifeboat-llm.mumchimp.com MEASURED_FAIL no answer from
https://lifeboat-llm.mumchimp.com/health (URLError)`, and `dig +short lifeboat-llm.mumchimp.com`
prints **nothing** — the name does not resolve. So the design existed in
`platform/otto-gateway/three-homes.yaml` and `docs/explanation/otto-survival-matrix.md`, and the
practice was one cluster and one laptop.

**The drill that measures the lanes** — `bin/idp-estate-homes`, the ladder as data in
`platform/ladder/critical-lanes.json`, on a schedule
(`.github/workflows/estate-homes-drill.yml`). Its first run, 2026-10-28T10:53Z, with
`--no-file`:

```
llm-router
  MEASURED_FAIL cloud (OKE LiteLLM)                oracle-oke     no answer: timed out after 10s
  MEASURED_FAIL lifeboat (Cloudflare edge)         cloudflare     no answer: [Errno 8] nodename nor servname provided, or not known
  UNKNOWN       groq free tier                     groq           a secret this lane needs is not in this environment
  MEASURED_OK   laptop front                       laptop         HTTP 200
otto
  MEASURED_FAIL cluster (otto-gateway)             oracle-oke     HTTP 404 (expected 200)
  MEASURED_FAIL lifeboat (Cloudflare edge)         cloudflare     no answer: [Errno 8] nodename nor servname provided, or not known
  UNKNOWN       groq free tier                     groq           a secret this lane needs is not in this environment
estate-doors
  MEASURED_OK   auth, catalogue, hc, langfuse, signoz, superset   HTTP 200
  MEASURED_OK   api, mcp, cyrus, otto             HTTP 404 (the door answers; the path is not the one)
  MEASURED_OK   www                                HTTP 308
  MEASURED_OK   sandbox                            HTTP 500 (a door that answers and is broken)
  MEASURED_FAIL meridian                           no answer: timed out after 10s

14 of 22 lane(s) answered; 6 down, 2 unknown
```

Two things in that table are the point of the drill. **The estate's doors survived its router** —
14 of 15 published hostnames answered while LiteLLM was down, because DNS and the edge are
cross-provider and the brains behind them are not. And **the drill caught its own wrong
measurement**: the `acg` lane does not resolve because that host is not published, and a lane in
the config that names a host the estate does not serve is a wrong measurement, not a dead one.

The cross-platform homes, and what each one costs, are in
[the analysis](../../docs/analysis/2026-10-28-the-critical-spines-and-their-fallbacks.md): the
Cloudflare edge (anycast, Workers AI in-process with no key and no account id — but its name
does not resolve today, and the `workers.dev` subdomain is the road when the zone is not in the
estate's Cloudflare account), a second vendor's free tier (Groq: 1,000 requests/day, a floor and
never the first try, and a probe that must carry a user-agent or Cloudflare's fingerprint
rejection grades a working vendor dead), and the laptop (which measured 16 output tokens in
24–46 s when it was a home, and is a fallback, never the only one).

## Capacity: the blindness, and the three over-asks

The founder, on the same day: *"the router failing because of casopacity is a disaster and should
never have happend, we ate blind to the capacity issue and should be proactive rather than
reactive"*. The estate's own numbers, measured:

| asked for | allowed | the gap |
|---|---|---|
| 14 block volumes / 700 GB | 200 GB Always Free (`platform/oci/main.tf`) | **+500 GB over**; nine of the volumes were dead (TERMINATED) and still held 450 GB — a deleted volume becomes TERMINATED, not gone, so reclaiming orphans freed nothing |
| 2 A1 nodes in pool `a1` | 1 node | OKE: `400-LimitExceeded, LimitExceeded: nodes-per-node-pool limit has been exceeded.` |
| LiteLLM `replicas: 2` with a `DoNotSchedule` spread on `kubernetes.io/hostname` | 1 node to schedule on | the second replica can never be scheduled → `available=1 desired=2` → the edge answers 503 while the deployment looks healthy |

The three fixes, in order: reclaim the dead as dead (done — the door's rule, 450 GB released);
ask the free tier for what it gives (one A1 node, `--nodes=1:1`, one LiteLLM replica or a
`ScheduleAnyway` spread); and **measure capacity before the apply, not after the refusal** — a
capacity guard that reads the compartment and the pools and compares them with one declared
allowance, on the drill's schedule. The estate had a `capacity_cap` tofu precondition once and
deleted it ([0034](../../docs/decisions/0034-workloads-are-placed-by-the-free-tier-not-by-the-cluster.md));
a precondition that blocks a merge is the wrong shape, and a scheduled drill that says "the
estate is 250 GB over its allowance, here is the list" is the right one.

## The storage waste: 1 GiB of data, 50 GB of volume

The founder, on the same day: *"given we are on free tier and don't want to pay we can't afford
to be lax about what's eating up resources"*. Measured, not assumed:

- **Every CSI block volume in the compartment is 50 GB.** The estate's own manifests declare
  `1Gi` (`platform/jit/deployment.yaml`, `platform/commerce/data/redis.yaml`), `2Gi`
  (`platform/ns-fences/*.yaml`), `5Gi` (`platform/llm/ollama.yaml`,
  `platform/agent-workforce/cronjob.yaml`, `platform/hermes-agent/gateway.yaml`,
  `platform/monitoring/kube-prometheus-stack.yaml`) and `20Gi`
  (`platform/cortex/statefulset.yaml`, `platform/ns-fences/commerce.yaml`). **OCI block
  volumes have a 50 GB minimum**, so every one of those claims is provisioned as 50 GB. We are
  not storing 250 GB of data; we are **buying** 250 GB of provisioned capacity to hold a few
  gigabytes. The waste is the provisioning, not the data.
- **The volume metadata is empty.** `oci bv volume get` on the five live volumes returns no
  tags and no metadata, so OCI cannot name the workload that owns a volume. The cluster is the
  only source of truth for that mapping, and the cluster is unreachable (below). The join key
  is the `csi-…` name.
- **The corpses are not the problem; deleting them is a no-op.** A replaced PersistentVolume
  leaves its volume TERMINATED — not deleted — and OCI keeps TERMINATED volumes listed. The
  reclaim door deleted seven of them on 2026-10-28 and printed
  `ok oci-reclaim deleted csi-a6d65057-…` for each, and **the compartment did not change**:
  the same fourteen names are listed with the same ages. Deleting a TERMINATED volume is a
  no-op that prints a receipt. The door's rule was wrong, and it is corrected in
  `platform/estate/libexec/oci-reclaim.py`: TERMINATED is *already dead*, not reclaimable.
- **What is actually over the allowance, measured:**
  `== live (AVAILABLE) total: 250 GB across 5 volume(s)` — five volumes, all `ATTACHED/iscsi`
  to the running node, against a **200 GB** Always Free allowance. The nine TERMINATED volumes
  (450 GB) are listed but dead. **We are 50 GB over on live storage, and a surge node needs a
  50 GB boot volume, so the apply needs 50 GB of headroom: live must be at most 150 GB.**
- **Live now:** five attached volumes (250 GB). OCI carries no tag or metadata on them
  (`oci bv volume get` returns none), so the owning workload can only be named by the
  cluster — and the join key is the `csi-…` name.

### What data we do not need

**No estate data needs 50 GB.** The largest real state is `cortex` at 20Gi. Everything else is
either a cache (`redis` 1Gi, `jit` 1Gi — reproducible), an artefact stream (`cronjob` 5Gi,
`hermes` 5Gi — R2 already holds the critical backups), a metrics window
(`kube-prometheus-stack` 5Gi — shorter retention, then R2), or model weights
(`ollama` 5Gi — the free floor lane, and the one that genuinely needs its bytes on disk).

### The plan, so this never eats the tier again

1. **One volume, not five.** Keep exactly one 50 GB block volume for the workload that
   genuinely needs disk (`cortex`). Move `redis`, `jit`, `cronjob`, `hermes` and the
   Prometheus window off block storage — in-memory or `emptyDir` where the data is
   reproducible, R2 where it is not. One volume is 50 GB against a 200 GB allowance; five is
   250 GB against it.
2. **A replaced PV must not leave a corpse.** The CSI storage class must reclaim with
   `Delete`; every lingering 50 GB shell is an outage waiting for a vendor refusal. And the
   reclaim door's rule is corrected: a TERMINATED volume is already dead — deleting it prints
   a receipt and changes nothing — so the door reports it as released, never as reclaimed.
3. **Ask for nothing new.** The apply fails because a **surge node** needs a 50 GB boot volume
   and there is no headroom. The surge is only needed because the pool's shape (4 OCPU /
   24 GB) does not match the **running** node (2 OCPU / 12 GB). Declaring the pool to be what
   the node already is removes the surge, removes the volume, and removes the refusal: the
   free tier decides, and the running node is what the free tier already gives.
4. **The capacity guard gates the apply.** Ask the free tier only for what it gives:
   `--nodes=1:1`, one LiteLLM replica with a `ScheduleAnyway` spread, one node of 2 OCPU /
   12 GB, and live block storage at or under **150 GB** so a 50 GB boot volume can be created
   when it is genuinely needed. The allowance is declared once, in
   `platform/ladder/capacity.json`, and the guard compares the ask with it **before** the
   vendor refuses.
5. **Two of the five attached volumes have to go, and they are the two smallest claims.**
   `redis` (1Gi) and `jit` (1Gi) are caches and scratch — reproducible, and R2 already holds
   the critical data. Releasing them takes live storage from 250 GB to 150 GB and buys the
   headroom the apply needs. That release needs the cluster to name the two volumes, which
   is the measurement below.
6. **Never pay.** The refusal `You cannot create a volume because you have reached your
   limit. Upgrade to a paid account.` is the estate's alarm, not a bill to accept.

**The gap:** the five live volumes' owning workloads are still unnamed, because the cluster
API is unreachable — the bridge instance is TERMINATED and the endpoint NSG (`cp-tiafzl`) has
no ingress rule. The next measurement, the moment the cluster answers, is
`kubectl get pv -o wide` and `kubectl get pvc -A -o wide`, joined on the `csi-…` name. Until
then the door keeps the three oldest volumes and the capacity guard counts them as live: a
guard that counts a corpse as live is a guard that under-reports, and that is why the
allowance is checked against the vendor's own list, not against a manifest.

## Recognition

The MiniMax lane — the lane that carried this recovery — is promoted by the founder to the
estate's **Lead Engineer**: [0038](../../docs/decisions/0038-minimax-is-the-lead-engineer.md),
the note in `AGENTS.md` §7b, and the letter
[to the Lead Engineer](../../docs/letters/2026-10-28-to-the-lead-engineer.md). It is a judgement,
attributed to the founder and recorded as one; the measured record of service is in the same
decision, and it is labelled as measurements.

