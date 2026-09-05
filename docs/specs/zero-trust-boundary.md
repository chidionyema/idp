# The zero-trust boundary — the build spec

Governed by decision 0023, "The boundary is enforced by the infrastructure, never by the
application", and by decision 0021's two planes. Six steps in order. Each is one pull request.
Step 1 is the only one that must happen tonight.

Founder records, verbatim, at
`~/.claude/docs/founder/2026-09-05T2124Z-got-it-zooming-out-entirely-you-re-talking-7347474b.md`,
`…2126Z-if-we-are-building-this-ultra-elite-zero-31daaa0e.md`,
`…2126Z-save-all-this-a0a86830.md`,
`…2127Z-we-have-the-front-door-envoy-and-the-3dd6f4d0.md`,
`…2128Z-assuming-you-want-to-lock-in-both-the-f914b670.md`,
`…2130Z-workspace-f0362998.md`.

---

## Step 1 — MEASURED, AND IT IS RED. The fences enforce nothing.

This step was written as "find out". It ran on 2026-09-05T21:5xZ and the answer is that the
estate has a live isolation defect, so LAW 1 applies before any other step in this spec.

**Angle one, the objects.** The only CNI DaemonSet in the cluster is `kube-flannel-ds`
(`kubectl get ds -A`): no Calico, no Cilium, no Antrea, no NetworkPolicy enforcement agent of any
kind. Flannel does not implement NetworkPolicy. The cluster carries 154 NetworkPolicy objects,
40 of them the both-ways default-deny that `bin/idp-ci` refuses a namespace without.

**Angle two, the traffic.** From `dagster-daemon-9cd8bd67f-45h8x`, a pod in the `dagster`
namespace, which carries `default-deny-all` with `policyTypes: [Ingress, Egress]` and an empty
`podSelector`:

```
internet 1.1.1.1:443 -> CONNECTED
internet 8.8.8.8:53  -> CONNECTED
cross-namespace 10.244.1.240:3100 (backstage/catalogue) -> CONNECTED
```

Both namespaces carry a both-ways default-deny. Every one of those three packets is on a path the
fences deny, and every one arrived. The 154 objects are a decoration.

Two smaller findings fell out of the same probe and belong here because they change how any of
this is graded:

