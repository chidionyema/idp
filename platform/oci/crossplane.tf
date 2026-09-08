# The only thing that makes Crossplane able to touch OCI, and it is not a credential.
#
# Under OKE Workload Identity the provider pod presents its own service account and OCI IAM decides
# from this statement whether that identity may act. The four conditions are the whole security
# boundary: it must be a workload principal, in this cluster, in crossplane-system, running as the
# service account platform/crossplane/providers/runtime.yaml pins by name. A token minted this way
# is worth nothing anywhere else -- there is no key to leak, rotate or revoke, which is why
# decision 0026 chose this over an API key even though an API key is fewer lines.
#
# The verb is `manage object-family` and nothing wider. Crossplane's step 3 emits buckets; a
# provider that could also read secret-family or manage instances would be a standing grant nobody
# asked for. The next capability widens this statement in the pull request that needs it.
resource "oci_identity_policy" "crossplane_workload" {
  provider       = oci.home
  compartment_id = var.compartment_ocid
  name           = "${var.cluster_name}-crossplane-objectstorage"
  description    = "Crossplane's OCI provider, by workload identity, may manage object storage in this compartment and nothing else (decision 0026)"
  statements = [
    "Allow any-user to manage object-family in compartment id ${var.compartment_ocid} where all { request.principal.type = 'workload', request.principal.namespace = 'crossplane-system', request.principal.service_account = 'crossplane-provider-oci', request.principal.cluster_id = '${module.oke.cluster_id}' }",
  ]
}
