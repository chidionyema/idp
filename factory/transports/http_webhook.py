"""A surface that pushes events to us over HTTP. We mount a FastAPI/Flask handler.
Everything from Telegram to Stripe is this."""

import json, os, hmac, hashlib
from pathlib import Path
from datetime import datetime, timezone
from ..ledger import write as ledger_write

INBOX = Path("queue/http_inbox")
INBOX.mkdir(parents=True, exist_ok=True)


def ingest(surface_id: str, raw_body: bytes, headers: dict) -> dict:
    """Called by the HTTP server. Writes to inbox and returns a receipt."""
    secret = os.environ.get(f"{surface_id.upper()}_WEBHOOK_SECRET")
    if secret:
        sig = headers.get("X-Signature") or headers.get("X-Hub-Signature-256", "")
        expected = (
            "sha256=" + hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
        )
        if not hmac.compare_digest(sig, expected):
            ledger_write(
                "errors",
                {"where": "webhook", "surface": surface_id, "err": "sig mismatch"},
            )
            return {"ok": False, "reason": "signature"}
    try:
        payload = json.loads(raw_body)
    except Exception:
        payload = {"raw": raw_body.decode(errors="ignore")}
    fname = INBOX / f"{surface_id}_{datetime.now(timezone.utc).timestamp():.6f}.json"
    fname.write_text(json.dumps({"surface": surface_id, "payload": payload}))
    return {"ok": True, "queued": str(fname)}
