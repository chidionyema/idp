# The recovery host (#7387, founder 2026-10-29): one Always Free A1 VM that carries the estate's
# router while there is no Kubernetes cluster, and that the surviving data volumes attach to.
#
# WHY. The OCI free trial ended; the tenancy is Always Free only and OKE's limits are 0, so the
# cluster that ran llm.mumchimp.com, memory, Postgres and Flux cannot come back. What Always Free
# still gives: A1 compute (2 OCPU / 12 GB measured free in AD-1 and AD-2) and 200 GB of block
# storage. The three csi-* volumes the cluster left behind (3 x 50 GB, all in AD-1) plus a 50 GB
# boot volume are exactly that 200 GB, so this host sits in AD-1 with the smallest boot volume.
#
# WHAT RUNS. LiteLLM directly under podman + systemd (no Kubernetes), started from a config bundle
# and a vault entry that .github/workflows/router-recovery.yml publishes, reachable only through a
# Cloudflare Tunnel (outbound; no inbound port). The volumes are attached READ-ONLY: nothing may
# write to the only copy of the estate's data before it has been copied off this provider.

locals {
  # Always Free shapes only (R14). The host must sit in the AD that HOLDS the surviving volumes:
  # an OCI block volume cannot attach across availability domains, so oci_core_volume_attachment.surviving
  # is for_each-empty whenever recovery_ad != volumes_ad -- measured 2026-10-30: zero attachments
  # existed, and the volumes could not be copied off this provider at all.
  # AD-1's live shape inventory (measured 2026-10-30T00:17:05Z) offers BM.Standard.A1.160 and
  # VM.Standard.A1.Flex ONLY: VM.Standard.E2.1.Micro is not offered in AD-1, so the shape that can
  # carry the volumes in their own AD is an A1.Flex. The router measured ~275 MB RSS; 1 OCPU / 6 GB
  # is ample, and A1.Flex resizes in place when capacity allows more.
  # A1.Flex capacity was refused "Out of host capacity" in both ADs on earlier attempts (apply runs
  # 40844922528 .. 40851920814). If the governed apply is refused again, the volumes stay detached
  # and safe and reverting these two lines restores the AD-2 E2.1.Micro host.
  recovery_shape = "VM.Standard.A1.Flex"
  # The volumes' own AD (measured 2026-10-30: all three csi-* volumes report
  # availability-domain lPOl:UK-LONDON-1-AD-1). The host follows them, not the other way round:
  # the router is stateless and can run anywhere, but the DATA can only be read where it lives.
  # AD-2 remains the fallback AD if AD-1 refuses the launch for capacity.
  volumes_ad  = "lPOl:UK-LONDON-1-AD-1"
  recovery_ad = "lPOl:UK-LONDON-1-AD-1"
  # The volumes the dead cluster's CSI driver created (tagged role=persistent_volume). Read as data,
  # never managed: tofu must never be able to destroy them.
  surviving_volumes = {
    v0825 = "ocid1.volume.oc1.uk-london-1.abwgiljr5jpg4uwfjsy3osgmermcllkopx4yjowicntxdooy2tnbgtfoyzaa"
    v0827 = "ocid1.volume.oc1.uk-london-1.abwgiljr4hnrmnglcsfnbajvfyishb2blahrmfgghkpc3q7vrxlu7fepky4a"
    v0904 = "ocid1.volume.oc1.uk-london-1.abwgiljrefnhgvapdken6pc5nmvwouvwipk37fdi3in6b5wazpkuwx42dsca"
  }
}

data "oci_objectstorage_namespace" "recovery" {
  compartment_id = var.compartment_ocid
}

data "oci_core_images" "ol9_arm" {
  compartment_id           = var.compartment_ocid
  operating_system         = "Oracle Linux"
  operating_system_version = "9"
  shape                    = local.recovery_shape
  sort_by                  = "TIMECREATED"
  sort_order               = "DESC"
}

# The router's config bundle (config.yaml + the auth module) and nothing else. Always Free object
# storage; the VM reads it with its instance principal.
resource "oci_objectstorage_bucket" "router_recovery" {
  compartment_id = var.compartment_ocid
  namespace      = data.oci_objectstorage_namespace.recovery.namespace
  name           = "${var.cluster_name}-router-recovery"
  access_type    = "NoPublicAccess"
  versioning     = "Enabled"
}

# Egress only: the tunnel and every vendor call go out; nothing on the internet may come in.
resource "oci_core_network_security_group" "recovery" {
  compartment_id = var.compartment_ocid
  vcn_id         = data.oci_core_subnets.workers.subnets[0].vcn_id
  display_name   = "${var.cluster_name}-recovery"
}

resource "oci_core_network_security_group_security_rule" "recovery_egress" {
  network_security_group_id = oci_core_network_security_group.recovery.id
  direction                 = "EGRESS"
  protocol                  = "all"
  destination               = "0.0.0.0/0"
  destination_type          = "CIDR_BLOCK"
}

