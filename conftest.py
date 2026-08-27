"""crew#85, 2026-08-25: load 236 on a 16 GB Mac while Chrome, agent scans and a pytest suite ran
at the same priority. Row 1 of that issue: a suite started from an interactive session must not
compete with the founder's foreground work. pytest loads this root conftest before collection,
so every run of this suite, from any checkout, any shell and any agent, lowers its own priority
first. `nice` on the command line was the rule that depended on every caller remembering it."""
import os

SUITE_NICE = 10

if os.getpriority(os.PRIO_PROCESS, 0) < SUITE_NICE:
    os.nice(SUITE_NICE - os.getpriority(os.PRIO_PROCESS, 0))
