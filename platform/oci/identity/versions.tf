# The front door's OIDC client, as an application in the estate's own identity domain (the one
# platform/oci already uses for the GitHub Actions token exchange). Every input is read from
# where it already lives; no console, no paste (crew#281, crew#269, LAW 46).
terraform {
  required_version = ">= 1.6"
  required_providers {
    oci    = { source = "oracle/oci", version = ">= 8.19.0" }
    random = { source = "hashicorp/random", version = ">= 3.6.0" }
  }
}
# Credentials come from ~/.oci/config, never from here, as platform/oci: APIKey on a laptop,
# SecurityToken in GitHub Actions (the profile holds the exchanged one-hour session token). Without
# auth = var.oci_auth the provider assumed an API key and the CI apply could never run (crew#408).
provider "oci" {
  region              = var.region
  auth                = var.oci_auth
  config_file_profile = var.oci_profile
}