- A pod in a fenced namespace could not be created to run the drill: the cluster refuses writes
  from user principals ("Git is the only writer of this cluster; change the file on main and Flux
  applies it"). So the drill lands as a Flux-reconciled row, never as a `kubectl apply` from a
  laptop, and that is correct.
- A first pass of the same probe reported `EGRESS_BLOCKED` because the pod had no `wget` and the
  shell returned 127. A drill that grades a missing binary as a passing fence is the class of
  mistake this whole spec exists to catch, so the drill below must fail closed on a probe that
  could not run, and must prove its own reachability against a path the fences allow.

### What still gets built

`fence-enforcement`, and in this repository a drill is two things: a scheduled workflow under
`.github/workflows/` and a row in `drills/catalogue.yaml` (owner `idp`, `schedule` copied verbatim
from the workflow's own cron line, `max_age_hours: 26`, a one-sentence `proves`). `bin/idp-verify`
grades the freshness of the last green run and nothing else, so a drill that is only a row is a
drill that never fires.

The workflow authenticates as the service user `estate-ci` through the OIDC identity propagation
`oke-check.yml` already uses — the one identity the cluster excuses from the Git-only-writer
lockdown. A laptop cannot run this drill and must not be able to. In two fenced namespaces it:

1. proves the probe works, by reaching a destination the fences allow — a probe that cannot reach
   anything measures nothing;
2. opens TCP to the other fenced namespace's pod, and to a public address;
3. **fails unless both are refused**, and fails when step 1 could not run.

`proves:` line:

> A packet on a path the fences deny is actually dropped, so the 154 NetworkPolicy objects are a
> wall rather than a decoration.

### The remedy, and it is one change

An enforcement agent on the CNI that already runs: **Calico in policy-only mode beside flannel**,
the combination that has shipped as Canal for a decade. It turns all 154 existing policies on at
once and rewrites none of them. It is not a CNI migration, the pod network keeps working through
flannel, and it is the smallest change that closes the defect. Rejected: migrating to Cilium
(replaces a working data plane to gain enforcement we can have without touching it), and rewriting
the 154 objects (they are correct; nothing reads them).

### The danger in the remedy, and it is the reason this is not a same-night fix

The 154 policies have never enforced, so no service's real traffic has ever been graded against
them. Switching enforcement on switches all 154 on at once, and any policy that does not allow
traffic a service actually needs takes that service down the moment Calico starts. The fences are
untested in the only sense that matters.

So the order inside item 0 is: install Calico policy-only with enforcement in **log-only** posture
first, collect one full day of would-be-denied flows, and merge the allow rules those flows
demand before anything is dropped. Only then does enforcement go on. That audit is the work; the
install is not. A flag-day cutover here is an estate-wide outage with 154 causes, and LAW 11
applies to the decision to flip it.

Nothing else in this spec matters until the enforcement agent is in and the drill is green,
because a policy engine at the edge beside an unenforced network is a lock on a door in a field.

## Step 2 — the edge asks a policy engine before it forwards

The gap decision 0023 names is external authorization on the data path. Traefik already ships
`ForwardAuth` middleware, so this is configuration plus one service, not an edge migration.

- New workload `platform/authz/` on the control plane: OPA, serving one decision endpoint.
- Traefik middleware `forward-auth` applied to every route that reaches a tenant-visible service.
- The policy bundle is a directory of `.rego` in this repository, graded by `conftest` in
  `bin/idp-ci` with a `must-fail` / `must-pass` fixture pair and a row in `AGENTS.md`.

The two rules, which are the founder's, in the engine's own language:

```rego
# A tenant principal reaches only its own tenant's resources.
allow if {
  input.principal.plane == "tenant"
  input.principal.tenant_id == input.resource.tenant_id
}

# The operator reaches every tenant, and every such request is recorded as operator access.
allow if { input.principal.plane == "control" }
```

Accept when a request carrying a tenant principal for another tenant's resource is refused at the
edge, proved by a real request and its 403, and the same request as the operator is allowed and
appears in the audit trail as operator access.

## Step 3 — the edge is the only source of truth about who is calling

- Traefik strips every client-supplied identity header at ingress: `x-tenant-id`, `x-role`,
  `x-verified-tenant` and anything else the policy input reads. A spoofed header must never
  survive ingress; the fixture pair proves a request arriving with `x-verified-tenant: estate` is
  rewritten, not honoured.
- Traefik derives identity from the SPIFFE certificate SPIRE already issues (SPIRE has run for
  nine days in `spire-server`, `spire-system`, `spire-mgmt`) and injects `x-verified-tenant`.
- Applications read that header and filter. No application holds authorization logic — decision
  0023 rule 3, and `if is_founder()` in any service is the defect.

Accept when `estate_memory`'s recall path contains no authorization branch, filters on the
injected header alone, and a spoof attempt is refused at the edge with the attempt logged.

## Step 4 — a tenant is stamped out by Flux, not by hand

`infrastructure/tenants/<name>/` in Git is the whole of a tenant's existence: its namespace, its
fence, its SPIRE registration entry, its quota, its Lago customer at its plan's price, and its
route registration. Flux reconciles it. Onboarding a customer is a merged pull request and nothing
else — no console step, no terminal (LAW 52, LAW 54).

The generator is `bin/idp-tenant-new <name>`, idempotent, and its output is graded byte-identical
over two runs like every other generator in this repository.

Accept when a throwaway tenant is created by merging a generated directory, its agent boots and
answers, and deleting the directory removes every trace — which is also decision 0021's diligence
test running for free.

## Step 5 — untrusted compute gets its own kernel

Only for a workload that executes code a model wrote. Not for every tenant, and not in advance
(decision 0023, the tension section).

- A `RuntimeClass` for gVisor, and admission that refuses a pod in a cell namespace that does not
  name it or that asks for `privileged: true`. Kyverno already runs and this is one more policy,
  not a second engine.
- Default-deny egress on the cell, with the one allowed route being the gateway.

Accept when a pod in a cell namespace without the runtime class is refused at admission, proved
both ways in one run.

## Step 6 — the isolation break is caught in the pull request

`bin/idp-ci` gains, in the pass that already exists rather than a new pipeline:

- `conftest` over the tenant directories: a fence that allows egress to the internet fails.
- A pod-security check: `privileged: true`, host networking, host path mounts and a missing
  runtime class in a cell namespace all fail.

Each with the fixture pair and the `AGENTS.md` row this repository requires of every rule.

---

## Order, and why

Step 1 first because it is the only step that can change what the other five are worth. 2 before 3
because the engine must exist before the edge can ask it. 4 after 3 because a stamped tenant needs
an edge that recognises it. 5 and 6 last: 5 is for a workload that does not exist yet, and 6
protects work already landed. Steps 2 through 6 are each small; step 1 is one drill and it is the
one that tells us what we actually own.
