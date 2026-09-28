# EU AI Act — what it looks like when it runs

Real output, captured on main (`66b4e43`) on 2026-08-25.

## The registers are complete

```
$ bin/ai-act-gate
ok    ai-act 1 system(s), 5 risk(s), every Annex IV section, risk field and data source present
```

One declared system (prospector), five risks in the register, a technical file
with all nine Annex IV sections, four data sources each carrying provenance,
lawful basis, personal-data flag and retention.

## The conformity assessment, generated from the gates

```
$ bin/conformity-report
# Conformity assessment by internal control (Annex VI), 2026-08-25

Voluntary, for systems below the high-risk tier. Each line is a gate's own output.

ok    ai-act 1 system(s), 5 risk(s), every Annex IV section, risk field and data source present
ok    security-policy 14 controls, every in-repo proof exists, 0 outside this repo not checkable here
PASS      every policy allows its good case and refuses its bad ones
ok    multiarch 0 findings across 1 root(s)

Systems assessed:
- prospector: tier limited, role ['provider', 'deployer'], owner chidionyema, file docs/ai-systems/prospector/technical-file.md, review due 2026-11-25
```

## The gate refusing a broken register

```
$ TODAY=2026-08-25 bin/ai-act-gate tests/fixtures/ai-act/bad; echo rc=$?
FAIL  ai-act risk R-1: review overdue (2020-01-01 < 2026-08-25)
FAIL  ai-act system demo: docs/ai-systems/demo/technical-file.md lacks Annex IV section '## 9.'
rc=1
```

## The real register, on the day its review is late

```
$ TODAY=2026-12-01 bin/ai-act-gate .; echo rc=$?
FAIL  ai-act risk R-PROSP-001: review overdue (2026-11-25 < 2026-12-01)
FAIL  ai-act risk R-PROSP-002: review overdue (2026-11-25 < 2026-12-01)
FAIL  ai-act risk R-PROSP-003: review overdue (2026-11-25 < 2026-12-01)
FAIL  ai-act risk R-PROSP-004: review overdue (2026-11-25 < 2026-12-01)
FAIL  ai-act risk R-PROSP-005: review overdue (2026-11-25 < 2026-12-01)
FAIL  ai-act system prospector: review overdue (2026-11-25 < 2026-12-01)
rc=1
```

That is the row that stops a register going stale: the build goes red the day the
quarterly review is missed.
