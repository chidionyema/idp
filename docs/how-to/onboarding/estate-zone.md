# Onboarding: the estate zone

Every URL in the estate has one shape, `https://<service>.<zone>`, and the zone is written in exactly one place: `clusters/<cluster>/estate-config.yaml`, key `ESTATE_ZONE`. Today it is `mumchimp.com`, the zone external-dns already manages. The catalogue lives at `catalogue.<zone>`, and that portal is the only place a person needs to look up any other address.

## To find a URL

Open the catalogue. Every entity with a route carries its address under `links`. You do not need to ask anyone.

## To migrate to a new zone

1. Change `ESTATE_ZONE` in `clusters/<cluster>/estate-config.yaml` and merge.
2. Flux reconciles: external-dns publishes records under the new zone and every route and listener written as `${ESTATE_ZONE}` follows.

Nothing else is edited. If a file somewhere still names the old zone by hand, `bin/estate-zone-gate` fails the pull request that introduced it and prints the file and line, so the migration cannot be half done.

## What the gate does not see

It scans `platform/` in this repository. `platform/oci` (the provisioner's record of what it measured), `clusters/*` (where the value lives) and `platform/ai` (the AI Act register, read as data) are exempt, and product repositories are outside it: a product names its own brand domain in its own config. Rows for other repositories are on crew#269.
