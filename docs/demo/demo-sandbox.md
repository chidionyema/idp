# Watch the one-hour buyer sandbox

The pitch in one line: hand a buyer's engineer a real, working cluster-in-a-cluster and let
them poke anything they like — it expires on its own an hour later, leaving nothing behind.

## Run it

A person launches it with the single command in
[the sandbox runbook](../runbooks/demo-sandbox.md). Within about two minutes there is a
working sandbox with a small demo shop already running inside it.

## What to show

1. The launch is one command, and it is the same machinery the whole estate runs on — no
   special path, no hand-built demo environment that drifts from production.
2. Inside the sandbox, the buyer's engineer has a full cluster of their own: they can list,
   deploy and break things without touching anything real.
3. The clock: the launch row carries a time-to-live label, and the platform's own policy
   engine deletes it on schedule. Show the row, show the label, come back after the hour
   and show that it is gone.

## What to expect

The sandbox control plane is deliberately small and keeps no state: restart it and it
resets. That is the point — the demo is the guarantee that a guest workload is bounded,
catalogued and mortal, which is exactly what a buyer's platform team wants to see enforced.
