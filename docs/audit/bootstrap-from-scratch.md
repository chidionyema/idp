# Rebuilding this estate from nothing

Founder, 2026-08-31: "i need estate audit and explain how we cann bootstrap estate fron scratch we
need to start all over again," then "THIS PROCEES NEEDS AUTOMATION and rerunnable."

The audit is `bin/idp-estate-audit`; its answer is
[what the estate actually runs](estate-inventory.md) and it is regenerated, never typed. This page
is the order the pieces have to be built in, and it names, for each layer, whether the code to
build it already exists.

## Where a rebuild stops today

Run the audit and the number that matters is the third one: **48 of 142 running resources exist in
no repository at all**. A fresh tenancy could not be brought to this state from git. The 48 fall
into four groups, and only one of them is genuinely hard.

| What | Count | Why a rebuild stops |
|---|---:|---|
| Vault secrets with no source | 27 | The values exist only inside the running vault. Losing it loses them. |
| Identity: users, groups, policies | 9 | Made in the console. Nothing describes who may do what. |
| Buckets, the compartment, tags | 7 | Includes `estate-tofu-state` — the bucket the state itself lives in. |
| The second vault, its keys, a route table | 5 | Left over; each is either adopted or deleted. |

Everything else is already reproducible: the network, the cluster and the worker pools come from
the upstream `module "oke"` in `platform/oci/main.tf`, and 41 more resources — the volumes, the
node boot disks, the private DNS, the load balancer — are made by something that is codified.
Those are not work.

## The one thing that cannot be recreated at all

Sixteen persistent volumes hold the estate's data, and all sixteen are provisioned with reclaim
policy `Delete`: deleting a claim destroys the volume with it. No Terraform can bring that data
back. `bin/idp-estate-backup` covers them, is safe to run again, and exits non-zero while any volume is
uncovered — so it can be a scheduled row rather than a morning of typing.

Nothing else in this document may start until that command exits zero.

## The order to build in

**Layer 0 — the ground the state stands on.** The compartment, the object-storage bucket
`estate-tofu-state`, and the S3-compatible credential that reaches it. This is the chicken and the
egg: it is the store every other layer keeps its state in, so it has to be created with local
state and then migrated. *Code: does not exist.* It is the one piece that must be written before
any of the rest can be applied to an empty tenancy.

**Layer 1 — identity.** Four users, three groups, two policies, the vault and its keys. Under
the one-root rule, one root credential per provider is set by hand and the pipeline mints the rest, so this
layer's job is to describe the shape, not to hold any value. *Code: partly exists* —
`platform/oci/identity/` and `platform/oci/iam.tf` already hold six policies, the dynamic group
and the domain apps; the users, the groups and the two remaining policies are not described.

**Layer 2 — network and cluster.** *Code exists and is applied.* `module "oke"` in
`platform/oci/main.tf` owns the VCN, five subnets, five network security groups, three security
lists, the internet, NAT and service gateways, the cluster and both worker pools (`a1` and
`a1-spot`, `VM.Standard.A1.Flex`, 6 ocpu and 24 GB each, Kubernetes v1.35.2). This layer needs
nothing written. It is the proof that the approach works.

**Layer 3 — secrets.** Fifty-one vault secrets, twenty-four of them already created by Terraform.
The other twenty-seven are the real blocker, and they are not one problem but three:

- values a pipeline can mint fresh on a new estate (database passwords, cookie secrets, internal
  tokens) — these need a Terraform block and no human,
- root credentials that come from outside and must be read from the sops vault beside the
  checkout (`cloudflare-api-token`, `github-app`, and the provider keys),
- rows nobody can currently place, which is itself the finding.

Sorting those twenty-seven into those three buckets is the next piece of work, and it is a script
that reads names and Terraform, never values.

**Layer 4 — storage and workloads.** Already reproducible. The storage classes and every claim
come from the manifests Flux applies; the volumes appear when the claims do.

## Standing up V2 without touching production

The founder's plan, and the order holds:

1. `bin/idp-estate-backup` exits zero, so the data is out of band.
2. Layer 0 written and applied into a **second compartment**, not the live one.
3. Layers 1 to 3 applied there. The network and cluster layer is a re-apply of code that already
   works, which is why V2 is a day's work and not a rewrite.
4. Snapshots restored into the new volumes, and the workloads pointed at them.
5. Traffic moves only after the gate below is green.

The live cluster is not touched at any point in that list.

## The gate that makes it stick

A new gate is run against the existing estate before it merges — against everything already there
and everything that generates changes — and the output is the list of things that will now fail
(founder, 2026-08-31). For this work that gate is `bin/idp-estate-audit` itself: it grades every
running resource against the state on every run, so "48 exist in no repository" is a number in CI
that has to go down, not a claim anybody makes.

---

Regenerate the facts on this page with `bin/idp-estate-audit`. Both commands are read-only except
`bin/idp-estate-backup`, which only ever creates backups.
