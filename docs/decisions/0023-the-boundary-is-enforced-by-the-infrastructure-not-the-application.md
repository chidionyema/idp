# 0023 — The boundary is enforced by the infrastructure, never by the application

- Status: DECIDED 2026-09-05 on the founder's instruction
- Deciders: founder
- Extends: 0021 (the founder wears two hats), 0008 (one front door), 0006 (the platform answers
  for itself over one MCP)
- Records, verbatim and in order:
  - `~/.claude/docs/founder/2026-09-05T2124Z-got-it-zooming-out-entirely-you-re-talking-7347474b.md`
  - `~/.claude/docs/founder/2026-09-05T2126Z-if-we-are-building-this-ultra-elite-zero-31daaa0e.md`
  - `~/.claude/docs/founder/2026-09-05T2126Z-save-all-this-a0a86830.md`
  - `~/.claude/docs/founder/2026-09-05T2127Z-we-have-the-front-door-envoy-and-the-3dd6f4d0.md`
  - `~/.claude/docs/founder/2026-09-05T2128Z-assuming-you-want-to-lock-in-both-the-f914b670.md`
  - `~/.claude/docs/founder/2026-09-05T2130Z-workspace-f0362998.md`

## The instruction

> "You aren't just building features; you are building the boundaries."

> "Never put authorization logic inside the MCP tools or agent code. The moment you write
> `if is_founder():` inside your Python backend, you accrue technical debt."

> "The Zero-Regret Test: If Customer 0 manages to achieve Remote Code Execution (RCE) inside their
> agent, this architecture ensures they still cannot access the memory door of Customer 1, nor can
> they reach the Founder's Control Plane."

## The decision

Authorization is a property of the request's path, not of the code that finally serves it. A
tenant boundary that any application must remember to check is a boundary that will be forgotten
once, and once is all it takes. So:

1. **Identity is cryptographic and short-lived.** Every workload — an orchestrator on the control
   plane, a worker in a tenant cell — boots with a SPIFFE identity, not a static key.
2. **The edge is the only source of truth about who is calling.** Client-supplied identity headers
   are stripped at ingress and replaced with headers derived from the verified certificate.
3. **Policy is code, outside the application.** The gateway asks a policy engine; the application
   receives a verified tenant and filters by it, holding no authorization logic of its own.
4. **Untrusted compute is confined by the kernel and the network, not by convention.** An agent
   that executes model-written code runs in its own cell with default-deny egress.

The test this decision is graded by is the founder's own, and it is adversarial: an attacker with
code execution inside a tenant agent reaches neither another tenant's data nor the control plane.

## What actually runs today, measured 2026-09-05

The blueprint above is the target. This section is what is true right now, because a decision that
reads as a description of the estate is the thing a buyer's engineer takes apart in one sitting.

| Layer | Blueprint | Measured today | Verdict |
|---|---|---|---|
| Workload identity | SPIFFE/SPIRE | SPIRE runs: namespaces `spire-server`, `spire-system`, `spire-mgmt`, 9 days. `platform/spire/` carries a proof CronJob. | Present; not yet the identity the edge authorizes on |
| Edge | Envoy + WASM | **Traefik** (`platform/edge/traefik.yaml`). No Envoy, no WASM, no `ext_authz`. | Different tool, same job; the gap is ext_authz, not the vendor |
| Policy as code | OPA / Cedar at the gateway | **Kyverno**, which is admission-time policy on the Kubernetes API, not per-request authorization on the data path. | Missing at the data path |
| Network isolation | Cilium eBPF, default deny | **flannel**. 154 NetworkPolicies exist, including 40 ns-fence default-denies. No Cilium, Calico or Canal agent runs anywhere in the cluster (138 running pods, zero matched). Cilium CRDs are installed but no agent backs them. | **See the finding below** |
| Kernel sandbox | gVisor / Kata | No `runtimeClassName` anywhere in `platform/`. | Missing |
| Cells | namespace or cluster per tenant | Namespaces are per platform service, not per tenant (`platform/ns-fences/`, 40 fences). | Deliberate — see the tension below |

## The finding this thread produced, and it is the reason to measure rather than to hire

`bin/idp-ci`'s `ns_fence_gate` refuses any namespace without a both-ways default-deny
NetworkPolicy, and it has been green. The cluster holds 154 NetworkPolicy objects. The CNI is
flannel, and no NetworkPolicy enforcement agent runs in the cluster.

Flannel does not implement NetworkPolicy. A cluster with policies and no enforcer accepts every
object and drops no packet, and every check we own reads green because every check we own reads
the objects rather than the traffic. That is precisely the failure THE EMPIRICAL PROOF RULE names:
a synthetic check that cannot fail.

State: **UNKNOWN**, and treated as a probable outage of the fences until traffic says otherwise.
The objects are measured; enforcement is not, because nothing has yet sent a packet down a denied
path. The first action of the spec below is that packet.

This is the answer to "should we get a consultant". A consultant would have drawn the diagram in
this decision, which we already had. Only running against our own estate turns up 154 policies
that may be enforcing nothing.

## The tension with 0021, and how it resolves

Decision 0021 rejects a namespace per tenant: "Tenancy is a row and an attribute, not a namespace;
a tenant per namespace is the second scheduler in fence form." The blueprint asks for
`tenant-0-workspace`. Both hold, because they are about different things:

- **Tenant data** is a row keyed by `tenant_id`, filtered by a header the edge injects. No
  namespace. 0021 stands unchanged.
- **Untrusted tenant compute** — an agent executing code a model wrote — is a cell with its own
  kernel and default-deny egress. That is not a fence per customer record; it is a blast radius
  around code we did not write.

So: one namespace per *execution cell*, created only for tenants that run untrusted code, and
never one per tenant row. Today no tenant runs untrusted code on the estate, so no cell exists,
and the first one is created by the workload that needs it rather than in advance.

## Rejected

- **`if is_founder()` in the application.** The founder's instruction names it, and it is already
  refused elsewhere: the register's Owner column, the vault grant shape, and the plane annotation
  all exist so that no service decides for itself who is calling.
- **Replacing Traefik with Envoy as step one.** The gap is external authorization on the data
  path, and Traefik has a ForwardAuth middleware that is exactly that. Swapping the edge is a
  large change that does not close the gap by itself; adding the policy call does. Portability
  outranks the vendor (LAW 19).
- **Cilium as step one.** It is the right destination and it is also a CNI migration on a live
  cluster. The first step is to find out whether the fences enforce, because if they do not, a
  policy engine at the edge is a wall beside an open door.

## What follows

`docs/specs/zero-trust-boundary.md`: the ordered build, first step the enforcement drill.
