# The full work: what gets built so agents can manage infrastructure safely

Companion to `docs/decisions/0025-agents-hold-no-write-on-production-and-the-greenlane-grows-by-rows.md`.
The ADR decides; this is the specification of the work, with the acceptance test for each piece.
The founder's standard is in two records, which are the only source and are never paraphrased from
memory:

- `~/.claude/docs/founder/2026-09-07T1528Z-this-is-the-net-super-inprotnsnt-peice-of-78f60e2c.md`
- `~/.claude/docs/founder/2026-09-07T1532Z-sually-forces-platform-teams-to-constantly-micromanage-their-9cce7f2d.md`

## THE ORDERING THAT HOLDS — the founder's correction, 2026-09-08

Record, verbatim and the only source (never paraphrased from memory):
`~/.claude/docs/founder/2026-09-08T0609Z-you-are-completely-right-to-question-that-and-996c7f35.md`

**This supersedes the 2026-09-07 redirect recorded below. No workstream is dropped.** He read
back the narrowed plan and rejected the narrowing in his own words:

> You are completely right to question that, and I made a mistake. We absolutely should not drop
> those workstreams.
>
> I pivoted too hard toward the temporary token idea and lost the plot of the "ultra-asymmetric"
> framework you asked for. If we drop the shadow environments (vcluster) and GitOps, we are just
> giving the agent direct access to prod via temporary keys. That is not elite; that is just a
> time-delayed footgun.

That sentence is the correction, and it is worth stating plainly because it is a real hole in what
was being built: a JIT broker **on its own** does not confine an agent. It shortens how long the
agent holds production write. It does nothing about the agent holding production write at all for
the ninety-five percent of work that never needed it.

### The shape: two engines, not one

**Engine 1 — the asymmetric engine, for code and config. This is W2, W3, W4 and W5.**

> For 95% of infrastructure work (changing configs, updating Kyverno policies, rolling out new
> images), the agent never needs a live token to production.
>
> The agent works in the vcluster shadow dimension. It mathematically proves the fix works. It
> opens a Git Pull Request. You click "Merge" on your phone (or the Greenlane auto-merges it).
> Flux pulls it into prod.
>
> Why we keep this: It prevents configuration drift. Every change is permanently
> version-controlled, rollback is instant, and the agent's blast radius is zero.

**Engine 2 — the JIT break-glass engine, for live emergencies. This is W0 and W1.**

> What happens if the agent needs to restart a frozen Oracle node, or query a live database, or
> clear a cache? GitOps cannot do this. If you give the agent a permanent Oracle or Kubernetes
> Admin key to do this, you lose your security guarantee.
>
> The agent hits a wall that requires live execution (e.g., restarting a pod). It pings your
> phone: "Need pods/delete in kube-system to clear a crash loop. Requesting 10 minutes." You tap
> "Approve." The system mints a cryptographic token that mathematically dies in exactly 10 minutes.

The two are not alternatives and the choice between them is not a judgement call: **if the change
can be expressed in git, it goes through Engine 1.** Engine 2 exists for the acts git cannot
express — restarting something, reading something live, clearing something. Every WJ item below is
Engine 2, and every one of them stays exactly as written.

### The directive, verbatim

> Do not drop any workstreams. We are building the full W0-W5 zero-trust framework. Proceed with
> W1 first, but with this ultra-elite architecture:
>
> All agents are permanently Read-Only by default.
>
> For W1 Break-Glass, do NOT use static keys or manual revocation. Implement Just-In-Time (JIT)
> short-lived tokens using the native Kubernetes TokenRequest API and Oracle's equivalent.
>
> The agent must request a TTL (Time-To-Live) token via my Telegram/phone. When I approve, the
> system mints a token that mathematically auto-revokes when the TTL expires.
>
> Execute W1 immediately under these constraints.

**W1 first, and it is not finished.** He added on the same day: *"this is a later idea but focus on
the core first."* So Engine 1 is specified here and not started; the WJ items are the core and they
are what gets built now. Issue #2470 tracks them.

Nothing in the WJ specification below changes under this correction. What changes is that W2-W5
stop being parked: they are the other engine, and the framework is incomplete without them.

---

## The 2026-09-07 redirect, kept because it is the reasoning that got here

Record, verbatim and the only source (never paraphrased from memory):
`~/.claude/docs/founder/2026-09-07T1606Z-ok-lets-add-these-also-ign-the-proof-c2f0f9be.md`

He read the six-workstream plan below and rejected its shape, not its findings:

> the blunt truth is that my previous, highly complex 6-workstream plan completely missed the
> essence of your prompt: you are a founder, not a dedicated platform engineering team.
> Building canary nodes, eBPF traffic shadowers, and automated mathematical convergence proofs is
> massive, enterprise-grade friction. It is the opposite of seamless.

And named what the gap actually is:

> The real gap isn't a lack of GitOps pipelines. The gap is that we didn't design a Just-In-Time
> (JIT) Cryptographic Access system.
>
> You want the agent to operate autonomously where safe, hit a wall, ask for a temporary key, do
> the job, and have the key vanish into thin air without you ever cleaning up behind it.

