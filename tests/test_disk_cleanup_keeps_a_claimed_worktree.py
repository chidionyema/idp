"""A worktree a live claim covers is never removed by the disk cleaner.

THE CLEANER ITSELF WAS RETIRED 2026-11-11 by founder order -- see tests/estate/test_disk_cleanup.py
for the full record and the measurement (120 steps at 3 MB each while the volume fell 500 MB, then
1012 MB -> 2335 MB recovered on its own once it was stopped).

THE RULE SURVIVES AND IS NOW ENFORCED WHERE IT MATTERS. "Never delete a worktree a live claim
covers" was this file's real content, and it was a rule of one script. The estates's rule is one
of each layer (AGENTS.md section 6): the authoritative statement of what a live claim covers is
the focus register, and the guards that read it are bin/claim-gate and
platform/estate/governance/executor_permission.py -- not a cleaner's allow-list.

With the cleaner gone there is no code path that deletes worktrees at all, which is a strictly
stronger version of this guarantee. The assertions are therefore not preserved in the cleaner's
form; the retirement falsifier lives in tests/test_disk_watch_plist_runs.py.
"""
