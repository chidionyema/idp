# The full work: what gets built so agents can manage infrastructure safely

Companion to `docs/decisions/0025-agents-hold-no-write-on-production-and-the-greenlane-grows-by-rows.md`.
The ADR decides; this is the specification of the work, with the acceptance test for each piece.
The founder's standard is in two records, which are the only source and are never paraphrased from
memory:

- `~/.claude/docs/founder/2026-09-07T1528Z-this-is-the-net-super-inprotnsnt-peice-of-78f60e2c.md`
- `~/.claude/docs/founder/2026-09-07T1532Z-sually-forces-platform-teams-to-constantly-micromanage-their-9cce7f2d.md`

## The correction that shapes everything below: most of our agents have no pod

The founder asked directly whether agents have pods, and whether this session does. Measured
2026-09-07 against the live cluster, agents here come in three shapes and only one of them is the
shape the record assumes:

| Shape | Who | Runs as | What can confine it |
|---|---|---|---|
| A — a session on the founder's machine | Claude Code, this session and every other | a process on his Mac, as his user, holding a kubeconfig | the credential, and the API server that reads it. Nothing else. |
| B — a workload in the cluster | `otto-gateway` (2 pods), `otto-golden` (2), `hermes-agent-gateway`, `mcp/agentgateway` (2), the `agent-workforce` CronJob | a Pod with a ServiceAccount | its ServiceAccount, plus gVisor for code it executes |
| C — a job in CI | GitHub Actions runners | a runner outside this cluster | the token it is handed |

Shape A does nearly all of the infrastructure work in this estate, and a pod sandbox is meaningless
for it. So the confinement boundary in the record — "The agent executes inside a locked-down pod
(using gVisor/runsc)" — is the second boundary here, not the first. The first is the credential,
which is ADR 0023's title already: the boundary is enforced by the infrastructure, not the
application.

gVisor's row narrows accordingly. `platform/edge/otto-gvisor-sandbox-namespace.yaml` exists and
says so itself — "no code-executing workload is onboarded at this slice, only the cell that will
host it." It confines code an agent *runs*. It does nothing about an agent *holding admin
credentials*, which is the actual exposure.

## The exposure, measured

```
$ bin/idp-kube auth whoami
Groups   [ocid1.compartment... ocid1.group... system:masters system:authenticated]

$ bin/idp-kube auth can-i delete pods -n kube-system
yes
```

`system:masters` bypasses RBAC entirely; it is Kubernetes' hardcoded superuser group. Every agent
session in this estate reaches the cluster through `bin/idp-kube`, and `bin/idp-kube` mints the
founder's own OCI principal. Until that changes, every other control in this document is optional
for an agent that would rather not use it.

---

# W1 — Identity. No agent holds a write credential on production.

This blocks everything else and is the smallest of the five workstreams.

**W1.1 One read-only identity, three ways in.**
A ClusterRole `estate-agent-read`, built from the built-in `view` (which excludes Secrets by
design) plus the cluster-scoped reads an investigation actually needs: nodes, namespaces, events,
CRDs, and the Flux kinds. A ServiceAccount `agent-reader` in a new `agent-identity` namespace,
bound to it. It follows `platform/rbac/bridge.yaml`, which already argues the case for the
founder's phone.
- Shape A: `bin/idp-kube` stops calling `bin/idp-cloud cluster kubeconfig` and requests a
  short-lived `agent-reader` token instead. The existing cache and `IDP_KUBE_MAX_AGE_MIN` stay.
- Shape B: each of the five in-cluster agents gets its own ServiceAccount bound to the same
  ClusterRole. Today's bindings are unaudited and are part of this piece.
- Shape C: CI jobs that read the cluster trade their OIDC token for the same identity.

*Done when:* `bin/idp-kube get pods -A` still works from a laptop session, and
`bin/idp-kube delete pod <x> -n kube-system` returns a quoted `Forbidden`; and
`kubectl auth can-i --as=system:serviceaccount:...` says no to create, update and delete for each
of the five in-cluster agents. Quoted from real output, not a test.

