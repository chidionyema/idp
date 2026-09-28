# Demo: idp-free-tier

## What it is

The one number the estate's compute cost depends on, measured every day instead of remembered.
OCI grants each tenancy an Always Free allowance of VM.Standard.A1.Flex cores and memory, and it
halved that allowance on 2026-06-15 (ADR 0004). The estate found out when the node pool stopped
scheduling. `bin/idp-free-tier` asks the limits API what the tenancy is granted today and grades
it against two numbers in `platform/oci/variables.tf`: the allowance the module assumes free
(`free_ocpus`, `free_memory_gb`) and the size it provisions (`worker_ocpus`, `worker_memory_gb`).

## Watch it

Open the `free-tier` job of the latest `oke-check` run. One line:

```
ok      free-tier  A1 limit 4 OCPU / 24 GB, block 200 GB; module assumes 2 / 12, provisions 4 / 24 (2 OCPU / 12 GB paid)
```

The parenthesis is the honest cost line: what the module provisions above the free allowance is
paid capacity, and this row is where that is stated rather than assumed to be zero.

## What red means

`FAIL free-tier A1 core limit N is below the M the module assumes free` is the ADR 0004 cut
happening again. The exit rehearsal on crew#488 is what the estate does about it; this row is
the alarm that says to start it, days before a node fails to schedule.
