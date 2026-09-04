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

## Why it goes through the Mac

Oracle's API server admits exactly one source address -- the house -- set in
`platform/oci/terraform.tfvars` as `control_plane_allowed_cidrs`. A phone on
mobile data is not that address, and opening the allowlist wider is the one
thing the allowlist exists to stop. So the phone reaches the Mac over the
tailnet, and the Mac reaches Oracle. That holds for any phone app you pick.

The Mac is outside the cluster on purpose. When the cluster, the gateway or the
catalogue is the thing that is broken, this still answers, because none of them
is in the path.

Authentication happens on the Mac, per request, from the estate's cloud API key.
Who may reach the port is decided by the tailnet policy in
`platform/tailscale/policy.hujson`, which grants your own devices and nothing
else; removing a device from the tailnet cuts it off immediately.

## If the app cannot connect

- Tailscale has to be on and connected on the phone.
- The Mac has to be awake. It is the bridge.
- Restart the bridge: `bin/idp-install-launchd kubeapi`.
- Regenerate the file, for example after the Mac's tailnet address changes:
  `bin/idp-phone-kubeconfig`, then AirDrop it from the Desktop.
