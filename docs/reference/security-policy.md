| Policy | Mode | Refuses | Flux layer | File |
|---|---|---|---|---|
| `capacity-affinity` | Audit | Preemptible capacity is for pods that can lose a node | `scheduling` | `platform/scheduling/capacity-affinity.yaml` |
| `protect-namespaces` | Enforce | A platform namespace cannot be deleted | `edge` | `platform/edge/protect-namespaces.yaml` |
| `provider-independence` | Enforce | Provider independence (R43) | `edge` | `platform/edge/provider-independence.yaml` |
| `require-availability` | Enforce | Founder-facing workloads survive losing one node | `scheduling` | `platform/scheduling/require-availability.yaml` |
| `require-priority-class` | Audit 1, Enforce 2 | Require a PriorityClass on platform workloads | `scheduling` | `platform/scheduling/require-priority-class.yaml` |
| `secrets-not-from-env-vars` | Audit | Disallow Secrets from Env Vars in CEL expressions | `edge` | `platform/edge/kyverno-secrets-policy.yaml` |
