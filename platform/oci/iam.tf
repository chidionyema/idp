# crew#310 / crew#301: every compartment-scoped grant for estate-operators is applied from CI,
# never from a founder laptop session.
#
# Root cause of the 4-hour blocker on 2026-08-26: the estate-operators policy is attached to the
# TENANCY (bin/idp-oci-bootstrap), and estate-tofu cannot edit a tenancy policy, so idp#196's
# `manage buckets` line sat in the file until the tenancy owner signed in on a laptop. The
# tenancy owner did not sign in, because the only message he got was "BLOCKED, nobody validated it".
#
# estate-operators already holds `manage policies in compartment estate` (live since the vault
# apply on 2026-08-25), so a policy attached to the compartment can be created and widened by
# estate-tofu itself. This resource mirrors every compartment-scoped statement of the same file the
# bootstrap writes; the tenancy-scoped lines (`in tenancy`) stay founder-only and rare. Adding a
# compartment-scoped statement is now: edit the json, open the PR, oke-check apply from Actions.
locals {
  operator_statements = jsondecode(file("${path.module}/policy/estate-operators.statements.json"))
  operator_compartment_statements = [
    for s in local.operator_statements :
    replace(s, " in compartment estate", " in compartment id ${var.compartment_ocid}")
    if endswith(s, " in compartment estate")
  ]
}

resource "oci_identity_policy" "operators_compartment" {
  provider       = oci.home
  compartment_id = var.compartment_ocid
  name           = "estate-operators-compartment"
  description    = "compartment-scoped grants for estate-operators, applied from CI (crew#310); tenancy-scoped lines stay in the bootstrap policy"
  statements     = local.operator_compartment_statements
}
