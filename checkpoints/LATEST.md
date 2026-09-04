## RESUME HERE — 2026-09-04T15:35Z, session 85f840c5, lane idp

**Where the work is.** idp#1505 (`feat/key-lifecycle-cp2`) is open with auto-merge pending:
crew#832 CP2, the vendor-key proving gate — `platform/warden/prove.py`, `platform/warden/__init__.py`,
`platform/vendors/consoles.yaml`, `tests/test_warden_prove.py`. 14 behavioural tests pass locally
(`python3 -m pytest tests/test_warden_prove.py -o addopts=""`). Auto-merge could not be turned on
because rule-guard refuses a merge onto a red main.

**Why main is red** (run 33887965653, offline-gate):
1. `root-trust` FAIL — `infra-crew` is read by `platform/infra-crew/external-secret.yaml`
   (my idp#1491, the lane-scoped router key) and has no row in
   `docs/reference/policy/root-trust.md`, and no line in `ROUTER_PLAN` in `bin/idp-estate-seed`,
   so the entry is never minted either.
2. `cp1`/`cp2`/`cp3` FAIL — `bin/idp-ci` lines 542, 553, 564 still run
   `tests/test_cp1_estate_inventory.py`, `tests/test_cp2_workload_state.py` and
   `tests/test_cp3_workload_logs.py`, which #1451 deleted. Dead rungs; delete them.

**Next step.** Branch `fix/main-red-router-entry` off `origin/main`, make those two fixes in one
commit, merge it, then #1505 auto-merges behind it.

**Worktree.** `/private/tmp/claude-501/-Users-chidionyema-dev-code-idp/85f840c5-baf3-4598-9496-1b3eb9dd83e9/scratchpad/kw`
