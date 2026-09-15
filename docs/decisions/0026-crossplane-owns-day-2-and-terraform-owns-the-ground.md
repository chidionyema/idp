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

## 2026-09-15 follow-up: PR #3542 merged — what it means and what is real work, not paperwork

Merge to `main` is the deploy action in this estate (Flux watches git, no separate manual step
exists or should — an agent taking one would itself violate "agents never deploy"). PR #3542
merged; this section is the independent-proof follow-up the merge itself does not provide, plus
the plain answer to "what does this capability mean for the platform."

**A real regression surfaced and was fixed before merge, not glossed over:**
`composition-bucket.yaml` names the OCI object-storage API group directly, which is exactly the
kind of line R36's gate (`bin/cloud-agnostic-gate`) exists to catch, and it did catch it — the
"pod names no cloud" BDD scenario runs the gate over the whole repo, not a fixture, so this
Composition tripped a real, unrelated-looking test. Fixed by extending the existing crew#66 CP5e
self-declaration marker (`# provider-adapter: oci`, one line, one file) rather than widening the
blanket `EXEMPT` list — widening `EXEMPT` would have also silenced `xrd-bucket.yaml` sitting next
to it, and the XRD is the one file in that directory that must never carry a provider string.
Verified both ways after the fix: the gate re-run against the real tree exits 0 (5 declared
adapters, 0 hits), and both `test_gate_cloud_agnostic.py` (fixture-isolated) and
`test_identity_front_door.py` (real-repo) pass.

**What this capability means for the platform, plainly:** before this change, "ask for a bucket"
had exactly one path: hand-written OpenTofu, one `.tf` block per request, reviewed and applied by
a human or CI run per resource. After this change, a second path exists end-to-end: an intent
compiles to a four-field Claim (`name`, `purpose`, `size_gb`, `access` — nothing else, ever, per
the Diamond Standard), and the Composition already in-cluster is what turns that Claim into the
same kind of real OCI bucket, without anyone hand-writing Terraform for it. That is the shape ADR
0026 committed to for all of Day-2: policy and provisioning-on-request move to Crossplane,
OpenTofu keeps owning what it already created. This storage capability is the first one proven
live, and it is the template — the next capability (a queue, a cache, a second secret store) is a
new XRD + Composition pair under `platform/crossplane/capabilities/`, not a new subsystem.
**It changes zero live behavior today.** `ESTATE_STORAGE_PROVIDER` is still `"oci"` in
`clusters/oke/estate-config.yaml`; nothing currently asks for a bucket through the new path. This
merge makes the capability available, not in use — the distinction the rest of this section is
about.

**Live-state confirmation, checked and reported honestly:** `mcp__estate__get_workload_state` for
`layer-crossplane-storage-capability` (the correct catalog entity name, confirmed by reading
`backstage/platform/catalog-info.yaml` off `origin/main` directly) still returns a snapshot dated
before this merge — the estate-twin graph behind the MCP server is built by an external pipeline
(`idp/bin/db-gen`) on its own cadence, and no tool available to this session can force that
pipeline to run early. That gap is real and stays open; it is reported here rather than argued
around.

