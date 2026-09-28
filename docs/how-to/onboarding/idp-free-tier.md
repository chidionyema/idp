# Onboarding: idp-free-tier

## Run it

The row runs in the `free-tier` job of `oke-check.yml` every day at 06:17Z with the runner's
exchanged OIDC session; nobody installs anything. `gh workflow run oke-check.yml -f mode=check`
dispatches it now. The `drills` row of `bin/idp-verify` goes red when the last green run is
older than 26 hours (`drills/catalogue.yaml`).

## Read it

Three numbers from the OCI limits API: `standard-a1-core-count`, `standard-a1-memory-count`
(the best availability domain, since the node pool lives in one) and block storage
`total-storage-gb`. Two pairs from `platform/oci/variables.tf`: what the module assumes free and
what it provisions. `ok` carries the paid remainder in parentheses; `FAIL` names which limit fell
below which assumption; `BLIND` means no session or a failed call, and nothing was graded.

## When it goes red

Do not edit `free_ocpus` or `free_memory_gb` to match the new limit; that hides the cut. Open the
crew#488 ticket, record the new limit with the run URL, and start the exit rehearsal (CP2). If
the provisioned size is what no longer fits, `worker_ocpus` and `worker_memory_gb` are the change,
and `platform/oci/main.tf` prints the cost of what remains paid.

## Grade it locally

`OCI_TENANCY_OCID=<tenancy> bin/idp-free-tier --json` with a live `oci session`, or
`pytest tests/test_incident_crew488_free_tier_allowance.py` for the grader both ways.
