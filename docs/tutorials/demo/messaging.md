# Demo: messaging, basic and advanced

Founder, 2026-08-30 (crew#639): "can you put together a basic demo and an advanced one that uses
more advanced features, eg outbox etc". Both run with nothing installed but Go: the broker is
`nats-server` embedded in the process, the same version the chart on `platform/event-bus` runs,
and the database is an embedded Postgres fetched once into the user's cache directory. Set
`NATS_URL` and `DATABASE_URL` and the same binary runs against the cluster bus (CP2) and a real
database. Every line printed is a measurement from the broker or the database.

## The command

    cd ~/dev/code/idp && bin/idp-messaging-demo            # both
    cd ~/dev/code/idp && bin/idp-messaging-demo basic
    cd ~/dev/code/idp && bin/idp-messaging-demo advanced

The first run fetches the Postgres binaries (about a minute on this Mac); every run after that is
ready in under ten seconds. The last line is `ok demo <mode> trace=<id>` or `RED demo <mode>: <why>`.

## Basic: what every service sees

One CloudEvents 1.0 message in binary mode (the attributes are NATS headers, the payload is the
body) on the locked `ORDERS_EVENTS` stream, consumed by a durable pull consumer with an explicit
ack, the trace id carried end to end. The stream's values are the ones ADR 0012 locks: subjects
`orders.event.>`, file store, 30-day retention, a 15-minute duplicate window, delete and purge
denied.

```
broker embedded nats://127.0.0.1:50607, database embedded, ready in 12.561s
stream ORDERS_EVENTS subjects=[orders.event.>] max_age=720h0m0s duplicate_window=15m0s deny_delete=true deny_purge=true
published orders.event.order.placed.v1 seq=1 ce-id=51e4f024-cd34-47dd-9501-421b55d80229 trace=ba65aff61f5e4cefa1feab1db24ed80d
consumed orders.event.order.placed.v1 by durable pull consumer "demo-orders": ce-id=51e4f024-cd34-47dd-9501-421b55d80229 ce-type=orders.event.order.placed.v1 traceparent=00-ba65aff61f5e4cefa1feab1db24ed80d-717f0dabe18f1b2d-01 delivered=1 acked=explicit
consumer pending=0 ack_pending=0 redelivered=0
ok demo basic trace=ba65aff61f5e4cefa1feab1db24ed80d
```

## Advanced: what the estate relies on

The transactional outbox (decision D3), end to end, with the failures a real day brings:

1. **Enforced by credentials, not review.** The service's NATS user publishes an event directly
   and the broker refuses it with a permissions violation. The only path is the outbox table.
2. **One transaction.** Three orders are committed, each with its outbox row in the same
   transaction. The service opened no broker connection.
3. **At-least-once ends in one stored copy.** The relay publishes the first row and crashes before
   marking it. The second pass republishes all three; the broker answers `duplicate=1` for the
   one it already holds (Nats-Msg-Id is the event id, the duplicate window is 15 minutes) and the
   stream holds exactly three messages.
4. **Poison goes to the DLQ, not the floor.** A message whose payload names no sku fails the
   handler three times (`max_deliver 3`); JetStream raises `MAX_DELIVERIES` and the DLQ processor
   copies the original, headers intact, to `orders.dlq.order.placed.v1` in `ORDERS_DLQ`.
5. **Idempotent consumer.** Each event's effect is applied inside one transaction with its
   `processed_events` row: three effects for three events.
6. **Replay changes nothing.** A fresh consumer replays the stream from the start into the same
   handler: four deliveries, zero effects applied, the poison message fails again, the effect count
   stays three (the shape of §11 test 8).

```
broker embedded nats://127.0.0.1:50564, database embedded, ready in 16.611s
step 1: service user "app" publishing orders.event.order.placed.v1 directly -> nats: permissions violation: Permissions Violation for Publish to "orders.event.order.placed.v1"
step 2: 3 orders committed, outbox unpublished=3, broker connections by the service=0
step 3: relay pass 1 published 1 row(s) then crashed before marking ce9726a5-7b0a-4047-b9ce-86d70947f625
step 3: relay pass 2 (unpublished before=3) published 3, broker answered duplicate=1, stream messages=3, unpublished after=0
step 6: delivery 1 of 3 failed (event c3558881-261b-4ad6-98fa-c37d492068a7: cannot grant credits, payload names no sku) -> nak
step 6: delivery 2 of 3 failed (event c3558881-261b-4ad6-98fa-c37d492068a7: cannot grant credits, payload names no sku) -> nak
step 6: delivery 3 of 3 failed (event c3558881-261b-4ad6-98fa-c37d492068a7: cannot grant credits, payload names no sku) -> nak
step 6: consumer "demo-orders" applied=3 effects_in_db=3 poison_deliveries=3
dlq: advisory MAX_DELIVERIES -> copied to orders.dlq.order.placed.v1, stream ORDERS_DLQ messages=1
step 7: replay from the start delivered=4 applied=0 failed_again=1 effects_in_db=3
ok demo advanced trace=1f4a5abd67a072cabda2551d90e0ff1b
```

## What it is not yet

The payload is JSON; the protobuf schema and `buf breaking` gate arrive with CP3. The four NATS
users carry local-only passwords; on the cluster they are nsc-issued JWTs from the vault (D4). The
demo is a command, not yet the portal button of CP10.
