# The estate router: a failure-mode map

**Date:** 2026-11-02 - **Scope:** the estate's model router -- the cloud route
`https://llm.mumchimp.com` (the declared default route, founder's ruling 2026-10-26) and the
laptop route `http://127.0.0.1:4000` (the fallback: a byte-forwarding *front* on :4000 and two
LiteLLM *slots* on :4001/:4002).
**Method:** every mode below is graded by evidence class, and the class is named in the table:

| Grade | Meaning |
|---|---|
| **LIVE** | Reproduced on this machine on 2026-11-02; the command is in sec 8. |
| **LOG** | Present in the router's own recorded history (the `lanes.jsonl` census, the front log, the watchdog log). |
| **INCIDENT** | Recorded by the estate in an incident document with a date. |
| **RESEARCH** | Documented upstream (LiteLLM / Cloudflare / provider docs), not observed here. |
| **THEORY** | Structurally possible, no observation. Named so it is not mistaken for a finding. |

A mode with no grade is not in this document. **"All failure modes" is not claimed and cannot be;
this is the comprehensive practical map, and every row says how it would be falsified.**

---

## 1. Executive summary -- the router is one refusal away from answering nobody

Measured on 2026-11-02 between 13:00 and 14:05 UTC:

1. **The cloud route is dead and has been since 2026-10-28.** `https://llm.mumchimp.com/health/liveliness`
   answers **HTTP 530** with Cloudflare's body `error code: 1033` -- "Cloudflare cannot find a
   healthy cloudflared instance to receive the traffic" (Cloudflare, Error 1033). The cause is the
   cluster control plane that vanished on 2026-10-28 (`docs/incidents/2026-10-29-the-cluster-lost-its-control-plane.md`),
   which took the tunnel connector with it. GitHub issue **#7387** is open and still states that
   `llm.mumchimp.com` has no backend.
2. **The laptop route answers, but only when the host is not saturated.** The front refused
   **757** callers with `the box is saturated (load 45.9 > 32.0); refusing` while the cloud was
   down. The refusal is correct behaviour (a box at load 46 on 4 CPUs cannot answer inside its own
   budget) -- the failure is that it was the **only** route left, so the estate had no route at all
   during those refusals.
3. **The twin-slot redundancy is not holding.** At 13:05 UTC slot 4001 answered and 4002 refused
   the connection; at 13:08 UTC `lsof` showed **only** :4002 and the front listening; the watchdog
   log carries **79** `restart: kickstart` lines in its last 3 MB. Each restart is a ~90 s boot
   (LiteLLM's boot time, measured by the estate on 2026-10-02), and the watchdog's cooldown is
   240 s -- so a flapping slot spends much of its life booting.
4. **Rate limiting, not failure, is the dominant current lane cause.** Over the last 24 h: 640
   registry transitions, of which **295 were `rate`** (429) and **280 observed 429s**; `auth` was
   **1**. Over the whole recorded history: 35,178 `ready -> exhausted` transitions and 35,173 of
   them are `rate`.
5. **The estate's own doctor says `BROKEN` about lanes that are running.** `~/.estate/router-doctor.last`
   (13:02:29Z) reports 18 lanes "dropped (key absent at render)" and the whole router BROKEN -- while
   the *running* rendered config (`~/.estate/router-state/config.runtime.yaml`, 29 model entries)
   contains **all 18** of those lanes. The doctor grades a *render*, not the *deployment*.

Two consequences follow, and they are the report's real findings:

- **The router has no degraded mode.** Cloud dead, laptop refusing, doctor blind -- each layer
  fails alone, and the estate's own incident record already names the gap: *"there is no degraded
  mode for router, memory, or keys."*
- **The deployed router is not the repository's router.** The running front is 38,994 bytes with
  the cloud leg, the answer budget, the saturation guard and the slot pass-over; the repository
  copy is 3,466 bytes and has **none** of them, and `main` does not mention `ESTATE_ROUTER_CLOUD`
  at all. A routine `bin/litellm-local install` from `main` would **delete the cloud leg and the
  budget guard** from the machine that is serving the estate.

---

## 2. The map

Each row: what breaks, what it looks like from outside, where the evidence is, how to confirm it,
and what actually fixes it.

### A. Edge and tunnel (Cloudflare in front of `llm.mumchimp.com`)

| ID | Failure mode | Signature | Diagnostic | Mitigation | Grade |
|---|---|---|---|---|---|
| A1 | **Tunnel connector down** -> edge cannot find an origin | `HTTP 530`, body `error code: 1033` | `curl -s -o /dev/null -w '%{http_code}' https://llm.mumchimp.com/health/liveliness` | Bring the connector back (`cloudflared` up, or move the route to a home that survives a cluster outage) | **LIVE** + **RESEARCH** (Cloudflare Error 1033: tunnel "Down" = "the cloudflared process has stopped... the machine is powered off, an application crash") |
| A2 | **Cloudflare Browser Integrity Check blocks the caller's own signature** | `HTTP 403`, body `error code: 1010` | `curl -A 'Python-urllib/3.12' https://llm.mumchimp.com/health/liveliness` | The front already presents one estate signature (`estate-router-front/1.0`) instead of the caller's | **LIVE** + **RESEARCH** (Error 1010: the default Python urllib UA is treated as a non-browser client) |
| A3 | Edge 5xx from the origin (520/521/522/524) | `5xx` with a Cloudflare body | same probe, read the body | Origin health, not edge health | **RESEARCH** (Cloudflare 5xx index) |
| A4 | TLS/cert expiry on the origin behind the tunnel | `525`/`526` | `curl -v` | Renew | **RESEARCH** |
| A5 | Edge-side rate limiting or WAF rule on the estate's own traffic | `429`/`403` from the edge | compare edge headers with provider headers | Rule change | **RESEARCH** |
| A6 | DNS / split-horizon resolution for `llm.mumchimp.com` | resolves to the wrong address; intermittent 530 | `dig +short llm.mumchimp.com` | Fix the record | **THEORY** |
| A7 | The tunnel is connected but points at a **dead origin** (tunnel Healthy, origin gone) | `530`/503 with a healthy tunnel | `cloudflared tunnel list` + origin probe | Repoint the tunnel | **RESEARCH** (the 1033 table distinguishes Healthy / Inactive / Down) |

### B. Cloud origin (the OKE cluster that serves the cloud route)

| ID | Failure mode | Signature | Diagnostic | Mitigation | Grade |
|---|---|---|---|---|---|
| B1 | **Control plane gone** -> the cluster serves nothing | `kmi count is 0`; the API endpoint closed | `cluster-control-plane` intent | Restore/rebuild the control plane | **INCIDENT** (2026-10-28/29 incident doc) + **LIVE** (consequence A1) |
| B2 | **Tunnel connector runs inside the dead cluster** -> the edge loses its origin | `1033` | A1 probe | Move the connector off the cluster, or the route off the cluster | **LIVE** (the route's only origin is the cluster) |
| B3 | **Vendor keys lived only in the cluster** -> 19 lanes lost their credential | lanes "dropped (key absent at render)" | `bin/idp-vendor-render` in a clean worktree | Keys by name from the vault, not from the cluster | **INCIDENT** (19 lanes dropped) |
| B4 | Deployment/rollout stalls, pods unschedulable, node lost | pods not Ready; tunnel flaps | `cluster-health`, `k8s-pods` | Cluster ops | **RESEARCH** (standard) |
| B5 | The cluster is fine but **the cloud route's LiteLLM config drifted** from the fleet's | lanes present but wrong model, 404s | `litellm-router-map` | Re-render from source | **THEORY** (measured 404s: 722 observed) |
| B6 | Cloud cost ceiling stops the route mid-flight | `402` / budget refusal | observe status counts | Budget routing | **LOG** (362 x 402 observed; 17 in the last 24 h) |

### C. The laptop front (`~/.estate/litellm-local/front.py`, the byte-forwarding door on :4000)

The deployed front is 38,994 bytes and carries a long header that already names six incident
classes it was built to fix (boot gap, accepting-but-not-answering, no total budget, cloud-first
ordering, cloud refusal relayed as the answer, caller signature forwarded to the edge). Those
classes are listed here because the code, not just the memory, is the evidence.

| ID | Failure mode | Signature | Diagnostic | Mitigation | Grade |
|---|---|---|---|---|---|
| C1 | **Saturation refusal** -- the host is too loaded to answer inside the budget | `front: the box is saturated (load 45.9 > 32.0); refusing` -> HTTP 503 with `Retry-After: 30` | `uptime`; count `saturated` in `~/Library/Logs/litellm-local.log` | Relieve the host; the guard is correct, the absence of any other route is not | **LIVE** -- 757 refusals in the log |
| C2 | **Budget exhaustion** -- the front held the request past what it could deliver | `504` to the caller; the front's total budget (240 s) is spent across targets | front log; caller-side timeout | Already fixed in the deployed front; **not in the repository copy** | **LOG** (front header, 2026-10-30) + **RESEARCH** (LiteLLM: router `timeout` covers the whole call) |
| C3 | **Cloud-first wait** -- every caller pays the cloud's failure before the laptop is asked | slow answers; the front's own header: "the cloud leg burns up to ANSWER_TIMEOUT before the laptop is asked" | front log `the cloud failed to answer (N in a row)` | Cloud cooldown (deployed front passes a failed cloud over for 60->120->240 s) | **LOG** -- 288 cloud-failure lines |
| C4 | **Cloud in cooldown still ahead of the slots** | every caller handed a known-dead cloud | (fixed in the deployed front: the cloud moves LAST) | Keep the deployed front; do not reinstall from `main` | **INCIDENT** (753 requests handed a dead cloud) |
| C5 | **The edge's refusal relayed as the answer** (403 1010 / `key_model_access_denied`) | caller receives the cloud's 403 as if it were the answer | front log | The deployed front reads the refusal body and asks the next target | **LOG** (front header, 2026-10-30) + **LIVE** (403 confirmed from the raw path) |
| C6 | **The caller's own User-Agent forwarded to the edge** -> 1010 | `403 error code: 1010` | A2 probe | One estate signature -- deployed front only | **LOG** + **LIVE** |
| C7 | **Slot that answers slowly** (accepts, does not answer) | front waits, then passes the slot over | `front: slot 4002 did not answer inside the budget (1 in a row); it is passed over for 60s` | Slot pass-over with doubling (deployed front) | **LIVE** (34 slot lines) |
| C8 | **The front dies** | connection refused on :4000 | `estate_invoke router-status` | launchd keeps it; watchdog restarts a refused front at once | **RESEARCH** (watchdog docstring: "A refused front is restarted at once") |
| C9 | **Front and repository disagree** (deployed != source) | a reinstall silently deletes the cloud leg | `wc -c ~/.estate/litellm-local/front.py platform/llm/front.py`; `git show main:platform/llm/front.py \| grep -c ESTATE_ROUTER_CLOUD` -> **0** | Land the deployed front in the repository before any reinstall | **LIVE** |
| C10 | The front's in-memory state (cooldowns, pass-overs) is lost on restart | a known-dead cloud is tried first again | front restart time vs `the cloud failed to answer` lines | Acceptable, but it must not be the only defence | **THEORY** |

### D. Slots, boot and the watchdog (`platform/llm/watchdog.py`, launchd agents)

| ID | Failure mode | Signature | Diagnostic | Mitigation | Grade |
|---|---|---|---|---|---|
| D1 | **Refused port** (slot process gone) | `probe refused :4001 (n/3)` | `estate_invoke router-status`; `lsof -nP -iTCP -sTCP:LISTEN \| grep 400` | Watchdog restarts after `FAIL_THRESHOLD = 3` | **LIVE** (79 restarts in the watchdog log tail) |
| D2 | **Listening but not answering** -- the classic false failure | `probe <verdict> -- listening, not restarted` | same | Deliberately **not** a failure: "ONLY A REFUSED PORT IS A FAILURE" | **RESEARCH** (watchdog docstring: on 2026-10-02 this rule stopped 12 pointless restarts) |
| D3 | **Storm** -- the host is too loaded for a restart to help | `load 531 >= 20 -- storm, not restarting` | watchdog log | Relieve the load | **LOG** |
| D4 | **90 s boot gap** on every slot restart | callers see "Connection error" for ~90 s | watchdog log timestamps (2026-10-02 17:03-17:05, 17:12-17:14) | Boot the new router in the idle slot and switch only when it answers (`bin/litellm-local swap`) | **INCIDENT** (founder: "i dont want to see any more failures") |
| D5 | **Cooldown blocks the restart that is needed** | `threshold hit but cooldown active (n s < 240 s)` | watchdog log | `COOLDOWN_SECS = 240` is deliberate (a start under load takes longer) | **LOG** |
| D6 | **launchd unload/bootout race** | `Bootstrap failed: 5: Input/output error` | `bin/litellm-local` log | The script waits for the unload | **RESEARCH** (measured 2026-09-26) |
| D7 | **macOS TCC blocks launchd from reading `~/Documents`** | the slot cannot read the rendered config or the vault | `bin/litellm-local` stages into `~/.estate/litellm-local/` | Staging exists for this reason | **RESEARCH** (script docstring) |
| D8 | **A slot exits on every start** (config unwritable, venv missing) | slot never appears; `front: no router slot answers` | launchd log | The script writes its rendered config before launch | **RESEARCH** (script: "a router that cannot write its rendered config exits on every restart and never comes back") |
| D9 | **Only one slot listening** -> no twin fallback | one of :4001/:4002 absent from `lsof` | `lsof -nP -iTCP -sTCP:LISTEN \| grep -E ':400[0-2]'` | Keep both slots up; the flapping is D1/D4 | **LIVE** (13:05 one way, 13:08 the other) |
| D10 | **The laptop sleeps / the user closes it** | the only remaining route disappears | `pmset -g log` | The cloud route must exist for this to be survivable -- which is why B2 is P0 | **INCIDENT** + **THEORY** |

### E. Router configuration and LiteLLM semantics (`llm/config.yaml`, `platform/llm/lane_registry.py`, `platform/llm/route_table.py`)

| ID | Failure mode | Signature | Diagnostic | Mitigation | Grade |
|---|---|---|---|---|---|
| E1 | **Lane dropped at render because its key is absent** | doctor: `dropped (key absent at render)` | `bin/idp-vendor-render` in a clean worktree | Keys by name from the vault | **LIVE** (doctor) -- but see E2: the running config has them |
| E2 | **The doctor grades a render, not the deployment** -> false BROKEN | doctor BROKEN while :4000 answers 200 and the runtime config holds all lanes | compare `~/.estate/router-state/config.runtime.yaml` `model_list` with the doctor's dropped list | Make the doctor compare against the *running* config | **LIVE** |
| E3 | **Cooldown is blind to cause** -- a deployment is cooled down for any failure | `ready -> exhausted` then `exhausted -> ready` churn | census transitions | LiteLLM's own `allowed_fails`/`cooldown_time`; the estate's own note: "cooldown is blind to why a deployment failed and only watches whether it answers" | **LOG** (99,706 transitions) + **RESEARCH** (LiteLLM router settings) |
| E4 | **A lane is `ready` while its last observation was a 429** | `state=ready, status=429` in `~/.estate/router/lanes.json` | read the file | The label lags the observation by `allowed_fails` (3) | **LIVE** (2 lanes) |
| E5 | **Fallback only after `num_retries`** -- the first failure is the caller's error | caller sees the provider's error, not the fallback's answer | LiteLLM docs | `num_retries` and `fallbacks` in the rendered config | **RESEARCH** (LiteLLM: "If a call fails after num_retries, it falls back to another model group") |
| E6 | **A fallback target skipped from the cooldown check** | a known-dead lane is tried anyway | LiteLLM docs | Model-specific fallback by `model_info.id` skips cooldown by design | **RESEARCH** (LiteLLM) |
| E7 | **Timeout covers the whole call; `stream_timeout` covers the first chunk** | a hung provider holds the caller for the full timeout | LiteLLM docs | Set `timeout` and `stream_timeout` per lane | **RESEARCH** (LiteLLM Timeouts) |
| E8 | **`/health` probes every model on every call** when background checks are off | each health read costs tokens on every deployment | `GET /health` | `background_health_checks: true`, `health_check_interval: 300` | **RESEARCH** (LiteLLM Health) |
| E9 | **Every worker/pod keeps its own health cache** | two slots disagree about the same lane | LiteLLM docs | One shared store (Redis) for cross-instance state | **RESEARCH** (LiteLLM: "Each proxy worker, and each pod, runs its own background loop and keeps its own cache") |
| E10 | **Rate-limit state is per instance** unless Redis is configured | two slots both spend the same quota | LiteLLM docs | `router_settings.optional_pre_call_checks` + Redis | **RESEARCH** (LiteLLM Load balancing) |
| E11 | **Daily quota (RPD/TPD) exhaustion** | 429 with a reset time; `exhausted` state | registry | LiteLLM retries another deployment in the group, then the group's fallbacks | **LOG** (35,173 rate transitions) + **RESEARCH** |
| E12 | **`max_budget` cannot trip** on a lane that bills $0 | silent overspend | `llm/config.yaml` comments (the 2026-08-27 fix) | Price per character, not per token | **LOG** (config comment) |
| E13 | **Route-table alias points at a lane that no longer exists** | 404 on the alias | `litellm-router-map` | Recompile the table | **LOG** (722 x 404 observed) |
| E14 | **Config drift between the repository and the deployed render** | a redeploy changes behaviour silently | `git diff` of the rendered config against the repo's | Render-and-diff in the gate | **LIVE** (E9/C9) |

### F. The lane registry (`platform/llm/lane_registry.py`, `~/.estate/router/lanes.jsonl`)

| ID | Failure mode | Signature | Diagnostic | Mitigation | Grade |
|---|---|---|---|---|---|
| F1 | **`dead:auth`** -- credential revoked/expired | 401/403 -> `dead:auth` | census | Re-key; `exhausted -> dead:auth` happened **11,600** times | **LOG** (4,591 `ready -> dead:auth`; 11,600 `exhausted -> dead:auth`) |
| F2 | **`dead:credit`** -- account out of balance | 402 -> `dead:credit` | census | Top up; 128 `ready -> dead:credit` | **LOG** |
| F3 | **`exhausted:rate`** -- 429 with a reset time | 429 -> `exhausted:rate` | census | Quota forecast and routing around it | **LOG** (35,173) |
| F4 | **`degraded:error` / `degraded:server` / `degraded:timeout`** | 5xx / timeout | census | Retry/fallback | **LOG** (863 + 369 + 43 `ready -> degraded`) |
| F5 | **Probe traffic exceeds real traffic** | probes 351,831 vs observes 335,235 over the window | census | Every probe is a billable call | **LOG** |
| F6 | **A dead lane is reprobed forever** | `dead` lanes probed every 10 min | census | The registry's documented cadence | **LOG** + **INCIDENT** (`docs/diagnoses/2026-10-12-router-reprobes-condemned-lanes.yaml`) |
| F7 | **`load-purge` / `load-heal`** -- the registry's state is dropped and rebuilt under load | 172 purges, 5 heals | census | Load shedding resets the learning | **LOG** |
| F8 | **Unbounded state growth** | `lanes.jsonl` = 110,110,729 bytes | `ls -la ~/.estate/router/` | Rotate and compact; the file is read by the census and by every doctor run | **LIVE** |
| F9 | **Dead-group substitution becomes the normal path** | 9,112 substitutions, all `why = dead group` | `substitutions.jsonl` | deepseek->minimax 2,339; groq->default 2,057; deepseek-v4-flash->default 1,967; groq->openrouter 318; voice->default 163 | **LOG** |
| F10 | **A lane marked ready whose last observation was an error** | E4 | `lanes.json` | -- | **LIVE** |
| F11 | **Timestamps that do not resolve** (clock skew) | a record dated 2024-01-01 | scan `lanes.jsonl` for `t < 1.6e9` | -- | **NOT REPRODUCIBLE** on 2026-11-02: 0 skewed timestamps in the last 30 MB; oldest `since` = 2026-10-02T13:55:18Z. Reported here as *checked and not found*, not as a finding. |

### G. Upstream providers

| ID | Failure mode | Signature | Diagnostic | Mitigation | Grade |
|---|---|---|---|---|---|
| G1 | **429 rate limit** (per-minute / per-day / tier) | 429 + `retry-after` | registry | Forecast and route around it | **LOG** (19,563 observed) + **RESEARCH** (Groq: 429 with `retry-after`, RPD/TPM headers) |
| G2 | **529 overloaded_error** | 529 | registry | Retry with backoff | **LOG** (28 observed) + **RESEARCH** (Anthropic 529) |
| G3 | **500 api_error** | 500 | registry | Backoff and retry | **LOG** (7,587 observed) |
| G4 | **502 / 504 gateway errors and timeouts** | 502, 504, 408 | registry | Retry; `stream_timeout` for hung streams | **LOG** (25 / 1 / 1,636) |
| G5 | **402 billing_error / credit exhausted** | 402 | registry | Fund the account | **LOG** (362) + **RESEARCH** (Anthropic 402) |
| G6 | **401 authentication_error** (malformed, revoked, expired key) | 401 | registry | Re-key | **LOG** (569) + **RESEARCH** (Anthropic 401) |
| G7 | **403 permission_error** | 403 | registry | Grant the scope | **LOG** (1 in the window) + **RESEARCH** |
| G8 | **404 not_found** (wrong model id / endpoint) | 404 | registry | Fix the alias | **LOG** (722) + **RESEARCH** |
| G9 | **413 request_too_large** | 413 | registry | Split the request | **RESEARCH** (Anthropic 413) |
| G10 | **409 conflict_error** | 409 | registry | Retry | **RESEARCH** (Anthropic 409) |
| G11 | **Slow tail** -- the provider answers, but minutes later | `latency_ms_p95` in the hundreds of seconds | registry percentiles | The caller's patience is the ceiling | **LOG**: `openai/MiniMax-M3` max **4,400,588 ms (73.3 min)**, p99 165,093 ms; `openai/nvidia/nemotron-3.5-lightning-30b-a3b` max 2,254,352 ms; `deepseek/deepseek-v4-flash` max 1,843,440 ms; `anthropic/claude-opus-5-5` max 799,186 ms, p99 97,703 ms; `anthropic/claude-sonnet-5` max 761,967 ms |
| G12 | **A tier spend-cap 429 with no `retry-after`** | 429 that never clears | registry | Recognise it; it is not a rate limit to wait out | **RESEARCH** (Anthropic: "A tier spend-cap 429 has no retry-after header and keeps failing until access resumes") |
| G13 | **An SSE stream fails after a 200** | the client sees a broken stream, not an HTTP error | caller transcript | Retry the request, not the stream | **RESEARCH** (Anthropic: error events on SSE arrive after a 200) |
| G14 | **The provider's SDK retries underneath the router** | retries the estate did not author | request log | Know that the router's `num_retries` is not the only retry | **RESEARCH** (Anthropic SDK: "retries transient failures... twice by default, honoring the retry-after header") |

### H. The host (the laptop is the fallback route, so its health is the estate's health)

| ID | Failure mode | Signature | Diagnostic | Mitigation | Grade |
|---|---|---|---|---|---|
| H1 | **Runaway load** | load 45.9 -> 701 (2026-10-30) against `LOAD_MAX = 8 x cpus = 32` | `uptime` | The front refuses (correct); relieve the load | **LIVE** |
| H2 | **Disk exhaustion** | the executor door refused a job: "the volume has 1288 MB free, under this door's 1500 MB floor" | `df -k /System/Volumes/Data` | `estate_invoke disk-cleanup` -- on 2026-11-02 it reclaimed **6 MB** and could not reclaim more: every candidate is on the keep-list | **LIVE** |
| H3 | **Worktree sprawl** -- 35+ agent worktrees at ~290 MB each | `git worktree list` | same | The cleaner keeps every claimed/dirty/in-use one | **LIVE** (861 M in `~/Documents/code/idp-worktrees`) |
| H4 | **The router's own state file is a disk consumer** | `lanes.jsonl` 110 MB and growing | `ls -la ~/.estate/router/` | Rotate | **LIVE** |
| H5 | **Sleep / lid closed** | both slots stop answering | `pmset -g log` | The cloud route must exist | **THEORY** |
| H6 | **Network path change / VPN / DNS change** | the cloud route fails while the laptop is fine | probes | -- | **THEORY** |
| H7 | **Thermal or CPU contention from other estate work** | latency percentiles climb | registry | Budgeted concurrency | **LOG** (G11) |

### I. The caller contract

| ID | Failure mode | Signature | Diagnostic | Mitigation | Grade |
|---|---|---|---|---|---|
| I1 | **Caller patience is shorter than the front's budget** | the front answered after the caller left | the front's own measurement: 21 "Request timed out" events in the founder's seven sessions, the gap landing in a 361.3-374.4 s band; the front's budget is 240 s | The front's budget (240 s) is under the patience (364 s) | **INCIDENT** (2026-10-30 session audit) |
| I2 | **The caller asks for a model the route cannot serve** (the cloud has no Claude lane -- the founder's subscription is local) | the cloud answers a refusal naming the model | the front reads the refusal and moves on | Keep Claude Code on the founder's own login | **INCIDENT** (`docs/diagnoses/2026-10-22-claude-code-403-cloud-has-no-claude-lane.yaml`) + **LOG** (front header) |
| I3 | **A client that streams** and dies mid-stream | truncated response | caller transcript | -- | **RESEARCH** (G13) |
| I4 | **The caller retries into a saturated box** | more refusals | front log | The `Retry-After: 30` is the contract | **LIVE** |
| I5 | **A client that cannot follow a redirect or uses a proxy UA** | 403 1010 | A2 probe | One estate signature | **LIVE** |

### J. The estate's own gates and observability

| ID | Failure mode | Signature | Diagnostic | Mitigation | Grade |
|---|---|---|---|---|---|
| J1 | **A gate that fails on a render, not on reality** | doctor BROKEN while the router answers 200 | doctor vs `config.runtime.yaml` | Grade the deployment | **LIVE** |
| J2 | **No degraded mode** for router, memory or keys | the estate incident record, 2026-10-29 | the incident doc | Build one | **INCIDENT** |
| J3 | **The router's history is a 110 MB append-only file** with no rotation | `lanes.jsonl` | `ls -la` | Rotate + compact | **LIVE** |
| J4 | **A "fix" that lives only on the machine** | deployed front 38,994 B vs repo 3,466 B | `wc -c` both | The repository is the source of truth, or the deployment is | **LIVE** |
| J5 | **The census itself must be re-run to see the truth** -- no dashboard | -- | the census script | Publish the census as a scheduled artefact | **LIVE** |

---

## 3. What a caller actually experienced, reconstructed

On 2026-11-02, a request to `http://127.0.0.1:4000` met this chain:

1. The front computed its route. The cloud had failed repeatedly (288 cloud-failure lines: "the cloud
   failed to answer (N in a row); the laptop answers for 60s/120s/240s"), so the cloud was passed
   over -- *if* the running front was the one with that logic (it is; the repository copy is not).
2. If the host's load was above 32, the front **refused before trying anything**:
   `the box is saturated (load 45.9 > 32.0); refusing` -> HTTP 503 + `Retry-After: 30`. 757 such
   refusals are in the log.
3. If the load was below 32, the front asked the live slot. Often only one slot was listening
   (4001 at 13:05, 4002 at 13:08) -- the twin was mid-restart, and a restart costs ~90 s of boot
   behind a 240 s cooldown.
4. The slot routed to a provider lane that was mostly **rate-limited**: 280 of the 640 transitions
   in the last 24 h were 429s. The registry then substituted a different lane -- 291 dead-group
   substitutions in the same 24 h (`deepseek-v4-flash -> default` 242 times) -- so the answer came
   from a *different model* than the caller asked for, silently.
5. If the lane answered slowly (the measured tail runs to 73 minutes), the front's 240 s budget
   fired and the caller got a 504 -- or the caller had already given up at 364 s.

So the estate's "one route, always" is false on three independent axes at once: the default route
is dead, the fallback route refuses under load, and the fallback's lanes are mostly rate-limited
into silent substitution.

---

## 4. The census (what the router's own history says)

Window: the whole of `~/.estate/router/lanes.jsonl` (110,110,729 bytes, **786,949** rows).

| Event | Count |
|---|---|
| probe | 351,831 |
| observe | 335,235 |
| transition | 99,706 |
| load-purge | 172 |
| load-heal | 5 |

**Observed statuses** (from real calls): 429 -> 19,563 - 500 -> 7,587 - 400 -> 2,568 - 408 -> 1,636 -
404 -> 722 - 401 -> 569 - 402 -> 362 - 503 -> 42 - 529 -> 28 - 502 -> 25 - 504 -> 1 - 403 -> 1.

**Transitions** (state -> state, with the cause):

| From -> to | Total | By cause |
|---|---|---|
| ready -> exhausted | 35,178 | rate 35,173 - headroom 5 |
| exhausted -> ready | 28,370 | -- |
| dead -> ready | 11,502 | -- |
| exhausted -> dead | 11,627 | **auth 11,600** - credit 27 |
| ready -> dead | 4,719 | **auth 4,591** - credit 128 |
| ready -> degraded | 1,275 | error 863 - server 369 - timeout 43 |
| dead -> exhausted | 4,825 | rate 4,825 |
| degraded -> ready | 1,167 | -- |
| degraded -> dead | 145 | auth 135 - credit 10 |
| degraded -> degraded | 424 | error 198 - server 204 - timeout 22 |

**Dead events by lane** (the lanes that died most): `openai/gpt-oss-120b` 16,457 -
`gemini/gemini-3.5-flash` 22 - `anthropic/claude-sonnet-5-5` 17 - `deepseek/deepseek-chat` 16 -
`anthropic/claude-haiku-4-5` 5 - `deepseek/deepseek-v4-flash` 5 - `anthropic/claude-opus-5-5` 3.

**Substitutions** (`substitutions.jsonl`): **9,112** rows, every one `why = dead group` --
`deepseek -> minimax` 2,339 - `groq -> default` 2,057 - `deepseek-v4-flash -> default` 1,967 -
`deepseek -> default` 1,299 - `glm -> default` 435 - `groq -> openrouter` 318 - `voice-tts -> default` 253 -
`voice -> default` 163 - `gemini -> default` 46 - `cerebras -> default` 20.

**Live lane state at 14:00 UTC** (13 lanes): `ready` 9 - `dead` 2 - `degraded` 1 - `exhausted` 1.
`gemini/gemini-3.5-flash` is `exhausted` (reason `rate`); `groq/whisper-large-v3-turbo` is
`degraded` (reason `error`); `openai/gpt-oss-120b` is `ready` while its last observation was a
**429**; `openai/MiniMax-M3` is `ready` with a p95 of **333,362 ms**.

**Last 24 h** (measured separately, same files): 640 transitions -- rate 295, server 17, credit 13,
auth 1; observed 429 -> 280, 500 -> 26, 402 -> 17, 400 -> 6, 408 -> 3, 502 -> 2, 401 -> 1, 403 -> 1;
291 dead-group substitutions (`deepseek-v4-flash -> default` 242, `groq -> openrouter` 44,
`deepseek -> minimax` 3, `minimax_m27 -> default` 2).

---

## 5. Research findings (external, cited)

| Source | What it establishes for this estate |
|---|---|
| LiteLLM -- *Fallbacks (Provider Failover)*, `https://docs.litellm.ai/docs/proxy/reliability` | "If a call fails after `num_retries`, it falls back to another model group"; `router_settings.allowed_fails: 3` "cooldown a deployment once it fails more than 3 calls within `cooldown_time`"; `cooldown_time: 30`; a fallback to a specific `model_info.id` "skips any cooldown check". Maps directly onto E3-E6. |
| LiteLLM -- *Health checks*, `https://docs.litellm.ai/docs/proxy/health` | Without `background_health_checks`, "every call sends a real test request to each of those deployments, so it costs a few tokens per deployment"; `health_check_interval` default 300; "**Each proxy worker, and each pod, runs its own background loop and keeps its own cache**" -- the estate runs two slots, so they disagree (E9). |
| LiteLLM -- *Timeouts*, `https://docs.litellm.ai/docs/proxy/timeout` | The router `timeout` covers the whole call and is passed to `completion()`; `stream_timeout` bounds the wait for the first chunk ("to abort 'hanging' providers"); pass-through routes have their own precedence. Maps onto E7, G4, G13. |
| LiteLLM -- *Load balancing*, `https://docs.litellm.ai/docs/proxy/load_balancing` | Per-deployment `rpm`/`tpm`; a spent daily quota "falls over to the other deployments in its group until the next reset"; **for multiple proxy instances, add Redis to share rate limit state** -- the estate's two slots do not share it (E10). |
| Cloudflare -- *Error 1033*, `https://developers.cloudflare.com/support/troubleshooting/http-status-codes/cloudflare-1xxx-errors/error-1033/` | "Your tunnel is not connected to Cloudflare's network because Cloudflare's network cannot find a healthy cloudflared instance"; statuses Healthy / Inactive / **Down** ("the cloudflared process has stopped... the machine is powered off, an application crash"). This is exactly the estate's live A1/B2. |
| Cloudflare -- *Error 1010*, `https://developers.cloudflare.com/support/troubleshooting/http-status-codes/cloudflare-1xxx-errors/error-1010/` | "The owner of this website has banned your access based on your browser's signature"; the default **Python urllib** UA is treated as a non-browser client. This is the estate's live A2. |
| Anthropic -- *Errors*, `https://docs.anthropic.com/en/api/errors` | 401 authentication_error (malformed/revoked/expired) - 402 billing_error - 403 permission_error - 404 not_found - 409 conflict - 413 request_too_large - **429 rate_limit_error** (a tier spend-cap 429 has **no** retry-after) - 500 api_error - 504 timeout_error - **529 overloaded_error**; the SDK "retries transient failures... twice by default, honoring the retry-after header"; on SSE an error can arrive **after** a 200. |
| Groq -- *Rate limits*, `https://console.groq.com/docs/rate-limits` | 429 with `retry-after`; `x-ratelimit-remaining-requests` (RPD), `x-ratelimit-remaining-tokens` (TPM) and the matching reset headers -- the estate's lane registry already reads these. |

**One upstream fact the estate's own config had already discovered:** `llm/config.yaml` records
that a primary attempt is *not* a fallback hop, and that "cooldown is blind to why a deployment
failed and only watches whether it answers". That is E3, found independently by the estate.

---

## 6. Prioritised remediation

| # | Action | Why (measured) | Falsifier / proof of done |
|---|---|---|---|
| **P0.1** | Give the cloud route a home that does not die with the cluster, or restore the cluster's tunnel connector | the default route answers 530/1033 and has since 2026-10-28 (#7387) | a real request to `https://llm.mumchimp.com/v1/...` returns 200 with the estate's signature, and `/fleet` shows it |
| **P0.2** | Land the **deployed** front (38,994 B) in the repository, or re-derive it, and make `bin/litellm-local install` refuse to overwrite a deployed front that is newer than the repo's | `main`'s front.py is 3,466 B with no cloud leg; a reinstall today would delete the cloud leg and the saturation/budget guards | `git show main:platform/llm/front.py` contains `ESTATE_ROUTER_CLOUD`, `LOAD_MAX` and the answer budget, and the deployed file is byte-identical to the repo's |
| **P0.3** | Build the **degraded mode** the 2026-10-29 incident asked for: when the cloud is down and the laptop is saturated, say so in one line with the measured reason and the next action | 757 refusals with no route behind them | a gate: a known-bad fixture (cloud 530 + load 60) produces the degraded answer, and the fixture is in CI |
| **P1.1** | Forecast and route around quotas before they bind | 295 of 640 transitions in 24 h were rate limits; 35,173 `ready -> exhausted` overall | the forecast names the lane and the reset before the first 429 of the day; measured on a day |
| **P1.2** | Keep **both** slots up | at 13:05 one slot was refused and at 13:08 the other; 79 restarts in the watchdog log tail | `lsof` shows 4001 and 4002 both listening for 24 h; the twin is proven by killing one slot and watching the front move |
| **P1.3** | Make the doctor grade the **deployment** | the doctor says BROKEN about 18 lanes that are in the running config | the doctor's dropped list is empty while the running config is the one it reads; a fixture that drops a lane makes it fire (a gate that can fail) |
| **P2.1** | Rotate and compact `lanes.jsonl` | 110 MB and growing; it is a disk consumer on a volume that is already at its floor | the file is bounded and the census still runs over the whole window |
| **P2.2** | Publish the census as a scheduled artefact, not a script in /tmp | the truth about the router exists only because someone ran the census | the artefact is committed with a date and a diff against the previous one |
| **P2.3** | Reconcile the latency tail with the caller's patience | the measured tail reaches 73 minutes against a 240 s budget and a 364 s patience | a lane whose p99 exceeds the budget is either fixed or taken out of the default chain |

---

## 7. Gaps -- what could not be measured, and what would close them

1. **No cluster access to the origin.** The cloud route's own logs were not read (the control plane
   is gone); the cloud's failure is characterised from the edge and the incident record only.
2. **No provider dashboards.** Per-account quota resets, remaining balances and tier limits were
   not read; the 429/402 counts are what the estate *saw*, not the accounts' truth.
3. **The doctor's render path was not traced.** Why it drops 18 lanes that the running config
   holds is established by comparison, not by reading its render.
4. **No end-to-end request trace.** The chain in sec 3 is reconstructed from the front's log lines and
   the registry's events; the router's own per-request trace was not available.
5. **The 73-minute latency tail has no cause.** It is measured (`openai/MiniMax-M3` max
   4,400,588 ms), not explained.
6. **Load is a moving target.** The saturation figure (757 refusals) is the log's total to
   13:00 UTC on 2026-11-02; the host's load changes minute to minute.
7. **DuckDuckGo began serving an anomaly page mid-research** (67 occurrences of "anomaly" in the
   response body), so the search path was abandoned in favour of fetching the upstream docs
   directly. Every citation above is a document that was fetched with HTTP 200 and read.

---

## 8. Reproduction

Every number in this document comes from one of these; all were run on 2026-11-02.

```bash
# the live route, exactly as a caller sees it
curl -s -m 15 -o /dev/null -w '%{http_code} %{time_total}\n' https://llm.mumchimp.com/health/liveliness   # 530 1.71
curl -s -m 15 -A 'Python-urllib/3.12' -o /dev/null -w '%{http_code}\n' https://llm.mumchimp.com/health/liveliness  # 403 (1010)
curl -s -m 15 -o /dev/null -w '%{http_code} %{time_total}\n' http://127.0.0.1:4000/health/liveliness        # 200 0.05
curl -s -m 15 -o /dev/null -w '%{http_code}\n' http://127.0.0.1:4001/health/liveliness                      # 200
curl -s -m 15 -o /dev/null -w '%{http_code}\n' http://127.0.0.1:4002/health/liveliness                      # refused (at 13:05)
lsof -nP -iTCP -sTCP:LISTEN | grep -E ':400[0-2]'                                                          # at 13:08: 4002 + 4000 only
cat ~/.estate/router-state/active                                                                          # 4002

# the front's own account of itself
grep -c 'saturated' ~/Library/Logs/litellm-local.log                   # 757
grep -c 'the cloud failed to answer' ~/Library/Logs/litellm-local.log   # 288
tail -c 3000000 ~/Library/Logs/litellm-watchdog.log | grep -c 'restart: kickstart'   # 79
cat ~/.estate/router-doctor.last                                         # doctor BROKEN, 18 lanes "dropped"

# the drift (P0.2)
wc -c ~/.estate/litellm-local/front.py platform/llm/front.py             # 38994 vs 3466
git show main:platform/llm/front.py | grep -c ESTATE_ROUTER_CLOUD        # 0

# the census (sec 4): event counts, statuses, transitions, latency percentiles, substitutions
python3 <census script>                     # 786,949 rows of lanes.jsonl
python3 /tmp/probe_router.py status 24      # the 24h slice
python3 /tmp/probe_router.py subs 24        # the 24h substitutions

# the live lane states
python3 -c "import json,os;print(json.load(open(os.path.expanduser('~/.estate/router/lanes.json')))['lanes'])"
```

The census script reads `~/.estate/router/lanes.jsonl`, `substitutions.jsonl` and `table.json`; it
never writes them.

---

## 9. The two questions this document exists to answer

**Q. What can fail?** **89** named modes across ten layers (sec 2) -- A 7, B 6, C 10, D 10, E 14,
F 11, G 14, H 7, I 5, J 5 -- each with a signature, a diagnostic and a grade. The ones live right
now are the headliners in sec 1: **A1/A2** (the edge), **B2** (the origin behind it), **C1** (the
refusal), **C9/J4** (deployed != repository), **D1/D9** (the slots), **E2/J1** (the doctor's false
BROKEN) and **H2** (the disk at the executor's floor).

**Q. What does the estate do about it, in order?** sec 6. The first three are P0 and each carries a
falsifier, because a gate that cannot fail is not a gate.
