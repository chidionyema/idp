# crew#227 CP3: secrets reach the cluster by identity, not by a key in the cluster.
# OCI Vault (software-protected key, no charge: `oci limits value list --service-name kms`
# shows virtual-vault-count 10 on 2026-08-25) holds the secrets; the worker nodes are an
# instance principal (dynamic group) allowed to read them; External Secrets Operator in the
# cluster (platform/secrets) turns them into Kubernetes Secrets. Nothing static lands in git
# or on a node. Workload identity per pod needs an Enhanced cluster (billed per hour), so the
# node identity is the boundary for now; the decision is recorded on crew#227.
# The register's Customer-owned entries, as a Terraform list. Generated, not typed: see the
# regeneration command on vault_writer_customer_entries below. Kept beside the vault rather than
# in a separate file so the policy and its list are read together.
locals {
  customer_owned_entries = [
    "CURSOR_API_KEY",
    "DEEPSEEK_API_KEY",
    "EXA_API_KEY",
    "GEMINI_API_KEY",
    "GROQ_API_KEY",
    "MINIMAX_API_KEY",
    "MOONSHOT_API_KEY",
    "OPENROUTER_API_KEY",
    "TELEGRAM_ALERTS_BOT_TOKEN",
    "TELEGRAM_ALERTS_CHAT_ID",
    "TELEGRAM_HERMES_BOT_TOKEN",
    "commerce-payment-provider",
    "cyrus-linear",
    "cyrus-linear-api-token",
    "cyrus-linear-client-id",
    "cyrus-linear-client-secret",
    "flux-telegram",
    "hermes-agent-env",
    "litellm-upstream",
    "notify-apprise-founder-telegram",
    "otto-staging-telegram",
    "prospector-engine-env",
  ]
}

resource "oci_kms_vault" "estate" {
  compartment_id = var.compartment_ocid
  display_name   = "${var.cluster_name}-secrets"
  vault_type     = "DEFAULT"
}

resource "oci_kms_key" "estate" {
  compartment_id      = var.compartment_ocid
  display_name        = "${var.cluster_name}-secrets"
  management_endpoint = oci_kms_vault.estate.management_endpoint
  protection_mode     = "SOFTWARE"
  key_shape {
    algorithm = "AES"
    length    = 32
  }
}

resource "oci_identity_dynamic_group" "workers" {
  provider       = oci.home
  compartment_id = var.tenancy_ocid
  name           = "${var.cluster_name}-workers"
  description    = "every instance in compartment estate: the OKE worker nodes (crew#227 CP3)"
  matching_rule  = "ALL {instance.compartment.id = '${var.compartment_ocid}'}"
}

resource "oci_identity_policy" "workers_read_secrets" {
  provider       = oci.home
  compartment_id = var.compartment_ocid
  name           = "${var.cluster_name}-workers-read-secrets"
  description    = "worker nodes may read secret bundles in this compartment, never the verdict signing key (crew#631 CP2)"
  statements = [
    "Allow dynamic-group ${oci_identity_dynamic_group.workers.name} to read secret-family in compartment id ${var.compartment_ocid} where target.secret.name != 'verdict-hmac-key'",
  ]
}

# The key ingest door's write grant (docs/specs/key-ingest-door-part4.md, part C).
#
# The founder's requirement is that anyone can set this up themselves from the portal, and the
# door needs to write a pasted key into the vault. This is the narrowest statement that lets it:
# `use` rather than `manage`, and a NAME LIST rather than the compartment.
#
# Why it is not simply added to the workers policy above, and this is the whole reason part 4 is
# a separate piece of work: per-pod workload identity needs an Enhanced cluster (billed per
# hour), so the only identity a pod has today is its NODE's (see the header of this file). A
# compartment-wide write grant would therefore hand whatever runs on that node -- the portal
# included -- the ability to write every Operator secret. Decision 0021 says superadmin is a
# grant on the operator road and never a widening of the customer road; a `manage secret-family`
# here would be exactly that widening.
#
# The list is generated from the register (docs/reference/policy/root-trust.md) so it cannot
# drift from the rows a customer actually owns. Regenerate it with:
#
#   python3 - <<'EOF'
#   import sys; sys.path.insert(0, "platform/vault-writer")
#   import scoping; print(scoping.customer_owned_entries("docs/reference/policy/root-trust.md"))
#   EOF
#
# A name in this list that no secret carries matches nothing and costs nothing; a real entry
# MISSING from it means the door refuses a write it should allow, which is the failure to watch.
resource "oci_identity_policy" "vault_writer_customer_entries" {
  provider       = oci.home
  compartment_id = var.compartment_ocid
  name           = "${var.cluster_name}-vault-writer-customer-entries"
  description    = "the key ingest door may write exactly the entries whose register Owner is Customer (decision 0021)"
  statements = [
    format(
      "Allow dynamic-group %s to use secret-family in compartment id %s where target.secret.name in (%s)",
      oci_identity_dynamic_group.workers.name,
      var.compartment_ocid,
      join(", ", [for n in local.customer_owned_entries : "'${n}'"]),
    ),
  ]
}

output "vault_id" {
  value = oci_kms_vault.estate.id
}

output "vault_key_id" {
  value = oci_kms_key.estate.id
}
