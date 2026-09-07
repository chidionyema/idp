# 0025 — Agents hold no write on production, and the Greenlane grows one row at a time

- Status: DECIDED 2026-09-07 on the founder's instruction in session
- Deciders: founder
- Extends: 0024 (Otto runs every tool and asks only for the unundoable), 0023 (the boundary is
  enforced by the infrastructure, not the application), 0021 (the founder wears two hats),
  0006 (the platform answers for itself over one MCP)
- Governs: `bin/idp-kube`, `platform/rbac/`, `.github/workflows/deploy-when-green.yml` and every
  scope-check binary it calls, `platform/sandbox/vcluster/`, `platform/edge/gvisor-*`,
  `bin/idp-admission-policies`, and every agent session in this estate — including the thirty-odd
  in-flight branches that touch `platform/`, `bin/` or `.github/`.
- Founder records, verbatim, and the only source for what he asked (never paraphrased from memory):
  - `~/.claude/docs/founder/2026-09-07T1528Z-this-is-the-net-super-inprotnsnt-peice-of-78f60e2c.md`
    — the four pillars and the four-phase Zero-Trust Autonomous Framework.
  - `~/.claude/docs/founder/2026-09-07T1532Z-sually-forces-platform-teams-to-constantly-micromanage-their-9cce7f2d.md`
    — the Greenlane, the Trust Threshold, the Proof Contract and Glass-Break.
  - Two follow-ups in the same session: "this is for all agebts bits, alot of wip also needs to
    abitd by this if they doing infra work" and "eeds state wide analysis andcareful design".

## The instruction

From the first record, the sentence the whole design turns on:

> If you want to sleep at night, the agent cannot possess the physical ability to mutate production
> directly. It must live in a completely asymmetric architecture where its leverage is massive, but
> its blast radius is mathematically constrained to zero.

And its closing advice on order:

> To build this, you don't build the AI first. You build the cage first.

From the second record, the question this decision has to answer rather than return:

> To turn this on, we just define the Trust Threshold. What is the agent allowed to auto-merge
> right now?

## The estate-wide analysis

He is right that we have most of the building blocks. Counted against `origin/main` at 524a67ea,
by files containing the term:

| Pillar in the record | State here | Where it lives | What is missing |
|---|---|---|---|
| 1 — ephemeral vcluster | BUILT, for demos only | `platform/sandbox/vcluster/helmrelease.yaml`, `platform/sandbox/launch/{httproute,live}.yaml`, `.github/workflows/demo-sandbox.yml`, `bin/idp-sandbox-sweep`, `docs/runbooks/demo-sandbox.md`, `tests/test_demo_sandbox_is_defined_and_expires.py` (18 files name vcluster) | live state sync — nothing clones a production workload's manifest, limits and quota down into the sandbox — and no CI job runs assertions inside one |
| 2 — dark infrastructure, eBPF traffic shadowing | NOT BUILT | Cilium is present as the CNI (20 files); `requestMirror` / `mirrorPercent` appear in **0 files** | the mirror itself, and the Prometheus/OTel comparison between live and dark |
| 3 — tainted 1-node canary pool | NOT BUILT | the word `canary` is in 57 files, none of them a node pool; the RuntimeClass half exists — `platform/edge/gvisor-runtimeclass.yaml`, `gvisor-admission.yaml`, `otto-gvisor-sandbox-namespace.yaml`, `bin/gvisor-cell-gate`, `bin/gvisor-cell-fence-gate` (16 files name gVisor) | the `infra.canary=true:NoSchedule` pool, and the SLI watch that promotes or rolls back |
| 4 — Audit-mode shadow webhooks | HALF BUILT | `bin/idp-admission-policies:40-41` already treats a silent rule as Audit — "a rule that says nothing is Audit, which is Kyverno's default"; `platform/edge/kyverno-secrets-policy.yaml:30` is `validationFailureAction: Audit` (29 files name Audit) | nobody reads the audit stream, so nothing measures a full day of churn and nothing flips a clean rule to Enforce |
| Phase 4 actuator | BUILT | Flux reconciles every namespace; `.github/workflows/deploy-when-green.yml` lands the tag | progressive traffic — `flagger` and `argo-rollouts` appear in **0 files** — and the deadman's switch |
| Phase 1 confinement | **NOT BUILT** | `platform/rbac/bridge.yaml` is the only read-only identity in the repo, and it is the founder's phone, not an agent | everything |
| Phase 3 immutable ledger | BUILT | `allow_auto_merge` was set false on 2026-08-30 with the founder-only-releases ruleset (`bin/repo-rulesets`); `bin/idp-pr-arm` reports "the merge is the founder's" rather than failing | nothing |

