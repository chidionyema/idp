## RESUME HERE

**Lane:** idp — one Postgres for the estate (idp#1450) and the default-account token rule (idp#1467).

**idp#1450 `feat/one-estate-postgres`** — rebased onto main at a3b60464. One merge replaces ten
Postgres servers with one CloudNativePG cluster, copies every database onto it and deletes the old
servers, with each consumer's Flux row waiting on `estate-db-migrate` so nothing is pruned before it
is copied. Four checks that graded the estate as it was are fixed: the platform catalogue gained a
`data` system, `platform/alerts/alert.yaml` covers namespace `estate-db`, the Temporal acceptance
test reads the estate address, and the research engine moved off `hindsight-db` onto
`estate-rw.estate-db.svc.cluster.local`. Also registered `flux-webhook-token`, which reached main
unregistered with idp#1463. Local: every changed kustomize dir builds, `bin/idp-root-trust` PASS.
Next: push and watch the run.

**idp#1467 `fix/no-kube-token-by-default`** — Kyverno mutates `automountServiceAccountToken: false`
onto pods running as the `default` service account. Red on
`tests/test_incident_crew488_cp5_root_reds_are_never_green.py`: the security page table must be
regenerated with `bin/idp-admission-policies` now that a policy was added. Next: regenerate, commit,
push.

**Then:** back to the research engine (founder's standing instruction).
