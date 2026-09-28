# A gate that read "skipped" as "failed"

2026-09-04. Record for the change on `.github/workflows/ci.yml`.

## What was measured

The `bdd` job asserts that the `bdd-suites` job succeeded. `bdd-suites` only runs when a pull
request touches something a behaviour suite covers, so a pull request that touches none of
them leaves it `skipped`. The assertion was `test "$result" = success`, and on idp#1372 — a
change to one value in one manifest — that read:

```
bdd-suites: skipped
Process completed with exit code 1
```

## What this cost

Every change outside the behaviour-suite surface arrived with a red `bdd` check that had
nothing to do with the change. The only way past it was to merge over a red check, which
trains everyone to merge over red checks, including the ones that mean something.

## What changed

`skipped` is now a pass and says so; `failure` and `cancelled` are still red.

## The rule this sits under

LAW 38 — a guard that refuses correct work is an outage, and is fixed as an outage rather than
worked around. The general form: a gate that reads a conditional job's result must decide what
"did not run" means before it ships, because "did not run" is the common case, not the edge.
