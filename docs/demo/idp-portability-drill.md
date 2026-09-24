# Demo: idp-portability-drill

## What it is

The migration scenario the estate has described in prose since crew#250, run for real every week.
A GitHub-hosted runner creates the estate's k3d cluster from `platform/k3d/estate.yaml`, installs
Flux from its own CLI, points one GitRepository at the commit under test and applies every
Kustomization under `clusters/oke/`. The runner holds no OCI identity, no vault, no laptop
session. Whatever comes Ready on that cluster is the part of the platform that hydrates from git
alone, and that count is the portability number.

## Watch it

Open the latest run of the `portability-drill` workflow in GitHub Actions. The last step prints
one line per layer that did not come up, with Flux's own reason, and then the verdict:

```
  not-ready  flux-system/secret-store: OCI vault unreachable
ok      portability  ready 17/22 layers on a cluster with no OCI (floor 17)
```

The receipt artifact carries `flux get kustomizations -A`, the HelmRelease table and the JSON
the grade was computed from, so the number can be re-derived without trusting the line.

## What red means

`FAIL portability ready N/M is below the floor F` means a layer that hydrated last week no
longer does on a cluster that is not OKE. That is a portability regression and it is fixed
before the change that caused it merges, because the buyer's engineer will run exactly this.
