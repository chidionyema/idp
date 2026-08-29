# crew#631 CP2: the verdict signing key is readable by the prover identity only. The prover is the
# GitHub Actions service user estate-ci (token exchange, bin/idp-oci-bootstrap), and the group
# estate-provers holds it and nothing else. The group is created by the bootstrap (estate-operators
# may not manage groups in the tenancy), so this policy waits for it: count is 0 until the group
# exists, and the compartment policy lands on the next oke-check apply after the founder's bootstrap
# run. estate-operators and the worker nodes carry `where target.secret.name != 'verdict-hmac-key'`
# on their secret grants (policy/estate-operators.statements.json, vault.tf), so a laptop session
# and a pod on a node are both refused the key; the agents that write claims cannot sign verdicts.
data "oci_identity_groups" "provers" {
  provider       = oci.home
  compartment_id = var.tenancy_ocid
  name           = "estate-provers"
}

resource "oci_identity_policy" "provers_read_verdict_key" {
  count          = length(data.oci_identity_groups.provers.groups) > 0 ? 1 : 0
  provider       = oci.home
  compartment_id = var.compartment_ocid
  name           = "estate-provers-read-verdict-key"
  description    = "the prover (estate-ci) reads the verdict signing key and nothing else (crew#631 CP2)"
  statements = [
    "Allow group estate-provers to read secret-family in compartment id ${var.compartment_ocid} where target.secret.name = 'verdict-hmac-key'",
  ]
}
