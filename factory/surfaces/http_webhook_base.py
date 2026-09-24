from __future__ import annotations

import json, hmac, hashlib, os, time
from pathlib import Path
from .base import Surface
from .. import llm, ledger

INBOX = Path("queue/webhook_inbox")
INBOX.mkdir(parents=True, exist_ok=True)


class HTTPWebhookSurface(Surface):
    """Subclass overrides: id, parse(payload) -> (expression, chat_id)."""

    def __init__(self):
        self.secret = os.environ.get(f"{self.id.upper()}_WEBHOOK_SECRET")

    def verify(self, raw: bytes, headers: dict) -> bool:
        if not self.secret:
            return True
        sig = headers.get("X-Signature") or headers.get("X-Hub-Signature-256", "")
        expected = (
            "sha256=" + hmac.new(self.secret.encode(), raw, hashlib.sha256).hexdigest()
        )
        return hmac.compare_digest(sig, expected)

    def parse(self, payload: dict) -> tuple[str, str] | None:
        """Return (expression, chat_id) or None to ignore."""
        raise NotImplementedError

    def intake(self):
        files = sorted(INBOX.glob(f"{self.id}_*.json"))
        if not files:
            return None
        f = files[0]
        try:
            data = json.loads(f.read_text())
        except Exception:
            f.unlink()
            return None
        f.unlink()
        parsed = self.parse(data.get("payload", {}))
        if not parsed:
            return None
        expression, chat_id = parsed
        p = llm.decompose(expression, tenant=f"per_{chat_id}")
        oid = (
            "ord_"
            + hashlib.sha256(f"{self.id}:{time.time()}".encode())
            .hexdigest()[:26]
            .upper()
        )
        return {
            "order_id": oid,
            "tenant_id": f"per_{chat_id}",
            "goal": p["goal"],
            "capabilities": p["capabilities"],
            "chat_id": chat_id,
            "surface": self.id,
            "raw": expression,
        }

    def receipt(self):
        return None