resource "oci_core_instance" "recovery" {
  compartment_id      = var.compartment_ocid
  availability_domain = local.recovery_ad
  display_name        = "${var.cluster_name}-recovery"
  shape               = local.recovery_shape

  # 1 OCPU / 6 GB, not the 2 / 12 the AD offers: AD-1 answered "Out of host capacity" for 2 / 12
  # (apply run 40844922528 and retries), and small A1 shapes are placed far more often. The router
  # and the tunnel need under 2 GB; A1.Flex resizes in place when capacity returns.
  dynamic "shape_config" {
    for_each = endswith(local.recovery_shape, ".Flex") ? [1] : []
    content {
      ocpus         = 1
      memory_in_gbs = 6
    }
  }

  create_vnic_details {
    subnet_id        = data.oci_core_subnets.workers.subnets[0].id
    assign_public_ip = false # the tunnel dials out; there is no door to open
    nsg_ids          = [oci_core_network_security_group.recovery.id]
    display_name     = "${var.cluster_name}-recovery"
  }

  source_details {
    source_type             = "image"
    source_id               = data.oci_core_images.ol9_arm.images[0].id
    boot_volume_size_in_gbs = 50 # 3 x 50 GB volumes + this = the 200 GB free allowance
    # Destroy-then-create, never create_before_destroy: the regional allowance
    # (total-free-storage-gb-regional = 200, measured 2026-10-30) is already full at 150 GB of
    # csi-* volumes + this 50 GB boot volume, so two boot volumes alive at once would be refused
    # with LimitExceeded. The csi-* volumes are detached and untouched either way.
  }

  metadata = {
    ssh_authorized_keys = var.ssh_public_key
    user_data = base64encode(templatefile("${path.module}/cloud-init/recovery-host.yaml", {
      region         = var.region
      compartment_id = var.compartment_ocid
      namespace      = data.oci_objectstorage_namespace.recovery.namespace
      bucket         = oci_objectstorage_bucket.router_recovery.name
    }))
  }

  agent_config {
    plugins_config {
      name          = "Compute Instance Run Command"
      desired_state = "ENABLED"
    }
  }

  lifecycle {
    ignore_changes = [source_details[0].source_id, metadata["ssh_authorized_keys"]]
  }
}

resource "oci_core_volume_attachment" "surviving" {
  for_each        = local.recovery_ad == local.volumes_ad ? local.surviving_volumes : {}
  attachment_type = "paravirtualized"
  instance_id     = oci_core_instance.recovery.id
  volume_id       = each.value
  display_name    = "recovery-${each.key}"
  is_read_only    = true # nothing writes to the only copy before it is copied off-provider
}

resource "oci_identity_dynamic_group" "recovery" {
  provider       = oci.home
  compartment_id = var.tenancy_ocid
  name           = "${var.cluster_name}-recovery"
  description    = "the recovery host, and only it (#7387)"
  matching_rule  = "ALL {instance.id = '${oci_core_instance.recovery.id}'}"
}

resource "oci_identity_policy" "recovery" {
  provider       = oci.home
  compartment_id = var.compartment_ocid
  name           = "${var.cluster_name}-recovery"
  description    = "the recovery host reads its own vault entry and its own bucket, nothing else (#7387)"
  statements = [
    "Allow dynamic-group ${oci_identity_dynamic_group.recovery.name} to read secret-family in compartment id ${var.compartment_ocid} where target.secret.name = 'router-recovery'",
    "Allow dynamic-group ${oci_identity_dynamic_group.recovery.name} to read objects in compartment id ${var.compartment_ocid} where target.bucket.name = '${oci_objectstorage_bucket.router_recovery.name}'",
    "Allow dynamic-group ${oci_identity_dynamic_group.recovery.name} to inspect secrets in compartment id ${var.compartment_ocid}",
    # The host has no SSH door (no public IP, no bastion): Run Command is how the recovery lane
    # mounts and identifies the surviving volumes and copies them off-provider (plan step 3).
    "Allow dynamic-group ${oci_identity_dynamic_group.recovery.name} to use instance-agent-command-execution-family in compartment id ${var.compartment_ocid} where request.instance.id = '${oci_core_instance.recovery.id}'",
    "Allow dynamic-group ${oci_identity_dynamic_group.recovery.name} to manage objects in compartment id ${var.compartment_ocid} where target.bucket.name = '${oci_objectstorage_bucket.router_recovery.name}'",
    # The CI principal needs the same door, or the declared repair path cannot reach the host.
    # 2026-10-29: .github/workflows/recovery-data.yml creates a Run Command against this instance
    # and the create returned NotAuthorizedOrNotFound, because estate-github-actions held only
    # `manage secret-family` (platform/oci/github-actions.tf) and no Run Command at all. The door
    # was declared and unusable: a host with no cloudflared connector (Cloudflare 1033) could not
    # be repaired by the workflow that existed to repair it. Scoped to THIS instance only, because
    # the group matches every GitHub Actions principal in the tenancy.
    "Allow dynamic-group ${oci_identity_dynamic_group.github_actions.name} to use instance-agent-command-execution-family in compartment id ${var.compartment_ocid} where request.instance.id = '${oci_core_instance.recovery.id}'",
  ]
}

output "recovery_host_id" {
  value = oci_core_instance.recovery.id
}
