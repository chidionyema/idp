# intercloud manifests (Piece 1)
CRDs, RBAC, admission gate, controller deployment, Crossplane providers, Flux source.
The controller runs two modes: `fs` (complete, runs anywhere) and `k8s` (K8sStore adapter:
reads Lane/Approval/WorkloadSpec CRs, reads/writes Crossplane Claims, watches Ready status).
Provider package tags MUST be verified at deploy time (registry naming changes; see SECURITY_REVIEW M4).
