# Runbook - LLM routing stack: every failure mode (cause -> symptom -> detection -> recovery)

Scope: everything the estate's model voice runs on, as measured live on 2026-11-04/05 and in
the recorded incidents. The router stack is: the laptop front (:4000), the LiteLLM slot (:4002,
standby :4001), the Rust sovereign router (:4102), the Cloudflare edge (`llm.mumchimp.com`,
tunnel `d77a438e`), the vault (`estate-secrets`, SOPS+age), and the provider lanes. The
architecture of record is decision 0050: the router's home is the estate node, the MacBook is a
thin client that calls Cloudflare first.

Container table, then long-form for the modes that need an explanation.

## 1. Machine (the 8 GB MacBook, keeper of no router forever)

| Mode | Cause | Symptom | Detection | Recovery |
|---|---|---|---|---|
| Swap-fill saturation | Sessions + heavy GUI apps exceed RAM; swap 5.4-5.6/6 GB every time | 1-min load 300-522 at ~45-90% per-proc CPU; health endpoints answer `000`; everything waits | `uptime` (load >> 4*nCPU), `sysctl vm.swapusage`, load > 32 refuses the front | Close the fleet's appetite (fewer concurrent heavy sessions); the laptop keeps no resident router after 0050's uninstall door |
| Disk wedge | Data + worktrees + logs exceed ~10% free | SQLite WAL failures, Rust builds die, 1.9 GB free measured 2026-11-04; cf. 94% full on 10-24 | `df -h /` (target > 10 GB free) | Clear caches/old runtimes only, as the founder measures; the estate's own scan tool writes `~/.estate/disk-cleanup.last-scan` |
| Thread-explosion stalls | Runner storms x client retries while the box is thrashing | Load giga-scale (306-370 on 10-24, 522 tonight) with every process < 10% CPU | `ps aux | awk '$8 ~ /^R/'` count vs CPU | Give the box air; retry storms stop on their own when the router refuses fast (503 + Retry-After) |

## 2. Front (:4000)

| Mode | Cause | Symptom | Detection | Recovery |
|---|---|---|---|---|
| Load-gate refusal | gate set at load > 32 (2026-10-10 753-request storm) | `front: the box is saturated (load 33.2 > 32.0); refusing` + HTTP 503, Retry-After 30 | `tail ~/Library/Logs/litellm-local.log` | Same as machine modes; when load < 32 the front answers again by itself |
| Wedged-but-listening | accept loop alive upstream dead (O outage signature) | TCP connect OK, HTTP never answers; watchdog restarts only on *refused* | watch `critical-watch.out.log` + a real 1-body probe with a 5 s budget | Killed with SIGKILL historically; the launcher then switches the ACTIVE slot |
| Referral loop, ONLY IF someone publishes the laptop as the edge | tunnel ingress -> :4000; front prefers cloud upstream (UA `estate-router-front/1.0` is edge-allowed) | one extra hop per recursion, unbounded depth, 240 s budget burns | the front's own log: `ROUTE upstream=llm.mumchimp.com` on a request that arrived through the tunnel | Rule, not patch: **the tunnel connector never runs on the MacBook and the edge never terminates at the laptop.** Recorded in 0050 and on `~/.cloudflared/config.yml` |
| Cloud preferred over healthy local during an outage | pass-over built with the known-dead cloud first (2026-10-29 pre-fix) | 753 requests in a row handed to the dead cloud | front log ordering | Fixed 2026-10-29: cooldown cloud is tried LAST, behind the sick slots |
| Edge's own refusal relayed as answer | Cloudflare UA rule (403/1010) or "model not found" (400) | caller dies on a healthy cloud with wrong key or wrong model | front log: refusal naming the model or error code 1010 | Fixed 10-28/10-30: those refusals pass over to the next target |

## 3. LiteLLM slot (:4002 active, :4001 standby)

| Mode | Cause | Symptom | Detection | Recovery |
|---|---|---|---|---|
| 90 s boot | litellm proxy import + config build | :4002 answers 000 then 200 | `bin/litellm-local status` | The front's retry covers callers; zero-gap `swap` while a deploy is needed |
| Model-name drift (catalog vs slot) | cloud catalog names (`gemini-3.8-flash`, `MiniMax-M3.1-Flash`) don't exist as slot model_names | `no healthy deployments for this model` | measured 2026-11-04: call the slot's own names (`gemini`, `minimax_m31f`) | call with the deployed model_name, and fix the catalog to the one the slot carries |
| Reasoning model eats the budget | tiny `max_tokens` consumed by internal thought | empty completion (`finish_reason=length`) with empty content | one measured call | raise `max_tokens`; the vault-recorded 2026-11-04 lane test all passed at 64 |
| Lane refusal, absent credential | key not in the slot env | lanes.json `refused` entries naming the env var, `MEASURED_FAIL` | `~/.estate/router-state/lanes.json` | refresh the key through the vault, restart the slot via the install door |

