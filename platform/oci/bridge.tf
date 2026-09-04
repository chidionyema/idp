# crew#841: the break-glass bridge, off the founder's laptop.
#
# Founder, 2026-09-04: "while this works fir now t crete dependency on laptop so while we can
# use this w need t consider debugging fro aother nachine, we have oracle login so not sure why
# ll this". He is right. Reading a pod log needs the Kubernetes API, the Oracle Console has no
# pod log view, and the API's public endpoint admits one address -- the house. So something
# other than his Mac has to hold the door open.
#
# This is that something: one Always Free instance (R14: EUR 0), inside the VCN, with no public
# IP at all. It reaches the control plane's PRIVATE endpoint, so `control_plane_allowed_cidrs`
# is not widened and nothing new is exposed to the internet. It joins the tailnet outbound
# through the NAT gateway the workers already use, so no ingress rule is opened either. Identity
# is an instance principal: nothing is stored on the machine and nobody types a credential.
#
# It is not in the cluster. A pod would die with the thing it is meant to debug; a separate
# instance survives a node event, a gateway failure and a bad Flux reconcile. The Mac
# (bin/idp-kubeapi-mac) stays as the second road, on a different failure domain again -- two
# ways in, never one.

data "oci_identity_availability_domains" "ads" {
  compartment_id = var.tenancy_ocid
}

# The workers subnet is private and regional, and its route already reaches the NAT gateway and
# the control plane. Looked up rather than passed in, so this file names no OCID (LAW 46).
data "oci_core_subnets" "workers" {
  compartment_id = var.compartment_ocid
  filter {
    name   = "display_name"
    values = ["^workers-"]
    regex  = true
  }
}

data "oci_core_images" "ol9" {
  compartment_id           = var.compartment_ocid
  operating_system         = "Oracle Linux"
  operating_system_version = "9"
  shape                    = "VM.Standard.E2.1.Micro"
  sort_by                  = "TIMECREATED"
  sort_order               = "DESC"
}

# The OAuth client the Tailscale operator already uses (platform/tailscale/external-secret.yaml).
# The bridge reads the same entry to join the tailnet; no second credential is minted.
data "oci_vault_secrets" "tailscale" {
  compartment_id = var.compartment_ocid
  name           = "tailscale-operator"
}

resource "oci_core_instance" "bridge" {
  compartment_id      = var.compartment_ocid
  availability_domain = data.oci_identity_availability_domains.ads.availability_domains[0].name
  display_name        = "${var.cluster_name}-bridge"
  shape               = "VM.Standard.E2.1.Micro" # Always Free; a shape change here costs money

  create_vnic_details {
    subnet_id        = data.oci_core_subnets.workers.subnets[0].id
    assign_public_ip = false # the whole point: no door on the internet
    display_name     = "${var.cluster_name}-bridge"
  }

  source_details {
    source_type = "image"
    source_id   = data.oci_core_images.ol9.images[0].id
  }

  metadata = {
    ssh_authorized_keys = var.ssh_public_key
    user_data = base64encode(templatefile("${path.module}/cloud-init/bridge.yaml", {
      cluster_id          = module.oke.cluster_id
      region              = var.region
      tailscale_secret_id = data.oci_vault_secrets.tailscale.secrets[0].id
    }))
  }

  # The image is rebuilt by Oracle constantly; a new one is not a reason to replace a working
  # bridge. Recreate deliberately with -replace when the base image should move.
  lifecycle {
    ignore_changes = [source_details[0].source_id, metadata["ssh_authorized_keys"]]
  }
}

resource "oci_identity_dynamic_group" "bridge" {
  provider       = oci.home
  compartment_id = var.tenancy_ocid
  name           = "${var.cluster_name}-bridge"
  description    = "the break-glass bridge instance, and only it (crew#841)"
  matching_rule  = "ALL {instance.id = '${oci_core_instance.bridge.id}'}"
}

resource "oci_identity_policy" "bridge" {
  provider       = oci.home
  compartment_id = var.compartment_ocid
  name           = "${var.cluster_name}-bridge"
  description    = "the bridge may reach the cluster and read the tailnet join credential, nothing else (crew#841)"
  statements = [
    "Allow dynamic-group ${oci_identity_dynamic_group.bridge.name} to use cluster-family in compartment id ${var.compartment_ocid}",
    "Allow dynamic-group ${oci_identity_dynamic_group.bridge.name} to read secret-family in compartment id ${var.compartment_ocid} where target.secret.name = 'tailscale-operator'",
  ]
}

# The subject a ClusterRoleBinding names for an instance principal is the instance's OCID
# (platform/rbac/bridge.yaml). Printed here so the binding can be filled in without a console.
output "bridge_instance_ocid" {
  value = oci_core_instance.bridge.id
}
