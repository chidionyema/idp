# Debug the cluster from your phone

Turn Tailscale on and open **http://chidis-macbook-pro-1.tail3f2ff4.ts.net:4466/**

That is the whole thing. Pods, logs, events, describe, node conditions, Flux rows, restarts — the
same screens you would get from a laptop, in a phone browser, with nothing to sign in to beyond
Tailscale itself and nothing to paste.

## Why it is not on the catalogue

You asked for this after two dead ends, and both were the same mistake in different clothes. A
debugger has to outlive the thing it debugs.

- **On `catalogue.mumchimp.com/cluster/`** it would sit behind the same Traefik gateway and the
  same oauth2-proxy as the catalogue. The morning the catalogue is down is the morning you need
  it, and that is the morning it would be down too.
- **On the cluster at all** — even reached over Tailscale, bypassing the gateway — it would still
  be a pod on the same two worker nodes as everything it is meant to diagnose. A node event takes
  the patient and the doctor together.

So it runs on the estate Mac, and it reads Oracle's managed control plane directly. That API
server is Oracle's to keep up, not ours to lose: every pod in the estate can be gone and it still
answers. Nothing in the path is ours except the Mac.

## What is actually running

`headlamp-server` — the backend half of the Headlamp app already installed on the Mac, a
kubernetes-sigs project — kept alive by launchd (`ai.estate.headlamp`), started by
`bin/idp-headlamp-mac`.

It binds **only** the Mac's Tailscale address. Not `localhost`, not `0.0.0.0`: the UI does not
exist on the coffee-shop wifi, the home LAN, or any public port. The only network it is on is the
tailnet, and `platform/tailscale/policy.hujson` is deny-by-default with one rule that reaches the
Mac — `group:founder`, which is your login and nobody else's. Somebody else's device on the tailnet
cannot open it. That rule was already there; this needed no new access.

## Why it never asks you for a token

The prompt you hit — *"Please paste your authentication token"* — is Headlamp's **in-cluster** mode.
It is asking for a Kubernetes service account token: a bearer string with no expiry, no person's
name on it, and no audit trail, which is exactly what decisions 0003 and 0007 refuse. Do not paste
one, here or anywhere.

Out of cluster there is no prompt. The kubeconfig carries an exec plugin, and headlamp-server runs
`oci ce cluster generate-token` itself against the estate's OCI API key. Short-lived, minted per
use, and attributable to the estate identity rather than to an anonymous secret.

## If it does not answer

1. **Tailscale off on the phone.** Everything else is downstream of this.
2. **The Mac is asleep or off.** This is the one dependency the design has, and it is a real one:
   the Mac is the estate's out-of-cluster station, the same way it already is for Guacamole's
   screen and for Otto's `mac-run`.
3. **The OCI identity expired.** `bin/idp-oci-login` on the Mac, then
   `launchctl kickstart -k gui/$(id -u)/ai.estate.headlamp`. The log is `run/headlamp-launchd.log`.

## Reinstalling it

    bin/idp-install-launchd headlamp
