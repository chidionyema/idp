# Mac remote desk (iPhone → Mac over Tailscale)

Tracked: crew#562. Founder spec verbatim on the issue. This is a laptop-access convenience for
the founder, not a platform layer (crew#66 decision, a0d64ea4): it does not make the Mac
load-bearing for any workload, and it is not the Hermes fix (crew#516 CP4).

What a session can do (LAW 24, in git): the `Brewfile` and this checklist. What only the
founder's hands can do — and no session will do — is everything under "Founder, one sitting":
system/security settings, credentials, and pairing. No IPs, usernames or credentials are
recorded here; every value below is a placeholder the founder fills in on his own machine.

## Run once (any session)

```
brew bundle --file docs/founder/mac-remote-desk/Brewfile
```

Installs (via Homebrew, the mature tool — LAW 43, no wrapper script):

- [x] `tap LizardByte/homebrew`
- [x] `brew sunshine` (`brew services list` shows `sunshine started`, measured 2026-08-29)
- [x] `cask deskpad` (`/Applications/DeskPad.app` present, measured 2026-08-29)
- [x] Tailscale is the App Store build already on the Mac; the `tailscale` cask is the standalone
      build and would fight it for the tunnel, so the Brewfile does not name it

## Founder, one sitting

What is left for your hands, measured on this Mac on 2026-08-29: the two Privacy & Security
grants, Tailscale "Run at Login", the DeskPad display, Sunshine's encoder settings, the phone
(Moonlight pairing, Tailscale, the Shortcut) and the four acceptance tests. Everything ticked
`[x]` below was measured, not assumed; `bin/idp-mac-adopt-otto --check` re-measures the Mac side.

Phase 1 — Host provisioning:

- [ ] System Settings → Privacy & Security: grant Screen Recording to DeskPad and to Sunshine
- [ ] System Settings → Privacy & Security → Accessibility: grant Sunshine
- [x] System Settings → General → Sharing: Remote Login (SSH) is ON (`nc -z 127.0.0.1 22`
      succeeded, measured 2026-08-29; `bin/idp-mac-adopt-otto --check` re-measures it)
- [x] Power policy `sudo pmset -a disablesleep 0 sleep 0 womp 1`: `pmset -g` shows `sleep 0`,
      `womp 1` (measured 2026-08-29)
- [x] `brew services start sunshine` (running, measured 2026-08-29)

Phase 2 — Network & virtual display:

- [ ] Tailscale menu → Settings: turn "Run at Login" ON (measured OFF on 2026-08-29:
      `TailscaleStartOnLogin = 0`; a system setting, so your hand, not a session's). Signed in
      with SSO already; the host's tailnet IP is measured into `clusters/oke/estate-config.yaml`, nothing
      to record
- [x] Otto's way in is "Remote Login (SSH)" above, nothing more. Tailscale SSH does not run in the
      App Store Tailscale build ("The Tailscale SSH server does not run in sandboxed Tailscale GUI
      builds", measured on this Mac 2026-08-29; tailscale.com/kb/1193). Your Mac already carries
      the tailnet tag `tag:founder-mac` (measured the same day), so the cluster reaches it on
      port 22 by a key that CI minted (`bin/idp-bootstrap-macrun`) and `bin/idp-mac-adopt-otto`
      authorises here — run from a session on this Mac, no paste. The tailnet policy
      (`platform/tailscale/policy.hujson`, git-tracked, CI-applied) lets `tag:k8s` at the Mac on
      22 and 5900 only, and your own login at the Mac on every port, so Moonlight, the Shortcut
      and screen sharing keep working and the next person added to the tailnet inherits nothing.
- [x] Nothing to tell anyone: your Mac's short username and tailnet IP were measured on the Mac
      and sit in `clusters/oke/estate-config.yaml` (`FOUNDER_MAC_USER`, `FOUNDER_MAC_TS_IP`); your
      Tailscale login is read from the tailnet's owner record by `bin/idp-tailscale-policy`
      (`FOUNDER_TAILNET_USER` stays empty in git and only overrides). The remote desk waits on the
      pairing PIN and nothing else.
- [ ] DeskPad: create a virtual display at 1170x2532, scaled/HiDPI, mode Extended (not Mirrored)
- [x] Sunshine Web UI (`https://localhost:47990`): admin username/password set
      (`~/.config/sunshine/sunshine_state.json` carries a username and a salted password,
      measured 2026-08-29; the values stay yours)
- [ ] Sunshine settings: Target FPS 60/120; Encoder = Apple VideoToolbox (HEVC); Video Format =
      NV12 or P010

Phase 3 — iPhone client:

- [ ] Tailscale app on the iPhone, signed into the same tenant
- [ ] Moonlight app installed; add host by `<HOST_TAILSCALE_IP>`
- [ ] Pair using the 4-digit PIN shown in the Sunshine Web UI (0 paired clients on
      2026-08-29 — this is the step the remote desk is waiting on)
- [ ] Moonlight stream settings: Bitrate 20 Mbps; Frame Rate = host; On-Screen Controls Hide

Phase 4 — iOS Shortcut "Launch Remote Mac" (two actions):

- [ ] Action 1 — Run Script over SSH: host = the Mac's tailnet IP (Tailscale app on the phone
      shows it under the Mac's name), port 22, user = your Mac short username, authenticate with
      an SSH key (never a password; Shortcuts generates the key and shows the public half — add
      it with `bin/idp-mac-adopt-otto --shortcut-key '<paste>'` from a session on the Mac),
      script `caffeinate -u -t 2`
- [ ] Action 2 — Open App: Moonlight

## Phase 5: Verification & Acceptance Testing

- [ ] Cold Wake Test: with the Mac locked/sleeping, the Shortcut wakes the screen and opens
      Moonlight
- [ ] Aspect Ratio Check: the stream is edge-to-edge on the iPhone, no letterboxing
- [ ] Network Portability: the stream survives a Wi-Fi → cellular handoff
- [ ] Latency Verification: the cursor stays smooth at 60 FPS over cellular

DONE = founder receipt against the four items above (crew#562 CP3).
