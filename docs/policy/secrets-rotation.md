# Secrets rotation: the estate-wide strategy

**Why this exists.** Founder, 2026-08-31: "poorly designed enterprise-wide secrets rotation
strategy, this will harm us badly if we let it slide." Twice in one week a rotation "succeeded"
and the running program kept the old value: crew#506 CP4 (the vault held the new key, the pod
held the old one) and crew#684 (the rotated key reached neither of its two consumers). Both were
found by a person hitting a broken door. The defect was never one annotation — it was that no
stage of the road from vault to running process was owned, graded, or drilled.

**The rule in one sentence:** a rotation is not done when the vault write succeeds; it is done
when every running consumer answers with the new value, and the estate proves that without a
person looking.

## The road, stage by stage

Every secret travels the same five stages. Each stage has one owner (a control, never a person)
and one way it is proved.

| # | Stage | What happens | Owned by | Proved by |
|---|-------|--------------|----------|-----------|
| 1 | Mint | A new value is created. One root per provider, code mints the rest (R52). | `bin/idp-vault-put` — the only writer | vault-put prints key NAMES only; credential-guard refuses a value in chat or a PR |
| 2 | Store | The value lands in the OCI vault entry. | OCI Vault (the one store; a second store is stitching) | `bin/idp-vault-put` exits non-zero on a failed write |
| 3 | Deliver | The cluster copy syncs. | External Secrets Operator, `ClusterSecretStore estate-vault` | receipt row per ExternalSecret: Ready AND `last_sync` fresher than 2× refreshInterval (crew#387/#406) |
| 4 | Reload | Running consumers restart onto the new value. | Reloader, `reloader.stakater.com/auto: "true"` on every consumer (estate standard, crew#720 — auto-discovery, never an enumerated Secret list) | admission + guard on the annotation (crew#717/#720 lane) |
| 5 | Prove | The estate shows stages 1–4 actually composed. | **5a backstop:** cluster-state receipt row `secret-freshness`. **5b drill:** the daily `rotation-canary`. | this PR — see below |

Stages 1–4 each existed before crew#722 and each was individually green while both incidents
shipped. Stage 5 is what was missing: nothing graded the composition.

## Stage 5a — the backstop row (every secret, every 15 minutes)

The in-cluster collector (`platform/state/cluster-state.yaml`) lists Secrets as
`PartialObjectMetadataList` — names and write timestamps only; its RBAC grants `list` alone, so
reading a value is not even expressible from that pod. A Secret's last write is the newest
`managedFields` time. Any **Running** pod that consumes a Secret (env, envFrom, volume,
projected) and started **before** that Secret was last written is a stale consumer — the
rotation never reached it.

The grader (`bin/idp-cluster-state`, run by `oke-check.yml`) FAILs the estate on:

- `secret_stale_consumers > 0` — each row printed whole: namespace/pod, the Secret, both times;
- `secret_stale_consumers = -1` — the metadata list failed, so staleness was **not graded**
  (silent green is the defect class; a failed read is never a clean zero);
- the count absent — the receipt predates this control.

Exemptions, deliberately few: `kube-system`/`flux-system`/`kyverno` (the same set the reload
standard excludes), Job-owned pods (they run to completion), workloads opted out with
`reloader.stakater.com/auto: "false"` (each opt-out needs an open issue), and a 15-minute grace
after any write so an in-flight roll is not a false alarm.

Known edge, accepted: a no-op apply that rewrites identical bytes does not move the
managedFields time, and ESO only writes on change — so the row cannot false-positive on
refresh churn. The daily drill below exercises the timestamp behaviour against the live API
server, so a Kubernetes change to it shows up within a day, not at the next incident.

## Stage 5b — the rotation canary (the whole road, daily, for real)

`platform/state/rotation-canary.yaml` is a two-replica consumer in `backstage` that mounts the
Secret `rotation-canary` as a file (never env — the env policy flips to Enforce), reads it
**once at container start** (modelling the worst consumer, crew#506's class), and publishes
`sha256=<12 hex>` of the value it is actually running with to the receipts bucket every two
minutes.

The `rotation-drill` job in `oke-check.yml` (daily, `17 6 * * *`) writes a fresh random value to
the vault entry through `bin/idp-vault-put` — the real stage-1 writer, not a test double — and
polls the receipt until a running pod answers with the new value's sha.

**SLO: 25 minutes, vault write to running pod, no hand.** Budget: ≤10m ESO refresh + roll +
≤2m receipt loop + slack. Graded by `drills/catalogue.yaml` row `rotation-canary`
(max_age_hours 26): a day without a green end-to-end rotation is a red estate row.

The canary value guards nothing; its only job is to change.

## What this deliberately does not cover yet (later waves, crew#722)

- **CP4** — the generated secrets inventory: every vault entry with an owner and a maximum age,
  red row when overdue. Today rotation happens on incident, not on age.
- **CP5** — per-key value schema on `bin/idp-vault-put`, so a rotation cannot write a
  well-formed wrong shape.
- **CP6** — overlap-then-revoke for credentials with server-side state (two valid keys during
  the roll, revoke the old one only after the receipt shows the new one serving).

## Control ladder placement

Backstop row: rung 4 (continuous instrument, graded in CI, red is loud). Canary drill: rung 5
(the control is exercised against the live estate on a clock, and its own absence — a missing
run — is itself a red row). Proof obligation met in
`tests/test_incident_crew722_rotation_reaches_the_running_pod.py`: the pre-fix state (a receipt
whose pods predate a rotated Secret) is shown failing the grader.
