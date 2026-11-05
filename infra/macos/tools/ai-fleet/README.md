# ai-fleet - login-time supervisors for the agent desktops

`ai_fleet_autostart_macos.sh` lays three user LaunchAgents so the agent surfaces come back
after a login:

| label | what it keeps up |
|---|---|
| `local.aifleet.dsh` | DSH's own web server (`dsh web`), kept alive by launchd |
| `local.aifleet.gui` | the desktop apps that are installed - Kimi Code, Codex (ChatGPT), Claude - reopened every 60 s if closed |
| `local.aifleet.kimiweb` | the Kimi CLI's `web` server, only when Kimi Code Desktop is absent |

It is **declared here and deliberately not activated** (founder, 2026-11-05). The estate already
runs `ai.estate.dsh-web`, and two supervisors for one DSH web process is a second copy of a
layer - they would race for the port and neither would be the truth. The script is kept because
it is the handler for the case the estate's own agent does not cover: a Mac with the desktop
apps installed and no estate job running.

```bash
bash ai_fleet_autostart_macos.sh status    # what launchd thinks, read-only
bash ai_fleet_autostart_macos.sh install   # lay and bootstrap the three agents
bash ai_fleet_autostart_macos.sh disable   # boot out and remove the plists; apps keep running
```

## What it refuses, and why that matters

`install` is a preflight, not a best effort: if DSH's CLI is broken, or Codex, Claude or Kimi
is not discoverable, it exits `BLOCKED` before writing a single plist. A login-time supervisor
that silently starts two of four surfaces is worse than none - the founder sees a desktop that
looks provisioned and is not.

It never uses `sudo`, never edits a shell profile, and writes its state as plain lines
(`~/Library/Application Support/AI Fleet/*.path`), never as something a shell evaluates.

## If it is activated later

The plists are generated at install time into `~/Library/LaunchAgents/`, so `bin/idp-inventory`
will show `local.aifleet.*` as `ORPHAN` until those files are tracked with their exact label
names. If this tool is ever turned on for real, move its three definitions into a `launchd/`
directory here and have `install.sh` render them the way `../disk-sentinel/` does - do not leave
a running job with no tracked definition.

Before turning it on, retire `ai.estate.dsh-web` in the same change. One DSH web supervisor, not
two.
