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
provider "oci" {} # ~/.oci/config profile from the environment, as platform/oci
