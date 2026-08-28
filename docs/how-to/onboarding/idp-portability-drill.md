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

Each red layer prints one line with Flux's own message, and the first word says what kind of red
it is (crew#488 CP5):

- `cascaded` — the message is `dependency X is not ready`: a row above it is red, this one is
  not. Counted, never judged.
- `oci-red` — red for a reason of its own that `drills/portability-oci-reds.txt` names for that
  layer (the vault ConfigMap, the private catalog artifact). Expected on a cluster with no OCI.
- `ROOT-RED` — red for a reason of its own that nothing names. The run FAILs whatever the floor
  says: a CRD applied before its operator, a chart that will not template, a node label only one
  cloud has. Fix it in the tree so the same tree runs anywhere; add a row to the reds file only
  when the reason really is the missing cloud, and say why on crew#488.

Before CP5 the run `ok portability ready 2/38 (floor 2)` hid four root breaks behind thirty-two
cascades (run 33208911991).

## Why the drill clusters have two nodes

The front door runs two traefik replicas spread across hostnames with `DoNotSchedule`
(crew#555: a routed surface survives one node), and `require-availability` refuses a
weaker spread. On one node the second pod never seats and `edge` reads ROOT-RED forever
(runs 33212542369, 33212575403). So the k3d job passes `--agents 1` over
`platform/k3d/estate.yaml` (which stays one node for the founder's 16 GB Mac) and the k3s
job joins a second node from the `rancher/k3s` image over Docker. The PriorityClasses the
front door names live in their own layer, `priority-classes`, that `edge` waits on; they
used to sit in `scheduling`, which waits on `edge`, a deadlock on every fresh cluster.

## Grade it locally

`bin/idp-portability-drill <kustomizations.json>` takes the JSON `kubectl get kustomizations -A -o json`
prints from any cluster, including the laptop k3d cluster from crew#191, and exits non-zero on
FAIL. `pytest tests/test_incident_crew488_portability_floor.py` proves the grader both ways.
