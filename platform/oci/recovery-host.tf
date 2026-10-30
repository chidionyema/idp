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
# Cloudflare Tunnel (outbound; no inbound port). The volumes are attached READ-ONLY when the host
# can reach them: nothing may write to the only copy of the estate's data before it has been copied
# off this provider.

locals {
  # Always Free shapes only (R14). TWO placements are possible on this tenancy and which one is
  # live depends on a fact OCI will not publish in advance: whether the region has A1 host
  # capacity today. Both placements below are measured, not assumed.
  #
  #   AD-1 HOLDS THE DATA. All three surviving csi-* volumes report availability-domain
  #   lPOl:UK-LONDON-1-AD-1 (measured 2026-10-30). A block volume only attaches inside its own AD,
  #   so only an AD-1 host can carry them. AD-1's shape inventory (measured 2026-10-30T00:17:05Z)
  #   offers BM.Standard.A1.160 (paid -- forbidden by R14) and VM.Standard.A1.Flex ONLY:
  #   VM.Standard.E2.1.Micro is not offered in AD-1 and AD-1's E2.1.Micro service limit is 0.
  #
  #   AD-2 CARRIES THE ROUTER. AD-2 offers VM.Standard.E2.1.Micro (service limit 2, measured) and
  #   the router is stateless -- it needs no volume. An AD-2 host restores the ROUTER and the
  #   TUNNEL and leaves the data where it is: detached, untouched and safe.
  #
  # WHY AD-2 IS THE LIVE PLACEMENT (measured 2026-10-30). Four governed applies asked AD-1 for an
  # A1.Flex host and OCI refused every one with the same line:
  #     Error: 500-InternalError, Out of host capacity.        (operation LaunchInstance)
  #   runs 40983597207, 40985289787, 40988200652 (01:52:13Z), 40989327811 (02:03:50Z).
  #   Quota headroom is NOT capacity: AD-1 reports standard-a1-core-count available=2 while every
  #   launch is refused. The AD-1 data route is blocked by physics, not by configuration.
  #
  # WHY ONLY ONE HOST EVER (measured). The Always Free block-storage allowance for the region is
  # 200 GB (total-storage-gb=200, total-free-storage-gb-regional=200). The three csi-* volumes are
  # 150 GB of it, so exactly ONE 50 GB boot volume fits: 150 + 50 = 200. A second host is refused
  # with LimitExceeded. There is therefore one slot, and it is either the AD-1 host that carries
  # the data or the AD-2 host that carries the router -- never both at once.
  #
  # THE FLIP. When AD-1 A1.Flex capacity returns, these three lines are reverted to
  # recovery_shape = "VM.Standard.A1.Flex" and recovery_ad = "lPOl:UK-LONDON-1-AD-1" -- the
  # configuration that landed in #7488. The guard below then attaches the three volumes READ-ONLY
  # and the data route opens. The AD-2 host is destroyed FIRST (its 50 GB boot volume is the slot),
  # never create_before_destroy.
  recovery_shape = "VM.Standard.E2.1.Micro"
  # The volumes' own AD (measured 2026-10-30: all three csi-* volumes report
  # availability-domain lPOl:UK-LONDON-1-AD-1). The DATA stays where it lives; the host follows it
  # only when the AD can actually be placed.
  volumes_ad  = "lPOl:UK-LONDON-1-AD-1"
  recovery_ad = "lPOl:UK-LONDON-1-AD-2"
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
  # (apply run 40844922528 and retries) AND for 1 / 6 (runs 40983597207 .. 40989327811), and small
  # A1 shapes are placed far more often. The router and the tunnel need under 2 GB; A1.Flex resizes
  # in place when capacity returns. On VM.Standard.E2.1.Micro the block is empty (the shape is
  # fixed at 1 OCPU / 8 GB) and the host's 2 GB swap file -- cloud-init, "a 1 GB shape needs room
  # to breathe" -- lives on the 50 GB boot volume.
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