**W1.2 Break-glass: loud, recorded, never blocked.**
`bin/idp-kube --break-glass "<reason>"` mints the admin path for one invocation, expiring in 15
minutes, refusing without a reason. Every use writes an append-only ledger row and fires a founder
push notification naming the reason and the exact command. A fence that refuses correct work is an
outage (LAW 38); a fence that records every crossing is an audit trail, and that is the asymmetry —
reading costs nothing, writing costs a permanent public record.

*Done when:* a real break-glass use produces a notification on his phone and a ledger row, both
quoted.

**W1.3 A guard so it cannot be re-opened.**
`agent_write_path_gate` in `bin/idp-ci` refuses any file that mints a cluster-admin kubeconfig
outside `bin/idp-cloud` and the break-glass path, with `tests/fixtures/agent-write/admin-mint.bad.sh`
and `read-only.good.sh`. A row in `AGENTS.md`, which is how a rule binds every session and every
in-flight branch (LAW 45).

*Done when:* the gate refuses the bad fixture, passes the good one, and refuses a real
re-introduction on a branch.

**W1.4 The reasoning trail, on the collector we already run.**
`bin/idp-kube` and the estate MCP server each emit one span per cluster call to the central
collector (LAW 50): identity, verb, resource, and the reason string the caller passed. This is not
a new proxy — Teleport appears in zero files here and is not being introduced; we instrument the
two doors that already exist (ADR 0006, ADR 0024).

*Done when:* a query against the collector returns this session's own reads, by identity and
reason.

---

# W2 — The shadow dimension. A virtual cluster that carries production's state.

The virtual cluster is built (`platform/sandbox/vcluster/helmrelease.yaml`,
`.github/workflows/demo-sandbox.yml`, `bin/idp-sandbox-sweep`). Giving it production's state, and
running assertions inside it, is the work.

**W2.1 State sync.**
`bin/idp-shadow up <workload>` spins a vcluster and clones down what the workload actually needs to
converge: its rendered manifests as Flux applies them, its namespace's ResourceQuota and
LimitRange, its NetworkPolicy, and the CRDs it depends on. Secrets are never copied — dummies of
the same shape and key names, so a Deployment mounts and starts (LAW 21). `bin/idp-shadow down`
destroys it; the existing sweeper covers a leak.

**W2.2 The assertion run.**
`bin/idp-shadow verify <workload>` applies the branch's diff inside that vcluster and asserts the
things a change can break: the workload reaches Ready, it meets its previous replica count, its
probes pass, and its own tests run if it has any. A CI job `shadow-verify` runs it on every pull
request touching `platform/` or `clusters/`.

*Done when:* a pull request raising a memory limit shows a green `shadow-verify` naming its
vcluster, and a pull request that breaks the workload shows it red — both quoted from the run.

**W2.3 Proof of Convergence, machine-read.**
A block in the pull request body:

```
Proof-of-Convergence:
  vcluster: shadow-<workload>-<run-id>
  run: <CI run URL>
  asserted: <what passed>
```

`bin/idp-convergence-proof` parses it and verifies the run exists, is green, and belongs to this
pull request's head commit. Missing, unparseable, or pointing at another commit is a fail-closed
FAIL, never a pass. `convergence_proof_gate` and its two fixtures become a row in `AGENTS.md`, so
every in-flight infra branch meets it on rebase.

*Done when:* the gate refuses a pull request with no block and one whose run belongs to a different
commit.

---

# W3 — The Greenlane. Widen the trust threshold by rows.

It already runs, on one row. `.github/workflows/deploy-when-green.yml` with
`bin/idp-image-only-diff` and `bin/idp-pr-landable` is the Proof Contract from the record — Scope
Check, Test Pass, Autonomous Execution — landing image tag bumps since 2026-08-31. We add rows to
it. We do not build a second merge path beside it.

**W3.1 `bin/idp-limit-raise-only-diff`.** Passes only when every changed line is
`resources.limits.memory` or `resources.limits.cpu`, the value only moves up, exactly one workload
is touched, and the namespace's ResourceQuota still fits after the raise. Two fixtures. Requests
are excluded on purpose: the scheduler counts requests, so raising one can evict a neighbour.