His instruction on scope: **"we drop workstreams W2 through W5. We focus solely on building the
JIT Token Broker."** Answered "Yes" in the same message.

**This paragraph is superseded by the 2026-09-08 correction above and is kept as the reasoning,
not as the instruction.** It read: W2 to W5 are parked, with this line as the path back (LAW 16),
and no session starts one without his word. He gave that word on 2026-09-08 — W2 to W5 are Engine
1 and are back in the framework. What survives from it unchanged is the ordering: W0 and W1 are
the JIT system's own foundation, they are folded into the WJ items below, and they come first.

---

# WJ — The JIT Token Broker. The one thing we build.

## The shape

Static credentials are abandoned. Nothing holds standing write privilege on production — not an
agent, not a session, not CI. Write is minted on demand, scoped to one named action, and dies by
the passage of time rather than by anyone remembering to clean up.

**WJ.1 Zero standing privileges (this is W1.1, unchanged).**
Every agent identity — laptop session, in-cluster workload, CI job — is bound to read-only in
Kubernetes and read-only in OCI. `bin/idp-kube` stops minting the founder's OCI principal.
Diagnosis stays completely unrestricted: logs, metrics, events, manifests, everything but Secrets.
Mutation is not possible, not discouraged.

*Done when:* `bin/idp-kube auth whoami` no longer shows `system:masters`, reads still work, and a
delete returns a quoted `Forbidden`.

**WJ.2 The frictionless ask.**
When an agent hits the wall it does not fail and it does not report back. It asks, in one message
to the founder's phone carrying exactly three things, in plain English:

- **The why** — "The Backstage pod is OOM crashing."
- **The what** — the exact verb, kind, name and namespace: `patch deployment/backstage -n backstage`.
- **The time to live** — "10 minutes."

**WJ.3 The one-click grant.**
He taps Approve. No terminal, no YAML, no repository (LAW 54, LAW 31). Deny is one tap too, and a
silent no-answer is a deny — the request expires on its own.

**WJ.4 The cryptographic auto-revoke — this is the mathematical certainty.**
Approval mints a token with `kubectl create token --duration=<ttl>`, bound to a temporary Role
scoped to exactly the resource and verbs in the ask. At the end of the TTL the JWT is invalid by
its own signature. Nothing has to run for the revoke to happen: a crashed cleanup job, a network
partition, a rogue agent and a forgotten session all fail closed, because expiry is a property of
the token, not of a process. For OCI the same shape uses short-lived session tokens.

This is what the earlier plan could not deliver. The blast radius is not argued from a scope
checker that might have a bug — it is bounded by a signature that stops verifying.

## The security core: the broker is the new crown jewel

The broker can mint write access, so an agent that can forge an approval has admin. Four
properties, and every one of them is load-bearing:

**WJ.5 A grant is chosen, never composed.** The broker mints only from grant templates declared in
git — a closed set naming verb, kind, namespace pattern and maximum TTL. The agent picks a template
and fills its parameters; it cannot describe a permission of its own. A template that would grant
`*`, `cluster-admin`, secrets, RBAC, or anything in the core blast radius is refused by a gate, not
by review. (This is W0.6 generalised: **the agent does not get to author what it is measured or
granted by.**)

**WJ.6 The approval is signed and the agent never sees the channel.** The callback carries an HMAC
over the request id, the template, the parameters and the TTL, verified by the broker against a key
the agent's identity cannot read, and accepted only from the founder's own chat. An agent cannot
reach the approval path even by holding its own request.

**WJ.7 Every request, grant, denial, expiry and use is recorded — signed, append-only, and on the
collector.** Cosign is already in this repository, so the primitive exists (W0.5): the ledger entry
is signed, and the sink is one the agent's identity may append to and nothing else. Append-only by
convention is not tamper-proof.

**WJ.8 The broker and its templates are outside what the agent can change (W0.1).** The broker's
code, its templates, `bin/idp-kube`, `platform/rbac/` and the gates are permanently glass-break,
enforced by the repository and provably not bypassable by any merge bot.

## The safety rails the earlier plan found, kept because they still apply

These are the W0 items, restated against the JIT shape rather than the GitOps shape. None is
dropped.

- **WJ.9 A rate limit (W0.7).** One ten-minute patch is safe; forty in an hour is an incident.
  The broker caps grants per hour and per template, and refuses above it.
- **WJ.10 A kill switch he can reach (W0.7).** One tap halts every grant, standing and pending,
  from his phone. No terminal.
- **WJ.11 The morning summary (W0.10).** One message: what was asked, what he approved while
  asleep, what expired unused, what was denied. The cheapest item here and the one that decides
  whether he trusts it.
- **WJ.12 The failure reaches the agent (W0.9).** When a granted action makes things worse, the
  agent that asked is told, so it does not ask for the same grant again.
- **WJ.13 Check and use are the same thing (W0.3).** The token encodes the scope, so there is no
  gap between what was approved and what is used — the drift W0.3 worried about cannot exist here.
