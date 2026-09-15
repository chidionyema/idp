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

## 2026-09-15 status: step 3 shipped, step 4 still deliberately not started

**Shipped:**
- `bin/intent-compile`'s `compile_storage()` now dispatches on `ESTATE_STORAGE_PROVIDER`: `"oci"`
  keeps emitting the existing `.tf`, a new `"crossplane"` branch (`compile_storage_crossplane()`)
  emits a `Bucket.storage.estate.io/v1alpha1` Claim instead. Any other value is a `BLIND` refusal
  (no silent fallthrough).
- `platform/crossplane/capabilities/storage/xrd-bucket.yaml`: the `XObjectStorageBucket` XRD,
  claiming as `Bucket.storage.estate.io`, with exactly the four fields
  `schema/intent/storage.schema.json` already exposes to agents (`name`, `purpose`, `size_gb`,
  `access`) — no provider, region or bucket URL reaches the intent vocabulary.
- `platform/crossplane/capabilities/storage/composition-bucket.yaml`: the `Composition` that maps
  those four fields onto the real `Bucket.objectstorage.oci.upbound.io/v1alpha1` managed resource
  confirmed live in-cluster (`bin/idp-kube get crd`), patching in `compartmentId`/`namespace` from
  the DNA (below) and `access` (`private`→`NoPublicAccess`, `public-read`→`ObjectRead`).
- `clusters/oke/estate-config.yaml`: added `ESTATE_OCI_COMPARTMENT_OCID` and `ESTATE_OCI_NAMESPACE`,
  measured against the live tenancy with the OCI CLI (`oci os ns get`; `oci iam compartment list`
  + `oci os bucket list` per compartment, to find the one actually holding
  `estate-shop-backups`/`estate-drill-receipts`/`estate-db-backups`/`estate-tofu-state` — the
  "estate" compartment, not the tenancy root `platform/oci/variables.tf`'s comment calls
  "acceptable," which this measurement found holds zero buckets).
- `clusters/oke/platform.yaml`: a fourth Crossplane `Kustomization`, `crossplane-storage-capability`,
  `dependsOn: [crossplane-providerconfig]`, installing the XRD+Composition live (not suspended) —
  safe to run live because a `Composition` provisions nothing by itself; no Claim references it yet
  (`ESTATE_STORAGE_PROVIDER` is still `"oci"`), so this ships a real, reviewable capability with
  zero cloud-resource or production-data blast radius.
- Proved, not asserted: `bin/idp-split-brain` passes (`ok split 6 Crossplane resource(s) against 84
  OpenTofu identity/identities; no cloud object has two owners`); a scratch intent compiled through
  the new branch with `ESTATE_STORAGE_PROVIDER=crossplane` DNA produces a Claim that (a) validates
  against the XRD's own `openAPIV3Schema` via `jsonschema.validate`, (b) is byte-identical across
  two compiler runs (determinism, same proof `bin/idp-ci`'s `intent` rung already holds the
  `"oci"` branch to); YAML syntax checked on every edited/created file; `bin/idp-rules
  render-agents-md --check` and `bin/idp-ci` both green after the change.

**Still not started, on purpose — step 4 is unchanged from the paragraph above:** migrating any
existing OpenTofu-owned resource (buckets or the eight secrets files) needs (a) a provider not
installed (secrets/vault has no Crossplane provider in this estate yet — only
`provider-oci-objectstorage` is), (b) the capacity-claim measurement this ADR already says is
"decided by measurement then, not asserted here," which nobody has re-run since 2026-09-08, and
(c) Terraform state surgery + cross-tool resource adoption against a resource with a live consumer
— genuine production risk that a same-pass "get it operational" change should not absorb. Step 4
stays exactly where this ADR left it: blocked on measurement, not on step 3.

**Two things this pass deliberately did not attempt, and why:**
- **The `simulate_change`/`execute_change` `admission` grader** (MUM-288) still answers `UNKNOWN`.
  `platform/mcp/estate-mcp.yaml`'s pod has no path to the K8s API at all today —
  `automountServiceAccountToken: false`, no `ServiceAccountName`, no kubeconfig — and the only
  sanctioned way to grant it one, even a dry-run-only verb (Kubernetes has no such verb; the API
  server authorizes `--dry-run=server` against the real `create`/`patch` verb before discarding),
  is `platform/jit/grants.yaml`, which `bin/idp-glass-break` holds permanently glass-break: no
  merge bot, no self-approval, founder review only. Left alone rather than routed around.
- **The `converge`/`network`/`placement` graders** stay `UNKNOWN` too, per the founder's own
  2026-09-12 call on the world-model spec ("park. Code complete, gated"): no shadow-apply executor,
  no Calico deny-log feed (`idp#2452`), no placement-receipt producer exist to grade against.
  Wiring their env flags with no real feed behind them would make `simulate_change` assert instead
  of verify. Only `ESTATE_MCP_GRADE_LAWS_DOOR` was turned on, because `bin/idp-rules run --plane
  ci` is real, already green, and needed no new infrastructure.

**One finding surfaced, not fixed:** `bin/idp-glass-break`'s `PROTECTED` path list contains the
literal string `"platform/rbac/"`. The RBAC floor actually lives at
`platform/rbac-floor/agent-reader.yaml` — a different prefix — so that file is not currently
covered by the glass-break gate, despite the gate's own docstring naming "the RBAC" as one of the
five things it protects. Not exploited (nothing in this pass touched that file). Fixing
`bin/idp-glass-break` is itself in its own `PROTECTED` list, so the fix needs the founder's review
regardless of who writes the diff.
