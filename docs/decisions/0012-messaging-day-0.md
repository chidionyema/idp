# 0012. Messaging day 0: NATS JetStream behind a transactional outbox, contracts locked, broker replaceable

- Status: PROPOSED 2026-08-29 (founder specification v0.1; principal review on crew#639)
- Date: 2026-08-29
- Deciders: founder (the specification and the locked contracts), session 80471694 (the review against the estate)
- Affects: `platform/event-bus` (idp#800), `platform/messaging` (new Go module), `catalog/ports.yaml`, `platform/monitoring`, `docs/prose/messaging-cp*.feature`, crew#639, crew#623.

## The day, in plain words

The founder wrote the day-0 messaging specification himself and asked for a principal review, an
architecture, a build, operations and a demo. The full text is preserved verbatim in
`crew/docs/specs/issue-639.md`. This record holds the decisions so nobody re-derives them.

## Decisions, as the founder logged them

| # | Decision | Status | Reversal cost |
|---|----------|--------|---------------|
| D1 | Subject grammar `{domain}.{kind}.{aggregate}.{action}.{version}`; no environment, tenant or region in a subject; a new version is a new subject | Locked | Very high, treat as an API |
| D2 | CloudEvents 1.0 binary mode over NATS headers, protobuf 3 payload, additive-only evolution, `buf breaking` in CI | Locked | High |
| D3 | The transactional outbox is the only path a business event takes; the relay is the only writer; enforced by credentials, not review | Locked | High |
| D4 | Operator mode with `nsc`; accounts SYS, PLATFORM, APP-{domain}, TENANT-{id}; seeds in OCI Vault, JWTs in git | Locked | High |
| D5 | NATS JetStream is the broker | Adopted | Medium by design; D1 to D4 make it swappable |
| D6 | Self-host on the cluster (the official nats-io chart already in `platform/event-bus`) versus Synadia Cloud | Open, default self-host | Low |
| D7 | Pull consumers only, durable, explicit ack | Adopted | Low |
| D8 | 30-day stream retention; Postgres plus outbox is the record | Adopted | Low, a value |

## The estate's rulings on top (crew#639, review items 1 to 14)

- R1 on day 0. The OKE pool has two worker nodes, so `num_replicas: 3` across zones cannot exist.
  Streams run R1 with the outbox as the disaster-recovery truth; R3 is one values change when the
  pool has three Ready nodes. This is the only number in the specification that day 0 changes.
- One broker, not two: the HelmRelease of idp#800 is the broker; the hand-written server config in
  the specification becomes chart values.
- Secrets are OCI Vault through ExternalSecrets; telemetry is the SigNoz collector; the seven alerts
  are PrometheusRule rows to alertmanager and never the founder's chat.
- Schemas live in `platform/messaging/schemas`; a separate schema repository waits for its trigger.
- Go for every daemon (relay, consumer library, DLQ processor, `ops replay`); a .NET client is a
  later checkpoint for the store.
- Acceptance is the eight §11 tests as BDD scenarios, run on the portability drill's k3s job, then
  weekly on the cluster.

## Consequences

A service that publishes around the outbox gets a permissions violation. Replacing the broker means
rewriting the relay and the consumer library and nothing above them. Two-node R1 means a node loss
pauses the bus until the pod reschedules; nothing is lost because the outbox replays.
