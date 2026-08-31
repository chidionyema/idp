# The SigNoz verdict — what it is for, what it costs, where it lives, how to stop it

## What it is for

SigNoz is the estate's telemetry store (`platform/observability/signoz.yaml`). Before this, the
only statement about it was "the pod is Running," which says nothing about whether it answers, whom
it answers, or whether a person who signed in at the front door can reach it. The verdict is a
signed, hourly, machine-checked answer to those four questions, from the same checker identity that
signs the Langfuse and catalogue checks, so a buyer's engineer reads one page for all
three surfaces and sees the same shape.

The negative control is the part that matters. `/api/v2/dashboards` is the one path a program is
allowed to reach without the browser login, and every hour the checker proves that a caller holding
no key is refused there. If SigNoz ever answers that caller, the row turns red the same hour.

## What it costs

Nothing new runs. One route on the existing edge, one GitHub Actions job an hour (the same
runner minutes the Langfuse verdict already spends), one service account inside SigNoz with the
vendor's read-only role, one entry in the vault.

## Where it lives

```
platform/observability/httproute.yaml      route signoz-api: /api/v2/dashboards alone, annotated
probes/signoz.py                           L1, L2 with the key, the negative control
probes/front_door.py                       L3: reached_host and signed_in, from the login drill
bin/idp-prove signoz                       the prover; BLOCKED with a reason when it cannot measure
bin/idp-signoz-key                         mints the service-account key from the vault's root login
bin/idp-estate-seed                        step 4 calls the minter; --rotate signoz-prover renews it
.github/workflows/verdict-signoz.yml       hourly at :47, and the portal button verdict-signoz
drills/catalogue.yaml                      row verdict-signoz (the dispatcher covers a missed hour)
docs/reference/policy/root-trust.md        row signoz-prover, the register of minted credentials
tests/test_front_door_every_route_is_behind_the_one_login.py   refuses the route on any other path
```

The key is born in the vault entry `signoz-prover`, field `key`, minted over a port-forward from
the root login Terraform wrote (`signoz-root-email`, `signoz-root-password`); no person sees it and
no console is touched (the one-root-credential rule). The session and service-account endpoints stay behind the one login.

## How to stop it

Revert the commit that added it: the route closes, the workflow and catalogue row go, the front-door
gate no longer knows the annotation. The vault entry can stay; a viewer key on a closed door does
nothing. To rotate instead of stop: `bin/idp-estate-seed --rotate signoz-prover` from a runner with
a cluster session (`oke-check.yml -f mode=apply`).

## What it does not do

It does not make SigNoz take the estate's one login; SigNoz's community edition has no single sign-on.
Until it does, the signed-in walk marks the check as blocked with that reason, and the
verdict is never green over a login screen.
