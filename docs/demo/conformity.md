# Demo: conformity-report

`bin/conformity-report` renders the EU AI Act Annex VI internal-control
assessment as markdown, built entirely from other gates' own output rather
than written by hand. Nothing it prints is committed — a stored copy of a
generated report is a stale copy the moment any gate's output changes.

````
$ bin/conformity-report
# Conformity assessment by internal control (Annex VI), 2026-08-25

Voluntary, for systems below the high-risk tier. Each line is a gate's own output.

```
ok    ai-act 1 system(s), 5 risk(s), every Annex IV section, risk field and data source present
ok    security-policy 14 controls, every in-repo proof exists, 0 outside this repo not checkable here
PASS      every policy allows its good case and refuses its bad ones
ok    multiarch 0 findings across 1 root(s)
```

Systems assessed:
- prospector: tier limited, role ['provider', 'deployer'], owner chidionyema, file docs/ai-systems/prospector/technical-file.md, review due 2026-11-25
````

There is no separate failure mode: whichever of `bin/ai-act-gate`,
`bin/security-policy-gate`, `bin/policy-test` or `bin/multiarch-gate` is red
shows up as that gate's own FAIL line inside the fenced block, because this
script pipes their real stdout through rather than re-implementing a verdict.
The systems list comes straight from `platform/ai/systems.yaml`, so a new AI
system appears here the moment it is registered there.
