# 11. Money never enters the application

Date: 2026-08-29
Status: Accepted (layer built dark; the cutover is a separate decision)

## Context

The founder, 2026-08-29:

> we ban money from the application logic entirely ... The .NET API should not know what a
> credit card is, it should not generate Stripe Checkout sessions, and it absolutely should not
> parse Stripe webhooks ... deploy a Universal Commerce Primitive as a firewall between the
> internet's money and your application's logic.

and, the same day:

> also we want user subscriptions also

What was measured on 2026-08-29 in `prospector-main/store_platform/src/Store.Api`:

- `Payments/StripeProvider.cs` opens `using Stripe; using Stripe.Checkout;`. The application
  holds the SDK and builds Checkout Sessions.
- The same file reads `Stripe:ApiKey` and `Stripe:WebhookSecret` from its own configuration.
- Lines 53-65 read the `Stripe-Signature` header and call `EventUtility.ConstructEvent`. The
  application is the webhook parser. `Endpoints/WebhookEndpoints.cs` is its route.
- The Flux tree had no commerce primitive and no event bus of any kind.

So the application is the money layer today, which is exactly what is being banned.

## Decision

One primitive owns the money: **Lago** (`lago` chart 1.28.0, app 1.32.4). It holds the payment
provider SDK and secrets, verifies webhook signatures, writes revenue to its own database, and
publishes a generic event onto an internal **NATS JetStream** bus. Nothing downstream ever
speaks to a payment provider.

Lago rather than the alternatives, because the requirement is packs *and* subscriptions, and
Lago's own OpenAPI contract carries both as first-class endpoints:

| Need | Lago endpoint |
|---|---|
| subscription to a plan | `/subscriptions`, `/subscriptions/{id}/entitlements` |
| prepaid credit pack (`100_ai_credits`) | `/wallets`, `/wallet_transactions` |
| the Checkout URL for a pack | `/wallet_transactions/{id}/payment_url` |
| the Checkout URL for a subscription invoice | `/invoices/{id}/payment_url` |

- **Medusa** was the first answer, before subscriptions were asked for. It is a cart-and-order
  engine: packs yes, subscriptions only through a community plugin or a module we would write.
  That is the half-stitched solution, so the requirement change ended it.
- **Kill Bill** does subscriptions, but has no prepaid-credit wallet and is a JVM plus Kaui plus
  its own database. Two tools instead of one, on a 4-6 OCPU node.

The bus is NATS JetStream, not Kafka, Redpanda or RabbitMQ: at-least-once delivery and replay
from one StatefulSet and a 2Gi volume (LAW 23, take the smaller road when both arrive).
Flux's own notification-controller was rejected outright: it carries GitOps events, and routing
revenue through the GitOps controller couples money to the deployment system.

## Consequences

- The .NET API's role shrinks to reading its own database. It gets no payment credential, and
  the payment credential is namespaced to `commerce`, so re-adding the SDK to `Store.Api` would
  not give it access.
- The event contract is fixed and versioned in
  `platform/event-bus/contract/estate.commerce.order_paid.json`, the founder's payload verbatim.
- This is the estate's seventh Postgres, against a stated target of one
  (`platform/features/features.yaml`, `shared.postgres`). A money ledger is the last database
  that should join a shared instance, so consolidation excludes it.
- Everything above is **suspended** in `clusters/oke/commerce.yaml`. Nothing runs, nothing is
  routed, no live money moves. Cutover is its own decision and its own PR, on the founder's word
  (LAW 11): real cards, a live account, and an in-flight webhook stream cannot be undone alone.
