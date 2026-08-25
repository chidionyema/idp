# Onboarding: migration-gate

## What it is

`bin/migration-gate <script>` runs a migration script through three phases on
a pristine temp environment — apply, apply again, roll back — and fails the
run if any phase is red. The script under test must speak five verbs:
`can_apply`, `apply`, `healthcheck`, `rollback`, `state`.

## Why it exists

This is R22's first enforcement mechanism (crew#186 CP1): a migration is not
trusted just because it ran once. `apply` must leave the system healthy;
`apply` run a second time must be a no-op, because a migration that is not
idempotent breaks the moment it is accidentally run twice; `rollback` must
restore exactly the pre-migration state, because a migration nobody can
reverse is a one-way door. All three are checked against a temp
`DAGSTER_HOME`, ledger and port, with launchd disabled, so a migration under
test never touches the real scheduler or the real machine.

## When it runs

Inside `bin/idp-ci`: once against `tests/fixtures/migration-not-idempotent`,
a fixture built to fail phase 2 on purpose, to prove the gate actually
discriminates; and once against the real `bin/scheduler-migrate`, but only
when `dagster` is importable in the Python running CI — where it is not, the
gate reports `BLIND` rather than a false pass, because a check that cannot
reach its evidence must say so.

## Related files

```
bin/migration-gate                       the three-phase check
bin/scheduler-migrate                    the real migration it proves
tests/fixtures/migration-not-idempotent  the fixture that must fail phase 2
```
