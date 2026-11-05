# infra/macos/tools - the Mac host tools the estate owns

Three tools arrived as downloads on 2026-11-05 and are kept here instead: tracked, declared,
and measured. Nothing here is a copy of an estate layer - each is a Mac host utility with no
in-cluster equivalent, and each is listed in the table below with where it installs and how
the estate knows it is still there.

| tool | what it does | installs to | measured by |
|---|---|---|---|
| [disk-sentinel](disk-sentinel/) | 60-second disk-pressure sample, a bounded read-only inventory retried every 30 minutes until complete, the deep forensic investigation, local HTML dashboard | `~/.local/share/disk-sentinel`, `~/Library/LaunchAgents/dev.disksentinel.*.plist` | `bin/idp-inventory --plane mac` - three `MANAGED` rows; `sentinel.sh status` reports the investigation verdict |
| [ai-fleet](ai-fleet/) | login-time supervisors for DSH web, the Kimi web UI, and the desktop agents | `~/Library/Application Support/AI Fleet`, `~/Library/LaunchAgents/local.aifleet.*.plist` | `bin/idp-inventory --plane mac` after `install` |
| [pi-node](pi-node/) | repairs the pinned Node runtime Pi needs, without nvm or sudo | `~/.local/opt/pinned-node`, `~/.local/bin/{node,npm,npx}` | `pi --version` in fresh bash and zsh; the script's own PASS line |

## Why a tracked plist is the whole point

`bin/idp-inventory --plane mac` reads `launchctl list` and marks a job `MANAGED` only when a
file with that exact label name - `<label>.plist` - is tracked in a repository. Everything else
is `ORPHAN`, "loaded, plist in no repository": a thing running on the founder's Mac that no
commit declares. That is how the three disk-sentinel jobs were running on 2026-11-05 while the
estate could not say where they came from.

So the rule for this directory:

- **The plist in `disk-sentinel/launchd/` is the source of truth.** `install.sh` renders
  `${HOME}` and installs it; it does not build the plist from a second heredoc.
- **The label in the file equals the file name**, because that is what the inventory matches on.
- **`${HOME}` is the only placeholder.** It is the same substitution `bin/plist-gate` applies to
  `launchd/*.plist.tmpl`, so `plutil -lint` never sees an unparseable file.

## Maintaining them

```bash
# disk-sentinel: reinstall from this tree (idempotent; reloads only its own jobs)
bash infra/macos/tools/disk-sentinel/install.sh
"$HOME/.local/bin/disk-sentinel" status

# disk-sentinel: stop the jobs, keep the diagnostics
bash infra/macos/tools/disk-sentinel/uninstall.sh

# ai-fleet: install | status | disable
bash infra/macos/tools/ai-fleet/ai_fleet_autostart_macos.sh status

# pi-node: repair, then prove it in fresh shells
bash infra/macos/tools/pi-node/repair_pi_node_macos.sh
```

Then prove the estate sees them:

```bash
bin/idp-inventory --plane mac --out /tmp/inv
python3 -c 'import json;print([r["name"] for r in json.load(open("/tmp/inv/mac.json")) if r["verdict"]=="MANAGED"])'
```

## The boundary these tools keep

None of the three takes root, writes a shell profile (pi-node's one PATH line is the exception,
and it is idempotent), runs a server, or deletes anything a person made. Disk Sentinel deletes
only its own diagnostics older than 14 days; AI Fleet only opens apps that are already installed;
pi-node only replaces the `node`/`npm`/`npx` symlinks it owns and backs up what it replaced.

That is deliberate. A host tool that reaches wider than its own installation is a layer the
estate did not declare, and section 6 says a second copy of a layer gets deleted - not trusted.
