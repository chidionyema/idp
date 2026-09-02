# Tailscale images come from GitHub's registry

## Decision

Both Tailscale images the cluster pulls — the operator
(`ghcr.io/tailscale/k8s-operator`) and the proxy the operator creates
(`ghcr.io/tailscale/tailscale`) — are named from GitHub's registry, not Docker Hub.

## Why

The whole cluster leaves through one outbound address, and Docker Hub counts
unauthenticated pulls against that address. On 2026-09-02, the moment the pod-security fix
let both Mac proxy pods be created, they sat unable to pull with:

```
toomanyrequests: You have reached your unauthenticated pull rate limit
```

The quota had been burned by earlier pulls (the estate has hit this once before: 102
re-pulls of a container that never ran, 2026-08-31, recorded in
`platform/tailscale/operator.yaml`). Any anonymous `docker.io` pull can be refused on
quota some other workload spent — the failure arrives on whichever pod pulls next, which
makes it look random.

The vendor publishes the same images, same tags, on GitHub's registry, which sets no such
anonymous quota on public images. Both were measured before the change (2026-09-02):
`ghcr.io/tailscale/tailscale:v1.102.3` answers 200 with an `arm64` build in its index, and
`ghcr.io/tailscale/k8s-operator:v1.102.3` answers 200.

## Scope

This record moves the two Tailscale images. Other `docker.io` images in the estate share
the same exposure but each needs its own measured mirror before it moves; the guard below
holds only the Tailscale pair.

## Guard

`tests/test_incident_tailscale_dockerhub_rate_limit.py` fails any change that points
either Tailscale image back at Docker Hub.
