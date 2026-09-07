# Crossplane owns Day-2, OpenTofu owns the ground, and one target never has two owners

2026-09-08. The founder, reading the Diamond Standard record's rejection line: "i think if
crossplane has benefits for us we need to work out how to fit it in."
Record: `~/.claude/docs/founder/2026-09-07T2331Z-like-why-cant-they-coexist-ntyring-to-undertsd-8fd87e60.md`.

This supersedes point 5 of `2026-09-01-diamond-standard-jit-compiler.md`, which named Crossplane,
rejected it for control-plane weight, and stopped there. That rejection was not wrong for what was
known then. Two things have changed since, and both are measured below.

## What OpenTofu holds today

`platform/oci` is 44 resources: 13 `random_password`, 11 `oci_vault_secret`, 7
`oci_identity_policy`, 4 `random_uuid`, 4 NSG rules, 2 buckets, 2 dynamic groups, 1 KMS vault, 1
KMS key, 1 object lifecycle policy, 1 NSG, 1 compute instance, 2 `terraform_data`. State lives in
OCI Object Storage. Every apply runs from CI, holding an OCI credential in the runner.

Nothing in that list is a per-application or per-tenant resource. There is no self-service path
today: an application that wants its own bucket gets one by a human editing `.tf` and merging.

## The line

**OpenTofu owns what must exist before the cluster does.** The VCN, the NSG and its rules, OKE
itself, the KMS vault and key, the state bucket, the identity policies and dynamic groups that let
anything authenticate at all, and the one compute instance. These are ordered, they are few, they
are edited about once a quarter, and a reconciliation loop buys nothing against them. Terraform's
plan-diff-in-a-pull-request is the right gate for the ground floor.

**Crossplane owns what a running namespace asks for.** A bucket for an application, a managed
PostgreSQL for a tenant, the scoped identity policy that goes with it. These are many, they are
requested rather than designed, they are created and destroyed on an application's schedule, and
their lifetime is the namespace's lifetime — which is a Kubernetes fact, not a Terraform one.

The test for which side a resource sits on is one question: **does the cluster have to already be
running for this to be asked for?** If yes, it is Crossplane's. If the cluster cannot exist without
it, it is OpenTofu's.

## The seam already exists, and it is one branch wide

`bin/intent-compile:145`, `compile_storage()`, already dispatches on `ESTATE_STORAGE_PROVIDER` and
raises `BLIND` when a provider has no backend. It emits `oci_objectstorage_bucket` HCL today.
Crossplane is a second branch of that same dispatch: the same storage intent JSON, emitted as a
Crossplane Claim instead of HCL.

This is why coexistence costs almost nothing here. The agents' intent vocabulary does not change by
one field. Nothing in `schema/intent/` changes. The compiler grows an emitter; the estate grows an
operator. If the operator ever turns out to be the wrong call, the emitter branch is deleted and the
HCL branch is still sitting there — the intents are untouched either way.

## The split-brain guard, which is the load-bearing part

Two controllers owning one cloud resource is the failure everyone means when they say these tools
fight. It is not a philosophical risk; it is a write loop that runs at Crossplane's reconcile
interval until someone notices the bill.

So: **one target has exactly one owner, and a rule proves it.** `bin/intent-compile` refuses to
emit both a `.tf` resource and a Claim for the same intent name, and a `rules.yaml` row refuses a
pull request in which a Crossplane Claim's `external-name` matches any `resource` address under
`platform/oci`. Both fixtures, both ways, graded like every other row in `AGENTS.md`.

## Two things that changed since the rejection

**1. The provider is Oracle's own, not a community port.** `oracle/crossplane-provider-oci` is
built with Upjet, reached v1.0.1 in April 2026, covers 150-plus OCI services through a modular
provider family, and supports Crossplane v2's namespaced resource model. The weight objection was
priced against one monolithic provider; the family architecture means installing only the
sub-providers a resource class actually needs.

**2. It authenticates by Workload Identity, and that is a LAW 52 win OpenTofu cannot match here.**
Terraform applies from CI, which means an OCI credential lives in the runner. Crossplane running
inside OKE with Workload Identity holds no credential at all — the pod's projected service-account
token is the identity. That is the one-root-per-provider rule satisfied by the tool rather than by
our own mint-and-store scripts, and it removes a stored credential rather than adding one.

## The autonomy objection, and why it does not apply to this estate

The standard fear is that an agent applies a bad Claim and a controller executes it against live
infrastructure before anyone blinks. That fear is correct for a `kubectl apply` Crossplane. It does
not describe this estate: the agents-never-deploy ruling (2026-09-01) stands, no agent holds write
on production (decision 0025), and Claims land in Git and reach the cluster through Flux like every
other manifest. The reconciliation loop runs on founder-merged Claims. Crossplane's autonomy is
downstream of the same gate as everything else.

What Crossplane does add is drift correction on the resources it owns, which the estate has none of
today for anything under `platform/oci`.

## What actually blocks it, measured 2026-09-08

Not architecture. Capacity.

```
$ kubectl top nodes
NAME           CPU(cores)   CPU(%)   MEMORY(bytes)   MEMORY(%)
10.0.148.221   3036m        52%      16283Mi         79%
10.0.159.197   1373m        23%      16107Mi         78%

$ kubectl describe nodes | grep -A6 'Allocated resources'
  cpu     5791m (99%)    memory  20295Mi (99%)
  cpu     5726m (98%)    memory  15945Mi (77%)
```

Both nodes are at 98 and 99 percent of allocatable CPU requests. A Crossplane control plane is the
core deployment plus one pod per installed sub-provider; it will not schedule against one percent of
request headroom, and forcing it there evicts something already load-bearing.

**So the precondition is a node pool with room, not a decision.** Until that lands, this record is
the design and nothing is installed. The capacity work is governed by the paid-capacity cap in
`estate-defaults.yaml`, and it is the same conversation as the ClickHouse ceiling a peer session
reported on 2026-09-07 (LEAD, unverified here).

## Order of work, when capacity exists

1. The `rules.yaml` split-brain row and its two fixtures, before any operator is installed. The
   guard predates the thing it guards.
2. Crossplane core plus `provider-family-oci` with only the object-storage sub-provider, under
   Flux, with Workload Identity and no stored credential.
3. The Claim emitter branch in `compile_storage()`, behind `ESTATE_STORAGE_PROVIDER`.
4. One real application bucket moved from HCL to a Claim, with the OpenTofu resource removed in the
   same pull request — never both, per the guard above.

Nothing else in `platform/oci` moves until that loop has run a full cycle and the drift it corrected
has been read out of the cluster, not out of a plan file.