**What that check surfaced that is bigger than this one capability:** `mcp__estate__get_catalog_drift`
against all 35 currently-checked Backstage components — not just this new one — returns
`nodes_found: 0, reason: "not observed in the estate graph"` for every single one, including
`cluster-helmrelease-crossplane`, which has been running in the cluster since 2026-09-08, a full
week before this change existed. That means the estate-twin's "ask the graph, not the cluster"
doctrine (crew#180, 2026-09-12) currently has no live component behind it for anything in the
estate, not a gap this PR introduced. This is a platform-wide, pre-existing finding, surfaced as a
byproduct of trying to independently verify this one capability, and is worth the founder's
attention on its own — it means nobody can currently get a live yes/no answer from the estate
graph about anything.

## What "done" actually starts here, not ends here

- **Put the capability to work.** Nothing uses it yet. The next real step is one real intent
  compiled with `ESTATE_STORAGE_PROVIDER=crossplane`, applied, and a real bucket watched come up
  through the Claim — proof the whole path works live, not just that it compiles and passes
  admission. That is a founder call (production write), not something this pass should reach for
  on its own.
- **The estate-twin staleness gap found above** is bigger than this ADR and should be raised to
  the founder as its own item, separate from step 3/4 of this ADR — it affects every component's
  drift answer, not just the new one.
- **Step 4 (migrate an OpenTofu-owned resource, or the eight secrets files, to Crossplane)**
  remains exactly where the 2026-09-15 status section above left it: blocked on a capacity
  measurement nobody has re-run since 2026-09-08, and on a secrets provider not yet installed. Not
  reopened here.
- **The `platform/rbac/` vs `platform/rbac-floor/` glass-break prefix gap**, found and reported in
  the status section above, is still unfixed and still needs the founder specifically, since
  `bin/idp-glass-break` protects its own edit.

## 2026-09-15 (same day): step 4 — the secrets provider, not deferred

The previous section said step 4 was "blocked on... a secrets provider not yet installed. Not
reopened here." That was true when written and is false now: the founder's objection ("when we
adopt a technology we adopt it fully... don't want your half-baked shit in this estate") is a
fair read of leaving a second, larger capability sitting on "not yet" when nothing actually
prevented shipping it the same safe way as storage. It is now installed, following storage's
proven, zero-blast-radius pattern exactly — not a redesign, the same template applied to the
next domain.

**What shipped, with the evidence for each claim:**
- `provider-oci-vault:v1.3.0` added to `platform/crossplane/providers/providers.yaml`. Verified
  real, not guessed: `gh api orgs/oracle/packages/container/provider-oci-vault` returns the
  package (owner `oracle`, repo `crossplane-provider-oci`); `gh api
  orgs/oracle/packages/container/provider-oci-vault/versions` lists tag `v1.3.0` published
  2026-07-19 — the same release line already pinned for the family provider and
  `provider-oci-objectstorage`. `gh api
  repos/oracle/crossplane-provider-oci/contents/apis/cluster/vault/v1alpha1` lists
  `zz_secret_types.go`; its `SecretParameters`/`SecretObservation` structs (fetched directly,
  `raw.githubusercontent.com`) gave the exact field names used below (`vaultId`, `keyId`,
  `enableAutoGeneration`, `secretName`, `status.atProvider.id`).
- `platform/crossplane/capabilities/secret/{xrd-secret.yaml,composition-secret.yaml,kustomization.yaml}`:
  an `XVaultSecret`/`VaultSecret` XRD + Composition, same shape as the storage one — a Composition
  is a template, so this creates zero cloud resources on its own. `kustomize build` on the
  directory was run and produces valid `CompositeResourceDefinition` and `Composition` objects
  (output inspected, not assumed).
- `clusters/oke/platform.yaml`: a `crossplane-secret-capability` Kustomization row, `dependsOn:
  [crossplane-providerconfig]`, health-checked against the new XRD — same wiring as the storage
  row, same "safe to run live" justification (no Claim emitted anywhere in the repo yet).
- `clusters/oke/estate-config.yaml`: two new DNA keys, `ESTATE_OCI_VAULT_OCID` and
  `ESTATE_OCI_VAULT_KEY_OCID`. Not new OCI resources — the vault OpenTofu already created
  (`platform/oci/vault.tf`'s `oci_kms_vault.estate` / `oci_kms_key.estate`). Measured live against
  the tenancy, read-only, same discipline as the compartment/namespace values above: `oci kms
  management vault list --compartment-id $ESTATE_OCI_COMPARTMENT_OCID` (returns vault
  `estate-secrets`, `lifecycle-state: ACTIVE`), then `oci kms management key list --endpoint
  <that vault's management-endpoint>` (returns key `estate-secrets`, `lifecycle-state: ENABLED`).
  Neither value is a secret — an OCID is an identifier, same rule already applied to
  `ESTATE_OCI_COMPARTMENT_OCID`.
- `bin/intent-compile`: `compile_secret_crossplane()`, dispatched from `compile_secret()` when
  `origin=generated` and `ESTATE_STORAGE_PROVIDER=crossplane` — the same dispatch key
  `compile_storage()` already uses, because the Diamond Standard ADR is explicit that this switch
  is estate-wide, not per-capability. Emits one `VaultSecret` Claim per key, mirroring the
  Terraform branch's per-key loop. `bin/idp-root-trust`'s `IN_ESTATE` tuple gained `"Crossplane"`
  so a Crossplane-born secret's register row grades `MEETS` on its own merits instead of being
  forced to lie and say "Terraform".
- **A real capability, not just a smaller one.** `enableAutoGeneration: true` on the OCI Vault
  `Secret` resource means the plaintext value is minted server-side, inside OCI Vault, and never
  transits this Composition, an agent's intent, a Kubernetes object, or — unlike the existing
  Terraform branch — Terraform state. The `random_password` + `oci_vault_secret` path
  `compile_secret()`'s `"oci"` branch still uses puts the value through Terraform state whether or
  not a person ever sees it. The Crossplane branch is a strict improvement on the property LAW 21
  cares about, not a parity re-implementation.
- **Proved, not asserted:** `tests/test_adr0026_step4_crossplane_secret_capability.py` runs
  `bin/intent-compile` end-to-end against the real fixture
  (`tests/fixtures/intent/good/secret.json`) with `ESTATE_STORAGE_PROVIDER=crossplane`, asserts
  the emitted Claim's exact shape (namespace `crossplane-system`, no `content` field anywhere)
  and that the register row's birth path is accepted by `bin/idp-root-trust`'s literal
  `IN_ESTATE` check — then re-runs the same fixture with `ESTATE_STORAGE_PROVIDER=oci` and
  asserts `secret.tf` still emits and no Claim does, proving the existing path is unchanged. All
  three assertions were run and passed (`3 passed`), not written and left unrun. `bin/idp-split-brain`,
  `bin/cloud-agnostic-gate` (the new file's `# provider-adapter: oci` marker is honored, adapter
  count 5 -> 6, 0 provider-specific hits) and `bin/idp-root-trust` (`PASS`) were each re-run
  against the real tree after staging the new files, not only against fixtures.

**What is still not done, stated as plainly as the gaps above:** this is the same state storage
shipped in — installed, reviewable, zero live effect — not a claim that secrets have migrated.
`ESTATE_STORAGE_PROVIDER` is still `"oci"`; no `VaultSecret` Claim exists anywhere in the repo; no
existing secret (vendor or generated) has moved. Flipping the DNA switch, and the copy/migration
work real secrets need once it flips, stay exactly what the Diamond Standard ADR already said they
are: the founder's call, not this session's. What changed is that "full adoption" no longer has a
missing second capability sitting between it and reality — both domains that matter (object
storage and generated secrets, together the majority of what `platform/oci` holds today) now
compile through Crossplane, on the same switch, proven live and tested, waiting on one decision
instead of two unbuilt capabilities.
