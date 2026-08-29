# Demo: migration-gate

`bin/migration-gate <script>` proves a migration script is safe on a pristine
temp environment, in three phases: apply and check the healthcheck; apply
again and confirm the state did not change (idempotent); roll back and confirm
the state matches the pre-migration snapshot (reversible). The script must
implement five verbs: `can_apply`, `apply`, `healthcheck`, `rollback`,
`state`. This is R22 mechanism 1 (crew#186 CP1).

Run against a fixture built to fail phase 2 — its second `apply` adds a
resource instead of leaving state unchanged:

```
$ bin/migration-gate tests/fixtures/migration-not-idempotent
FAIL  migration tests/fixtures/migration-not-idempotent: phase 2 second apply changed state: {"dagster_yaml_sha": null, "resources": 1} -> {"dagster_yaml_sha": null, "resources": 2}
```

The gate's own environment is isolated per run: `DAGSTER_HOME`,
`MIGRATE_LEDGER` and `SCHEDULER_PORT` are all set to a fresh temp directory,
and `MIGRATE_LAUNCHD=0` keeps it from touching the real launchd. On a genuine
failure it also tails every `.out` log under that temp home, so the reason is
visible from the one command rather than requiring a second investigation.

The real target is `bin/scheduler-migrate`, proved the same way inside
`bin/idp-ci` whenever `dagster` is importable in the running Python; where it
is not, the gate prints `BLIND` and the migration is not proved on that run
rather than being reported as passing.
