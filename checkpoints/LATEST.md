# RESUME HERE

2026-09-04T21:1xZ, session 5f6f4e72, lane idp.

## What is being built

crew#841 — the break-glass bridge moves off the founder's Mac. Today the phone reaches the
cluster through `ai.estate.kubeapi` on his laptop (idp#1589, merged). He objected: "while this
works fir now t crete dependency on laptop ... we need t consider debugging fro aother nachine".

## The design, after reading the VCN

The bridge does **not** need a public IP and does **not** need `control_plane_allowed_cidrs`
widened. Measured 2026-09-04T21:0xZ:

- the cluster has a private control-plane endpoint at `10.0.0.11:6443` as well as the public
  `141.147.80.229:6443`;
- the VCN has subnets `pub_lb-tiafzl` (public), `workers-tiafzl` (private, 10.0.144.0/20),
  `cp-tiafzl`, `int_lb-tiafzl`, `operator-tiafzl`;
- `VM.Standard.E2.1.Micro` (Always Free, so R14 is satisfied) is offered in this compartment.

So: one Always Free instance in the private workers subnet, no public IP, reaching the private
endpoint. It joins the tailnet outbound through the existing NAT gateway, so nothing inbound is
opened anywhere. Identity is an instance principal — nothing stored on the machine.

The Mac stays as the second road, on a different failure domain (the VCN).

## Files in flight on branch feat/bridge-off-the-laptop

- `platform/oci/bridge.tf` — instance, dynamic group, policy
- `platform/oci/cloud-init/bridge.yaml` — tailscale, oci-cli, kubectl, the systemd unit
- `platform/tailscale/policy.hujson` — `tag:estate-bridge` owned by `tag:k8s`, and
  `group:founder -> tag:estate-bridge:8001`
- `platform/rbac/` — the ClusterRoleBinding mapping the instance principal
- `bin/idp-phone-kubeconfig` — points at the bridge, falls back to the Mac
- `docs/founder/debug-the-cluster-from-your-phone.md`

## Vault facts already established

`tailscale-operator` in the OCI vault holds `client_id` and `client_secret` (OAuth). The bridge
reads it by instance principal and joins with `--advertise-tags=tag:estate-bridge`; `tagOwners`
must list `tag:estate-bridge` as owned by `tag:k8s`, because a client may only request tags its
own tags own (the reason is already written in the policy file's header).

## Still open elsewhere

idp#1577 (commerce) needs one word from the founder — which payment provider.
