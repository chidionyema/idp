# Mac remote desk (iPhone → Mac): Jump Desktop

The founder opens his Mac on his iPhone by tapping one icon. Nothing to pair, no PIN, no
virtual-display app to babysit, no Shortcut. That is the whole design, and it is bought, not
built (LAW 43, THE HEADLINE).

## The one answer

**Jump Desktop** (iPhone app, one-time purchase) talking to **Jump Desktop Connect** (free host
agent on the Mac) over Jump's **Fluid** protocol.

Why it wins, from the vendor's own pages read on 2026-08-29 (support.jumpdesktop.com, "Setup
Unattended Remote Access", "Using the Display menu and virtual displays in Fluid sessions",
"Cloudless Fluid"; changelog.jumpdesktop.com):

- **Phone-shaped desktop, automatically.** Fluid asks the Mac to create *one virtual display
  sized for the device you are holding* ("Single Virtual Display" preset, "Match Display
  Resolution", Retina). That single virtual display is included on every plan. It replaces
  DeskPad, the 1170x2532 hand-typed mode, and the aspect-ratio fiddling in one line.
- **Unattended, from anywhere, no ports.** Install Connect, add your Jump account as a remote
  access user, and the Mac's icon appears on the phone. No port forwarding, no VPN needed, LAN
  and direct paths are detected on their own. End-to-end encrypted.
- **Touch is the pointer.** Jump's gesture set (tap, two-finger scroll, pinch, long-press right
  click, a real keyboard bar) is built for a phone; Moonlight's is built for a game controller.
- **Kept alive by the vendor.** Connect for Mac 10.15.22 shipped 2026-08-27; 2026 fixes name
  headless Macs, virtual displays after reboot, macOS 26.6. Sunshine + DeskPad were two separate
  community projects with no one owning the seam between them.
- **"Keep After Disconnect"** leaves the virtual display and your windows where they were, so the
  next tap lands on the same desk.

What it replaces: Sunshine (host), Moonlight (client), DeskPad (virtual display), the "Launch
Remote Mac" iOS Shortcut, the Sunshine admin password in the vault (`sunshine-auth`), the PIN
pairing, and the Backstage "Pair phone" panel. Each of those is retired in the follow-up PR once
the founder has used Jump once (Definition of Done v2.1: his confirmation, not our merge).

## The risk, in one sentence

On the standard plan the connection is *brokered* through Jump's cloud (signalling; the session
itself is end-to-end encrypted and goes direct when it can); a fully cloudless Fluid link over the
tailnet exists but is a Teams Enterprise feature, so the founder's remote desk is one third-party
account (his Jump sign-in) away from Jump's uptime — Otto's own path to the Mac (SSH over
Tailscale, crew#561) does not depend on Jump at all.

## What stays

- **Tailscale** stays for Otto (`tag:k8s` → `tag:founder-mac:22`) and as the fallback road for a
  human (SSH, or Screen Sharing over the tailnet). Jump does not need it.
- **Remote Login** (sshd :22) stays for Otto.
- The Mac never sleeps on the wall: `sudo pmset -a disablesleep 0 sleep 0 womp 1` (Jump's own
  advice: "prevent the machine from going to sleep").

## Run once (any session)

- [ ] `brew bundle --file docs/founder/mac-remote-desk/Brewfile` (installs Jump Desktop Connect
      from the Homebrew cask `jump-desktop-connect`; it auto-updates)
- [ ] `sudo pmset -a disablesleep 0 sleep 0 womp 1`
- [ ] Remote Login on (already measured on, crew#561 `bin/idp-mac-adopt-otto --check`)
- [ ] Tailscale signed in and "Run at Login" (already measured on, crew#561)

## Founder, one sitting

What is left for your hands (a vendor sign-in and two macOS privacy grants cannot be done by a
pipeline; everything else above is done by a session):

1. On the Mac, open **Jump Desktop Connect** (installed by the Brewfile). System Settings →
   Privacy & Security asks for **Screen Recording** and **Accessibility** for Jump Desktop
   Connect: grant both.
2. In Jump Desktop Connect click **Add Remote Access User** and sign in with your Jump Desktop
   account (Google or Apple sign-in; SSO is the same account on the phone).
3. On the iPhone install **Jump Desktop** from the App Store (one-time purchase), open Settings
   → **Sign in** with the same account. The Mac's icon appears.
4. Tap the Mac. In the session's Display menu choose **Single Virtual Display**; leave
   **Match Display Resolution** on and tick **Keep After Disconnect**. Done — the next tap
   remembers it.

No Sunshine, no admin password, no FPS or Encoder settings, no Moonlight, no PIN, no iOS
Shortcut: those items were the stitched version of this page and are gone.

## Phase 5: Verification & Acceptance Testing

- [ ] Cold Wake Test: with the Mac locked, one tap on the phone brings up the login screen and
      a typed password lands (Connect handles the wake and the lock screen).
- [ ] Aspect Ratio Check: the desktop fills the phone in portrait and re-lays out on rotation
      without a black bar ("Match Display Resolution").
- [ ] Network Portability: same tap works on Wi-Fi, on 5G with Wi-Fi off, and on the tailnet.
- [ ] Latency Verification: typing in a terminal over 5G feels live (no visible key lag);
      scrolling a web page is smooth.
- [ ] Otto Parity: `gh workflow run oke-check.yml -f mode=break-glass -f playbook=otto-parity`
      is still green after the change (Jump and Otto share nothing).
