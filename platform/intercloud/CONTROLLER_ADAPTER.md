# controller — K8s adapter spec (the production binding of Store)
The trait is the contract; FsStore is the complete local implementation.
K8sStore implements the same methods as:
  load()   -> LIST Lanes/WorkloadSpecs (all namespaces), LIST Claims (estate.estate.internal),
              GET Approvals (rejected unless status.verified=true set by spooler signer).
  apply()  -> CREATE/PATCH/DELETE Claims; UPSERT PropagationPolicies; append receipts to
              an estate-receipt sidecar (chain head also mirrored to a ConfigMap for
              external anchoring; see SECURITY_REVIEW C2).
Readiness observation: watch Claims' status.conditions[Ready==True] before minting.
RBAC is enforced by manifests/rbac.yaml: controller SA reads Approvals, never writes them.
