# The estate inventory

Tracked on [the inventory ticket](https://github.com/chidionyema/crew/issues/740).

**What you can do now:** open the latest `estate-inventory` run (Actions → estate-inventory) and
read one table: every thing the cloud, the cluster, GitHub, Cloudflare, Tailscale and the Mac
actually run, each graded MANAGED, DRIFTED, ORPHAN or GHOST against what git declares.

## How it works
- `bin/idp-inventory` reads each plane from its own control plane. The cloud plane rides on
  `bin/idp-estate-audit` (one structured search for the whole tenancy, then the OpenTofu state);
  the cluster plane is a full `kubectl get` of every listable kind, classified by Flux and Helm
  labels, owner references and the applied inventory of each Flux folder of manifests; the three SaaS planes are
  Steampipe queries under `platform/inventory/queries/`.
- MANAGED: declared and live. DRIFTED: declared, live differs (`tofu plan -refresh-only`, or a Flux
  object not Ready). ORPHAN: live, declared nowhere. GHOST: declared, not live.
- A plane that cannot be read prints `BLIND inventory <plane>` and the table says UNKNOWN for it; a plane read in part prints `PARTIAL` with its counts, never `ok`, and `--strict` refuses both.
- The run publishes the table to `oci://ghcr.io/chidionyema/idp/estate-inventory:latest` and
  attaches it to the run. The schedule is a row on `drills/catalogue.yaml`.

## Run it yourself
- On the runner: Actions → estate-inventory → Run workflow.
- On the Mac, the Mac half only: `bin/idp-inventory --plane mac --out ~/.estate/inventory`.

## Demo
A pull request that touches the tool runs the workflow read-only; the step summary holds the
table. `pytest tests/test_incident_crew740_inventory_from_live_apis.py` grades a cluster dump on
disk through all four verdicts.

## Not done yet
- Audit mode: no red row fails the run. E1 (the next pull request) turns on `--strict` as a required check.
- The read-only cloud principal is a Terraform change in the E2 pull request; this first run uses the
  oke-check identity.
- The Mac half runs on the Mac; until the estate clock lands its snapshot in the artefact the Mac
  plane reads UNKNOWN on the runner.
