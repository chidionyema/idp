# Merged is operating: one delivery path for the laptop plane

**Status:** phase 1 merged (#4537). Phases 2–4 are on branch `delegate/merged-is-operating`, phase 5
on `delegate/mio-fleet`. Built, not operating: nothing is operating until the pkg is installed
on this laptop. Tracked on crew#975. Graph: `risk/laptop-plane-delivery-gap`.

**One sentence:** a PR merged to `main` reaches the place it runs on the laptop by one governed
path, the executor runs nothing else, and Fleet shows each PR as merged → operating.

## The problem (measured 2026-09-27)

On the cluster, merge → Flux → running, and the Flux ledger proves it. On the laptop (ADR 0034
rung 5: `~/.estate` intents and helpers, the executor, harv), nothing delivers a merge:

- `IDP-Estate.pkg` postinstall (`installer/build.sh`) and `bin/idp-install-all:160` only
  `mkdir` empty `~/.estate/{bin,intents,libexec}`. No installer copies an intent, a helper or the
  executor.
- `~/.estate/bin/estate-execute` is a symlink into `~/.local/estate/releases/4ccf643ac/`, recorded
  as "built from agent-trunk, not main" (`.growmos/journal.md` L5206). No repo script references
  that directory, and it has not moved since 2026-09-25.
- The executor reads only `~/.estate/intents` (`estate-execute` L24); an intent cannot be tried
  from a worktree.

| | repo `origin/main` | installed | merged, never installed | installed ≠ repo | running, never merged |
|---|---|---|---|---|---|
| intents | 44 | 109 (incl. 45 backups) | 16 | 1 | 37 |
| libexec | 22 | 39 (incl. 1 backup) | 2 | 2 | 18 |

Each drifted file has a newer repo copy (e.g. `fleet-regression` lacks the merged voice-latency
step). Usage from `~/.estate/estate.db` `intent_tickets`: 8 of the 37 unmerged intents have ever
run.

## Decision (founder, 2026-09-27)

Adopt everything unmerged, then enforce. "Done" includes Fleet: it is the founder's surface for
work, agent delegation and monitoring.

## Phases

1. **Adopt (this PR).** 29 intents + 18 helpers into `platform/estate`. Found while adopting:
   - 8 "unmerged" intents (`shell-parse`, `shell-suggest`, `shell-verify`, `git-commit`,
     `git-branch`, `k8s-debug`, `hypotheses-race`, `ci-errors`) are byte-identical, bar the name
     line, to merged dot-named intents and have 0 runs. Not adopted (§6: no second copy).
   - `jev-setup` step 2 failed every run (`IndentationError`); rewritten in shell, home paths
     replaced by a `repo` arg and `$HOME`.
   - `node-pressure.sh` was not valid bash (unquoted JSONPath filter); quoted.
   - `k8s-diag.py` failed the estate Python standard; fixed.
   - `*-real` harness wrappers used an absolute home path; now `$HOME`.
   - The running `estate-execute` (agent-trunk build) is main's copy plus intent composition
     (`_run_composed`, `from:`). It is adopted too, with four lint fixes; otherwise the
     converger would install main's copy and drop composition.
2. **Converge (built).** `platform/estate/bin/estate-converge`, run by the root LaunchDaemon
   `ai.estate.converge` every 120 s. Layout:
   `/usr/local/estate/{src/idp.git, releases/<sha12>, releases/current, converge/{state.json,
   ledger.jsonl, lock}, sbin/estate-converge, logs/}`. Each run fetches `main`, cuts a
   read-only release of `platform/estate` (files 0444/0555, dirs 0555, sealed after the rename),
   flips `current` with one atomic rename, and relinks the console user's
   `~/.estate/{intents,libexec,bin/*}` into it. A hand copy is moved to `*.pre-converge-<ts>`,
   never deleted. It writes a ledger line (from/to sha, PRs carried, merge → operating latency)
   and keeps 5 releases. A run that finds nothing new writes no ledger line. A failed fetch
   leaves the running release untouched and sets `last_error`. The daemon updates its own
   `sbin` copy only after the candidate passes `--self-test`.
3. **Install (built).** `IDP-Estate.pkg` (`installer/build.sh`) is the one place a password is
   typed. It lays down the converger and its LaunchDaemon, and nothing else. Its postinstall
   refuses a converger that fails its self-test. The pkg is built, never committed.
4. **Refuse (built).** `estate-execute` runs only intents resolving inside `releases/current`:
   - A hand copy is REFUSED (exit 2).
   - An intent that exists only in a moved-aside copy says NOT MERGED.
   - `--from <worktree>` runs an unmerged intent, labelled `unmerged`.
   - Before the pkg is installed, the local copy runs, labelled `unconverged`. The harness
     never blocks on the network.
5. **Fleet (built).** `GET /fleetview/delivery` and the Delivery panel on /fleet show:
   - the converger state and ledger
   - unmerged and unconverged runs
   - delegate-build `empirical` results (never the builder's scratchpad)
   - the health of every estate launchd job
6. **Every job from a release.** A manifest maps each repo to its launchd jobs. The converger
   installs each job from a release of that repo's `main`, unloads orphans, and lists them on
   Fleet.
7. **harv.** kronos CI publishes the `harv` binary; the same converger installs it.

## No human step, no flake (founder, 2026-09-27)

"Telling you to run a script is dumb; we need intelligent and safe systems." "We can't have our
harness flaky." The founder chose root-owned releases installed by the GUI pkg, which is the one
place a password is typed. So:

- **Nothing to run by hand.** The pkg's README and Conclusion no longer tell anyone to open
  Terminal. The daemon converges on load and every 120 s after.
- **Safe.**
  - A lock stops concurrent runs.
  - Every git call has a timeout and cannot prompt.
  - Releases are root-owned and read-only.
  - The pkg's payload is exactly two files, so it never re-owns a shared directory such as a
    user-owned `/usr/local/bin`.
- **Tested without flakes.**
  - The tests use a temporary prefix, HOME and local git origin, with no network. Each suite
    runs three times.
  - Mutations prove the checks can fail: dropping the release seal, the self-test gate, link
    repair, the postinstall retry, or payload hygiene each fails a test.
  - `test_scheduler_venv` depends on host free disk (it refuses under ~1500M) and failed on
    this laptop with 1.4Gi free. It stays on the gap register.

## Gap register (2026-09-27)

Measured with `fleetview_backend.delivery` on this laptop: 40 estate launchd jobs (22 failing,
7 running, 7 ok, 4 orphaned); 0 run from a release.

| id | gap | status |
|---|---|---|
| G1 | a merge to main never reaches `~/.estate` | built: converger + pkg; operating once the pkg is installed |
| G2 | the executor runs any file in `~/.estate/intents` | built: `estate-execute` admits only `current` |
| G3 | jobs run from working checkouts (`idp-wt-fleetview-key`, estate-core, crew, maestro) | open: phase 6 manifest |
| G4 | 22 jobs failing | open: shown on Fleet; each fixed through its repo |
| G5 | 4 jobs' programs missing: `ai.estate.disk-clean`, `ai.estate.session-timeout`, `ai.hermes.runaway-reaper`, `ai.openclaw.gateway` | open: unloaded by phase 6 |
| G6 | `~/bin` has no provenance | open |
| G7 | litter: `~/.estate/.git`, `~/.local/estate`, empty `/usr/local/estate/0.1.0` | 0.1.0 removed by postinstall; rest open |
| G8 | Fleet did not show delivery | built: Delivery panel |
| G9 | harv not delivered (kronos PR #1) | open: phase 7 |
| G10 | ring3-egress credential | open |
| G11 | flux-deploy stages with `git add -A` | open |
| G12 | `feat/harv-intent` branch unmerged | open |
| G13 | pkg: builder's HOME rendered into a LaunchAgent, `$HOME`/`gui/0` as root, `/usr/local/bin` in payload, Terminal instructions, committed binary | fixed in `installer/` |
| G14 | Fleet shows the laptop sha, not the cluster sha beside it | open |
| G15 | `bin/idp-executor-install` (uid `idp_executor`, LaunchDaemon `ai.estate.executor`) is a second execution boundary | open: §6 decide one, delete the other |
| G16 | `test_scheduler_venv` fails on low host disk | open |

## Done

Operating, not built: a PR merged to `main` appears in `~/.estate` without anyone copying it, a
ledger line proves when, a hand-copied intent is refused, and Fleet shows all three.
