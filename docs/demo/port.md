# Demo: port-gate

`bin/port-gate` compares `catalog/ports.yaml` (intent: what may bind, and
where) against reality. Plain, it checks every compose file publication in
this repository; `--live` also checks every listener on this machine right
now, read with `lsof` at the moment the check runs.

```
$ python3 bin/port-gate
ok    ports    20 declared, 0 findings
```

`--live` reads the machine directly rather than a saved inventory snapshot,
because a saved snapshot can be stale — measured 2026-08-24: a snapshot 73
minutes old still said a service was bound `*` forty-five minutes after it had
moved to `127.0.0.1`, so the gate failed a service that was actually correct.
Run now, it can find a listener that was never declared at all:

```
$ python3 bin/port-gate --live
FAIL  ports    live listener 7233 (temporal[89681]) is not in catalog/ports.yaml
FAIL  ports    20 declared, 1 findings
```

That is a real, current finding on this machine, not a constructed example —
`catalog/ports.yaml` has no row for the `temporal` process now listening on
7233. `--live` also refuses a bind address that differs from what
`ports.yaml` declares (a service registered as `127.0.0.1:PORT` but actually
bound to `*:PORT`), and any non-loopback bind not explicitly marked
`non_loopback: true` (R20). A script in this repository that probes a
127.0.0.1 port nothing declares is caught the same way, since a probe is the
same claim a compose publication makes. `REG` and `INV` can be overridden so
`bin/idp-ci` proves every one of these findings against fixtures rather than
the real ledger.
