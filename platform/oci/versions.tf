# ADR 0004 step 2. OpenTofu, OCI provider, Oracle's own OKE module (LAW 43: the module Oracle
# maintains builds the VCN, the cluster and the node pools; nothing here is hand-rolled).
terraform {
  required_version = ">= 1.6.0"
  required_providers {
    oci = {
      source  = "oracle/oci"
      version = ">= 8.19.0"
    }
  }
}

provider "oci" {
  # Credentials come from ~/.oci/config (profile DEFAULT), written by bin/idp-oci-login from the
  # sops vault (OCI_* names). Nothing here (LAW 46, LAW 21).
  region = var.region
}

# The module needs a second alias for the home region (IAM lives there). Same region here.
provider "oci" {
  alias  = "home"
  region = var.region
}
