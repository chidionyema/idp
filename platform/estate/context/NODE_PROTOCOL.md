# Estate Node Protocol v1

The gateway is the authority for every replaceable estate surface: mobile apps, desktop apps,
web clients, agent harnesses and future runtimes.

Every capability call carries an envelope in `params.envelope`. The connection state travels in
`params.connectivity` as `online` or `offline` and defaults to `online`.

```json
{
  "protocolVersion": "estate.node-protocol.v1",
  "rulesHash": "18e3ccdaee2a0cceff3ad85c777ddfe7b33255694844b6925a4d331b29a9f3dd",
  "nodeId": "stable-node-id",
  "sessionId": "logical-session-id",
  "surface": "app|desktop|web|mobile|agent|cloud",
  "capabilities": ["context.read"],
  "cursor": {"eventId": "evt-id", "offset": 0},
  "leaseId": null,
  "contextPlanHash": null,
  "idempotencyKey": null
}
```

## Admission

- Every capability call requires the identity, session, surface, capability scope and cursor
  fields named by `node_protocol.json`.
- The requested capability must be present in `capabilities`.
- Online reads are allowed with a compatible envelope.
- Online mutations also require `leaseId`, `contextPlanHash` and `idempotencyKey`.
- Offline mutations are queued only when the protocol and action policy classify them safe.
- Unknown rules or versions are read-only and cannot mutate.
- Every accepted mutation must return a receipt object.

## Scope

- Context is compiled by the cloud gateway, not by harness-specific hooks.
- AI Studio is CONSULT only.
- Mobile actions obey the shared Android/iOS policy.
- WDA is reachable only over verified TLS.
- Capability claims require registry and context evidence.
