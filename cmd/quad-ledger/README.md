# quad-ledger — layer 4 of the Quad: history that cannot be quietly edited

Elpis signs every request an agent makes (layer 3) and publishes one record per signature on
`estate.quad.actions.<agent-urn>`. This service is the single writer that turns those records
into a hash chain in estate-db, anchors the chain head outside the cluster, and verifies the
whole chain against that anchor. `verify` exits 1 on a planted fault; `cmd/quad-ledger/chain_test.go`
proves that for an altered row, a deleted-and-relinked row, and a truncated chain.

| subcommand | does | runs as |
|---|---|---|
| `migrate` | `agent_actions`, `merkle_anchors`; revokes update/delete from the app role | init container |
| `consume` | durable JetStream consumer → one row per action, `row_hash = sha256(prev_hash ‖ canonical)` | Deployment, 1 replica |
| `anchor` | chain head → `merkle_anchors` and a JSON object PUT to the `quad-anchors` bucket via a write-only PAR | CronJob every 15 min |
| `verify` | recompute every row, compare with the latest anchor, publish `estate.quad.ledger.state` | CronJob every 15 min, and intent `quad.ledger-verify` |

Secrets are files: `DATABASE_URL_FILE`, `QUAD_ANCHOR_PAR_URL_FILE`. `NATS_URL` is not a secret.
Vault entry `quad-ledger` holds `postgres-password` and `anchor-par-url` (founder seeds by name).
