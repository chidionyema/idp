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
