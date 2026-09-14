# Opening stream stats for the epistemic fabric

idp#3448 CP1's four ingestion connectors publish onto four JetStream streams on the estate's
existing NATS event-bus (`platform/event-bus`) -- `epistemic.github`, `epistemic.slack`,
`epistemic.cicd`, `epistemic.incidents`. There is no web dashboard for JetStream in this estate
(`platform/event-bus/nats.yaml` disables `natsBox`, and no Console chart is installed), so the
door is the same `nats` CLI port-forward the event-bus row's own catalogue entry already uses,
not a second bus or a second UI.

## Opening it

From your idp checkout, with the `nats` CLI installed (`brew install nats-io/nats-tools/nats`):

```bash
kubectl port-forward -n event-bus svc/nats 4222:4222 &
nats stream ls
```

A healthy CP1 shows all four streams with a non-zero message count once at least one event has
been ingested from each source:

```
╭─────────────────────────────────────────────────────────────────╮
│                             Streams                              │
├────────────────────┬─────────────┬─────────────────────┬────────┤
│ Name                │ Description │ Created              │ Messages │
├────────────────────┼─────────────┼─────────────────────┼────────┤
│ EPISTEMIC_GITHUB    │             │ ...                 │ > 0    │
│ EPISTEMIC_SLACK     │             │ ...                 │ > 0    │
│ EPISTEMIC_CICD      │             │ ...                 │ > 0    │
│ EPISTEMIC_INCIDENTS │             │ ...                 │ > 0    │
╰────────────────────┴─────────────┴─────────────────────┴────────╯
```

## If a stream is missing or stuck at zero

- The stream itself is created by whichever connector publishes to it first
  (`ensureStream` in `platform/messaging/cmd/epistemic-ingest/main.go`), so a missing stream
  means that one Deployment has never successfully connected -- check
  `kubectl logs -n epistemic-fabric deploy/epistemic-ingest-<github|slack|cicd|incidents>`.
- A stream present at zero messages usually means its credential is not synced yet: `kubectl get
  externalsecret -n epistemic-fabric` shows `SecretSyncedError` until the matching vault entry
  (`epistemic-fabric-github`, `epistemic-fabric-slack`, `epistemic-fabric-github-api`) is filled --
  this is a `FOUNDER ACTION`, not a defect (`bin/idp-externalsecret-blockers`).
