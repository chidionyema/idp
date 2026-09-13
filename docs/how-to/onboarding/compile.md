# Onboarding: compile the estate

## What it is for

It answers one question that the estate could not previously answer: **what will the cluster
actually run, for every workload, as decided by the Helm chart?**

A values file, a comment and a `postRenderer` patch are all *claims*. The rendered chart is the
*decision*. They disagree more often than anyone expects — a merged right-sizing sat unapplied for
five days because a comment claimed a value the file did not set, and every check was green because
the YAML was valid.

Use it before believing any number written in prose, and before concluding a cluster is full: the
scheduler reserves what `requests` says, which is often far more than the workload uses.

## Run it

```console
$ bin/idp-compile-helm                      # every release, one document
$ bin/idp-compile-helm --release observability/langfuse
$ bin/idp-compile-helm --json               # the document to stdout
```

It needs `helm` on PATH. It adds each chart's repository itself, so a machine that has never run
`helm repo add` produces the same document. It writes `.estate/compiled-helm.json` by default.

## Where it lives

| piece | path |
|---|---|
| the compiler | `bin/idp-compile-helm` |
| the gate | `features/gates/compiled-helm.feature`, `sovereign/tests/bdd/test_compiled_helm.py` |
| the page | `backstage/packages/app/src/modules/home/compiled.ts` (logic, tested), `useCompiled.ts` (read), and the Ops section |
| the published document | `docs/compiled-helm.json` on the estate state branch, written by CI |

CI runs it on every pull request. A chart that fails to render **fails the run**: an unrendered chart
is a workload whose numbers nobody knows, and reporting success while blind is worse than no gate.

## What it costs

Nothing. It runs offline against charts pinned in git, in about two minutes for all 33 releases. It
uses no cluster, no credentials and no cloud resources.

## How to stop it

Remove the two `bin/idp-compile-helm` steps from `.github/workflows/ci.yml`. The gates stop running
and the Ops section shows the last published document, which then goes stale — the section reports
that it could not read the document rather than showing an old one as current.

## What it does not cover

Kustomize-native objects, Crossplane resources, and anything a Kubernetes operator creates at run
time. It covers exactly the class of defect that hid for five days: a value the estate believes it
set, that a chart actually decides.
