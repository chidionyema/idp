# The bad half: this bucket is still OpenTofu's, and the Claim beside it says it is Crossplane's.
resource "oci_objectstorage_bucket" "receipts" {
  compartment_id = var.compartment_ocid
  name           = "estate-receipts"
  namespace      = data.oci_objectstorage_namespace.ns.namespace
  access_type    = "NoPublicAccess"
}
