import os
import uuid
from .base import Surface
from .. import llm, ledger


class CLISurface(Surface):
    id = "cli"

    def intake(self):
        expr = os.environ.get("FACTORY_EXPRESSION")
        if not expr:
            return None
        parsed = llm.decompose(expr, tenant="per_local")
        oid = "ord_" + uuid.uuid4().hex[:26].upper()
        return {
            "order_id": oid,
            "tenant_id": "per_local",
            "goal": parsed["goal"],
            "capabilities": parsed["capabilities"],
            "surface": self.id,
            "raw": expr,
        }

    def deliver(self, order, message):
        print(f"[cli:{order['order_id']}] {message}")
        ledger.write(
            "deliveries",
            {"order_id": order["order_id"], "surface": self.id, "delivered": True},
        )
        return {"delivered": True}