**W3.2 `bin/idp-rollback-only-diff`.** Passes only when every changed line is a `newTag:` and each
new tag is one that file already carried on main, proved from git history. Two fixtures.

**W3.3 The lane table.** `deploy-when-green.yml` gains one row per admitted class: the label or
branch that selects it, the scope binary that proves it, and the requirement that a green
Proof-of-Convergence is attached. Auto-remediation pull requests carry `type: auto-remediation`, as
the record specifies.

**W3.4 The 3 a.m. path, end to end.** An OOMKill alert wakes the agent; it runs W2 against the
failing workload, raises the limit, verifies it starts, opens the labelled pull request with its
proof; the lane merges it; Flux applies it.

*Done when:* a real OOMKill is resolved this way with the founder asleep, and the recovered pod and
the merge are both quoted from live logs — not a synthetic alert (THE EMPIRICAL PROOF RULE).

---

# W4 — Glass-break. No work; the list is closed.

Waits for the founder, always: anything under `clusters/`; a NetworkPolicy; an HTTPRoute, Gateway
or ingress route; a Kyverno or admission rule; a CRD or operator version; a node pool, CNI or
kernel change; RBAC; a ResourceQuota or LimitRange; a resource *request*; and a ConfigMap.

The ConfigMap is the one departure from the record's own list, and the reason is that a ConfigMap
here has no bounded blast radius — the same kind holds an nginx config, a feature flag and a
database DSN, so "fixing a misconfigured ConfigMap" is not one risk class and cannot be one scope
check. It waits until someone can name a subset that is provable.

Secret rotation, also on the record's list, is not a merge at all here: External Secrets pulls from
Bitwarden and no manifest changes, so a rotation never becomes a pull request. It is already
autonomous and stays out of this lane.

---

# W5 — Node, network and rollout. Last, and only after W1 to W3.

None of this exists (`flagger`, `argo-rollouts`, `requestMirror`/`mirrorPercent` and `teleport` are
each in zero files), and it protects the class of change agents make least often here.

**W5.1** The `infra.canary=true:NoSchedule` one-node pool, with the RuntimeClass gating that
already exists, and the watch that promotes after a clean window or drains on kernel panic, eBPF
drop metrics or pod startup latency.

**W5.2** Traffic shadowing at the gateway for ingress and mesh changes: mirror live requests to the
dark copy, discard its responses, and compare error rate, latency distribution and CPU against the
live one.

**W5.3** The Audit-to-Enforce promoter. Policies already default to Audit
(`bin/idp-admission-policies:40-41`); nothing reads the stream. Read it from the collector across a
full churn cycle, and on zero unintended flags open the flip pull request — which is itself
glass-break, since it is a policy change.

**W5.4** Progressive rollout: Flagger, one choice, because it drives the Gateway API this estate
already runs. Wired to the golden signals, aborting and reverting on a 1% error-rate rise.

---

# Order, and why it is this order

1. **W1.** While a session holds `system:masters`, every other control is optional for an agent
   that would rather not use it. Smallest workstream, highest value.
2. **W2.** Nothing can be trusted to merge itself until the proof exists.
3. **W3.** This is what buys the founder the night's sleep, and it is small once W2 exists.
4. **W5.** Real new infrastructure, protecting the rarest class of change.

W4 is already true and costs nothing.

---

# W0 — What the first pass of this spec missed

The founder asked what we missed, and named the mathematical certainty himself. He is right that
the first pass did not deliver it. These pieces are not extras; W0.1, W0.2 and W0.3 are the reason
the certainty is not there yet, and they come with W1.

## The honest statement of what W1 actually buys

The record asks for a blast radius "mathematically constrained to zero". W1 removes the agent's
*direct* write to production. It does not remove its write. The agent still writes to production —
through Git, on Flux's next reconcile. So the boundary is not the API server. **The boundary is the
merge gate, and the whole guarantee lives inside the scope-check binaries.** A bug in one of them
is an arbitrary production write with a green tick on it.

