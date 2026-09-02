## RESUME HERE — 2026-09-02T14:05Z, lane .wt-crew612-phone (session a14fc078)

Two branches pushed/pushing, both off main 397c1d96, neither merged (founder merges):

1. `fix/kyverno-judge-audit-warn-split` (c9651775, PUSHED): the judge wave — ns labels reach the
   offline judge, bin/lib/kyverno_policy_set.py splits mixed Enforce+Audit policies + dedupes the
   double-appended estate set, FAIL grep anchored on 'failed:', backstage base judged as its oke
   overlay, observability singleton PolicyException ×6. Proof: 14 tests passed, llm ok warn:4,
   observability all ok, must-fail still exits 1 (scratchpad/judge-wave/proof-battery.txt).
2. `fix/priority-class-on-platform-workloads` (committing now): founder order in
   ~/.claude/docs/founder/2026-09-02T1357Z-the-cluster-is-bleeding-out-across-three-different-cba107c9.md.
   priorityClassName onto litellm/litellm-db/estate-mcp/github-mcp (new class platform-service,
   value 10000, added to platform/priority-classes/priorityclasses.yaml) and the two spend
   CronJobs (platform-batch). Judged: llm pass:271 fail:0 warn:0; mcp pass:218 fail:0 warn:0.

Open next: (a) deep-trace reply to founder — corrections: audit rule admits (not an outage),
signoz READY, otto = sequencing (idp#1144 merged 13:57:16Z; secret values land on founder's next
oke-check mode=apply, per code-f9 14:0xZ); superset cause UNKNOWN at pod level (code-0c cluster
read BLIND, digging). (b) langfuse chart's five workloads still lack a class — blocks flipping
platform-workload-names-a-class to Enforce. (c) dagster kyverno availability denial: unclaimed lane.
