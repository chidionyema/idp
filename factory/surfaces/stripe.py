import os, json, urllib.request, urllib.parse
from .http_webhook_base import HTTPWebhookSurface
from .. import ledger


class StripeSurface(HTTPWebhookSurface):
    id = "stripe"

    def parse(self, payload):
        t = payload.get("type", "")
        obj = payload.get("data", {}).get("object", {})
        # Only meaningful events become needs
        if t not in (
            "charge.succeeded",
            "invoice.paid",
            "payment_intent.succeeded",
            "customer.subscription.created",
            "customer.subscription.deleted",
        ):
            return None
        amount = obj.get("amount", 0) / 100.0
        currency = (obj.get("currency") or "usd").upper()
        expr = f"record event {t} amount {currency}{amount} customer {obj.get('customer', 'unknown')}"
        return (expr, obj.get("customer", "stripe_customer"))

    def deliver(self, order, message):
        # Stripe has no outbound channel; log only
        ledger.write(
            "deliveries",
            {
                "order_id": order["order_id"],
                "surface": self.id,
                "delivered": True,
                "note": "recorded only — no outbound",
            },
        )
        return {"delivered": True, "note": "recorded_only"}
