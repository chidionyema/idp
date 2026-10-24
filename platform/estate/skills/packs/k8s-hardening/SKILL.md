---
name: k8s-hardening
description: "Upstream Kubernetes security guidance: the cluster security checklist and pod security standards. Use when a change touches a manifest, a workload's privileges, RBAC, secrets in a cluster, or a node's configuration."
license: CC-BY-4.0
metadata:
  estate-category: infrastructure
  estate-upstream: kubernetes/website
---

# Kubernetes hardening checklist -- the cluster's own security baseline

The upstream Kubernetes security checklist and pod security standards: the baseline the estate's cluster is held to, so an agent reviews a manifest against the standard rather than against memory.

## When to use this

When a manifest, a workload's privileges, an RBAC rule or a node's configuration
changes. The estate runs Flux on a single node; the standard is what makes that node
safe to expose to an agent.

## How to use it

1. `upstream/content/en/docs/concepts/security/security-checklist.md` - the baseline.
2. `.../content/en/docs/concepts/workloads/pod-security-standards.md` - what a pod may do.

The estate's own placement ladder (docs/decisions/0034) decides where a workload runs;
this pack decides how safely it runs once it is there.

## Estate rules that bind this pack

- **Proof, not assertion.** A claim about this skill's effect is a command and its output.
- **One of each layer.** If the estate already owns the capability, use it; a pack never
  becomes a second copy of a layer.
- **Voice first.** A surface the founder cannot speak to and watch live is not finished.
- **The claim is the contract.** Work lands only against a live claim (AGENTS.md 5).

<!-- provenance:begin -->
## Upstream material

Vendored verbatim from `kubernetes/website` at commit `bf999f0184431d6fd0908b8f8340ddf42fc4e6a6`
(CC-BY-4.0, 5410 stars at 2026-10-24T08:04:40+00:00). See `NOTICE.md`.

- `upstream/LICENSE`
- `upstream/content/en/docs/concepts/security/security-checklist.md`

<!-- provenance:end -->
