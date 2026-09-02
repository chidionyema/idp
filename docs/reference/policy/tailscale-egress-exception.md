# Tailscale egress proxy exception

Two Tailscale egress proxies carry the founder's screen-sharing traffic to his
Mac: `ts-founder-mac-vnc` and `ts-sunshine-mac`. The Tailscale operator creates
them as workloads in the `tailscale` area of the cluster, and they need network
capabilities (`NET_ADMIN`, `NET_RAW`) that the cluster's baseline security
policies refuse.

Rather than weaken any baseline policy, the platform carries one scoped
exception: `PolicyException/tailscale-egress-proxies` in the `kyverno`
area of the cluster, defined in `platform/edge/tailscale-egress-exception.yaml`.

## What it covers, and nothing else

- Area of the cluster: `tailscale` only.
- Workload names: `ts-founder-mac-vnc*` and `ts-sunshine-mac*` only.
- Kinds: `StatefulSet`, `Pod`, `ReplicaSet` (the chain the operator creates).
- Policies excepted: the nine baseline rules the operator's proxies cannot
  satisfy (capabilities, privilege escalation, probes, resource limits,
  read-only root, non-root user, seccomp).

Any other workload in the `tailscale` area, and any workload anywhere
else, still faces the full baseline.

## Receipt

The admission policy operator's log recorded the denial of both workloads at
2026-09-02T14:02:45Z; the nine policy names in the exception are taken from
that log line, not guessed. The precedent for this shape is
`platform/edge/tailscale-operator-exception.yaml`.
