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

The founder, reading the first draft of this record: "bu if we are bootsarpping why is anyone
looking a diff in confused". He is right, and the first draft was wrong.

That draft justified OpenTofu's half with "you want a human looking at a plan diff in a pull
request." That argument is worthless here, for two reasons. It does not distinguish the two tools —
a Crossplane Claim lands in Git and reaches the cluster through Flux, so it gets exactly the same
pull-request gate the HCL does. And it does not survive the bootstrap goal at all: the point of
compiling intents is that nobody reads Oracle resource addresses. Reaching for the industry's
standard defence of Terraform imported a governance argument this estate does not run on.

Strike it. There is exactly one real reason the foundation is OpenTofu's, and it is physics, not
policy: **Crossplane runs inside the cluster, so it cannot build the things that must exist before
the cluster does.** It cannot create the network it is reachable on, the cluster it is scheduled in,
the vault its Workload Identity reads, or the identity policy that makes that Workload Identity mean
anything. Something outside the cluster has to make those. That is OpenTofu's entire job here.

Applied honestly, that criterion cuts far deeper than the first draft admitted.

**The irreducible bootstrap set is six resources**, and they are all in three files:

| file | resource | why it cannot be Crossplane's |
|---|---|---|
| `main.tf` | the `oke` module | it is the cluster Crossplane would run in |
| `iam.tf` | `oci_identity_policy.operators_compartment` | the compartment grant everything else hangs off |
| `vault.tf` | `oci_kms_vault.estate` | holds the seed, read before any pod starts |
| `vault.tf` | `oci_kms_key.estate` | same |
| `vault.tf` | `oci_identity_dynamic_group.workers` | the identity a pod presents |
| `vault.tf` | `oci_identity_policy.workers_read_secrets` | what makes that identity able to read anything |

Plus the state bucket OpenTofu keeps its own state in, which is outside this count because it
predates the code.

**The other thirty-eight are application resources wearing foundation clothes.** The 13
`random_password` and 11 `oci_vault_secret` resources live in `langfuse.tf`, `flux-webhook.tf`,
`healthchecks.tf`, `otlp-ingest.tf`, `bridge.tf`, `commerce.tf`, `signoz.tf` and `superset.tf` —
eight files, each named after a workload that runs in the cluster. Not one of them can be needed
before the cluster exists, because the thing that consumes it is a pod. They are in OpenTofu for a
historical reason, not a structural one.

They also carry a cost worth naming: `random_password` puts the generated plaintext in the
OpenTofu state file, which lives in an Object Storage bucket. Twenty-four secrets for eight
workloads are sitting in a state file today because Terraform is where they were born. Moving them
off is a security improvement, not housekeeping.

**So the test stands and the answer changes.** The question is still "does the cluster have to
already be running for this to be asked for?" Applied to all 44 resources, the honest split is six
on the OpenTofu side and thirty-eight candidates on the other — not the roughly-half the first draft
implied. Six is the number that makes the coexistence argument, because six is small enough that
nobody has to look at it again.

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

Not architecture. Not money either, which the first version of this section got wrong.

The founder, on the capacity claim: "why are they at that budget ? sonehing no tright". He was
right to distrust it. Both nodes report 98 and 99 percent of allocatable CPU **requests**, but
`kubectl top nodes` reports 52 and 23 percent **used**. A gap that wide is not a full cluster; it is
a misdeclared one.

```
$ kubectl top nodes
10.0.148.221   3036m  52%   16283Mi  79%
10.0.159.197   1373m  23%   16107Mi  78%

requested across 142 running pods:   11437m
actually used, sum of both nodes:     5833m
reserved and idle:                    5604m  (49% of the cluster)
```

Three pods explain most of it, all in `observability`:

| pod | requests | uses | note |
|---|---|---|---|
| `langfuse-web` | 1000m | 9m | 0.9% of its own reservation |
| `langfuse-worker` | 1000m | 108m | 134 restarts in 27h — crash-looping while holding a full CPU |
| `chi-signoz-clickhouse-cluster-0-0-0` | 1000m | 1998m | double its reservation; the one that genuinely needs CPU |

The shape of the problem is inverted from the first reading. The workload that actually consumes CPU
is under-declared and being squeezed; two neighbours that consume almost none hold 2000m between
them, which is 17 percent of the cluster. The scheduler is full on paper while the machines are half
idle, so nothing new can be placed — Crossplane included.

**The precondition is right-sizing three requests, not buying a node pool.** That is free. It is
also the same root cause as the ClickHouse ceiling and the silent OTLP collector a peer session
reported on 2026-09-07, so it is not new work. Those pods are that session's lane; the measurement
was handed over rather than acted on here.

This is adjacent to the placement rule that landed in `AGENTS.md` as `bin/idp-fits-a-node`, and
distinct from it: that rule grades whether a pod *could be placed* on the nodes that exist. It does
not grade a pod that places fine and then reserves eleven times what it uses. Whether that second
rule is worth writing is a question for after the three requests are corrected, and it is not
claimed here.

## Order of work, when capacity exists

1. The `rules.yaml` split-brain row and its two fixtures, before any operator is installed. The
   guard predates the thing it guards.
   **Shipped 2026-09-07:** `bin/idp-split-brain`, the `rules.yaml` row and both fixtures (#2449).
2. Crossplane core plus `provider-family-oci` with only the sub-providers the first move needs,
   under Flux, with Workload Identity and no stored credential.
   **Shipped 2026-09-08:** `platform/crossplane/` (chart 2.4.0, the family provider and
   `provider-oci-objectstorage` v1.3.0, a `DeploymentRuntimeConfig` pinning the service account
   name, and a `ProviderConfig` whose credential blob is two keys and no key material),
   `platform/oci/crossplane.tf` (the IAM statement that is the entire boundary), and the two
   `Kustomization` rows in `clusters/oke/platform.yaml`. `ESTATE_OCI_REGION` joins the DNA.
3. The Claim emitter branch in `compile_storage()`, behind `ESTATE_STORAGE_PROVIDER`.
4. One workload's secrets moved off OpenTofu, with the `random_password` and `oci_vault_secret`
   resources deleted in the same pull request — never both sides, per the guard above. The
   candidate is whichever of the eight files has the fewest consumers, decided by measurement then,
   not asserted here.

Nothing else moves until that first one has run a full cycle and the drift it corrected has been
read out of the cluster, not out of a plan file. Thirty-eight resources is a migration, and a
migration is proved one workload at a time.
