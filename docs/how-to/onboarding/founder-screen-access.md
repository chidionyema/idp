# Onboarding: seeing the estate Mac's screen

## What it is

Three ways to see and drive the estate Mac from wherever you are, decided on ADR 0009
(`docs/decisions/decision-matrix.yaml`, decision `founder-screen-access`). None of them stores a
password for you anywhere: the Mac login is typed at connect time and forgotten.

| Path | Use it when | Where |
|---|---|---|
| 1. Your phone (Moonlight) | you want the desktop at full speed, sound included | portal card **Pair my phone** |
| 2. Your browser | you are on any machine with a browser and the estate login | portal card **Estate Mac screen (in the browser)** |
| 3. Apple Screen Sharing | you are on another Mac on the tailnet | Finder › Go › Connect to Server |

## One-time setup (done once, on the Mac)

1. **System Settings › General › Sharing › Screen Sharing: on.** This is the only switch. It is a
   Mac security setting, so no session may flip it for you; the estate watches the port and pages
   you (`MacScreenSharingOff`) whenever it is off, with this line in the alert.
2. Nothing else. The Mac's tailnet address is an estate-config row (`FOUNDER_MAC_TS_IP`), the
   pairing credential for path 1 is minted by CI into the vault (`bin/idp-bootstrap-sunshine`,
   run on every `oke-check` apply), and the browser row rolls out with Flux.

## Each time

### Path 2 — browser

1. Open `https://catalogue.<zone>/screen/` (or the portal card). Sign in with the estate login if
   asked — the same one as the catalogue.
2. Click **Estate Mac**.
3. Type the Mac's username and password when prompted. They go to the Mac over the tailnet and
   are not stored.
4. The desktop is in the tab. Close the tab to disconnect.

### Path 1 — phone

1. Open the portal card **Pair my phone**; it shows a four-digit PIN field.
2. On the phone, open Moonlight, add the Mac, and read the PIN it shows.
3. Type that PIN into the portal card. Once. The phone stays paired.

### Path 3 — another Mac

Finder › Go › Connect to Server › `vnc://<the Mac's tailnet name>` › the Mac login.

## What "working" looks like

- Portal › Founder › **Estate Mac screen (in the browser)** and **Pair my phone** are both cards.
- No `MacScreenSharingOff` alert on your phone. If one arrives, the switch in step 1 is off.
- `bin/idp-verify` founder-surfaces row: `https://catalogue.<zone>/screen/` probes 200.

## When it does not

| You see | It means | Do |
|---|---|---|
| "connection refused" after clicking Estate Mac | Screen Sharing is off on the Mac | step 1 above; wait a minute |
| the login page instead of the connection list | the estate login expired | sign in again |
| pairing PIN rejected | the Sunshine credential was not adopted on the Mac | nothing; the next `oke-check` apply re-mints it and the alert names it |

Everything here is measured, not remembered: the probe (`platform/monitoring/rules/founder-mac-screen-sharing-probe.yaml`),
the alert (`platform/monitoring/rules/estate.yaml`), the surface list
(`backstage/founder/catalog-info.yaml`).
