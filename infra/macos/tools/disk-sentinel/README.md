# Disk Sentinel - macOS developer workstation

A compact, **stdlib-only shell** disk-pressure observer with a continuously refreshed local HTML dashboard. No `node`, Python, brew, pip, root privileges, browser server, or third-party package is needed.

## Install

This tool is tracked in the estate at `infra/macos/tools/disk-sentinel/`. From Terminal:

```bash
cd ~/Documents/code/idp/infra/macos/tools/disk-sentinel
bash install.sh
```

`install.sh` installs the three LaunchAgent definitions that are tracked in `launchd/` (rendering
`${HOME}`), so the job launchd runs and the job the estate declares are the same file. To prove
the estate sees them: `bin/idp-inventory --plane mac` reports a `MANAGED` row per label.

### Storage-pressure modes

Free space decides what the supervisor is allowed to do. The thresholds are absolute, because a
percentage of a 113 GiB laptop is not the same safety margin as a percentage of a 1 TiB box:

| mode | free space | autonomous response |
|---|---|---|
| NORMAL | over 20 GiB | capacity tracking, growth attribution, retention accounting |
| WARNING | 15-20 GiB | identify fast-growing owners, report reclaimable capacity |
| CRITICAL | 3-15 GiB | discretionary work refused; verify low-risk reclamation before acting |
| EMERGENCY | under 3 GiB | optional investigations stopped; preserve headroom and notify |

The **15 GiB reserve** is the line an owner must not cross (provisional, founder 2026-11-05, on a
113 GiB volume): below it, discretionary disk-heavy work is refused and only observation and
verified reclamation may run. It is policy, not code: write `RESERVE_GIB=..` and `WARNING_GIB=..`
into `~/.local/state/disk-sentinel/policy.conf`, or read the effective values with
`disk-sentinel policy`.

`scan --auto` is refused in CRITICAL and EMERGENCY and records `DEFERRED` with the reason; `forensics`
and `elephant` refuse with exit 75 and print the policy. `--force` overrides for a human who has
decided the read-only cost is worth it. The monitor itself never stops: it is one `df` and a small
JSON write every 60 seconds, which is the one thing that must keep working when the disk is full.

### The investigation, in one door

Two investigations ship with this tool and are installed next to `sentinel.sh`, so there is one
disk-management surface rather than a second download:

```bash
disk-sentinel forensics --deep     # named suspects, throttled, ~185s budget
disk-sentinel forensics --quick    # ~55s budget
disk-sentinel elephant --deep      # every Data-volume entry, visited once, 20-minute budget
disk-sentinel elephant --quick     # 5-minute budget
```

**`forensics`** measures APFS volumes and snapshots, top-level directories, Docker/VM images,
Xcode and simulators, Node and agent footprints, files over 500 MiB, active processes, Disk
Sentinel's own health and the capacity delta across the run. Each check is time-bounded and
reported as complete, partial or timed out; nothing is deleted and no agent is stopped.

**`elephant` holds a single-flight lock**, so a second walk is refused rather than started
beside the first: two concurrent whole-volume walks were measured on 2026-11-05 writing the same
report file, each truncating the other's offsets until the report froze mid-progress.

**`elephant`** answers the question `forensics` cannot when every named suspect times out: it
walks the APFS Data volume **once**, attributes allocated blocks to buckets by owner at depth
1-5, lists files at or above 512 MiB, and reports `SCAN_STATE: COMPLETE`,
`TIME_BOUNDED_PARTIAL` or `PARTIAL_OR_RESTRICTED`. It de-duplicates hardlinks, prunes other
mounts, runs at `nice 15`, prints progress every 20 seconds and never re-walks a directory.
Read the coverage line before trusting a bucket: a `PARTIAL` walk means unknown areas may be
larger, not smaller.

`scan` remains the recurring, cheap inventory the dashboard reads. The two investigations are
run by hand when the cause is not yet known.

