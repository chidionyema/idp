No-Issue: crew#562 (founder setup: iPhone → Mac remote desk) is the tracked item on the crew board; this repo has no issue for it.

Founder, 2026-08-29: "founder wanted a much better experience ... search ... heavenly setup." The remote desk was four community pieces stitched by hand (Sunshine host, DeskPad virtual display, Moonlight client, an iOS Shortcut over SSH) with a PIN pairing, an admin password in the vault and encoder settings he had to type. THE HEADLINE says buy the mature platform.

The one answer, read from the vendor's own pages on 2026-08-29 (support.jumpdesktop.com "Setup Unattended Remote Access", "Using the Display menu and virtual displays in Fluid sessions", "Cloudless Fluid"; changelog.jumpdesktop.com): Jump Desktop on the phone, the free Jump Desktop Connect on the Mac, Fluid in between. One virtual display sized to the phone is on every plan; unattended access is "add your account as a remote access user"; no ports, no VPN, end-to-end encrypted; Connect for Mac 10.15.22 shipped 2026-08-27. The Brewfile is now one line (`cask "jump-desktop-connect"`, Homebrew cask verified locally). What is left for the founder's hands: two privacy grants and one sign-in.

## Options considered
- Keep Sunshine + DeskPad + Moonlight and polish the checklist: four projects, no owner of the seam, PIN pairing and a vault password to babysit; rejected on THE HEADLINE.
- Screens 5 (VNC over Tailscale): the nicest Apple client, but VNC streaming on a phone is the laggy path and its Tailscale link needs an OAuth secret; rejected on experience.
- Chosen: Jump Desktop (Fluid). Risk, one sentence: on the standard plan signalling goes through Jump's cloud (cloudless Fluid is Teams Enterprise), so the founder's desk depends on his Jump sign-in; Otto's road to the Mac (SSH over Tailscale, crew#561) shares nothing with it.

## Architecture laws
- LAW 1 zero-gravity: `brew bundle` from the Brewfile -> Jump Desktop Connect on the Mac -> founder's account added once -> the Mac's icon on the phone; no estate service in the path
- LAW 2 fractal: `python3 -m pytest -q -p no:cacheprovider tests/test_incident_crew562_mac_remote_desk_brewfile.py`
- LAW 3 nervous system: `tests/test_incident_crew562_mac_remote_desk_brewfile.py` (the Brewfile is exactly the Jump cask; the founder section names the two grants, the sign-in and the three display settings and never again asks for a PIN, Moonlight, an encoder or an FPS; the risk section and Otto's independent road are pinned)
- LAW 4 calibration: `n/a: one package, one account`
Cost-delta-usd-month: 0
Drill: oke-check
Lifecycle: hermes-mac-run row on docs/reference/policy/credential-lifecycle.md

## Definition of done
1. Tracked item — crew#562
2. Code or config — `docs/founder/mac-remote-desk/{README.md,Brewfile}`, `tests/test_incident_crew562_mac_remote_desk_brewfile.py`
3. Gate proved both ways — the test refuses a Brewfile that brings back sunshine/deskpad/tailscale, a founder section that asks for a PIN or Moonlight, a README with a machine-specific literal; the shipped files pass (11 passed)
4. Reference doc — `docs/founder/mac-remote-desk/README.md` (the one answer, the risk in one sentence, what stays, what his hands do)
5. How-to and demo — `brew bundle --file docs/founder/mac-remote-desk/Brewfile` in a session on the Mac; the founder grants two permissions and signs in; one tap on the phone
6. Catalog entity — none (a founder device, not a workload)
7. Operational proof — the founder's first tap (Phase 5 checklist; DoD v2.1: his confirmation on crew#562)
8. Scheduled re-grade — Jump Desktop Connect auto-updates (cask `auto_updates`); otto-parity stays the estate-side check
9. Standard row — none changed; the stitched stack (bin/idp-bootstrap-sunshine, sunshine-egress, PairPhone panel, `sunshine-auth` vault row) is retired in the follow-up PR after his first use
10. Evidence block — below, attached by pr-evidence
Standard: Founder setup
Optimised: 9 -> 3 founder steps, 4 apps -> 2; cut: PIN pairing, vault password, DeskPad mode, Shortcut; memoised: "Keep After Disconnect" keeps the desk between taps; lazy: the retire-Sunshine PR waits for his first tap so nothing is deleted before the replacement is used

Author-session: 80471694

## Verify

Verify: `python3 -m pytest -q -p no:cacheprovider tests/test_incident_crew562_mac_remote_desk_brewfile.py`
Verify: `grep -c 'cask "jump-desktop-connect"' docs/founder/mac-remote-desk/Brewfile`
