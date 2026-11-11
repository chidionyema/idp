"""The disk cleaner was RETIRED 2026-11-11 by founder order.

WHY THIS TEST IS GONE (not skipped, not weakened):

1511 lines asserting the behaviour of `platform/estate/libexec/disk-cleanup.sh` against a fake
HOME: that a dry run deletes nothing, that apply empties every allow-listed cache, that a
claimed worktree survives. Those assertions were true. The script did what it said.

It was still the wrong thing to have on this machine, and the measurement is what settles it:

  - 120 bounded steps completed, last_freed_mb=3
  - free space 1526 MB -> 1012 MB over the same period, i.e. it lost 500 MB while "cleaning"
  - the machine sat at 26 MB free RAM with 80% swap, one more process competing for memory
  - when it was finally stopped, the volume recovered on its own: 1012 MB -> 2335 MB

A correct cleaner that costs more than it returns is a defect, and a test suite that keeps it
green is what keeps the defect in place. So the file is not preserved in any form.

The founder's ruling: needing 113 steps to clean a disk IS the root cause, and worse than
anything else. Free space is a maintenance operation run when it is needed, not a resident
daemon -- and never one that holds the executor's disk floor closed against its own off switch,
which this one did (it refused `launchctl bootout` and `/bin/rm` on itself at 1012 MB).

Falsifier for the retirement lives in tests/test_disk_watch_plist_runs.py: it fails if anyone
reinstalls the guardian or makes the sources clean again.
"""