## 4. Sovereign router (:4102)

| Mode | Cause | Symptom | Detection | Recovery |
|---|---|---|---|---|
| DISCOVERY_FAILED | upstream `/v1/models` answers non-200 (edge down) and the chain only falls through on >=500 | log line `SOVEREIGN_RUST_ROUTER=DISCOVERY_FAILED error=upstream /v1/models answered 404` | the log | the 404-fallthrough fix in `crates/sovereign-router` (owned by the argon/argon-sync lane, in flight) |
| Chunked-POST decode failure | proxying chat completions through the active slot fails body decode | **measured 2026-11-04 23:47Z**: every POST (stream:false too) -> `UPSTREAM_FAILED ... chunked body could not be decoded`, ROUTE returns the upstream 530 | `tail ~/.estate/logs/sovereign-router.log` | same lane; GET `/v1/models` (catalog, 159 models) works meanwhile |
| Port refusal by design | the daemon binds 4102 only; :4001/:4002 are the legacy slots | `SOVEREIGN_LINUX_ROUTER refuse` boot log | pid + listen ports | not a defect; decision 0039's one mouth at :4102 |
| Stale binary drift | running build (3 Nov) behind the repo's in-flight fix | log behavior mismatches the branch's tests | `ls -la ~/.estate/bin/sovereign-routerd` vs branch | rebuild from the landed state, install with the launcher + launchd label |

## 5. Cloudflare edge (`llm.mumchimp.com`, tunnel `d77a438e`)

| Mode | Cause | Symptom | Detection | Recovery |
|---|---|---|---|---|
| No connector | no cloudflared process anywhere holds the tunnel | **530 error code 1033**, measured all of tonight | `curl -o /dev/null -w "%{http_code}" https://llm.mumchimp.com/...`; `cloudflared tunnel info d77a438e` -> "does not have any active connection" | start the connector **on the router's node, never on the MacBook** (0050) |
| DNS route auth expiry | `cloudflared` cert.pem (23 May 2025) fails zone API calls | `tunnel route dns` -> `code: 10000 Authentication error` | that command's exit code | re-authorize cloudflared (browser login) - needs founder's hands |
| Quick-tunnel confusion | a `/private/tmp/cloudflared` quick tunnel (visible for another debugging surface) | looks like "cloudflared is up" while the edge is dead | `ps aux | grep cloudflared` shows `--url http://127.0.0.1:3000` | leave it; use `tunnel info d77a438e` for the edge's truth |
| Edge returns before the connector is asked | nginx 530/1016 vs 1033 distinction lost | status tells which half (DNS vs connector) is dead | map status: 530+1033 = no connector; 530+1016 = DNS/origin | act on the half the status names |

## 6. Credentials (vault + caller copies)

| Mode | Cause | Symptom | Detection | Recovery |
|---|---|---|---|---|
| Stale caller copy | local `caller/LITELLM_LAPTOP_KEY.yaml` (Oct 16) differs from the vault copy | 401 through the slot with the caller value; the vault value answers 200 | compare `shasum` of the two decrypted values (never print them) | refresh via the vault bridge; rotation recorded **KeyLeak-20261104** after tonight's export defect printed the stale value once |
| Vault door unreachable | memory/edge down | `estate-brief: no brief (URLError ... EOF)` | the tool's own error | use the graph (local) until the edge returns |
| Keys printed into transcripts | broken shell expansion | rule violation (already happened tonight for the *stale* value) | review; the fact carries it | rotate + never `export $(...)`; load via `secret-load env name KEY` by name |

## 7. Booking the fleet onto lanes

| Mode | Cause | Symptom | Detection | Recovery |
|---|---|---|---|---|
| Path overlap | two agents claim the same files | the second claim's work is refused by claim-gate | `bin/claim-gate` red naming the file | pick other work or comment on the holder's issue; a lapsed heartbeat frees the issue |
| Live-session collision | a repo has uncommitted WIP from a running session (argon, argon-sync tonight) | touching it kills the other agent's loop | `git log -1` dates + `ps` for the other agent | don't edit; hand the measured defect over (graph/journal) the way `SovereignRouterDefect-Chunked` was handed to the `crates/sovereign-router` lane |
