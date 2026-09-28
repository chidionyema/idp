# Demo: the money is built, and it is switched off

The commerce primitive is in the repository and it is dark. Four separate things hold it
off, and each one is a command you can run yourself.

## It costs nothing while it is off

```
$ bin/idp-features plan | grep -E 'commerce|^total'
feature commerce             tier off        cpu 0     memory_gb 0     storage_gb 0
total cpu 4.68 memory_gb 20.45 storage_gb 27.0 (git requests over 39 switches + node reserve cpu 0.3 memory_gb 1.5)
```

The register defaults this feature to `off`, so the planner counts nothing for it. The same
run ends with the list of switches that are on, and no commerce row is in that list. Nothing
about this change makes the node bigger or the bill larger until somebody turns it on.

## The cluster is told not to run it

```
$ grep -E '^  name:|^  suspend:' clusters/oke/commerce.yaml
  name: commerce-data
  suspend: true
  name: commerce
  suspend: true
  name: event-bus
  suspend: true
```

Three rows, three suspends. Flux reads the files, sees the suspend, and does not apply
anything. This is the estate's normal dark switch, not a new mechanism.

## The manifests are real, not a sketch

```
$ kubectl kustomize platform/commerce/data | grep -c '^kind:'
10
$ kubectl kustomize platform/commerce/app | grep -c '^kind:'
2
$ kubectl kustomize platform/event-bus | grep -c '^kind:'
3
```

Fifteen objects render cleanly today: the ledger database and its cache, the money
application, and the event bus that carries "this customer paid" to whatever needs to know.
Suspended is not the same as unfinished. When the switch is thrown, this is what runs.

## There is still no way in from the internet

The namespace carries no edge label, so the gateway refuses a route from it even if one were
added by mistake, and every ingress in the chart values is `enabled: false`. Two independent
locks, on top of the suspend, on top of the register default.

## The rules are pinned by tests

```
$ python -m pytest -q tests/test_crew623_money_never_enters_the_application.py
13 passed in 0.33s
$ python -m pytest -q tests/test_incident_crew623_a_chart_class_in_another_branch_is_still_batch.py
7 passed in 2.89s
```

Twenty tests. They are the fence around the promise: no product may carry payment code, the
event contract keeps its shape, the layer stays dark until a pull request deliberately turns
it on, and the capacity guard can still read a chart that puts its priority class in one
branch of the values and its requests in another.
