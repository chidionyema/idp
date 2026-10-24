# Delegated estate routing review and implementation record

Date: 2026-10-24
Baseline reviewed: `81bd8c467df4f3151ffb509c10997037264fdb46`
Status: implementation landed through the estate's claim and Greenlane path; deterministic
tests green; the operational proof is a production routing log line, recorded on the claim
issue named in this change's commit trailers

## Review corrections

The 2026-10-23 delegated-estate document is a proposal, not an implementation record. Its
fan-out narrative also misses important prior art: `delegate-build.py` already has a plan,
step dependencies, disjoint-file dependency waves, bounded parallel dispatch, rewind, and
empirical done-checks. The correct implementation is therefore an extension of that
orchestrator, not a second delegation runtime.

The review also found two routing defects relevant to the proposal:

1. Planner and builder defaults named Claude models directly instead of resolving an
   artifact policy through the estate router.
2. Dead-group rescue preserved request class and mode, but not a delegated call's required
   capability tier. The legacy `default` and `fast` groups contain mixed model classes and
   cannot honestly stand for one tier.

The existing lane registry remains the only health/failure classifier used here. The action
ledger remains the attribution substrate; this change adds routing decisions to delegate
usage records and tier/policy data to substitution evidence rather than creating another
health system or ledger.

## Routing contract

The canonical policy is `platform/llm/artifact-tier.yaml`; `artifact_tier.py` validates and
executes it. There is no model-based semantic classifier in this path.

| Work | Initial route |
| --- | --- |
| verify, merge, land, bind, status | `none`: deterministic, no model call |
| standard plan/review/new-file authoring | `mid` |
| deep reasoning or high risk | `frontier` |
| mechanical build/edit with an executable gate | `cheap` |
| mechanical build/edit without a gate | `mid`; cheap is refused |

Automatic dispatch re-plans at frontier after two failed gated attempts. A missing or
invalid re-plan stops the step: there is no blind third attempt. Re-planning may change only
the step title and instructions; identity, file/read scope, dependencies, done-check, and
routing metadata are protected. Failed changes are still rewound and subsequent builders
receive raw empirical output, not prior model reasoning.

Policy aliases map to existing LiteLLM groups. Providers and credentials remain outside the
policy. Legacy aliases retain their previous rescue behavior; known policy aliases rescue
only within their tier and never fall through to a weaker healthy lane. The local floor is
mandatory, cheap-tier, and last in the cheap rescue order.

Explicit planner/builder model names remain manual compatibility overrides. Automatic mode
is the default and is the mode covered by the capability and escalation contract.

## Implemented

- Canonical artifact policy, schema validation, configured-alias validation, policy hash,
  deterministic routing decisions, same-tier rescue order, and failure-triggered re-plan
  decisions.
- Policy-aware dead-group rescue with tier and policy version in metadata and substitution
  journal rows.
- Automatic `planner=auto` and `builder=auto` delegate operation, per-step artifact metadata,
  routing evidence in usage records, protected frontier step re-planning, and updated
  `plan.json` persistence.
- Intent defaults and explicit `reasoning`/`risk` inputs.
- Router installation and runtime synchronization of both the policy module and canonical
  YAML, so policy-only changes trigger the existing restart/acceptance/rollback path.

## Verification evidence

Shell syntax checks passed for `bin/estate-runtime-sync`, the only shell script this change
touches. The following focused suite passed **46 tests**:

```sh
python3 -m pytest -q \
  tests/test_artifact_tier.py \
  tests/test_route_table.py \
  tests/estate/test_delegate_build_reality.py \
  tests/estate/test_delegate_build_prior_art.py \
  tests/estate/test_delegate_plan_survives_a_late_message.py \
  tests/test_runtime_sync_router.py
```

The tests cover no-model deterministic classes, mid-versus-frontier planning, cheap gating,
high-risk escalation, the two-failure boundary, local-floor and alias uniqueness invariants,
real configured aliases, legacy router compatibility, same-tier rescue and evidence, manual
rewind behavior, automatic re-planning, invalid-replan stop behavior, planner stream recovery,
and policy rollout.

## Landing and operational status

- The change lands through the repository's normal path: a claim on an open issue, the
  commit carrying the `Claim:` and `Agent:` trailers, and the lane handed to the Greenlane.
  The claim issue is named in this change's commit trailers.
- `bin/litellm-local` is deliberately not touched by this change: it is held by a live
  claim (#6857). The policy module and the canonical YAML therefore travel to the live
  router through `bin/estate-runtime-sync`, which names both files explicitly instead of
  relying on that script's `MODULES` list. A from-scratch `bin/litellm-local install`
  therefore does not stage `artifact_tier.py` by itself; the runtime sync re-adds it on
  its next tick, and the holder of that claim has been asked for the one-line `MODULES`
  entry so both paths agree.
- Operational proof is the existing router acceptance path plus a real production log
  line showing a tier decision and, when exercised, a capability-preserving rescue. That
  evidence is recorded on the claim issue, not asserted here.
- Discovery Plane, Message Plane, Quad operationalisation, family-diverse semantic review,
  Fleet/Face surfaces, and the rest of the wider delegated-estate epic remain separate work.
