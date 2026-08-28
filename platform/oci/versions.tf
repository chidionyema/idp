# ADR 0004 step 2. OpenTofu, OCI provider, Oracle's own OKE module (LAW 43: the module Oracle
# maintains builds the VCN, the cluster and the node pools; nothing here is hand-rolled).
terraform {
  required_version = ">= 1.6.0"
  required_providers {
    oci = {
      source  = "oracle/oci"
      version = ">= 8.19.0"
    }
    random = {
      source  = "hashicorp/random"
      version = ">= 3.6.0"
    }
  }
}

provider "oci" {
  # Credentials come from ~/.oci/config, never from here (LAW 46, LAW 21). On a laptop
  # bin/idp-oci-login writes an API key profile from the vault (auth APIKey). In GitHub Actions
  # the profile holds a one-hour session token minted from the workflow's OIDC token
  # (auth SecurityToken, crew#227 CP2), so no key exists to leak.
  region              = var.region
  auth                = var.oci_auth
  config_file_profile = var.oci_profile
}

# The module needs a second alias for the home region (IAM lives there). Same region here.
provider "oci" {
  alias               = "home"
  region              = var.region
  auth                = var.oci_auth
  config_file_profile = var.oci_profile
}
