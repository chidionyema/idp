# Getting started with the one-hour buyer sandbox

## What it is for

Diligence and demos. When a buyer's engineer asks to try it themselves, the answer is one
command, and the thing they get expires by itself an hour later. Nobody has to remember to
tear it down, and nothing they do inside it can reach the rest of the estate.

## What you need

Nothing new. The sandbox definition lives in the platform repository under
`platform/sandbox/vcluster`, and the expiry machinery is the platform's own policy engine
with its cleanup controller switched on. A person with cluster access launches it; agents
never deploy.

## First run

Follow [the sandbox runbook](../runbooks/demo-sandbox.md) top to bottom: launch, verify,
hand over the connection command, and let the clock do the rest.

## The rules it lives under

The sandbox clears the same admission bar as every real workload: images name their
registry, the control plane's processor request stays under the approved ceiling, its
public-facing endpoints carry the catalogue label, and it keeps no storage. All of that is
pinned by `tests/test_demo_sandbox_is_defined_and_expires.py`, so a future change that
breaks a bound is a red build, never a surprise mid-demo.
