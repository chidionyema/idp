# DoF freeze: a component may repair itself only if its registry entry says `selfRepair`

**Date:** 2026-11-09
**Incident:** #7334 (`estate-doors`), DoF level **L2**, lease `repair-only: Genesis-Resolves: estate-doors`
**Blast radius measured:** `estate_invoke lane` reported `state: RED`, **28 red lanes**, `main` red
on 7 required checks, `work_lost: 0`.

## The observed failure

Almost every red lane fails the same required job, verbatim:

```
ci-success failure -- dof-gate > Run base="${BASE:-$(git merge-base origin/main "$HEAD")}"
```

Measured on `approvals-visible`, `chronos-clock-registry`, `estate-disk-measured`,
`executor-pipefail-verdict`, `one-tap-approvals`, `prepush-gate-budget`,
`reconcile-disk-door-tests`, `retire-backstage-fe`, `ship-four-primitives`,
`substrate-staleness-gate`, `worktree-budget-zip-fix`, `guarded-paths-no-forged-signed-7770`,
`feat/router-zai-cutover-20261108`, `fix/recovery-run-command-pagination`.

This is section 5b working as written: while a `[lane] <service>: a lane is down` incident is open,
`dof-gate` is a `needs` of `ci-success` and refuses any commit that does not carry
`Genesis-Resolves: <id>` and stay inside that id's `repairScope`.

## The defect: one missing field in the registry

`bin/dof-gate` `evaluate()`:

```python
scope, comp = scope_of(registry, resolves)
if not comp.get("selfRepair"):
    frozen = [p for p in changed if any(glob_match(g, p) for g in registry.get("immutableWhileRed", []))]
    if frozen:
        return {**refusal, "reason": "the gate is immutable while a critical service is down", "files": frozen}
```

`immutableWhileRed` is `["bin/dof-gate", "catalog/dof-registry.json", "tests/test_dof_gate.py",
".github/workflows/ci.yml"]`. `selfRepair` is the **only** way a component may change those four
files while it is red.

`catalog/dof-registry.json` declares `selfRepair` for exactly one component:

```json
"dof-probe": {
  "selfRepair": true,
  "repairScope": ["bin/dof-gate", "catalog/dof-registry.json", "tests/test_dof_gate.py", ".github/workflows/ci.yml"]
}
```

`estate-doors`, the component whose incident is actually open, has **no `selfRepair` key**:

```json
"estate-doors": { "repairProtocol": "...", "repairScope": ["@substrate"] }
```

So the gate says: you may repair estate-doors, but not in any file that implements the freeze. The
freeze can then only be lifted by a commit from someone not bound by it, which is nobody: every
agent lands through the same `ci-success` to `dof-gate` path.

## Second, independent refusal on the same files

A change carrying `Genesis-Resolves: estate-doors` is refused again by `submit-lane`:

```
##[error]an agent patch may not change CI or hooks: .github/workflows/ci.yml
```

Measured in run `42539049729` (`conclusion=failure`). `ci.yml` is in `immutableWhileRed`, so no
agent path can move it. That is a deliberate safety property, and it is why the estate cannot
self-repair this class.

## The fix, as a one-field change

```json
"estate-doors": {
  "repairProtocol": "issue body of the open [lane] estate-doors incident",
  "selfRepair": true,
  "repairScope": ["@substrate", "bin/dof-gate", "catalog/dof-registry.json",
                  "tests/test_dof_gate.py", ".github/workflows/ci.yml"]
}
```

This does not weaken the freeze for anyone else: `estate-doors` is the component that is down, so
its repair is exactly what section 5b exists to permit. It does not open the frozen files to
arbitrary edits either: the `stray` check still refuses any path outside `repairScope`.

`catalog/dof-registry.json` is itself frozen, so an agent cannot land this. It needs the owner's
ruling: the change is small and structured, but it edits the gate that judges it, so it must not
be self-authorised. That is the "judgment / irreversible" residue named in AGENTS.md section 12.

## Why a diagnosis could be written at all

`estate-doors` `repairScope` is `@substrate`, and `substrateScope` includes `docs/diagnoses/**`. A
diagnosis therefore lands inside the existing freeze without loosening it: the one lane still open
to an agent on this incident.

## Falsifier

`tests/test_dof_gate.py` should assert all three:

- `Genesis-Resolves: estate-doors` changing `bin/dof-gate` is **admitted** with `selfRepair: true`;
- the same commit is **refused** with `the gate is immutable while a critical service is down`
  when `selfRepair` is absent (the measured current state);
- a commit carrying `Genesis-Resolves: estate-doors` changing a path outside its `repairScope` is
  still **refused**, so the change does not widen the scope.

The gate demonstrably can fail, and it is failing correctly. The defect is that its correct
failure has no exit.
