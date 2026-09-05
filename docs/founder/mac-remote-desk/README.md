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

- [ ] `tap LizardByte/homebrew`
- [ ] `brew sunshine`
- [ ] `cask deskpad`
- [ ] `cask tailscale`

## Founder, one sitting

Phase 1 — Host provisioning:

- [ ] System Settings → Privacy & Security: grant Screen Recording to DeskPad and to Sunshine
- [ ] System Settings → Privacy & Security → Accessibility: grant Sunshine
- [ ] System Settings → General → Sharing: turn Remote Login (SSH) ON
- [ ] Power policy: `sudo pmset -a disablesleep 0 sleep 0 womp 1`
- [ ] `brew services start sunshine`

Phase 2 — Network & virtual display:

- [ ] Tailscale: sign in with SSO, turn "Run at Login" ON, record the host's Tailscale IP as
      `<HOST_TAILSCALE_IP>` (kept by the founder, never committed — LAW 46/21)
- [ ] `tailscale up --ssh --advertise-tags=tag:founder-mac`: turns on Tailscale SSH (node-identity
      auth, no key) and tags this device `tag:founder-mac`, the one the tailnet policy names
      (`platform/tailscale/policy.hujson`, crew#516 CP5, founder's locked spec crew#66 5451926212).
      That policy is git-tracked and CI-applied (`bin/idp-tailscale-policy apply`, run from
      oke-check's apply job) — no admin-console edit, no ACL step here. Separate from the
      "Remote Login (SSH)" toggle above, which the iOS Shortcut uses; this one is what Otto's
      sidecar (`platform/hermes-agent/tailscale.yaml`) reaches through `mac-run`.
- [ ] DeskPad: create a virtual display at 1170x2532, scaled/HiDPI, mode Extended (not Mirrored)
- [ ] Sunshine Web UI (`https://localhost:47990`): set admin username/password
      (`<SUNSHINE_ADMIN_USER>` / `<SUNSHINE_ADMIN_PASSWORD>`, kept by the founder)
- [ ] Sunshine settings: Target FPS 60/120; Encoder = Apple VideoToolbox (HEVC); Video Format =
      NV12 or P010

Phase 3 — iPhone client:

- [ ] Tailscale app on the iPhone, signed into the same tenant
- [ ] Moonlight app installed; add host by `<HOST_TAILSCALE_IP>`
- [ ] Pair using the 4-digit PIN shown in the Sunshine Web UI
- [ ] Moonlight stream settings: Bitrate 20 Mbps; Frame Rate = host; On-Screen Controls Hide

Phase 4 — iOS Shortcut "Launch Remote Mac" (two actions):

- [ ] Action 1 — Run Script over SSH: host `<HOST_TAILSCALE_IP>`, port 22, user
      `<MACOS_USERNAME>`, authenticate with an SSH key (never a password), script
      `caffeinate -u -t 2`
- [ ] Action 2 — Open App: Moonlight

## Phase 5: Verification & Acceptance Testing

- [ ] Cold Wake Test: with the Mac locked/sleeping, the Shortcut wakes the screen and opens
      Moonlight
- [ ] Aspect Ratio Check: the stream is edge-to-edge on the iPhone, no letterboxing
- [ ] Network Portability: the stream survives a Wi-Fi → cellular handoff
- [ ] Latency Verification: the cursor stays smooth at 60 FPS over cellular

DONE = founder receipt against the four items above (crew#562 CP3).
