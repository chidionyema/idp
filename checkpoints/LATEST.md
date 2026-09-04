# Checkpoint — session 36c9262c — lane: the estate's memory

## RESUME HERE

The memory lane. Hindsight is the estate's memory store (namespace `hindsight`, on the one
estate Postgres, database `hindsight`, one bank `hermes`); estate-mcp is the interface in front
of it and holds no memory of its own.

Landed:
- hermes-v2#76 — the one Telegram door recalls before it answers and retains after.
- idp#1637 — three workloads were still calling the revoked DeepSeek lane; hindsight's
  extraction model is now the `fast` alias.
- idp#1640 — both Otto deployments carry the memory URL and the fence to reach it.

Open right now:
- **idp#1644** — main's offline-gate is red and blocks everything. Two gates disagreed with the
  controller they predict: `bin/idp-envsubst-gate` ignored Flux's per-resource
  `kustomize.toolkit.fluxcd.io/substitute: disabled` (platform/llm), and `bin/ns-fence-gate`
  failed three namespaces that are declared in git, switched off, and correctly skipped by
  `bin/idp-ns-fence-gen`. Both fixed, both fixtures still prove both ways.
- **idp#1642** — `remember` / `recall` on the estate MCP, every check green, waiting only on
  main going green so the merge does not inherit a red main.
- **next** — the founder said the memory work "is just happening in the dark". The deliverable
  is a Superset "Memory" dashboard seeded exactly like
  `platform/observability/superset-boardroom-seed.yaml`, over the `hindsight` database:
  memories per day, which channel they came from (`metadata->>'platform'` or `'surface'`),
  which conversation and person, what kind of fact, the latest memories, the ingest queue from
  `async_operations` and the extraction calls from `llm_requests`. Measured 2026-09-05:
  `audit_log` is empty, so per-call retain/recall volume is not visible from it today.
  Worktree for that work: `wt-mem3`, branch `feat/memory-in-the-open`.

Still unapplied from the one-door ruling: `hermes-agent` is a second Telegram registrant
(`platform/hermes-agent/gateway.yaml` TELEGRAM_WEBHOOK_URL). The pinned fork's polling
behaviour must be read before that env is touched, or removing it drops the fork into
long-polling and it steals the door from otto-gateway.