The user LaunchAgent samples the **home-volume** capacity every 60 seconds and opens a dashboard at user login; a second agent attempts a bounded, read-only directory inventory every 30 minutes until a full daily scan succeeds. High load defers work but records a non-success outcome; timeouts produce a partial inventory. The dashboard auto-refreshes every 60 seconds.

To see where space is used immediately:

```bash
"$HOME/.local/share/disk-sentinel/sentinel.sh" scan
"$HOME/.local/share/disk-sentinel/sentinel.sh" review
```

To open dashboard manually:

```bash
"$HOME/.local/share/disk-sentinel/sentinel.sh" open
```

To check health:

```bash
"$HOME/.local/share/disk-sentinel/sentinel.sh" status
launchctl print "gui/$(id -u)/dev.disksentinel.monitor"
```

Uninstall launch jobs without erasing diagnostics:

```bash
bash uninstall.sh
```

## Safety policy

- **Default: ZERO third-party deletion.** Projects, repositories, agent sessions, build directories, Docker data, Time Machine snapshots, caches and databases are left untouched. `scan` is read-only and lower priority. Do not sum inventory rows as paths may overlap.
- Automatic deletion is limited to the program's **own** diagnostic files older than 14 days and release of its own 64 MiB emergency write reserve. History is capped at 10,080 samples.
- The emergency reserve is only allocated when the volume has 25+ GiB available and released on EMERGENCY. This isn't a substitute for spare capacity or backups.
- Severity uses absolute and proportional headroom thresholds; trajectory is an estimate based on a history window, not a hard guarantee. If the free-space reading falls unexpectedly or a snapshot changes, investigate before cleaning anything.
- The dashboard is a local file, **not** a web service. It updates by reloading itself. No telemetry leaves the machine.
- A user LaunchAgent only runs while the user is logged in. Sleep, shutdown, broken macOS sessions, disk hardware failure or a completely full volume can interrupt observations. This system does not enforce quotas on third-party tools or guarantee no disk exhaustion.
- Developer files may be rebuildable but still be part of in-flight work. `brew cleanup -n`, `docker system df -v`, package-specific tools, and Xcode's managers are the proper review surfaces, followed by explicit approval under quiescence. Not `rm -rf`.
- `launchd` notifications use AppleScript. Check System Settings > Notifications permissions if they don't appear.

## Validation caveat

Tested for Bash syntax and dashboard rendering in a sandbox. A full production deployment requires verification on the target Mac, a logout/login, and testing alerting under **simulated readings**, not by filling the disk.

## Hardening roadmap

1. Introduce per-workload disk budgets and managed scratch directories with lease semantics and automatic TTL expiration.
2. Integrate your agents' task ledger, running CI jobs, Docker state and backups to prove quiescence before approving a cleanup.
3. Add operator-controlled off-device archive destinations, evidence receipts and a second volume for restore, rather than moving items to same-volume Trash.
4. For truly always-on coverage before login, use a separately reviewed root LaunchDaemon and signed native menu-bar UI with permissions controls.

## Version 1.1: deferred-scan fix

- The scan no longer returns success when high CPU load prevented inventory. DEFERRED, PARTIAL and COMPLETE are tracked visibly in the dashboard and `status` command.
- A dedicated `launchd` job retries every 30 minutes; once an inventory completes, subsequent scheduled checks skip I/O for 24 hours.
- Directory traversal is read-only, low-nice and limited to approximately 12 seconds per candidate and 90 seconds overall. Directory sizes may be partial/missing if a traversal timed out.
- The existing `scan --force` option is manual only and bypasses the high-load precheck, **not** the I/O timeouts. It can still compete with active work: use only after assessing load.
- This is **not** an autonomous third-party cleanup system. Deletion still requires owner-specific approval, in-flight evidence and verification.

To upgrade: extract the updated archive, then rerun `bash install.sh`. The installer backs up the prior `sentinel.sh`, reloads only Disk Sentinel jobs and leaves histories untouched.
