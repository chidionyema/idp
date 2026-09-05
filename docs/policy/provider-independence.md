# Provider independence

**Control ID:** R43 · **Owner:** platform (crew#66) · **Effective:** 2026-08-28 · **Class:** preventive, automated

Founder decree, 2026-08-28, verbatim: *"ensure we neevr couple ourslevs to oracle … you need to
thik enterpise policy … this is a founders decree … so take it seriously."* Recorded on crew#66
(comment 5450184299) and as standing ruling R43 in the guards' rulings, which binds every session.

## Rule

The platform never depends on one compute or cloud provider. A provider is named in exactly three
places, called the **provisioner boundary**:

| Place | What it may name | Why it is inside the boundary |
|---|---|---|
| `platform/oci/` | the compute provisioner (OpenTofu for the current tenancy) | it *is* the provider adapter; a second provider gets a sibling directory |
| `platform/secret-store/store.yaml` | the one cloud secret door (`ClusterSecretStore estate-vault`, labelled `idp.platform/provider-door=true`) | every `ExternalSecret` references the store by name; moving vaults changes this file only |
| `clusters/<name>/` | the per-cluster row: load-balancer shape, node identity, cluster-specific patches | a cluster is a provider's; the platform tree it applies is not |

Everything outside the boundary — every object under `platform/` that Flux applies — is provider-free:
no provider annotation, no provider `StorageClass`, no provider CSI driver, no provider
`loadBalancerClass`, no second cloud secret store. A cluster the estate does not control (its CNI,
its node ceiling) is a place the platform runs, never the platform's home.

## Enforcement — three points, all proven tools, no bespoke script

| # | Point | Mechanism | What refuses |
|---|---|---|---|
| 1 | **Admission** | Kyverno `ClusterPolicy provider-independence`, `failureAction: Enforce`, `platform/edge/provider-independence.yaml` | the API server refuses a Service/Ingress/PVC with a provider annotation, a PVC or StatefulSet template with a provider StorageClass, a Pod with a provider CSI driver, a Service with a provider `loadBalancerClass`, and any `SecretStore`/`ClusterSecretStore` whose provider is a cloud vault and is not the labelled door |
| 2 | **Pull request** | the same policy, judged by `bin/idp-kyverno-render` (Kyverno CLI) on the rendered HelmReleases and plain manifests of every changed `platform/` directory | the PR gate fails before the cluster ever sees the object |
| 3 | **Continuous proof** | `.github/workflows/portability-drill.yml` job `k3s`: the whole Flux tree hydrated on k3s on a non-Oracle runner (idp#519), on every PR touching `platform/**` or `clusters/**`, and a **required status check on `main`** | a change that only works on the incumbent provider cannot merge |

The one declared hole is written beside the policy: `platform/edge/provider-edge-exception.yaml`
excuses rule `no-provider-annotations` for `Service edge/traefik` only, because
`clusters/oke/edge.yaml` patches that Service with the OKE load-balancer shape (R36). A new hole is
a new `PolicyException`, in namespace `kyverno`, reviewed like any change to the boundary.

## Evidence — commands, not sentences

```sh
# 1. The policy refuses every known coupling and passes a clean tree (fixtures + LAW 38 sweep of platform/)
pytest -q tests/test_incident_crew66_provider_independence_policy.py
# 2. The live cluster enforces it
kubectl get clusterpolicy provider-independence -o jsonpath='{.spec.rules[*].validate.failureAction}'
# 3. The PR judge loads it
bin/idp-kyverno-render platform/edge | grep -E '^policies'
# 4. main requires the second-provider proof
gh api repos/chidionyema/idp/branches/main/protection --jq '.required_status_checks.contexts'
```

## What this control is not

A count of scripts that call a provider's CLI, a ledger of waived callers, or a grep ratchet
(the approach retracted on crew#66 the same day). Those measure plumbing; they do not stop the
cluster from taking a provider-shaped object, and they cannot be a required check anyone can
read. Plumbing inside the boundary (`bin/idp-oci-*`, `bin/idp-iam-*`) stays behind
`bin/cloud-agnostic-gate` as an inventory line, not as the control.

## Related

`docs/policy/governance-kernel.md` (how a control is written), `docs/policy/definition-of-done.md`,
`platform/edge/kyverno.yaml` (the admission controller), `drills/portability-floor.txt` (the floor
the k3s drill grades).
