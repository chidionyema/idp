# The estate world model: simulate before execute, on the door that already exists

Founder record: `~/.claude/docs/founder/2026-09-08T2341Z-and-thislaos-link-the-tickets-28028451.md`
("ok lets design and build the whole thing ... considering all edge cases", "genius high tech ...
asymmetrically production ready for enterprise", "dont wanna pay for gpu"). Board row: MUM-288,
linked to MUM-287 (FleetView part two) and MUM-289 (the autonomous-company research).

## What the founder pasted, and what it is underneath

The pasted design has four parts: a Z3 SMT "world model" MCP server that proves a change safe
before it runs; an eBPF DaemonSet that streams a causal graph of the cluster to NATS; a "dark
factory" that self-plays changes against the model overnight; and an OKE deployment with a
`cyrus-admin-sa` service account. The idea underneath is right and this estate already voted for
it: ADR 0006 says every state-changing tool is two calls, propose then execute, and execute refuses
when the state hash no longer matches. Nothing in `mcp/plugins/` implements that yet (grep for
`state_hash` finds nothing), and nothing in `bin/`, `platform/` or `.github/` uses Kubernetes
server-side dry-run. So the world model is the missing half of a decision already taken, not a
new system.

## Decision

The world model is **the cluster's own admission chain run without persisting**, plus four graders
this repository already owns, exposed as one propose/execute tool pair on the estate MCP server.

| Question the model must answer | Grounded source, already here | Why not the pasted version |
|---|---|---|
| Will the API server and admission accept it? | `kubectl apply --dry-run=server` through `bin/idp-kube`: Kyverno's 14 ClusterPolicies and every webhook run for real, nothing persists (KEP-576, GA) | Z3 over three booleans is an if-statement wearing a solver; the real invariants live in Kyverno and the 8 rego files under `policy/`, and a second copy would drift |
| Does it pass the repository's laws? | `conftest test` over `policy/`, the gates in `rules.yaml` via `bin/idp-rules run` | same |
| What else does it touch? | The catalog relation graph: `dependsOn` edges `bin/catalog-gen` proves from the inventory, checked by `bin/catalog-refcheck` | a homebrew eBPF causal DAG rediscovers edges the catalog already states, with a privileged DaemonSet |
| Can it reach what it needs, and nothing else? | Calico flow logs read by `bin/idp-calico-deny-log`; fence verdicts from `bin/idp-fence-enforcement` | the pasted DaemonSet HTTP-posts to NATS 4222; NATS is not HTTP, and flows already land in the collector |
| Will a node take it? | `bin/idp-fits-a-node` against live node capacity | admission passing is not scheduling passing; the pasted design never asks |
| Does it converge once applied? | The shadow-verify gate (PR #2670): Ready at replicas, probes and tests green in the shadow namespace | the "dark factory" self-play is this gate on a Dagster schedule, not a new loop |

Rejected outright: a standing `cyrus-admin-sa` (WJ.5, decision 0025: agents hold no write on
production; the executor is the JIT broker's short grant); any GPU node pool (nothing above needs
one; the estate is CPU-only OKE); manifests written to `/tmp` (the proposal is the artefact, stored
under the proposal id in the MCP server's state, never a host path).

## The tool pair

`simulate_change(source)` where `source` is one of: a git ref plus path in this repository (the
normal case, Flux owns the live object so the diff is graded, never the live object), an inline
manifest, or a named MCP action (`scale`, `suspend`, `rollout-restart`) with its arguments.

Returns one proposal:

```
proposal_id, computed_against: {cluster_state_hash, git_sha},
admission:   {verdict, kyverno_denials[], webhook_errors[]},
laws:        {verdict, failing_rules[]},
blast:       {resources_touched[], dependents_from_catalog[], namespaces[]},
network:     {new_reachability[], denied_paths_seen_last_cycle[]},
placement:   {fits: bool, node, or reason},
converge:    {shadow_verify: PENDING|PASS|FAIL, drill_url}
verdict:     SAFE | UNSAFE | UNKNOWN, expires_at
```

`execute_change(proposal_id, cluster_state_hash)` runs only when the hash equals the one the
proposal was computed against and the proposal has not expired (default 10 minutes). Execution is
a commit to the state branch that Flux reconciles, or a JIT grant from the broker for the named
action; never a direct write with a standing credential. The hash is the sha256 over the sorted
`resourceVersion` of every object in the touched namespaces plus the git sha of `clusters/`.

`UNKNOWN` is a real verdict and is not `SAFE`: a probe that could not run fails closed, the same
rule `bin/idp-fence-enforcement` already enforces.

## Edge cases, each with the behaviour and the test that pins it

| Case | Behaviour | Test |
|---|---|---|
| A validating webhook is down during dry-run | `admission.verdict = UNKNOWN`, whole verdict `UNKNOWN`; execute refuses | fixture: webhook Service with no endpoints |
| Proposal against a stale hash | execute refuses with the two hashes; caller must re-simulate | mutate a ConfigMap between simulate and execute |
| Passes admission, no node fits | `placement.fits = false`, verdict `UNSAFE` | fixture: request 64 CPU |
| CRD not installed yet (multi-document manifest, CR after CRD) | dry-run documents in order; a CR whose CRD is only in the same proposal is graded `PENDING`, verdict `UNKNOWN` until the CRD is applied | fixture from `tests/fixtures/nodesoftware-operator` |
| Document 3 depends on document 1 (Secret referenced by Deployment) | blast graph orders the apply; missing reference is `UNSAFE` | fixture with a dangling `secretKeyRef` |
| Flux owns the object | source must be a git ref; an inline manifest for a Flux-owned object is refused with the path in `clusters/` that owns it | fixture: inline manifest matching a Kustomization inventory entry |
| Namespace has no fence yet | `ns-fence-gate` fails, verdict `UNSAFE` | existing fixture `tests/fixtures/ns-fence/bad.yaml` |
| Proposal expired | execute refuses; re-simulate | clock fixture |
| Two proposals touch one object | execute of the second refuses on hash mismatch after the first lands | sequential test |
| The dry-run itself is a paid-capacity change | capacity rego (`policy/fixtures/capacity-over-cap.json`) grades it; over cap is `UNSAFE` | existing fixture |
| Agent asks to execute without simulating | no proposal id exists; refused | unit |
| The MCP server cannot reach the API server | `UNKNOWN`, never `SAFE`; FleetView shows the grader as down | kill the agent-reader kubeconfig in test |

## Where it lands

- `mcp/plugins/estate_simulate.py`: the two tools, byte-ceilinged summary by default (ADR 0006).
- Grader calls shell out to the existing `bin/` programs; no logic is copied.
- Dagster: one nightly job that re-simulates every open pull request touching `clusters/` or
  `platform/` and posts the verdict on the PR; this is the "dark factory".
- FleetView (MUM-287): a proposal is a node in the agent's live mind; the founder sees
  `SAFE`/`UNSAFE`/`UNKNOWN` per grader before the agent is allowed to execute.
- Cyrus and every engine get `simulate_change` in their allowed tools; `execute_change` stays
  behind the JIT broker's grant catalogue (`bin/idp-jit-grants`).

## Done, in commands

```
python3 -m pytest tests/test_estate_simulate.py            # every row of the edge-case table
bin/idp-ci                                                  # rules.yaml row: a state-changing MCP tool without a simulate twin is refused
# empirical: one real proposal from a real agent session, quoted from the MCP server log,
# with verdict UNSAFE on a Kyverno denial, then SAFE after the fix, then execute -> Flux commit sha
```

Not done by this spec: the eBPF causal layer (Calico flows and the collector carry it today; revisit
only if a grader needs an edge the catalog cannot state); Z3 (revisit when an invariant is
quantified over more than the Kyverno/rego engines can express, none is today).
