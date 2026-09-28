# 0004. Oracle OKE on Always Free is the Kubernetes target, and Flux delivers to it

- Status: DECIDED 2026-08-24. Founder: "happy to go to Oracle asap but we need a vote of
  confidence and next steps". Records the choice; nothing is provisioned (ruling R23).
- Date: 2026-08-24
- Deciders: founder
- Closes: crew#78 direction ("Decommission Fly, move to Kubernetes"); rulings R1 (never Fly),
  R15 (laptop is substrate until k8s), R23 (Oracle Always Free is the target, local green first)
- Affects: every workload under `platform/`, `bin/idp-verify`, the secrets path

## The problem

The Mac is the only substrate and it is at its thermal limit (CPU_Speed_Limit 48, swap 6.5 of
8 GB on 2026-08-24, apiserver TLS handshake timeouts). Fly is closed by R1. A paid cloud is closed
by R14. The one remaining option with a managed control plane at zero cost is Oracle Always Free.

## Decision

1. **Cluster: OKE Basic.** Basic clusters carry no control-plane charge. Workers are the Always
   Free Ampere A1 allowance, 2 OCPU and 12 GB (halved from 4/24 on 2026-06-15 with no announcement; a terminated resource may not be recreatable above the new limit, so grandfathering does not survive a teardown -- infoq.com/news/2026/07/oracle-cloud-free-tier-limits/). That is fewer CPUs than the dev VM (colima cpu: 4); size nothing against 4/24. A VM running k3s
   was rejected: it is the cluster we already hand-roll on the Mac, and the headline rule is to
   buy the managed platform, not stitch one.
2. **GitOps: Flux.** `crew/docs/STANDARDS.md` row 16 names Flux for solo-operator clusters and
   Argo CD as the reviewed deviation ("a UI service to run"). No deviation is taken.
3. **Infrastructure as code: OpenTofu with the `oci` provider** under `platform/oci/`. Plan
   output is the receipt for every change.
4. **Secrets:** the existing sops+age vault, decrypted in-cluster. No second secret store.
5. **The Mac stays** as the development substrate (R15). Cutover needs two green `idp-verify`
   runs against OKE.

## Vote of confidence, and the named risk

Everything on the local cluster is Kustomize (`platform/backstage`) and Helm (`platform/spire`),
so it ports to any conformant cluster without rewriting. The risk is capacity: Oracle returns
"Out of host capacity" for A1 shapes in busy regions. Step 1 below exists so we learn this before
writing any module.

## Steps

1. Founder creates one API key (Profile → My profile → API keys). Crew stores it in the vault,
   installs the `oci` CLI, and runs the A1 capacity check for `uk-london-1`. Receipt: the CLI
   output.
2. `platform/oci/` OpenTofu: VCN, OKE Basic cluster, one A1 node pool. Receipt: `tofu plan`.
3. `platform/*/overlays/oke/` and a Flux bootstrap from this repository's `main`.
4. Cutover after two green `idp-verify` runs on OKE. Tracked in crew.

## Consequences

- crew#78 has a concrete path again; it was stalled on "no paid infra".
- The registry-egress asymmetry frozen by R22 disappears on OKE, which pulls from
  ghcr.io directly.
- Tenancy facts: [reference/oci-tenancy.md](../reference/oci-tenancy.md).