- **WJ.14 The in-flight branches (W0.11).** Audited before they land; findings in the section at
  the end of this document.
- **WJ.15 The layer below Kubernetes (W0.4).** OCI, the GitHub App, Bitwarden and DNS get the same
  treatment. An agent read-only in Kubernetes while holding an OCI administrator key is not
  confined, and OCI's short-lived session tokens are the same primitive.

## What was rejected, and why (headline rule 1)

Teleport and HashiCorp Vault both solve brokered short-lived access and both were rejected by the
founder by name as heavy identity brokers for a one-founder estate; Teleport is in zero files here.
What remains is not a script standing in for a mature tool — it is thin glue over two vendor
primitives that already exist and already do the cryptography: the Kubernetes TokenRequest API
(`kubectl create token --duration`) and OCI short-lived session tokens. The expiry, which is the
whole guarantee, is theirs, not ours.

---

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

---

# The audit of the work already in flight (WJ.14 / W0.11), 2026-09-07

Every unmerged branch was graded against the rules above, excluding the 2026-09-03 `backup/` and
`rescue/` snapshots, which are recovery images rather than work. **82 branches touch
infrastructure. 62 are clean. 20 are flagged, and 5 must not land in their current shape.**

Uncommitted work is not the risk: of 25 working copies on the founder's machine only the main
checkout has uncommitted infrastructure changes — three files of another session's Cyrus work,
38 lines, no permission grant, no privileged or host-level setting, no cluster credential.

## The five that must not land as they are

| Branch | Age | Files | What it does |
|---|---|---|---|
| `temp-work` | 3 days | 19 | Adds `cluster-admin` and a ClusterRoleBinding to `platform/rbac/bridge.yaml` — the founder's phone bridge, which is deliberately `view` and says so in its own comment. Also adds `bin/idp-headlamp-mac`, `bin/idp-kubeapi-mac`, `bin/idp-phone-kubeconfig`. This is a standing credential being widened, which is the exact thing WJ replaces. |
| `salvage/crew710-minimax-headers` | 2 days | 103 | Touches the entire autonomous-merge machinery in one branch — `deploy-when-green.yml`, `bin/idp-image-only-diff`, `bin/idp-pr-arm`, `bin/idp-pr-landable`, `bin/idp-ci` — plus `platform/spire/`. WJ.8's concern, live. |
| `wt-render` | 10 days | 337 | Touches the cage and the gates together: `bin/idp-kube`, `bin/idp-cloud`, `bin/idp-ci`, `bin/repo-rulesets`, `platform/identity/`. Unreviewed for ten days. |
| `road-b-raw-calico-swap` | 29 hours | 2 | 4 ClusterRoleBindings, 4 `privileged: true`, 1 `hostNetwork: true`, 13 `hostPath` in `platform/calico/raw-migration/`. Calico legitimately needs host access, so this is likely correct — and it is also the largest blast radius in the estate, so it is core glass-break and gets read line by line. |
| `fix/tailscale-operator-tag` | 2 days | 17 | 6 ClusterRoleBindings, and it edits `bin/idp-oke-break-glass`, `bin/idp-estate-audit`, `bin/idp-estate-backup` and `platform/tailscale/policy.hujson` — the break-glass path itself. |

## The rest of the flagged set

Touching the cage in a small way, each to be read before merge: `fix/blind-line-names-the-real-fault`
(`bin/idp-kube`, `bin/idp-cloud`), `fix/crew722-seed-needs-no-tofu` (`bin/idp-cloud`),
`fix/crew727-intervals-one-value` (70 files, `platform/identity/`, `platform/spire/`),
`wip/crew488-cp5-merge-main` (`platform/spire/exception.yaml`).

Touching the machinery: `fix/kyverno-judge-grep-q-sigpipe-reads-green` (`bin/idp-ci`,
`bin/repo-rulesets`), `fix/rollup-duplicate-runs` (`bin/idp-pr-landable`), `pr361-review`
(`bin/idp-ci`), `test/r76-purge-prose-pinning` (`AGENTS.md`, `bin/idp-ci` — a rule change).

Reaching the core blast radius, ordinary platform work needing his merge as they already do:
`feat/otto-door-step5`, `feat/otto-memory-store`, `feat/otto-staging`, `fiu`,
`fix/calico-tigera-reset-lands-raw`, `fix/commerce-onto-estate-db`,
`fix/crew562-the-acl-locks-the-founder-out-of-his-own-mac`, `fix/human-vault-sdk-cycle`,
`fix/kyverno-judge-audit-warn-split`, `fix/tailscale-operator-runs-as-root`,
`otto-gateway-manifests`.

## The rule this produces

A branch may not change the machinery that constrains agents in the same commit as anything else.
The five above are not refused; they are **split** — the cage or machinery change becomes its own
small pull request the founder reads, and the rest lands normally. `temp-work`'s widening of the
phone bridge to `cluster-admin` is the one change that is refused outright rather than split: WJ.1
removes the need for it, and WJ replaces what it was reaching for.
