# The good half: OpenTofu keeps only the bootstrap set (decision 0026), and the bucket it used to
# own was deleted in the same pull request that added the Claim.
resource "oci_kms_vault" "estate" {
  compartment_id   = var.compartment_ocid
  display_name     = "estate"
  vault_type       = "DEFAULT"
}
