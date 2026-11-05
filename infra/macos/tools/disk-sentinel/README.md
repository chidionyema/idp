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

The user LaunchAgent samples the **home-volume** capacity every 60 seconds and opens a dashboard at user login; a second agent performs a read-only directory inventory at 03:15 daily. The dashboard auto-refreshes every 60 seconds.

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
