# Merged is operating: one delivery path for the laptop plane

**Status:** phase 1 in this PR, 2026-09-27. Tracked on crew#975. Graph: `risk/laptop-plane-delivery-gap`.

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
2. **Converge.** One LaunchAgent installed in `~/.estate` (TCC-safe) watches `origin/main`, cuts
   a read-only `releases/<sha>` from `platform/estate`, flips `current` atomically, and writes a
   ledger line (sha, time, PRs carried, drift). `IDP-Estate.pkg` and `idp-install-all` install
   this agent and nothing else into `~/.estate`, so first install and every update take one path.
3. **Refuse.** `estate-execute` runs only intents from `current`. `--from <worktree>` runs an
   unmerged intent for testing, labelled `unmerged` in the ledger and on Fleet.
   `estate-break-glass` stays for emergencies and every use is shown.
4. **Fleet.** A delivery view: each PR merged → operating (laptop release sha beside Flux), drift
   count, an alert when merge → operating passes its limit or the laptop falls behind `main`, and
   delegate-build runs showing `empirical` only. It joins the agent-job panel being built in the
   CP8/CP11 session rather than duplicating it.
5. **harv.** kronos CI publishes the `harv` binary; the same converger installs it.

## Done

Operating, not built: a PR merged to `main` appears in `~/.estate` without anyone copying it, a
ledger line proves when, a hand-copied intent is refused, and Fleet shows all three.
