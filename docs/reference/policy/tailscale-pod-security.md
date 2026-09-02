# Why the Tailscale area runs at the privileged pod-security level

## The one-sentence answer

The Mac proxy workloads that Tailscale's operator creates must run privileged
containers, and Kubernetes' built-in pod-security check refuses privileged
containers at the `baseline` level, so the `tailscale` area of the cluster is
labelled `privileged` — the smallest change that lets those proxies start.

## What was measured

On 2026-09-02, after the scoped admission-policy exception landed
(`platform/edge/tailscale-egress-exception.yaml`), the operator created both
proxy workloads, but their pods were still refused:

```
Create Pod ts-sunshine-mac-ql4xm-0 ... is forbidden: violates PodSecurity
"baseline:latest": privileged (containers "sysctler", "tailscale" must not
set securityContext.privileged=true)
```

That refusal comes from the API server's own pod-security admission, driven by
a label on the area of the cluster the pod lands in. It is a different layer
from the admission policy operator, and an exception written for that operator
cannot waive it.

## Why this is safe enough

- Only Tailscale's operator and the proxies it creates live in this area;
  nothing else is scheduled there.
- The `warn` and `audit` labels stay at `restricted`, so any other workload
  that lands there is reported loudly even though it is not refused.
- The admission policy operator still checks everything in this area; only the
  two Mac proxy workloads (`ts-founder-mac-vnc*`, `ts-sunshine-mac*`) carry an
  exception, and that exception names its nine rules.
- The estate already uses exactly this shape for the node log agent:
  `platform/edge/k8s-infra-namespace.yaml`.

## The alternative that was rejected

Editing the vendor's proxy spec to drop the privileged containers: rejected
because the operator owns and rewrites those workloads, so the edit would be
fought and reverted every time the operator applies its declared state, and
the vendor's images need those
privileges to program routing.

## How to undo it

If the Mac proxies are ever retired, set the enforce label in
`platform/tailscale/namespace.yaml` back to `baseline` and delete this page
and its navigation row.
