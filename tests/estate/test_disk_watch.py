"""The disk watcher was RETIRED 2026-11-11 by founder order.

WHY THIS TEST IS GONE (not skipped, not weakened):

This file's opening line was "The disk watcher is a bounded shell tick, not an agent-waking
resident process." That claim was made in good faith and was checked here -- the *shell tick*
shape was asserted. But the thing installed on the machine was a KeepAlive launchd job taking
one reclaim step per cycle forever, and the measurement is what settles it:

  - 120 bounded steps completed, last_freed_mb=3
  - free space 1526 MB -> 1012 MB over the same period, i.e. it lost 500 MB while "cleaning"
  - the machine sat at 26 MB free RAM with 80% swap, one more process competing for memory
  - when it was finally stopped, the volume recovered on its own: 1012 MB -> 2335 MB

A test that certifies the SHAPE of a guardian while the guardian costs more than it returns is
the R1 failure in AGENTS.md section 9 -- a gate that passes on the thing it was supposed to
catch. So the file is not preserved in any form.

The founder's ruling: needing 113 steps to clean a disk IS the root cause, and worse than
anything else on the machine.

WHAT REPLACED IT: nothing resident. `estate-execute disk-reclaim` steps 1-4 are the reclaim path
(duplicate local gate runs, finished pytest scratch, the estate's own run records, the stale
dependency tree) -- narrow, measured, and needing no daemon.

Falsifier for the retirement lives in tests/test_disk_watch_plist_runs.py: it fails if anyone
reinstalls the guardian, restores a KeepAlive template, or leaves an intent pointing at the
retired cleaner.
"""
