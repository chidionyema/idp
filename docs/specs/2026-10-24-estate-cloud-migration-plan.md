# Estate Cloud Migration — Execution Plan

**Date:** 2026-10-24
**Status:** Working execution plan (not an approved spec). Author: Kimi Code session, at founder's request. Audited 2026-10-24 19:30: all referenced paths verified (§1.4); NATS crash-loop found and fixed live; backup route reordered restic-first (P0.T1); KeepAlive-guard task added (P0.T8).
**Purpose:** End the recurrent resource-exhaustion outages on the 8GB laptop by moving heavy estate services to the OKE cluster, leaving the laptop a thin client. Written to be executed task-by-task by a fresh agent session (possibly a cheaper model) with no prior context.

---

## 0. How to execute this plan (read first, executor protocol)

1. **Read the laws before touching anything:** `~/AGENTS.md` (estate-wide) and `~/Documents/code/idp/AGENTS.md` + `~/Documents/code/AGENTS.md`. They are binding; the files win over this plan.
2. **Load shared memory:** `growmos --root ~/Documents/code/estate-graph context --brief`; `bin/estate-brief --task "<task>"` at each task start (or estate-memory MCP `brief`); `recall` before deciding; `remember` what a later session must know.
3. **Claim before you change anything.** No work without a ticket: `bin/claim-open --title "<what you are building>"` (or `--issue <n>`). Search open claims for path overlap first; refresh the claim heartbeat at least hourly; one capability at a time per agent; every change carries `Claim: <owner>/<repo>#<n>` and `Agent: <name>` trailers; close the issue only with a proof comment (command + output on the real path). Claims are visible on /fleet.
4. **Work ONE task at a time, in phase order.** Task IDs are `P<phase>.T<n>`. Do not start a task whose dependencies are not done.
5. **"Ship via lane" (used throughout this plan) means:** push the branch to `lane/<name>` with `estate-execute lane-submit`, then STOP. **An agent never raises a PR and never pushes main.** Greenlane proves the lane green on current main, raises the PR itself, and fast-forwards main; Flux deploys what lands. Runbook: `docs/runbooks/greenlane.md`. `kubectl apply` by hand is forbidden. If `gh`/pre-push stalls, that is a network defect to report, never a reason to hand-run the pipeline.
6. **Gates are hard.** Every task has a *Proof* step. If proof fails or is ambiguous, execute the *Rollback* (if anything changed), record the failure, and STOP that task. Max 2 attempts, then escalate to the founder with the exact error.
7. **Done = operational.** Merged/deployed/green-CI/HTTP-200 are steps, never done. Operational means used on the real production path and visible live on **/fleet** where the capability has a surface. **Report only "done" or "seriously blocked"** — a blocked claim must carry the intent that was run (`estate-execute <intent>`), its exit status, and the line it printed. Do not announce merges/PRs as progress.
8. **Evidence log:** after every task append to `~/.estate/migration/log.md`: task ID, claim issue, timestamp, exact commands, measured outputs, proof excerpt, rollback y/n. At each phase gate: `growmos --root ~/Documents/code/estate-graph journal "<phase> complete: <evidence summary>"`.
9. **Protected — never touch without an explicit founder instruction in the current session:**
   - The 7 `pi` processes and `opencode` (PID 34500): mid-session user work. Do not kill, STOP, restart, or edit their config files while sessions are live (except `router_catalog.py`'s normal model-catalog writes).
   - No reboot of the laptop without founder saying so in the current session.
   - Telegram token polling; other agents' processes generally.
   - `~/.estate/harness/cc` live session state; vault plaintext (never print secrets; env var names only).
10. **Secrets:** only via `estate-secrets` (SOPS+age) or the Bitwarden bridge. `sops`: `~/.cache/estate-tools/sops`. Age identity: `~/.config/prospector/age-key.txt` (never read into output). Loader: `~/Documents/code/estate-secrets/scripts/secret-load <env> <name> <KEY>`. Laptop router key = `LITELLM_LAPTOP_KEY` (vault `secrets/dev/LITELLM_LAPTOP_KEY.yaml`).
11. **Search rule:** `rg -l`, never `grep -r`. **Keep commands short:** no sleeps >90s, no unbounded scans, no `du` on big trees, no `mdfind` — the laptop degrades under load.
12. **Placement is decided by the free-tier ladder, not by the cluster** (`docs/decisions/0034-workloads-are-placed-by-the-free-tier-not-by-the-cluster.md`): delete → GitHub Actions schedule → Grafana Cloud free → Cloudflare Workers free → laptop just-in-time → KEDA scale-to-zero on the node → always-on on the node. For every workload this plan moves, record which rung it lands on and why; any change that adds to the node states CPU/memory requests and keeps the node's requests **under 1.8 CPU**; before any node reboot/resize/drain, `calico-node` must be Ready on every node.

---

## 1. Current state (measured 2026-10-24)

### 1.1 The incident this plan ends
- Repeated all-day waves where every agent session (pi ×7, opencode, claude, Kimi Code) died: load average peaked **~306–370**, swap **5.6/6 GB**, disk **94% full** on an **8GB** MacBook Pro (macOS 13.7.5 x86_64), 5+ days uptime.
- Signature: router accepts TCP but never answers HTTP; watchdog log (`~/Library/Logs/litellm-watchdog.log`) shows `probe slow:curl=28 http=000 -- listening, not restarted` for hours. The watchdog only restarts on *connection refused*, so a wedged-but-listening router is never restarted. Client retry storms amplify the wedge.
- Root amplifiers: backstage launcher boot-crash-respawn loop (new node processes every ~20–40s under PPID 1); ~20 periodic launchd jobs firing into storms; 5 KeepAlive daemons restart-looping under load; `caffeinate` keeping the box awake 24/7; ~4GB of worktrees and constant log churn on a nearly-full disk.

### 1.2 Recovery actions ALREADY DONE (do not repeat, do not blindly undo)
| Action | Detail |
|---|---|
| Stale processes killed | 3 `claude bg-spare` + pty-host + Oct-1 `claude --resume`; old yarn trees; claude chrome-native-host; stray `du` |
| Orphan Temporal killed | `:61866` had **zero client connections**; live dev server is **`:61938` (PID 54291)** — still running |
| Disk/log cleanup | 12 logs truncated (~103MB), 2 crash logs deleted, caches cleared; disk 94%→92%, swap total 6GB→3–4GB |
| Chrome + Google Drive quit | Founder relaunches Chrome when calm (tabs restore) |
| 11 interval jobs DISABLED (still disabled) | `ai.estate.router-doctor`, `ai.estate.voice-watch`, `com.estate.session-recorder`, `ai.estate.no-harness-folders`, `com.estate.costsentinel`, `com.estate.downshift`, `ai.estate.graph-drain`, `ai.estate.pi-reaper`, `ai.estate.runtime-sync`, `ai.estate.tracked-guard`, `ai.estate.oke-refresh` (also `ai.estate.disk-clean` was already disabled) |
| Backstage booted out + disabled | `ai.estate.backstage-backend`, `ai.estate.fleetview-frontend` — **Backstage UI intentionally down until P0/P4** |
| Router restarted | Old litellm (PID 1610) wedged; SIGKILL → launcher switched **active slot to `4002`** (see `~/.estate/router-state/active`). Front `:4000` healthy. Slot `4001` may be down — fine while `4002` is active |
| Kimi-session watcher | Cron job `01M5QCHAR8WAVP7CH16RN9M1DK` probes `127.0.0.1:4000/health/liveliness` every 12 min; cancel via the Kimi session if unwanted |
| **Preflight backups STAGED locally** | `~/.estate/backups/20261024-preflight/` (977MB): `outbox.db` (128MB, `sqlite3 .backup`, integrity ok), `estate.db` (3.2MB, integrity ok), `harv-index.db`, `harv-evidence.db`, `action-ledger.jsonl` (83M), `efficiency-ledger.jsonl` (32M), `facts.jsonl`, `nats-jetstream.tar` (695K), `harv-blobs.tar` (670M), `graph-sessions.tar` (42M), `keys/` (ledger signing key — handle as secret) |
| **NOT done: off-laptop copy** | Staged backups are still on the same disk. P0.T1 is the top-priority task |

### 1.3 Known-broken / unverified (verify, don't assume)
- **restic offsite backup probably broken:** no `restic` binary in PATH or usual locations; `~/.claude/scripts/estate/restic-env.sh` (sourced by `~/.estate/bin/restic-backup.sh`) not found. The 03:30 daily job `com.estate.restic-backup` targets Cloudflare R2. Verify from its log before relying on it (P0.T2).
- SSH to tailnet node `backstage-fleetview-mac` (100.83.63.31) port 22 **times out**.
- Cluster litellm auth unverified: config references `master_key: os.environ/LITELLM_MASTER_KEY` but that env name was **not seen in the deployment env list** (P2.T1 gate).
- Local Temporal consumers unknown (P3.T1 gate).
- 3 corrupted `nats.broken-*` snapshots exist in `~/.estate/nats` today.
- `~/.estate/graph/estate-graph` may be a drifted copy of `~/Documents/code/estate-graph` (P5).
- `founder-phone` SA token in `~/.estate/estate-cluster.yaml` **expired 2026-10-08**.

### 1.4 Audit of referenced assets (measured 2026-10-24 19:15–19:30)
- **NATS KeepAlive crash-loop — found live and FIXED.** `launchctl print` showed `runs = 112, last exit = 1`: an orphan server (PID 15758, started 14:14) held ports 4222/8222 while KeepAlive respawned a dying duplicate against the same JetStream store every few seconds. Fixed: bootout → kill orphan → single bootstrap → `runs = 1, never exited` (PID verified listening on 4222, monitor 8222 returns 200). A **cold** JetStream snapshot replaced the live-taken one: `nats-jetstream-cold-20261024.tar.gz` (314K) in the preflight dir; the old 695K live archive is superseded, keep both. Executor lesson: before touching any launchd job, read `launchctl print gui/501/<label>` — `runs` and `last exit code` reveal loops that `pgrep` hides.
- **Intent names on disk differ from estate AGENTS.md:** actual YAMLs are `pr-list`, `pr-merge` (not `pr.list`/`pr.merge`); **no `break-glass` intent exists** despite the AGENTS.md table. `estate_list` is the truth. AGENTS.md fix is a separate small task, not this plan.
- **`docs/specs/2026-10-23-the-delegated-estate.md` exists only on idp `origin/main`** (verified 2363 lines via git cat-file). Local checkout sits on `lane/meridian-design` [ahead 4, behind 124] with unrelated dirty files — **do not commit the migration plan from that checkout without founder guidance on lane strategy**; read the spec via `git show origin/main:docs/specs/2026-10-23-the-delegated-estate.md`.
- **estate-core has no `laws/` or `LAWS.md`** — only `LAWS-INCIDENTS.md` at repo root. P1.T3 must first found the canonical law file (this is the change, not a drift).
- **`restic` binary is absent from PATH entirely** (not just the env script) — P0.T1's brew-install step is mandatory, not optional. `restic-env.sh` confirmed missing as suspected.
- `~/.estate/migration/` and its `log.md` do not exist yet — **Task 0** (below) creates them before any other task.
- `crew/STATE.md` is a generated snapshot dated 2026-09-15/28 — stale on all of this, P1.T1 will refresh it.
- Verified present and correct: `bin/claim-open`, `bin/estate-brief`, `docs/runbooks/greenlane.md`, `docs/decisions/0034-...`, all litellm-local files (`front.py`, `watchdog.py`, `config.yaml`), `~/.estate/bin/restic-backup.sh`, preflight backups (~960MB, 13 items incl. `keys/`), growmos + estate-graph.
- Machine at audit time: front :4000 = 200, swap 3.5/4GB used (improved from 5.6/6), but 1-min load **382** with WindowServer 62% CPU and two stray `du` processes — the storm is partly GUI + fleet jobs, which is exactly what P0.T3/P0.T6 gate.

---

## 2. Invariants and laws (violating these = task failure)

1. **No hand-apply; no agent-raised PRs; no pushes to main.** Everything ships via `lane/<name>` + Greenlane + Flux (§0.5).
2. **Proof, not assertion; done = operational** on the real path, visible on /fleet where applicable (§0.7).
3. **Secrets by name only.** Never print, paste, or commit secret values. Known debt: laptop key is **inline in `~/.estate/harness/cc/settings.json:4`** (`x-litellm-api-key`) — fix is P0.T7, only with founder sign-off when no claude sessions are live.
4. **One of each layer.** Migration *converges* duplicates (two Temporals, two NATS, two routers, two API doors); it never adds a third. Before building anything: `growmos query "<capability>"` and read the candidate.
5. **Intents for estate actions.** Prefer existing intents (e.g. `estate-execute work-audit` before deleting worktrees; `estate-execute lane-submit` to ship). New recurring capabilities = intent YAML in `~/.estate/intents/` + ship to idp, not bespoke cron hacks.
6. **Harness glue is the exception.** New capability goes platform-side (router modules, cluster services) by default. Harness-specific hooks/config only when it cannot be solved architecturally, each recorded in the exception ledger (P1.T3). Transcript-scraping is a smell: prefer router-emitted events.
7. **Laptop stays a fallback.** Founder ruling 2026-09-26: a working local router slot must remain ("if cluster breaks we are all disabled"). Migration makes it *thin and idle*, never deletes it.
8. **Mid-session agents survive.** All client-facing changes keep `127.0.0.1:4000` answering. The front never migrates in-flight connections; cutovers only affect new connections.

---

## 3. Target architecture

```
                    THIN LAPTOP (8GB)                              OKE CLUSTER (heavy)
┌───────────────────────────────────────────┐   ┌──────────────────────────────────────────┐
│ pi / opencode / claude / Kimi Code        │   │ ns llm: litellm (2/2) + cache +           │
│        │  (all unchanged configs)          │   │        router-event-publisher            │
│        ▼                                   │   │ ns event-bus: NATS JetStream (only bus)  │
│ front.py 127.0.0.1:4000  (never restarts)  │   │ ns temporal: full suite + sovereign-worker│
│   ├─ thin local litellm slot (fallback,    │──▶│ ns estate-db: CloudNativePG estate-rw     │
│   │   laptop key, local-only lanes ollama) │   │   (only Postgres; estate.db/outbox land) │
│   └─ primary: https://llm.mumchimp.com ────┼──▶│ ns backstage/catalogue + Face (no laptop │
│ watchdog: restart on HTTP-timeout pattern, │   │   dependency)                              │
│   hysteresis + daily cap                   │   │ ns estate-bridge: cluster API door (Flux) │
│ interval fleet: load-gated, staggered      │   │ object storage R2: backups + ledgers      │
│ rotated logs; disk >15% free               │   │ Flux/Greenlane: only path to change       │
│ sqlite demoted to cache (Phase 5)          │   └──────────────────────────────────────────┘
└───────────────────────────────────────────┘
```

**The Delegated Estate spec** (`idp@origin/main:docs/specs/2026-10-23-the-delegated-estate.md`, 2363 lines, **PROPOSED**, Option A) is compatible in direction: one policy, many renderers (laptop + cluster spheres), with a **config-drift check** as the gate (its phase 6). D9: ZeroEdge folds into the cluster renderer, never a second routing policy; laptop key must not cross spheres. This plan operationalizes the infrastructure half and **adopts its phase-gate discipline**: each phase = claim + lane + green proof + measurable acceptance. `docs/specs/hosted-session-memory.md` supplies the data law: *"the laptop is one of the roads, never the place the data lives"*; one Postgres (`estate-rw.estate-db`), every client thin.

**Documented divergences from that spec (founder decisions, not spec-backed):**
- Retiring local Temporal for cluster Temporal: spec keeps laptop Temporal as durability plane (its Option C explicitly not recommended). Ours is infra-consolidation → **founder gate at P3.T3**.
- Moving `estate.db` to Postgres: spec adds tables to laptop sqlite and only demands "never the only copy" (line 1929). Our P5 demotes sqlite to a cache → requires the fleetview read-path change (P4/P5 coupled).

---

## 4. Authoritative-master map

| Component | Laptop today | Cluster today | Authoritative after | Must move / decide |
|---|---|---|---|---|
| Router / model spend | `front.py:4000` → local litellm slot (4001/4002), 13 custom modules | litellm ns `llm` (2/2) + cache + event-publisher | **Cluster litellm**, one drift-checked policy; local slot thin fallback | lanes/config policy; cluster capture parity (P2.T2) |
| Temporal | dev server `:61938` + sovereign engine (`SessionWorkflow`) | full suite + sovereign-worker | Cluster temporal | consumer map (P3.T1), workflow runners |
| Backstage / FleetView / Face | backstage down (disabled); fleetview-backend `:18790` reads sqlite; NATS client | backstage/catalogue; Face forwards intents to laptop (defect A11) | Cluster, self-contained | fleetview read path (coupled with P5) |
| NATS | local `~/.estate/nats` (856K store; 3 corrupted snapshots) | event-bus ns | **Cluster NATS only** | bus reachability from laptop (P4.T2) |
| `outbox.db` (128MB) | local, actively written (action_ledger) | none | estate Postgres | schema + writers (P5) |
| `estate.db` (3.2MB) | local state of record for /fleet (3,828 step_runs, 2,648 intent_tickets, 790 policy_decisions) | none | estate Postgres; sqlite→cache | readers/writers; fleetview coupling |
| Ledgers (`action-ledger.jsonl` 83M, `efficiency-ledger.jsonl` 32M) | local jsonl | none | R2 object storage | raw jsonl, date-partitioned (parquet optional later) |
| harv registry (evidence/index db + 670M blobs) | local | none | Preserved + backed up; evidence precious | offsite copies only |
| growmos graph + 572 session md | `~/.estate/graph/estate-graph` | none | git (`estate-graph` repo) | commit sessions; resolve drift |
| Cluster API door | laptop `kubectl proxy` on `100.98.58.115:8001 --accept-hosts=.*` (PID 3991) | **estate-bridge** (Flux kustomization `bridge`) | estate-bridge; laptop proxy retired | phone kubeconfig + token re-issue |
| Worktrees / runs / venvs | 4GB worktrees (17–21), 19k run dirs | — | Nowhere (regenerable) | audit then prune (P0.T6) |

---

## 5. Phase plan

### PHASE 0 — Data safety + stop the bleeding (laptop only; no cluster changes)

**Gate to exit Phase 0:** offsite backups verified by restore-test; backup job receipted daily; interval fleet re-enabled behind load-gate with rotated logs; disk ≥15% free or a dated plan to get there.

#### P0.T0 — Create the migration workspace (2 minutes, do first)
```bash
mkdir -p ~/.estate/migration ~/.estate/backups
printf '# Estate cloud migration — evidence log\n' > ~/.estate/migration/log.md
cp ~/Documents/code/idp/docs/specs/2026-10-24-estate-cloud-migration-plan.md ~/.estate/migration/plan-snapshot.md
```
**Proof:** `log.md` exists and the snapshot hash matches the spec file. Everything else in this plan logs into it.

#### P0.T1 — Push the staged preflight backup off-laptop and verify (TOP PRIORITY)
Already staged: `~/.estate/backups/20261024-preflight/` (977MB; integrity-checked SQLite copies; note the JetStream archive here was taken live — use `nats-jetstream-cold-20261024.tar.gz` instead, see §1.4).
**Route order (revised): (a) restic→R2 first** — it is the standing mechanism and P0.T2 needs it anyway, so repairing it first kills two birds: `brew install restic`, restore `restic-env.sh` via the vault flow (`rg -l "restic-env" ~/Documents/code/estate-secrets ~/Documents/code/estate-core`), snapshot the preflight dir, then run P0.T2's proof. **(b) kubectl cp fallback** only if restic is blocked >2h: into the estate-db PVC, outside PGDATA.
```bash
CTX=context-estate-crq7jwxsjxq   # or: oke
kubectl --context $CTX -n estate-db get pods          # pick the estate-rw instance pod, e.g. estate-rw-1
POD=<estate-rw pod name>
kubectl --context $CTX -n estate-db exec $POD -- mkdir -p /var/lib/postgresql/backups/preflight-20261024
cd ~/.estate/backups && tar -czf /tmp/preflight-20261024.tar.gz 20261024-preflight
shasum -a 256 /tmp/preflight-20261024.tar.gz | tee /tmp/preflight.sha
kubectl --context $CTX -n estate-db cp /tmp/preflight-20261024.tar.gz $POD:/var/lib/postgresql/backups/preflight-20261024.tar.gz
kubectl --context $CTX -n estate-db exec $POD -- sha256sum /var/lib/postgresql/backups/preflight-20261024.tar.gz
```
**Proof:** remote sha256 == local; then restore-test offsite bytes: `kubectl cp` the archive back to `/tmp/restore-test/`, extract, `PRAGMA integrity_check;` on `estate.db` + `outbox.db` = ok, and compare `SELECT count(*)` on one table against the live DB (record numbers).
**Note:** API calls took ~35s each during the storm — time-box retries, do not hammer. This PVC copy is *preflight only*; R2 restic is the standing mechanism (P0.T2). A copy on a PVC is not a backup *product* — P0.T2 makes it one.
**Rollback:** none needed (additive). **Effort:** ~30–60 min mostly waiting.

#### P0.T2 — Diagnose and repair the R2 restic backup
```bash
tail -50 ~/.estate/state/logs/restic-backup.log
launchctl print gui/$(id -u)/com.estate.restic-backup | head -40   # last exit status
ls ~/.claude/scripts/estate/ ; command -v restic
```
Restore `restic-env.sh` from its source (`rg -l "restic-env" ~/Documents/code/estate-secrets ~/Documents/code/estate-core`; if vault-managed, restore via the vault flow — never hand-create credentials). Install restic (Homebrew or official binary). Run `~/.estate/bin/restic-backup.sh` once manually.
**Proof:** script's own receipt prints `latest snapshot <id> age <...>` with age <26h; `restic snapshots --latest 2` shows the new snapshot; `restic restore` one small file to /tmp and diff.
**Rollback:** none (additive).

#### P0.T3 — Load-gate + stagger the interval fleet, then re-enable
Create `~/.estate/bin/load-gate` (new capability → also ship as an intent if it recurs):
```sh
#!/bin/sh
# exit 0 = safe to run; exit 75 = skipped (overloaded)
LOAD=$(sysctl -n vm.loadavg | awk '{print $2}')
FREE_SWAP_MB=$(sysctl -n vm.swapusage | awk '{print $7}' | tr -d 'M.')
LOAD_MAX=${ESTATE_LOAD_MAX:-12}
awk -v l="$LOAD" -v m="$LOAD_MAX" 'BEGIN{exit !(l+0>m+0)}' && { echo "load-gate: skip (load $LOAD > $LOAD_MAX)"; exit 75; }
awk -v f="$FREE_SWAP_MB" 'BEGIN{exit !(f+0<500)}' && { echo "load-gate: skip (swap free ${FREE_SWAP_MB}MB < 500MB)"; exit 75; }
exit 0
```
Wrap each of the 11 disabled jobs: plist `ProgramArguments` becomes `["/Users/roseonyema/.estate/bin/load-gate-and-run", "<original command...>"]` via a tiny `load-gate-and-run` that execs the gate then the original command (gate exit 75 = clean skip, logged). Stagger `StartInterval` values with 7–53s offsets so jobs never align (current intervals: 60/120/300/600/877/907/1783/1800s).
Re-enable one by one, lowest-risk first: `launchctl enable gui/$(id -u)/<label>` for: costsentinel, downshift, no-harness-folders, session-recorder, graph-drain, tracked-guard, oke-refresh, voice-watch, router-doctor, runtime-sync, pi-reaper (last; it reaps stale pi sessions — confirm its rules before enabling while 7 pi sessions are live).
**Proof:** for 2 hours: no interval job runs while 1-min load >12 (log shows `load-gate: skip`), jobs do run when calm; `launchctl print-disabled` matches the intended set; front :4000 stays healthy (5 measured probes).
**Rollback:** `launchctl disable` the job; restore original plist from `plist.pre-gate-20261024` (make that copy before editing).

#### P0.T4 — Log rotation without sudo
Estate-owned rotator `~/.estate/libexec/log-rotate.sh` run by a daily launchd job: rotate when >10MB, keep 5, gzip. Cover at minimum: `~/.estate/pi-reaper.log` (29M), `~/.estate/router-doctor.err.log` (11M), `~/.estate/nats.err.log` (7.7M), `~/.estate/runtime-sync.err.log`, `~/Library/Logs/litellm-local.log` (was 72M), `~/Library/Logs/litellm-watchdog.log`, `~/.estate/logs/*.log`, `~/.estate/fleetview-backend.{err,out}.log`. Copy+truncate for files held open by daemons (never unlink).
**Proof:** grow one test log >10MB, run rotator, confirm rotated + daemon still writes to the original path; disk reclaimed.
**Rollback:** remove the launchd job; rotated files kept.

#### P0.T5 — Watchdog: detect *wedged*, not just *refused*
`~/.estate/litellm-local/watchdog.py` currently: HTTP errors/slow probes logged; only connection-refused counts toward restart. Change (small, reviewable): restart when **3 consecutive HTTP probes time out** AND 1-min load <20, with a 15-min cooldown and max 3 kickstarts/day (log+alert beyond that; never restart-loop during a storm). Keep "listening, not restarted" when load ≥20 — under overload the fix is load reduction, not restart.
**Proof:** with the router healthy, simulate a hanging backend on a scratch port, point a test watchdog instance at it, observe exactly one kickstart then cooldown; quote real log lines. Production proof: watchdog log shows correct verdicts for 24h, and /fleet shows the watchdog deciding (pass/refuse) if it has a surface there.
**Rollback:** `cp watchdog.py.pre-20261024 watchdog.py` (make the backup first), `launchctl kickstart -k gui/$(id -u)/com.estate.watchdog`.

#### P0.T6 — Disk: audit then prune worktrees; keep >15% free
```bash
estate-execute work-audit        # existing intent: unlanded work -> LOST/PARTIAL/REMOVED/LANDED
```
Journal says 3.5GB is 12 unlanded lanes across 21 worktrees. **Never delete a worktree whose audit is not LANDED.** Prune only LANDED ones (`git worktree remove`), plus `~/.estate/runs` dirs older than 14 days (19,049 total). Downloads: 2 duplicate ZCode DMGs (~514MB) + old KimiCode DMG (139MB) — founder confirmation before deleting installers.
Add `ai.estate.disk-watch` alert threshold at 85% (currently triggers cleanup near-full).
**Proof:** `df -h` ≥15% free, or a written list of what remains and why; work-audit output saved to the evidence log.
**Rollback:** worktrees are git-recoverable if LANDED; else restore from audit notes.

#### P0.T7 — Hygiene debts (small, scheduled when sessions allow)
- Move inline laptop key out of `~/.estate/harness/cc/settings.json:4` to an env reference (founder sign-off; no claude sessions live).
- Spotlight: add `.metadata_never_index` to `~/.estate/worktrees`, `~/.estate/runs`, `~/.estate/backups` (no system-wide `mdutil` changes).
- `com.founder.estate-awake` (caffeinate 24/7): propose schedule or conditional awake; founder decision.
- Retire expired `founder-phone` token alongside P4.T4.

---

### PHASE 1 — Alignment, drift check, laws (documents + small code)

**Gate:** master map accepted by founder; drift check runs in production; harness-glue law + exception ledger landed.

- **P1.T1 — Master map review.** Walk §4 with founder; record decisions (esp. Temporal and estate.db divergences) via `growmos --root ~/Documents/code/estate-graph remember "..." --type DECISION --desc "..."`. Update `~/Documents/code/crew/STATE.md` where it disagrees with the reality measured here.
- **P1.T2 — Router config-drift check (prerequisite for Phase 2).** One script (platform-side, harness-agnostic): render the *policy* (lanes, tiers, budgets, ceilings, fallbacks — source of truth `llm/config.yaml`; note cheap=groq zero-marginal-cost and default=minimax per the living policy block) from laptop `~/.estate/litellm-local/config.yaml` and the cluster litellm ConfigMap; diff semantic fields; fail on divergence. Ship via lane to idp; laptop side runs under the gated fleet. This is the spec's K4 ("two routers, two bills") mitigation and D9 compliance.
  **Proof:** deliberate drift in a test copy → check fails; identical configs → passes. Lane lands; production log line of the check running.
- **P1.T3 — Harness-glue law + exception ledger.** Draft into estate-core laws: *"Capability lives in the platform; harness-specific features/hooks are the exception, each justified in the ledger."* Initial ledger: (a) CC hooks/statusLine/plugins/daemon jobs — review each, keep only what cannot be platform-side; (b) `router_catalog.py` per-harness adapters — model-list writing only; (c) transcript-scraping jobs (session-recorder, cost-sentinel, downshift) — plan migration to router events (graph_capture/action_ledger already emit per-call data for every client); (d) CC custom-header auth shape — protocol exception, stays; (e) Kimi Code direct-to-vendor bypass — documented exception vs routed (founder).
  **Proof:** ship via lane to estate-core (private; pre-push guards not bypassed); law file + ledger landed.
- **P1.T4 — Placement decisions.** For each workload moving in P2–P5, record the free-tier-ladder rung and justification (§0.12), the CPU/memory requests it will add, and the resulting node total (<1.8 CPU). If a workload fits a cheaper rung (e.g. GitHub Actions schedule instead of an always-on pod), change the plan to that rung instead of defaulting to the cluster.
  **Proof:** the placement table appended to this plan; node requests arithmetic shown.

---

### PHASE 2 — Router spend to the cluster (front cloud leg)

**Gate:** 3 real completions via `127.0.0.1:4000` served by the cluster (production pod log lines), with the local slot stopped for the drill and restored after; capture/ledger continuity proven; drift check green; /fleet shows real calls through the cloud lane.

- **P2.T1 — Verify cluster litellm auth before any spend.** `kubectl -n llm get deploy litellm -o yaml` (env **names** only): confirm how `LITELLM_MASTER_KEY` is provided (external-secrets? envFrom?); confirm whether the front's assumption "OKE router takes the same laptop key" is true. Test with a real request:
  ```bash
  source ~/Documents/code/estate-secrets/scripts/secret-load   # vault flow, no printing
  # obtain LITELLM_LAPTOP_KEY into env per vault script, then:
  curl -sS -m 20 https://llm.mumchimp.com/health/liveliness
  curl -sS -m 60 https://llm.mumchimp.com/chat/completions \
    -H "Authorization: Bearer $LITELLM_LAPTOP_KEY" -H 'Content-Type: application/json' \
    -d '{"model":"deepseek","messages":[{"role":"user","content":"reply with: ok"}],"max_tokens":5}'
  ```
  **Proof:** real completion JSON + corresponding request line in cluster litellm pod logs (`kubectl -n llm logs deploy/litellm --tail=...`). 401/403 = stop, fix auth via lane (never weaken auth to make the test pass).
- **P2.T2 — Capture/ledger parity.** Confirm what the cluster does with `graph_capture`, `action_ledger`, `active_memory`, `no_handback`, budgets (ns `llm` has `router-event-publisher` — read its spec/code path in idp). If the cluster lacks laptop-equivalent capture, founder decides: port modules via lane, or accept a documented capture gap with a dated fix. **No silent ledger gap.**
- **P2.T3 — Failover drill (the actual cutover test).** Front already implements: no local slot → new connections go to `https://llm.mumchimp.com`. Drill in a quiet window: `launchctl bootout gui/$(id -u)/com.estate.litellm-local-4001` and `-4002` (plists preserved), watch front serve completions from cloud (3 lanes: deepseek + gemini + one claude lane), measure latency, confirm pi/opencode sessions keep working on their next retry. Then restore local slots (`launchctl bootstrap` both plists) and confirm active slot returns.
  **Proof:** completion responses during the window + cluster pod log lines + front log showing cloud routing; before/after `~/.estate/router-state/active` recorded; /fleet shows the calls.
- **P2.T4 — Make cloud primary, local thin-idle.** Only after P2.T1–T3 green: set front/slot policy so local slot is standby (front prefers cloud; local slot kept alive, minimal config: laptop key + ollama local lanes only). Ship via lane. The heavy 116-thread local litellm becomes idle-tiny. **Do not delete the local slot** (invariant §2.7).
- **P2.T5 — Router fail-fast under saturation.** Add to the platform router (both renderers): when overloaded, return 503 quickly instead of accept-and-hang, so client retries back off instead of piling connections. Ship via lane + production proof under synthetic load on the cluster (never on the live laptop during a storm).
**Rollback for the phase:** bootstrap local slots; revert the front-policy lane; clients never changed, nothing else to undo.

---

### PHASE 3 — Temporal to cluster (founder-gated)

**Gate:** consumer map shows no remaining local submitters; one real workflow completes on cluster temporal from the production path; local dev server stopped 7 days with no errors, then removed.
- **P3.T1 — Consumer map (no changes).** `rg -l "61938|61866|temporal" ~/.estate/runtime ~/.estate/libexec ~/.estate/intents ~/.estate/bin ~/Library/LaunchAgents` plus the sovereign engine (`sovereign/engine/`, `SessionWorkflow`) and `sovereign-worker` on cluster. Sample transient connections hourly for 24h: `lsof -nP -iTCP:61938 -sTCP:ESTABLISHED` into the evidence log. Output: table of who submits locally vs to cluster.
- **P3.T2 — Point consumers at cluster temporal** (config/lane per consumer; cluster temporal already deployed).
- **P3.T3 — Founder decision gate:** retire local dev server `:61938` (spec divergence, §3). If approved: stop it (**not** launchd-managed; `kill <pid>`), keep its data dir 7 days, then remove. If rejected: make it launchd-managed + load-gated instead and move on.
**Proof:** real `SessionWorkflow` completion on cluster with production log line; zero new connections to `:61938` for 7 days.
**Rollback:** restart `temporal server start-dev --port 61938 ...` (exact cmdline in evidence log); repoint consumers back.

---

### PHASE 4 — Backstage / fleetview / NATS / API door

**Gate:** Backstage/Face functional without any laptop process; local NATS stopped with no clients for 7 days; laptop `kubectl proxy` retired after estate-bridge proven.
- **P4.T1 — Backstage on cluster is the only UI.** Local backstage labels stay disabled. Catalogue/Face at `catalogue.mumchimp.com/face/` must not forward intents to laptop `:18790` (spec defect A11) — coupling removal designed together with P5's read path; ship via lane to idp.
- **P4.T2 — Bus reachability.** Existing port-forward `14222→4222` (event-bus). Point the one known local NATS client (fleetview-backend) at `nats://127.0.0.1:14222` (env override, not code) or move that client to the cluster in the same lane. Verify publish/subscribe on real subjects (`estate.agent.*`). Spec A23 measured laptop can't resolve `nats.event-bus.svc` — never rely on in-cluster DNS from the laptop.
- **P4.T3 — Retire local NATS.** After zero local clients for 7 days: `launchctl bootout gui/$(id -u)/ai.estate.nats` + disable; keep the `~/.estate/nats` archive (in preflight backup) and delete the 3 corrupted `nats.broken-*` dirs.
- **P4.T4 — One API door.** Adopt estate-bridge (Flux-managed) for phone/tailnet: re-issue `founder-phone` credentials (expired 2026-10-08) via the vault/Bitwarden flow, update `~/.estate/estate-cluster.yaml`, prove a real `kubectl get ns` from the phone path. Then kill the laptop `kubectl proxy` (PID 3991) and remove its launcher. Review `--accept-hosts=.*` on the bridge as a security follow-up (lane; do not replicate the laptop's posture blindly).
**Rollback:** re-enable labels, restart local NATS/proxy (commands in evidence log).

---

### PHASE 5 — Data convergence (largest engineering; split into lane-sized steps)

**Gate:** Postgres is the read/write master for `estate.db`+`outbox.db` consumers; laptop sqlite is a rebuilt cache; ledgers land on R2 continuously; nothing lost (row counts + sampled record hashes before/after).
- **P5.T1 — Schema + writer/reader inventory.** `outbox.db`: writer = `action_ledger` module (file counter 31904 at time of writing); `estate.db`: readers = fleetview `/fleet`, writers = claim/checkpoint bin scripts + executor (verify with `rg -l "estate.db|outbox.db" ~/.estate ~/Documents/code/idp`). Dump schemas (`sqlite3 .schema`) into the evidence log; design Postgres DDL in `estate-rw.estate-db` (one-Postgres law).
- **P5.T2 — Dual-write then cut over** per store: writers dual-write sqlite+Postgres → backfill → compare counts/hashes → flip reads (fleetview first, behind a flag) → flip writes → sqlite becomes rebuildable cache (spec line 1929). Each step its own lane with production proof.
- **P5.T3 — Ledgers to R2.** Ship `action-ledger.jsonl` / `efficiency-ledger.jsonl` to the estate R2 bucket (raw jsonl, date-partitioned; parquet optional later). Local files rotate (P0.T4). Restore-test one partition.
- **P5.T4 — Graph sessions to git.** Resolve drift between `~/.estate/graph/estate-graph` and `~/Documents/code/estate-graph`; commit the 572 session markdowns (scrub secrets per estate-core law) so the laptop copy is disposable.

---

### PHASE 6 — Steady-state operations

- **P6.T1 — Runbook** (§7) adopted; alerts wired through `hc-wrap.sh` for backup age, front health, drift check, disk, load-gate skips; each safeguard visible deciding (pass/refuse) on /fleet.
- **P6.T2 — Reboot cadence.** Founder-approved reboot window (e.g. weekly, after agent checkpoint) — the 2026-10-24 storm class is not fully preventable without periodic resets on 8GB.
- **P6.T3 — Drills.** Monthly: restore one SQLite backup from R2 + failover drill (P2.T3) + phone-door check. Record in growmos journal.
- **P6.T4 — Capacity review.** If the laptop still hosts heavy processes after P4, escalate: move more or upgrade hardware — do not silently accept the old steady state.

---

## 6. Proof standards (apply to every task)

- A cutover is proven by **production traffic**: a real completion response + the serving pod's request log; a real workflow completion; real NATS pub/sub on real subjects. HTTP 200 on a health endpoint is *liveness*, never proof of function.
- **Done = operational:** used on the real path, and visible live on /fleet where the capability has a surface (a lane is operational when /fleet shows real calls through it; a safeguard when /fleet shows it deciding pass/refuse).
- Backups are proven by **restore**, not file existence: integrity check + row counts + one full-file hash comparison.
- "Load is better" is proven by `uptime` + swap samples over ≥30 min, not one reading.
- Quote actual log lines/outputs in `~/.estate/migration/log.md`. Report only done or seriously blocked; blocked carries the intent run, exit status, and printed line.

## 7. Operational runbook (steady state)

**Daily (automated, load-gated):** front :4000 real completion on one lane; restic receipt (latest snapshot <26h); disk free ≥15%; drift check green; count of load-gate skips (trend up = capacity problem).
**Weekly:** work-audit + prune LANDED worktrees; log sizes; watchdog kickstart count (target 0; >3/week = investigate); restore-test one random small file from R2.
**Monthly:** full SQLite restore drill; router failover drill; phone-door `kubectl get ns`; review exception ledger (any new harness glue?); reboot window.
**Alert thresholds:** 1-min load >12 sustained 15 min; swap free <500MB; disk >85%; backup age >26h; drift check red; front real-completion failure 2 consecutive checks.

## 8. Rollback master plan

Any phase: clients were never reconfigured, so **client rollback = none needed**. Router: bootstrap local slots, revert the front-policy lane. Temporal/NATS/Backstage/proxy: restart local processes (exact commands + plists archived in `~/.estate/migration/` before each change). Data: dual-write means sqlite is never behind until the final write-flip; final flip has a dated restore point from P0.T1/P0.T2. Cluster: revert the lane's change on a new lane; Flux converges back.

## 9. Appendix

### 9.1 Disabled jobs and how to re-enable
`launchctl enable gui/$(id -u)/<label>` (then `launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/<label>.plist` if booted out). The 11 interval jobs in §1.2 + `ai.estate.backstage-backend` + `ai.estate.fleetview-frontend` (latter two stay off until P4). `ai.estate.disk-clean` was already disabled before today.

### 9.2 Key ports (laptop)
`4000` front (clients' only door) · `4001/4002` litellm slots (active in `~/.estate/router-state/active`; **4002 active now**) · `4222/8222` NATS · `61938` Temporal dev (orphan `:61866` killed) · `7107` backstage (down) · `18790` fleetview-backend · `8091` voice-router · `8766/8767` kimi/deepseek bridges · `8770` mac-door · `8787` board_serve · `8788` cockpit · `8791` fleetview uvicorn · `8001` laptop kubectl proxy (retire P4.T4).
Forwards to cluster: `14222`→NATS 4222, `18222`→NATS 8222, `15432`→Postgres 5432, `18000`→unified-memory, `18888`→searxng.

### 9.3 Cluster
OKE API `https://141.147.80.229:6443`; contexts `context-estate-crq7jwxsjxq`, `oke` (rancher-desktop = stale). ns: `llm`, `event-bus`, `estate-db` (CloudNativePG `estate-rw`), `temporal`, `backstage`, `mcp`, `unified-memory`, `voice-router`, `estate-bridge`, plus platform (flux, external-secrets, cert-manager, keda, kyverno, spire, coroot, robusta, monitoring, chaos-mesh, weave-gitops, crossplane). Tailnet `tail3f2ff4.ts.net`; laptop = `roses-macbook-pro` = `100.98.58.115`; linux nodes include `backstage-fleetview-mac` (100.83.63.31, ssh:22 times out), `hermes-pod-1`, `otto-pod-1`, `jit-broker`.

### 9.4 Secrets by name (never values)
`LITELLM_LAPTOP_KEY` (laptop router key) · `MCP_GATEWAY_KEY` · `GROQ_API_KEY` · `MAC_DOOR_TOKEN` (vault `secrets/dev/`) · `LITELLM_MASTER_KEY` (cluster) · vendor keys via Bitwarden→`kubectl -n llm` · age identity `~/.config/prospector/age-key.txt` · ledger signing `~/.estate/keys/agent.pem`.

### 9.5 Open questions to resolve in order
1. Cluster litellm auth reality (P2.T1) — blocks router spend.
2. Local temporal consumers (P3.T1).
3. restic env/binary provenance (P0.T2).
4. Cluster capture/ledger parity (P2.T2).
5. fleetview read path off sqlite (P4/P5 design).
6. Graph drift (P5.T4).
7. Who besides action_ledger writes `outbox.db` (P5.T1).
8. Whether Kimi Code stays a documented estate bypass (P1.T3).

### 9.6 Useful existing assets (do not rebuild)
`front.py` cloud fallback (the whole cutover seam) · estate-bridge (in-cluster API door) · `work-audit` and `lane-submit` intents · `hc-wrap.sh` receipts · `router_catalog.py` harness adapters · `secret-load` vault flow · Delegated Estate spec phase-gate discipline · restic→R2 script + retention (once repaired) · Greenlane runbook `docs/runbooks/greenlane.md` · placement ladder `docs/decisions/0034-...`.