Two findings reorder his phase list, and both are the reason this document exists before any code.

**The cage is the one thing we do not have, and it is wide open.** `bin/idp-kube` is the estate's
only approved cluster path — rule-guard's `bare_kubectl` rule refuses `kubectl` and names this file.
It mints a kubeconfig through `bin/idp-cloud cluster kubeconfig` **as the founder's own OCI
principal**, caches it at `$XDG_STATE_HOME/idp/kubeconfig` for `IDP_KUBE_MAX_AGE_MIN` minutes, and
ends `KUBECONFIG="$KC" exec kubectl "$@"`. Every agent session in this estate therefore holds
cluster-admin on production today. Phase 2's vcluster and Phase 3's pull request are both optional
detours while that is true: an agent that can write to production has no reason to go through
either. His ordering is not a preference, it is a precondition.

**The Greenlane already exists — with exactly one row in it.** `.github/workflows/deploy-when-green.yml`
is his Proof Contract, built here on 2026-08-31 and running since: a Scope Check
(`bin/idp-image-only-diff` passes a pull request only when every changed line is a `newTag:`
carrying the controller's own `$imagepolicy` marker and the marker is unchanged), a Test Pass
(`bin/idp-pr-landable` reads the check rollup), and Autonomous Execution (the workflow merges with
a GitHub App token). So the answer to "what is the agent allowed to auto-merge right now" is a fact
before it is a decision: **one class of change, the image tag bump, and nothing else.**

That matters for how we grow it. We do not build a second merge mechanism next to it — that is the
stitching the headline rule forbids. The Trust Threshold is a **table of rows** in the mechanism
that already lands changes, and a row is admitted only when someone has written the binary that
proves its scope, with a fixture it must refuse and a fixture it must pass.

## The decision

### Phase 1 — confinement, and it is first

`bin/idp-kube` stops minting the founder's principal for agents. It mints a token for a
ServiceAccount bound to the built-in `view` ClusterRole, the pattern `platform/rbac/bridge.yaml`
already sets and already argues for: "view, not cluster-admin: this exists to read a pod log during
an outage, and a debugger that can delete things is a debugger that can cause one. `view` excludes
secrets by design." Reads stay as fast and as wide as they are today — every agent keeps `get`,
`list` and `watch` across every namespace, which is what the estate MCP server and every
investigation in this session actually needed. `create`, `update`, `delete` and `exec` are refused
by the API server, not by a wrapper an agent can route around.

Write is not removed, it is made loud and asymmetric. `bin/idp-kube --break-glass "<reason>"` mints
the admin path, and every use writes a ledger row and fires a founder push notification naming the
reason and the command. A fence that refuses correct work is an outage (LAW 38); a fence that
records every crossing is an audit trail. That, and not a blocked verb, is what "ultra asymmetric"
buys: reading costs nothing, writing costs a permanent public record.

The audit proxy sidecar in his Phase 1 is deferred, and named as deferred: `teleport` is in 0 files
here, and the estate already routes agent tool calls through Otto's gateway (ADR 0024) and every
cluster read through one MCP server (ADR 0006). We instrument those two, which exist, rather than
introduce a third thing to run.

### Phase 2 — the shadow dimension, built on the sandbox we already run

The vcluster is not new work; giving it production's state is. `bin/idp-sandbox-*` gains a mode
that clones one named workload's manifest, resource block and namespace quota into a fresh
vcluster, and CI gains a job that applies the agent's diff there and runs assertions. Node-level
and network-level changes are explicitly out of vcluster's reach, exactly as the record says, and
wait for the `infra.canary=true:NoSchedule` pool — which is honest new infrastructure and is not
claimed here.

**Proof of Convergence** gets a machine-readable definition so it can gate a merge rather than
decorate a description. A pull request carries a `Proof-of-Convergence:` block in its body naming
the vcluster the change was applied in, the CI run URL that applied it, and the assertion output.
A gate reads that block; a missing or unparseable block is a fail-closed refusal, never a pass.

### Phase 3 — the ledger, which already holds

The agent pushes to Git and never to Kubernetes. That is already true of the repository's
configuration and stays true. Nothing in this decision loosens the founder-only-releases ruleset.

### Phase 4 — the actuator

Flux stays the only writer. Progressive traffic (Flagger or Argo Rollouts) and the deadman's switch
are real gaps, are named as gaps, and are not started until Phase 1 has landed.

## The Trust Threshold, answered

**Live today, unchanged by this decision — one row:**

| Row | Scope check | Blast radius |
|---|---|---|
| Image tag bump on `flux/image-updates` | `bin/idp-image-only-diff` | the tag the founder already approved when he merged the code |

**Admitted by this decision, each landing as its own pull request with its two fixtures:**

| Row | Scope check to be written | Why it is inside the threshold |
|---|---|---|
| Raise a memory or CPU **limit** on one workload | `bin/idp-limit-raise-only-diff` — every changed line is `resources.limits.{memory,cpu}`, the value only moves up, exactly one workload is touched, and the namespace ResourceQuota still fits | his own 3 AM OOMKill example; it cannot deny a request that succeeds today, and the quota read bounds the cost |
| Roll one workload back to a tag main previously carried | `bin/idp-rollback-only-diff` — every changed line is a `newTag:`, and each new tag is one this file already held on main | a rollback to a known-good tag is a state the estate has already run and the founder has already approved |

**Refused — Glass-Break, and this list is closed:** anything under `clusters/`; a NetworkPolicy;
an HTTPRoute, Gateway or ingress route; a Kyverno or admission rule; a CRD or an operator version;
a node pool, CNI or kernel change; RBAC; a ResourceQuota or LimitRange; a resource **request**
(the scheduler counts requests, so raising one can evict a neighbour); and a ConfigMap.

The ConfigMap is the one place this decision departs from his list, and the reason is that a
ConfigMap here has no bounded blast radius — the same kind holds an nginx config, a feature flag
and a database DSN, so "fixing a misconfigured ConfigMap" is not one risk class and cannot be one
scope check. It waits for him until someone can name a subset that is provable.

Secret rotation, also on his list, is not a merge at all in this estate: External Secrets pulls
from Bitwarden and no manifest changes, so a rotation never becomes a pull request. It is already
autonomous and it stays out of this lane.

## The founder keeps all access

Nothing here narrows a path of his (LAW 54). `bin/idp-cloud cluster kubeconfig` is untouched and
still mints his cluster-admin. The phone bridge (`platform/rbac/bridge.yaml`) is untouched. He is
the only merger on every Glass-Break change and gains a second, wider read: every break-glass use
by an agent arrives on his notifications with its reason. The asymmetry runs one way only — agents
lose write, he loses nothing.

## Every agent, and the work already in flight

"this is for all agebts bits, alot of wip also needs to abitd by this if they doing infra work."
Thirty-odd unmerged branches touch `platform/`, `bin/` or `.github/`. A rule that binds them cannot
be a paragraph any of them can be unaware of, so it becomes a row in `AGENTS.md`'s table with a
gate and its two fixtures, which is this repository's own idiom for a rule no session walks past
(LAW 45):

| rule | gate | must-fail | must-pass |
|---|---|---|---|
| A change to `platform/`, `clusters/` or a DaemonSet carries a Proof-of-Convergence block naming the vcluster or canary run that proved it; a missing or unparseable block is a fail-closed FAIL, never a pass | `convergence_proof_gate` | `tests/fixtures/convergence/no-proof.md` | `tests/fixtures/convergence/proved.md` |
| No file mints a cluster-admin kubeconfig outside the founder's own path and the recorded break-glass | `agent_write_path_gate` | `tests/fixtures/agent-write/admin-mint.bad.sh` | `tests/fixtures/agent-write/read-only.good.sh` |

Both gates run in `bin/idp-ci`, so an in-flight branch meets them when it rebases, and a branch
that cannot pass them was doing something this framework forbids.

## Build order

1. Phase 1: `bin/idp-kube` mints `view`; break-glass is loud and recorded; `agent_write_path_gate`
   with its fixtures. Nothing else starts until this lands.
2. Production state sync into the sandbox vcluster, and the CI job that runs assertions in one.
3. `Proof-of-Convergence` block, `convergence_proof_gate`, and the `AGENTS.md` rows.
4. Trust Threshold rows two and three, one pull request each, fixtures both ways.
5. Only then: the tainted canary pool, traffic shadowing, the Audit→Enforce churn reader, and
   progressive rollout.

## Proof boundary

None of this is finished on a local run, and this document proves nothing on its own. Phase 1 is
finished when a live agent session runs `bin/idp-kube` and the API server refuses a write with a
quoted `Forbidden` from real output, while the same session still reads pod logs. The Greenlane
rows are finished when a real pull request of that shape lands itself and the quoted workflow log
names the scope check that passed it. A unit test asserting a scope check is a probe, not proof
(THE EMPIRICAL PROOF RULE).
