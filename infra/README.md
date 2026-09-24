# infra/ — declarative device provisioning, every OS the estate trusts

This directory is the **install surface** for every device the estate trusts: a founder's
Mac, a CI runner on Ubuntu, a dev container on Debian, an enterprise customer's laptop.
One orchestrator script, per-OS install artifacts, identical status contract.

## What's here

```
infra/
├── macos/                              brew + launchd install on macOS
│   ├── Brewfile                        pinned formulae + casks
│   ├── LaunchDaemons/
│   │   ├── com.idp.spire-agent.plist   user LaunchDaemon
│   │   ├── com.idp.executor.plist      root LaunchDaemon
│   │   └── com.estate.jit-device-renew.plist
│   └── spire-agent.conf.template       rendered to /etc/spire/agent.conf at install
└── linux/                              apt + systemd install on Debian/Ubuntu
    ├── apt-lists/
    │   └── runtime.txt                 apt-get install input
    └── systemd-units/
        ├── spire-agent.service         user systemd unit
        ├── jit-device-renew.service    user systemd unit
        ├── jit-device-renew.timer      every-10-minutes timer
        └── executor.service            system-wide unit (FOUNDER FENCE)
```

The orchestrator `bin/idp-device-provision` dispatches by `uname -s`:

| Platform | Package mgr | Service mgr | Source files |
| --- | --- | --- | --- |
| macOS (Darwin) | Homebrew | launchd | `infra/macos/` |
| Linux | apt | systemd | `infra/linux/` |
| Windows | winget (planned) | SCM (planned) | dispatched stub |

## Subcommands

```
bin/idp-device-provision install       lay everything declared + render templates
bin/idp-device-provision upgrade       upgrade + re-render
bin/idp-device-provision uninstall     reverses install
bin/idp-device-provision status        JSON on stdout (consumed by mumchimp.com/devices)
bin/idp-device-provision doctor        human-readable status + remediation
bin/idp-device-provision self-test     parses every artifact; CI-runnable on every PR
```

The status JSON contract is:

```json
{
  "platform":  "macos" | "linux",
  "brew":      {"installed": 0|1, "status": "..."},
  "apt":       {"installed": 0|1, "status": "..."},
  "tailscale": {"installed": 0|1, "status": "..."},
  "spire":     {"installed": 0|1, "status": "..."},
  "executor":  {"installed": 0|1, "status": "..."},
  "renew":     {"installed": 0|1, "status": "..."}
}
```

`platform` reports the current `uname -s` classification; `brew` is `not_applicable_for_platform`
on linux and `apt` is `not_applicable_for_platform` on macOS (the shape is stable across
platforms; only the populated field is relevant to the running OS).

## CI coverage

`.github/workflows/device-provision-test.yml` is the matrix:
- `macos-14` runner: install → status → uninstall → install (idempotency proven)
- `ubuntu-24.04` runner: same flow on Linux

`bin/idp-ci` has the `mac-provision` rung that runs on every PR — Brewfile parses,
plist XML well-formed, systemd unit well-formed, the script parses.

## Bootstrap on a fresh device

The one-time path a new machine:

```bash
# 1. Homebrew (mac) or apt-get (linux) — already present on every GitHub Actions runner
#    and most enterprise images. Otherwise install per the standard idiom.

# 2. Clone this repo at the version you want, e.g.
git clone https://github.com/chidionyema/idp.git /path/to/idp

# 3. Run the orchestrator
cd /path/to/idp
bin/idp-device-provision install

# 4. (Founder only) install the executor LaunchDaemon/systemd unit. This step
#    needs sudo: the orchestrator refuses, by design (FOUNDER FENCE).
sudo bin/idp-executor-install

# 5. (Any device) one-time per-Mac identity proof -- age identity.
bin/idp-jit enroll

# 6. Verify
bin/idp-device-provision doctor
```

After step 5, the LaunchAgent (Mac) or systemd timer (Linux) renews the
agent-reader kubeconfig every 10 minutes. The founder never touches
credentials again on this machine.

## Constraints

- **Per AGENTS.md SPIFFE primary rule 3**: an agent (CI, LLM, IDE) never asks
  the founder to log in or run a script. The orchestrator IS the one
  script; everything else is on a timer.
- **The executor daemon stays a FOUNDER FENCE**: `sudo bin/idp-executor-install`
  refuses an agent-invoked shell. The executor unit is in `infra/{macos,linux}/`
  for the founder to lay once per machine, by hand.
- **No platform-specific config files get committed** — every per-device
  secret (SPIRE join token, trust bundle, OCI secrets) is fetched from the
  estate vault at install time, never checked in.

## Adding a new platform

1. Add `infra/<platform>/` with the package list and service manifests
2. Extend `detect_os` in `bin/idp-device-provision` to classify `uname -s` to your platform
3. Add `install_<platform>` and `wire_<platform>` functions
4. Add a CI runner entry to `.github/workflows/device-provision-test.yml`
5. Add a status row to the `status_json` function (one field per row is fine)

The status JSON contract has stable field order. New platforms add fields; they
do not reorder or rename.
