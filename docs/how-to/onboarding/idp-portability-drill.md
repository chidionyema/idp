# Onboarding: idp-portability-drill

## Run it

Nothing to install. `gh workflow run portability-drill.yml` dispatches a run; the schedule fires
every Monday at 05:23Z and the `drills` row of `bin/idp-verify` goes red when the last green run
is older than `max_age_hours` in `drills/catalogue.yaml`. A pull request that touches the
workflow, the grader, the floor or the k3d config runs it automatically, so the change ships with
its own green run.

## Raise the floor

`drills/portability-floor.txt` is one integer: the number of Flux Kustomizations that must come
Ready. It only goes up. When a run reports more layers Ready than the floor, open a PR that
raises the floor and paste that run's URL as the evidence. Never lower it to make a run green;
fix the layer instead, or record on crew#488 why it can never hydrate without OCI.

## Read a failure

Each `not-ready` line quotes the Flux condition message. A layer red because its ExternalSecret
waits on the OCI vault is expected on this cluster and is not a regression. A layer red because
a manifest references a node label, a storage class or an address only OKE has is the finding
the drill exists for; fix it in the manifest so the same tree runs anywhere.

## Grade it locally

`bin/idp-portability-drill <kustomizations.json>` takes the JSON `kubectl get kustomizations -A -o json`
prints from any cluster, including the laptop k3d cluster from crew#191, and exits non-zero on
FAIL. `pytest tests/test_incident_crew488_portability_floor.py` proves the grader both ways.
