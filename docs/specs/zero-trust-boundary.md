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

## Step 1 — find out whether the fences enforce anything. Tonight.

The estate holds 154 NetworkPolicy objects, 40 of them ns-fence default-denies that `bin/idp-ci`
refuses a namespace without. The CNI is flannel and no NetworkPolicy enforcement agent runs
anywhere in the cluster. Flannel does not implement NetworkPolicy. Every check we own reads the
objects; none reads the traffic; so all of them are green either way.

New drill `fence-enforcement`, row in `drills/catalogue.yaml`, owner `idp`, daily. In a throwaway
namespace carrying the standard fence, it does one thing and reports one word:

1. Start two pods in two fenced namespaces that the fences forbid to talk.
2. From one, open a TCP connection to the other, and separately to the public internet.
3. **Both must fail.** A connection that succeeds is the fence proved decorative.

`proves:` line:

> A packet on a path the fences deny is actually dropped, so the 154 NetworkPolicy objects are a
> wall rather than a decoration.

If the drill is red, that is a live isolation defect and LAW 1 applies before any other step here.
The remedy is an enforcement agent on the existing CNI, and it is the smallest change that turns
every existing policy on at once — not a CNI migration, and not a rewrite of the 154 objects.

Nothing else in this spec matters until step 1 has run once, because a policy engine at the edge
beside an unenforced network is a lock on a door in a field.

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
