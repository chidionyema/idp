# Debug the cluster from your phone

A native app on the phone. No browser in this.

## Once

1. Install **InKuber** from the App Store. K8Z and Kuber do the same job if you
   prefer one of them -- all three read a standard kubeconfig, so the file below
   works with any of them.
2. Open the `estate-cluster.yaml` file you were sent and choose "Open in
   InKuber".

That is the whole setup. The file holds a URL and nothing else -- no token, no
certificate, no password -- so it is not a secret, and a lost phone leaks
nothing.

## After that

Open the app. Nodes, pods, logs, events, restarts, describe. Nothing to sign in
to and nothing to paste, ever.

## Where it runs

An Always Free Oracle machine inside the estate's network, always on, no laptop involved. It has
no public address at all: it reaches the cluster on Oracle's private endpoint, and your phone
reaches it over the tailnet. Nothing new is exposed to the internet.

Your Mac runs the same bridge as a second way in, for the case where that network is itself the
problem. `bin/idp-phone-kubeconfig` picks the Oracle one when it is up and falls back to the Mac,
and tells you which it wrote.

The bridge can read and nothing else -- pods, logs, events, nodes. It cannot delete anything and
cannot read secrets. A debugger that can cause an outage is not a debugger.

## Why it does not go straight from the phone

Oracle's API server admits exactly one source address -- the house -- set in
`platform/oci/terraform.tfvars` as `control_plane_allowed_cidrs`. A phone on
mobile data is not that address, and opening the allowlist wider is the one
thing the allowlist exists to stop. So the phone reaches a bridge, and the
bridge reaches Oracle. That holds for any phone app you pick.

The bridge is outside the cluster on purpose. When the cluster, the gateway or
the catalogue is the thing that is broken, this still answers, because none of
them is in the path.

Authentication happens on the bridge, per request, from the estate's cloud API key.
Who may reach the port is decided by the tailnet policy in
`platform/tailscale/policy.hujson`, which grants your own devices and nothing
else; removing a device from the tailnet cuts it off immediately.

## If the app cannot connect

- Tailscale has to be on and connected on the phone.
- If it fell back to the Mac, the Mac has to be awake.
- Restart the Mac's copy: `bin/idp-install-launchd kubeapi`.
- Regenerate the file, for example after the Mac's tailnet address changes:
  `bin/idp-phone-kubeconfig`, then AirDrop it from the Desktop.