That is not a reason to weaken the claim. It is the instruction for where to spend the rigour.

**W0.1 The machinery must sit outside what the agent can change.**
Nothing in the first pass stopped an agent from opening a pull request against the things that
constrain it: `bin/idp-image-only-diff` and every other scope check, `deploy-when-green.yml`, the
gate rows in `AGENTS.md`, `platform/rbac/`, and `bin/idp-kube` itself. Those become permanently
glass-break, and they need more than the founder's merge — `CODEOWNERS` already names him on
`/bin/`, `/.github/`, `/platform/` and `/tests/`, so the work is proving the branch protection
actually requires that review and that the Greenlane's GitHub App token cannot bypass it.

*Done when:* a pull request from an agent that edits a scope check is refused by the repository,
quoted, and the refusal is not something the agent can turn off.

**W0.2 A scope check is proved against history, not against two fixtures.**
Two fixtures say a checker handles two cases. The guarantee needs more: replay every pull request
this repository has ever merged through each scope check and assert it admits only the class it
claims. That produces a real number — "of N merged pull requests, this checker admits exactly
these" — and it is the closest thing to the mathematical certainty available here.

*Done when:* each scope check has a replay run over the merged history with its admitted set listed
in full.

**W0.3 The check and the merge are the same commit.**
A scope check grades a diff; a force-push between the check and the merge changes what lands. The
merge is pinned to the exact commit that passed, and a moved head is a refusal, not a re-check.

**W0.4 The layer below Kubernetes, which the record does not cover at all.**
The framework is written about the Kubernetes API. This cluster sits on OCI, and the credentials in
`bin/idp-cloud` can delete the cluster, the database and the object storage outright — cluster RBAC
is irrelevant to any of that. The same is true of the GitHub App token, which can rewrite main;
Bitwarden, which holds every secret; and DNS. An agent confined to read-only inside Kubernetes
while holding an OCI administrator key is not confined. W1's treatment — read by default, break
glass recorded and announced — applies to all four, and the OCI one is as urgent as the Kubernetes
one.

**W0.5 Sign the proof.**
The record says "a cryptographic signature *or* a passing CI test log". The first pass took only
the log, and a log URL in a body the agent wrote is forgeable in principle. `cosign` is already in
this repository, so the primitive is here: the shadow run signs its own result, the gate verifies
the signature, and agent commits are signed too. Append-only by convention is not tamper-proof
either — the audit sink must be one the agent's identity can append to and nothing else.

**W0.6 The agent must not choose the assertions it is graded on.**
Proof of Convergence as first written asserts whatever the agent decided to assert, so a weak
assertion passes trivially. The assertion set is defined by the platform, per workload, and the
pull request selects one rather than supplying one.

**W0.7 An aggregate limit, and a switch he can reach.**
One memory raise is safe; forty in an hour is a capacity incident, and neither the record nor the
first pass bounds the *rate* of autonomous merges. The Greenlane gets a budget per hour and halts
above it. Separately, one flag halts every autonomous merge, reachable from his phone with no
terminal (LAW 54). Nothing in this repository does either today.

**W0.8 A failed rollout must revert the commit, not only abort.**
The record's Kyverno scenario says the pipeline "automatically reverts the PR". W5.4 as first
written only aborted the rollout — and if the bad commit stays on main, Flux re-applies it on the
next reconcile and the two fight indefinitely. The abort opens and merges a revert.

**W0.9 The failure has to reach the agent that caused it.**
The record says the system "pages the agent to tell it the fix failed in reality". There is no path
today from an aborted rollout back to the agent that opened the pull request, so the agent retries
the same fix. That path is part of W5.

**W0.10 The morning summary.**
"You sleep through the whole thing and just read a Slack summary in the morning." The first pass
built per-event notifications and no digest. It is the cheapest item in this document and the one
that decides whether he ever trusts the lane.

**W0.11 The work already in flight was written under the old rules.**
A gate catches what the thirty-odd open infrastructure branches change from here on. Nobody has
read what they already contain. That is an audit pass, once, before they land.
