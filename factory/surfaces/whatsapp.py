import os, json, hashlib, time, logging, urllib.parse, base64
from pathlib import Path
from .base import Surface
from .. import llm, ledger
from ..net import open_https, https_request

log = logging.getLogger("factory.surfaces.whatsapp")


class WhatsAppSurface(Surface):
    id = "whatsapp"

    def __init__(self):
        self.sid = os.environ.get("TWILIO_ACCOUNT_SID")
        self.token = os.environ.get("TWILIO_AUTH_TOKEN")
        self.from_ = os.environ.get("TWILIO_WHATSAPP_FROM")

    def _auth(self):
        return "Basic " + base64.b64encode(f"{self.sid}:{self.token}".encode()).decode()

    def intake(self):
        for f in sorted(Path("queue/whatsapp_in").glob("*.json")):
            try:
                payload = json.loads(f.read_text())
            except Exception as e:
                log.debug("whatsapp inbox %s unparseable: %s", f, e)
                f.unlink()
                continue
            f.unlink()
            text = payload.get("Body") or payload.get("text", "")
            sender = (payload.get("From") or "").replace("whatsapp:", "")
            if not text:
                continue
            p = llm.decompose(text, tenant=f"per_{sender}")
            oid = (
                "ord_"
                + hashlib.sha256(f"wa:{sender}:{time.time()}".encode())
                .hexdigest()[:26]
                .upper()
            )
            return {
                "order_id": oid,
                "tenant_id": f"per_{sender}",
                "goal": p["goal"],
                "capabilities": p["capabilities"],
                "chat_id": sender,
                "surface": self.id,
                "raw": text,
            }
        return None

    def deliver(self, order, message):
        if not (self.sid and self.token and self.from_ and order.get("chat_id")):
            return {"delivered": False, "reason": "TWILIO_NOT_CONFIGURED"}
        to = order["chat_id"]
        if not to.startswith("whatsapp:"):
            to = f"whatsapp:{to}"
        url = f"https://api.twilio.com/2010-04-01/Accounts/{self.sid}/Messages.json"
        body = urllib.parse.urlencode(
            {"From": self.from_, "To": to, "Body": message}
        ).encode()
        delay, last = 1.0, ""
        for attempt in range(5):
            try:
                req = https_request(
                    url,
                    method="POST",
                    data=body,
                    headers={
                        "Authorization": self._auth(),
                        "Content-Type": "application/x-www-form-urlencoded",
                    },
                )
                with open_https(req, timeout=30) as r:
                    resp = json.loads(r.read())
                if resp.get("sid"):
                    ledger.write(
                        "deliveries",
                        {
                            "order_id": order["order_id"],
                            "surface": self.id,
                            "delivered": True,
                            "message_sid": resp["sid"],
                            "attempt": attempt + 1,
                        },
                    )
                    return {"delivered": True, "message_sid": resp["sid"]}
                last = f"twilio_no_sid: {resp.get('message')}"
            except Exception as e:
                last = type(e).__name__
            time.sleep(min(delay, 30))
            delay *= 2
        ledger.write(
            "dead_letters",
            {"order_id": order["order_id"], "surface": self.id, "error": last},
        )
        return {"delivered": False, "reason": last}

    def receipt(self):
        d = Path("queue/whatsapp_receipts")
        d.mkdir(parents=True, exist_ok=True)
        for f in sorted(d.glob("*.json")):
            try:
                payload = json.loads(f.read_text())
            except Exception as e:
                log.debug("whatsapp receipt %s unparseable: %s", f, e)
                f.unlink()
                continue
            f.unlink()
            oid = payload.get("order_id")
            if not oid:
                continue
            verdict = "ok" if payload.get("status") in ("delivered", "read") else "bad"
            ledger.write(
                "receipts",
                {
                    "order_id": oid,
                    "surface": self.id,
                    "verdict": verdict,
                    "engagement": 1.0 if verdict == "ok" else 0.5,
                },
            )
            return {"order_id": oid, "verdict": verdict}
        return None
